# File: mycelium_gateway/gateway.py

import asyncio
from typing import Optional
from datetime import datetime, timezone
from .state import CognitiveSnapshot, HubStateManager
from .adapters import BaseLLMEngine


class CogGateway:
    """
    Orchestrates the Asynchronous Cognitive Cycle (HACC).
    """

    def __init__(self, engine: BaseLLMEngine, state_manager: HubStateManager):
        self.engine = engine
        self.state_manager = state_manager
        # A reference to the background snapshot update task.
        self.reflection_task: Optional[asyncio.Task] = None

    async def _reflection_worker(self, prompt: str, response: str, old_snapshot: CognitiveSnapshot):
        """A background worker that updates the cognitive snapshot."""
        print(" -> Step 3 (Async): Beginning cognitive reflection...")
        new_data = await self.engine.generate_snapshot_update(prompt, response, old_snapshot)

        if new_data:
            # The engine returns a complete dictionary; create the new snapshot.
            # We explicitly set last_updated to the time of this successful update.
            new_data['last_updated'] = datetime.now(timezone.utc)
            new_snapshot = CognitiveSnapshot(**new_data)
            self.state_manager.save_snapshot(new_snapshot)
            print(" <- Step 3 (Async): Snapshot update complete.")
        else:
            print(" <- Step 3 (Async): Snapshot update failed, state was not saved.")

    async def process(self, user_prompt: str, session_id: str) -> str:
        """Executes the asynchronous cognitive cycle."""
        print(f"\n--- CYCLE START (Session: {session_id}) ---")

        # Ensure the previous cycle's reflection is finished before loading new state.
        if self.reflection_task and not self.reflection_task.done():
            print("...Waiting for previous reflection to complete...")
            await self.reflection_task
            print("...Reflection complete. Proceeding with fresh state.")

        current_snapshot = self.state_manager.load_snapshot(session_id)
        print(
            f"Loaded snapshot v{current_snapshot.version} from {current_snapshot.last_updated.isoformat()}")

        # === STEP 1: GENERATE DRAFT ===
        print(" -> Step 1: Generating internal draft...")
        internal_draft = await self.engine.generate_draft(user_prompt, current_snapshot)
        print(" <- Step 1: Draft complete.")

        # === STEP 2: GENERATE RESPONSE ===
        print(" -> Step 2: Generating final response...")
        final_response = await self.engine.generate_response(user_prompt, internal_draft, current_snapshot)
        print(" <- Step 2: Response complete.")

        # === STEP 3: ASYNCHRONOUS REFLECTION ===
        # Start the snapshot update process in the background.
        self.reflection_task = asyncio.create_task(
            self._reflection_worker(
                user_prompt, final_response, current_snapshot)
        )

        print(f"--- CYCLE END (Response returned, reflection running in background) ---\n")
        return final_response
