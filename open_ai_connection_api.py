import os 
from openai import OpenAI
from dotenv import load_dotenv
import re
import logging

# Load API Key
load_dotenv(override=True)

# Log file
LOG_FILENAME = "case_analysis.log"

# Setup Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(LOG_FILENAME, mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)
logging.StreamHandler()

# Define character limit for GPT-3.5 Turbo
CHAR_LIMIT = 11000

class OpenAIClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OpenAI API Key. Set OPENAI_API_KEY in environment variables.")
        
        self.client = OpenAI(api_key=api_key)

    def set_prompt(self, prompt):
        if not prompt:
            raise ValueError("Missing Prompt")
        if not isinstance(prompt, str):
            raise ValueError("Prompt is not a text")

        self._prompt = prompt

    def get_prompt(self):
        return self._prompt

    # Set Max tokens for GPT 3.5
    def analyze_text(self, messages, max_tokens=600):
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0,
                max_tokens=max_tokens
            )
            result = response.choices[0].message.content.strip()
            return result if result else None
        except Exception as e:
            raise ValueError(f"OpenAI API error: {str(e)}")

ai_client = OpenAIClient()
