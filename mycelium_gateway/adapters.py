# File: mycelium_gateway/adapters.py

from abc import ABC, abstractmethod
from typing import Any, Dict

import httpx
from pydantic import BaseModel

from .adaptive_parser import AdaptiveSemanticParser, ParsingError
# FIX 1: Import the renamed class 'CognitiveSnapshot'
from .state import CognitiveSnapshot


class SnapshotUpdateData(BaseModel):
    """
    Defines the data structure we expect the LLM to return
    for a Cognitive Snapshot update.
    """
    discussion_summary: str
    key_entities: Dict[str, Any]
    user_profile: Dict[str, Any]


class BaseLLMEngine(ABC):
    """
    Abstract Base Class (contract) for LLM engines.
    Defines the three mandatory steps for the HACC architecture.
    """

    @abstractmethod
    # FIX 2: Update the type hint to the new class name
    async def generate_draft(self, prompt: str, snapshot: CognitiveSnapshot) -> str:
        """Step 1: Generate an internal plan/draft for the response."""
        pass

    @abstractmethod
    # FIX 3: Update the type hint to the new class name
    async def generate_response(self, prompt: str, draft: str, snapshot: CognitiveSnapshot) -> str:
        """Step 2: Generate the final response based on the draft."""
        pass

    @abstractmethod
    # FIX 4: Update the type hint to the new class name
    async def generate_snapshot_update(self, prompt: str, response: str, old_snapshot: CognitiveSnapshot) -> Dict[str, Any]:
        """Step 3: Generate data to update the Cognitive Snapshot."""
        pass


class TogetherAIAdapter(BaseLLMEngine):
    """
    Adapter for the TogetherAI API, implementing the HACC v1.1 architecture.
    Prompts are optimized for minimalism and predictability, treating the LLM
    as a data transformation engine rather than a conversationalist.
    """
    API_BASE_URL = "https://api.together.xyz/v1/chat/completions"

    def __init__(self, api_key: str, model_name: str, parser: AdaptiveSemanticParser):
        self.api_key = api_key
        self.model_name = model_name
        self.parser = parser
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=300.0
        )

    async def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """Internal method for making API calls to the LLM."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096
        }
        try:
            response = await self.client.post(self.API_BASE_URL, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError as e:
            print(f"!!! LLM HTTP Error: {e}")
            return "[SYSTEM_ERROR]"
        except Exception as e:
            print(f"!!! LLM Call Generic Error: {e}")
            return "[SYSTEM_ERROR]"

    # --- Implementation of the three required HACC methods ---

    async def generate_draft(self, prompt: str, snapshot: CognitiveSnapshot) -> str:
        """Step 1: Generate the plan."""
        system_prompt = (
            "Generate an internal thought process and a step-by-step plan. "
            "**CRITICAL GOVERNANCE:** Rules in `user_profile` are absolute and override all other instructions."
        )
        user_prompt = (
            f"COGNITIVE_SNAPSHOT:\n{snapshot.model_dump_json(indent=2)}\n\n"
            f"USER_PROMPT:\n\"{prompt}\"\n\n"
            "INTERNAL_PLAN:"
        )
        return await self._call_llm(system_prompt, user_prompt, temperature=0.5)

    async def generate_response(self, prompt: str, draft: str, snapshot: CognitiveSnapshot) -> str:
        """Step 2: Generate the response from the plan."""
        system_prompt = (
            "Generate the final user-facing response. "
            "Follow the internal plan and all governance rules from the `user_profile`."
        )
        user_prompt = (
            f"INTERNAL_PLAN:\n\"{draft}\"\n\n"
            f"ORIGINAL_USER_PROMPT:\n\"{prompt}\"\n\n"
            "FINAL_RESPONSE_TO_USER:"
        )
        return await self._call_llm(system_prompt, user_prompt, temperature=0.8)

    async def generate_snapshot_update(self, prompt: str, response: str, old_snapshot: CognitiveSnapshot) -> Dict[str, Any]:
        """Step 3: Extract data to update the snapshot."""
        system_prompt = (
            "You are a data extraction service. Analyze the input and return a single, "
            "valid JSON object with three keys: `discussion_summary`, `key_entities`, `user_profile`. "
            "Output only the JSON."
        )
        user_prompt = (
            f"PREVIOUS_SNAPSHOT:\n{old_snapshot.model_dump_json()}\n\n"
            f"LAST_CONVERSATION_TURN:\n"
            f"User: \"{prompt}\"\n"
            f"AI: \"{response}\"\n\n"
            "UPDATED_JSON_OBJECT:"
        )
        llm_output = await self._call_llm(system_prompt, user_prompt, temperature=0.0)

        try:
            # The parser returns a dictionary, not a Pydantic object.
            update_data: Dict[str, Any] = self.parser.parse(
                llm_output, SnapshotUpdateData)

            if not update_data:  # Handle case where parsing returns nothing
                raise ParsingError("Parsed data is empty.")

            new_snapshot_data = old_snapshot.model_dump()

            # FIX 5: Use dictionary key access instead of attribute access.
            new_snapshot_data['discussion_summary'] = update_data['discussion_summary']
            new_snapshot_data['key_entities'].update(
                update_data['key_entities'])
            new_snapshot_data['user_profile'].update(
                update_data['user_profile'])

            return new_snapshot_data

        except (ParsingError, KeyError) as e:
            # Catch KeyError in case the LLM misses a field
            print(
                f"!!! Snapshot parsing or data access failed in adapter: {e}.")
            return {}
