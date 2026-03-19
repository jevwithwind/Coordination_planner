import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CHAT_API_KEY = os.getenv("CHAT_API_KEY")
QWEN_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
QWEN_MODEL = "qwen3-coder-plus"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# Validate that required API keys are present
if not CHAT_API_KEY:
    raise ValueError("CHAT_API_KEY environment variable not set")