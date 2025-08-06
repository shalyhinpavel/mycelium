# File: run_multi_user_demo.py
#
# ADVANCED Comparative Demo Stand with SESSION ISOLATION
# Each user who opens the application gets their own memory.
import os
import gradio as gr
import uuid
import httpx
from dotenv import load_dotenv
from mycelium_gateway.state import HubStateManager
from mycelium_gateway.gateway import CogGateway
from mycelium_gateway.adaptive_parser import AdaptiveSemanticParser
from mycelium_gateway.adapters import TogetherAIAdapter
from config import MODEL_NAME

# --- Global setup (components that do not depend on the session) ---
load_dotenv()
API_KEY = os.getenv("TOGETHER_AI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
HF_REPO_ID = "shalyhinpavel/mycelium"
API_URL = "https://api.together.xyz/v1/chat/completions"
if not API_KEY:
    raise ValueError("TOGETHER_AI_API_KEY must be set in .env file.")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN must be set in .env or Gradio secrets.")

# These objects are created once, they are stateless (do not store session state)
parser = AdaptiveSemanticParser()
state_manager = HubStateManager(repo_id=HF_REPO_ID)
engine = TogetherAIAdapter(
    api_key=API_KEY, model_name=MODEL_NAME, parser=parser)
gateway = CogGateway(engine=engine, state_manager=state_manager)

# --- Handler functions for Gradio ---
# Handler for the "Mycelium" tab


async def mycelium_respond(message, chat_history, session_state):
    # session_state is our "memory" for this specific user.
    # If it is empty, this is the first request from this user.
    if session_state is None:
        session_state = f"mycelium-user-{uuid.uuid4()}"
        print(f"New Mycelium session created: {session_state}")
    response = await gateway.process(message, session_state)
    chat_history.append((message, response))
    # We must return both the history and the updated session state
    return "", chat_history, session_state

# Handler for the "Naked Model" tab


async def naked_respond(message, chat_history, history_state):
    # history_state stores the history in API format for this specific user
    if history_state is None:
        history_state = []
        print("New Naked session created.")
    # Adding the current user message
    history_state.append({"role": "user", "content": message})
    response = await call_naked_llm(history_state)
    # Adding the model response to the API history
    history_state.append({"role": "assistant", "content": response})
    # Adding to the history for display in Gradio
    chat_history.append((message, response))
    return "", chat_history, history_state

# Helper function for "Naked Model"


async def call_naked_llm(chat_history):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {"model": MODEL_NAME,
               "messages": chat_history, "temperature": 0.7}
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

# --- Creating and launching the Interface ---
with gr.Blocks() as demo:
    gr.Markdown("# Comparative Demo Stand (Multi-user)")
    gr.Markdown(f"**Model being tested:** `{MODEL_NAME}`")
    with gr.Tab("Mycelium (Cognitive Enhancer)"):
        # `gr.State()` is an invisible component for storing session data
        mycelium_session = gr.State(None)
        mycelium_chatbot = gr.Chatbot(label="Dialog with Mycelium")
        mycelium_msg = gr.Textbox(label="Your request")
        mycelium_clear = gr.Button("Clear history (Mycelium)")
    with gr.Tab("Naked Model (Control Group)"):
        naked_history = gr.State(None)
        naked_chatbot = gr.Chatbot(label="Dialog with Naked Model")
        naked_msg = gr.Textbox(label="Your request")
        naked_clear = gr.Button("Clear history (Naked Model)")
    # Binding handlers, passing them State
    mycelium_msg.submit(mycelium_respond,
                        inputs=[mycelium_msg, mycelium_chatbot,
                                mycelium_session],
                        outputs=[mycelium_msg, mycelium_chatbot, mycelium_session])
    mycelium_clear.click(lambda: (None, None), None, [
                         mycelium_chatbot, mycelium_session], queue=False)
    naked_msg.submit(naked_respond,
                     inputs=[naked_msg, naked_chatbot, naked_history],
                     outputs=[naked_msg, naked_chatbot, naked_history])
    naked_clear.click(lambda: (None, None), None, [
                      naked_chatbot, naked_history], queue=False)

if __name__ == "__main__":
    print(f"--- Launching Comparative Demo Stand with Session Isolation ---")
    print(f"Model being used (from config.py): {MODEL_NAME}")
    demo.launch()
