import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Dict, Any
# Добавляем импорты для Hugging Face Hub
from huggingface_hub import HfApi, HfFolder, hf_hub_download
from huggingface_hub.errors import HfHubHTTPError


class CognitiveSnapshot(BaseModel):
    """
    Represents the cognitive state of a session. Version 1.0.
    """
    version: str = "1.0"
    session_id: str
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    discussion_summary: str = Field(
        default="Dialogue has just begun.",
        description="A brief, rolling summary of the entire dialogue.")
    key_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key entities, facts, and statements extracted from the dialogue.")
    user_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="Inferred user goals, knowledge, and communication style, including governance rules.")


class HubStateManager:
    """
    Управляет состоянием снимков, сохраняя их в репозиторий на Hugging Face Hub.
    """

    def __init__(self, repo_id: str, repo_type: str = "dataset", local_dir: str = ".cogn_snapshots_cache"):
        """
        Инициализирует менеджер состояния для работы с Hugging Face Hub.
        Args:
        repo_id (str): ID репозитория на Hugging Face (например, "YourUsername/MyceliumSnapshots").
        repo_type (str): Тип репозитория ('dataset', 'space', 'model'). По умолчанию 'dataset'.
        local_dir (str): Локальная папка для кэширования файлов.
        """
        # Убедимся, что токен доступен. На Gradio Spaces он будет из Secrets.
        token = os.getenv("HF_TOKEN")
        if not token:
            # Пытаемся получить токен, сохраненный через `huggingface-cli login`
            token = HfFolder.get_token()
        if not token:
            raise ValueError(
                "Токен Hugging Face не найден. Установите переменную окружения HF_TOKEN.")
        self.api = HfApi(token=token)
        self.repo_id = repo_id
        self.repo_type = repo_type
        self.local_cache_path = Path(local_dir)
        self.local_cache_path.mkdir(parents=True, exist_ok=True)
        # Проверяем, существует ли репозиторий, и создаем его, если нет.
        self.api.create_repo(
            self.repo_id, repo_type=self.repo_type, exist_ok=True)
        print(
            f"State Manager подключен к репозиторию '{self.repo_id}' на Hugging Face Hub.")

    def _get_remote_path(self, session_id: str) -> str:
        """Возвращает путь к файлу в репозитории."""
        return f"snapshots/{session_id}.json"

    def load_snapshot(self, session_id: str) -> CognitiveSnapshot:
        """
        Загружает снимок из репозитория на Hub или создает новый.
        """
        remote_path = self._get_remote_path(session_id)
        try:
            # Скачиваем файл из репозитория
            local_file_path = hf_hub_download(
                repo_id=self.repo_id,
                repo_type=self.repo_type,
                filename=remote_path,
                local_dir=self.local_cache_path,
            )
            with open(local_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Снимок для сессии '{session_id}' успешно загружен с Hub.")
            return CognitiveSnapshot(**data)
        except HfHubHTTPError as e:
            # Если файл не найден (404), это новая сессия.
            if e.response.status_code == 404:
                print(
                    f"Снимок для сессии '{session_id}' не найден на Hub. Создается новый.")
                return CognitiveSnapshot(session_id=session_id)
            else:
                # Другие ошибки HTTP (например, проблемы с авторизацией)
                print(f"Ошибка при загрузке снимка с Hub: {e}")
                raise

    def save_snapshot(self, snapshot: CognitiveSnapshot):
        """
        Сохраняет снимок, загружая его в репозиторий на Hub.
        """
        remote_path = self._get_remote_path(snapshot.session_id)
        # Сохраняем во временный локальный файл
        temp_local_path = self.local_cache_path / \
            f"{snapshot.session_id}.json.tmp"
        with temp_local_path.open('w', encoding='utf-8') as f:
            f.write(snapshot.model_dump_json(indent=2))
        # Загружаем файл на Hub
        self.api.upload_file(
            path_or_fileobj=str(temp_local_path),
            path_in_repo=remote_path,
            repo_id=self.repo_id,
            repo_type=self.repo_type,
            commit_message=f"Update snapshot for session {snapshot.session_id}"
        )
        print(
            f"Снимок для сессии '{snapshot.session_id}' успешно сохранен на Hub.")
        # Удаляем временный файл
        temp_local_path.unlink()
