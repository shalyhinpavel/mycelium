# -*- coding: utf-8 -*-
"""
adaptive_parser.py - Проект "Феникс", Компонент "Цербер" v1.4 (Final)

Изменения:
- Восстановлен полный каскад парсинга для максимальной устойчивости.
- Сначала ищем JSON в Markdown, потом пытаемся парсить напрямую,
  и только потом переходим к семантическому извлечению.
"""
import json
import re
from pydantic import BaseModel, ValidationError
from typing import Type, Dict, Any, List, Optional


class ParsingError(Exception):
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context if context is not None else {}


class AdaptiveSemanticParser:

    def __init__(self):
        # Компилируем паттерн для Markdown заранее
        self.json_block_pattern = re.compile(
            r"```(?:json)?\s*\n({.*?})\n\s*```", re.DOTALL)

    def _clean_value(self, value: str) -> str:
        # Убираем кавычки
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        # Убираем точку в конце для чисел
        if value.endswith('.') and value[:-1].replace('.', '', 1).isdigit():
            value = value[:-1]
        return value

    def _validate_and_dump(self, data: Any, schema: Type[BaseModel]) -> Dict[str, Any]:
        """Вспомогательная функция для валидации и возврата данных."""
        validated_model = schema.model_validate(data)
        return validated_model.model_dump()

    def _parse_semantic(self, text: str, schema: Type[BaseModel]) -> Dict[str, Any]:
        """Финальный слой: семантическое извлечение из естественного текста."""
        extracted_data: Dict[str, Any] = {}
        schema_fields = schema.model_fields

        for field_name in schema_fields.keys():
            pattern = re.compile(
                rf"\b{re.escape(field_name)}\b\s*:\s*(.*)", re.IGNORECASE)
            matches = pattern.findall(text)
            if matches:
                cleaned_value = self._clean_value(matches[-1].strip())
                extracted_data[field_name] = cleaned_value

        if not extracted_data:
            raise ParsingError("Semantic layer could not extract any fields.")

        return self._validate_and_dump(extracted_data, schema)

    def parse(self, raw_llm_output: str, expected_schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        Главный метод, который пропускает вывод LLM через полный каскад парсеров.
        """
        if not raw_llm_output or not raw_llm_output.strip():
            raise ParsingError("Input text from LLM is empty or whitespace.")

        # --- Слой 1: Поиск и извлечение JSON из блоков Markdown ---
        match = self.json_block_pattern.search(raw_llm_output)
        if match:
            json_str = match.group(1)
            try:
                # Пытаемся распарсить извлеченный JSON
                return self._validate_and_dump(json.loads(json_str), expected_schema)
            except (json.JSONDecodeError, ValidationError) as e:
                # Если даже он сломан, мы не сдаемся, а передаем его дальше
                raw_llm_output = json_str

        # --- Слой 2: Прямой парсинг (если это был чистый JSON или извлеченный, но сломанный) ---
        try:
            return self._validate_and_dump(json.loads(raw_llm_output), expected_schema)
        except (json.JSONDecodeError, ValidationError):
            pass

        # --- Слой 3 (Финальный): Семантическое извлечение из текста ---
        try:
            return self._parse_semantic(raw_llm_output, expected_schema)
        except (ParsingError, ValidationError) as e:
            # Если даже семантика не помогла, значит, это конец.
            raise ParsingError(
                "Failed to parse or validate LLM output after all layers.",
                context={"final_error": str(e)}
            )
