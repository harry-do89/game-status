import os
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Fix for relative credentials path when running from scripts/ directory
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if creds_path and not os.path.isabs(creds_path):
    # Assume it's relative to project root (one level up from scripts/)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    abs_creds_path = os.path.join(root_dir, creds_path)
    if os.path.exists(abs_creds_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_creds_path
        logging.info(f"Resolved relative GOOGLE_APPLICATION_CREDENTIALS to: {abs_creds_path}")

GCP_PROJECT = os.getenv("GCP_PROJECT")
# The new SDK handles location and project at the client level
# Global endpoint is recommended for Agent Platform models
client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT,
    location="global"
)

def ask(prompt: str) -> str:
    """Uses the new Gemini Enterprise Agent Platform SDK to generate content."""
    # Using gemini-2.5-flash which is confirmed to be available in the global region
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.1
        )
    )
    
    if not response.candidates:
        raise RuntimeError("Gemini returned no candidates — content may have been blocked")

    finish_reason = response.candidates[0].finish_reason
    if finish_reason != "STOP":
        logging.warning(f"Unusual finish reason: {finish_reason} | response: {response}")

    if not response.text:
        raise RuntimeError(f"Gemini returned empty text (finish_reason={finish_reason})")

    return response.text
