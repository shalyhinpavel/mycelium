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
# <<< CHANGE >>> Importing the list of models and the default model from the config
from config import AVAILABLE_MODELS, DEFAULT_MODEL

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

# These objects are created once; they do not store session state
parser = AdaptiveSemanticParser()
state_manager = HubStateManager(repo_id=HF_REPO_ID)
# <<< REMOVED >>> Global engine and gateway are no longer created here,
# as the model name is now dynamic. We will create them "on the fly" in the handler.

# --- Handler functions for Gradio ---
# Handler for the "Mycelium" tab

# <<< CHANGE >>> Adding 'selected_model' as an argument
async def mycelium_respond(message, chat_history, session_state, selected_model):
    if session_state is None:
        session_state = f"mycelium-user-{uuid.uuid4()}"
        print(f"New Mycelium session created: {session_state}")

    # <<< CHANGE >>> Creating instances 'on the fly' to use the selected model
    # This ensures that each call uses the model selected by the user
    engine = TogetherAIAdapter(
        api_key=API_KEY, model_name=selected_model, parser=parser)
    gateway = CogGateway(engine=engine, state_manager=state_manager)

    response = await gateway.process(message, session_state)
    chat_history.append((message, response))
    return "", chat_history, session_state

# Handler for the "Naked Model" tab

# <<< CHANGE >>> Adding 'selected_model' as an argument
async def naked_respond(message, chat_history, history_state, selected_model):
    if history_state is None:
        history_state = []
        print("New Naked session created.")

    history_state.append({"role": "user", "content": message})
    # <<< CHANGE >>> Passing the selected model to the helper function
    response = await call_naked_llm(history_state, selected_model)
    history_state.append({"role": "assistant", "content": response})
    chat_history.append((message, response))
    return "", chat_history, history_state

# Helper function for "Naked Model"

# <<< CHANGE >>> The function now accepts model_name
async def call_naked_llm(chat_history, model_name):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    # <<< CHANGE >>> Using the passed model name in the API request
    payload = {"model": model_name,
               "messages": chat_history, "temperature": 0.7}
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

# --- Creating and launching the Interface ---
with gr.Blocks() as demo:
    gr.Markdown("# Comparative Demo Stand (Multi-user with Model Selection)")

    # <<< CHANGE >>> UI for model selection
    with gr.Row():
        model_selector = gr.Dropdown(
            choices=AVAILABLE_MODELS,
            value=DEFAULT_MODEL,
            label="Select a model for testing"
        )
    # <<< CHANGE >>> State for storing the selected model
    model_name_state = gr.State(DEFAULT_MODEL)

    with gr.Tab("Mycelium (Cognitive Enhancer)"):
        mycelium_session = gr.State(None)
        mycelium_chatbot = gr.Chatbot(label="Dialog with Mycelium")
        mycelium_msg = gr.Textbox(label="Your request")
        mycelium_clear = gr.Button("Clear history (Mycelium)")

    with gr.Tab("Naked Model (Control Group)"):
        naked_history = gr.State(None)
        naked_chatbot = gr.Chatbot(label="Dialog with Naked Model")
        naked_msg = gr.Textbox(label="Your request")
        naked_clear = gr.Button("Clear history (Naked Model)")

    # <<< CHANGE >>> Handler for changing the model in the dropdown list
    # It updates the `model_name_state` when a new model is selected
    def update_model_selection(new_model_name):
        print(f"Session model changed to: {new_model_name}")
        return new_model_name

    model_selector.change(
        fn=update_model_selection,
        inputs=[model_selector],
        outputs=[model_name_state]
    )

    # <<< CHANGE >>> Binding handlers, passing them the state of the selected model
    mycelium_msg.submit(mycelium_respond,
                        inputs=[mycelium_msg, mycelium_chatbot,
                                mycelium_session, model_name_state],
                        outputs=[mycelium_msg, mycelium_chatbot, mycelium_session])

    mycelium_clear.click(lambda: (None, None), None, [
                         mycelium_chatbot, mycelium_session], queue=False)

    naked_msg.submit(naked_respond,
                     inputs=[naked_msg, naked_chatbot, naked_history, model_name_state],
                     outputs=[naked_msg, naked_chatbot, naked_history])

    naked_clear.click(lambda: (None, None), None, [
                      naked_chatbot, naked_history], queue=False)

if __name__ == "__main__":
    print(f"--- Launching Comparative Demo Stand with Session Isolation ---")
    print(f"Default model set to: {DEFAULT_MODEL}")
    demo.launch()