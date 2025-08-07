# -*- coding: utf-8 -*-
"""
adaptive_parser.py - Mycelium Project, "Phoenix" Component v1.4 (Final)

Changes:
- Restored the full parsing cascade for maximum robustness.
- First, we search for JSON in Markdown, then try to parse directly,
  and only then proceed to semantic extraction.
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
        # Pre-compile the pattern for Markdown
        self.json_block_pattern = re.compile(
            r"```(?:json)?\s*\n({.*?})\n\s*```", re.DOTALL)

    def _clean_value(self, value: str) -> str:
        # Remove quotes
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        # Remove a trailing dot for numbers
        if value.endswith('.') and value[:-1].replace('.', '', 1).isdigit():
            value = value[:-1]
        return value

    def _validate_and_dump(self, data: Any, schema: Type[BaseModel]) -> Dict[str, Any]:
        """Helper function to validate and return data."""
        validated_model = schema.model_validate(data)
        return validated_model.model_dump()

    def _parse_semantic(self, text: str, schema: Type[BaseModel]) -> Dict[str, Any]:
        """Final layer: semantic extraction from natural text."""
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
        The main method that passes LLM output through the full cascade of parsers.
        """
        if not raw_llm_output or not raw_llm_output.strip():
            raise ParsingError("Input text from LLM is empty or whitespace.")

        # --- Layer 1: Find and extract JSON from Markdown blocks ---
        match = self.json_block_pattern.search(raw_llm_output)
        if match:
            json_str = match.group(1)
            try:
                # Try to parse the extracted JSON
                return self._validate_and_dump(json.loads(json_str), expected_schema)
            except (json.JSONDecodeError, ValidationError) as e:
                # Even if it's broken, we don't give up and pass it on
                raw_llm_output = json_str

        # --- Layer 2: Direct parsing (if it was clean JSON or extracted but broken) ---
        try:
            return self._validate_and_dump(json.loads(raw_llm_output), expected_schema)
        except (json.JSONDecodeError, ValidationError):
            pass

        # --- Layer 3 (Final): Semantic extraction from text ---
        try:
            return self._parse_semantic(raw_llm_output, expected_schema)
        except (ParsingError, ValidationError) as e:
            # If even semantics didn't help, then it's the end.
            raise ParsingError(
                "Failed to parse or validate LLM output after all layers.",
                context={"final_error": str(e)}
            )