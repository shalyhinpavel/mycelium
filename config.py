# File: config.py

# --- SELECT YOUR MODELS HERE ---

# List of models that will be available in the dropdown list in the interface
AVAILABLE_MODELS = [
    "deepseek-ai/DeepSeek-V3",
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "openai/gpt-oss-120b",
    "mistralai/Mistral-7B-Instruct-v0.3"
]

# The model that will be selected by default when the application starts
DEFAULT_MODEL = AVAILABLE_MODELS[0]

# <<< REMOVED >>> The old MODEL_NAME variable is no longer needed
# MODEL_NAME = "deepseek-ai/DeepSeek-V2"

print(f"--- CONFIG LOADED: Default model is '{DEFAULT_MODEL}' ---")
print(f"--- Available models: {', '.join(AVAILABLE_MODELS)} ---")