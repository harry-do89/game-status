import os
import json
import re
import hmac
import logging
from flask import abort


def verify_key(request):
    """Checks X-Agent-Key header matches AGENT_KEY from .env using constant-time comparison."""
    agent_key = os.getenv("AGENT_KEY", "")
    provided = request.headers.get("X-Agent-Key", "")
    if not hmac.compare_digest(provided, agent_key):
        abort(401)


def load_prompt(name, **kwargs):
    """Loads a prompt from file and replaces {{key}} placeholders."""
    # Look for prompts directory relative to this file's parent
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "prompts", f"{name}.txt")
    
    if not os.path.exists(path):
        # Fallback for local dev if run from root
        path = os.path.join("prompts", f"{name}.txt")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt file {path} not found")

    with open(path, "r") as f:
        content = f.read()

    for key, value in kwargs.items():
        placeholder = f"{{{{{key}}}}}"
        content = content.replace(placeholder, str(value))

    return content


def parse_gemini_json(text):
    """Extracts and parses JSON from Gemini response."""
    if not text:
        return {}
    try:
        text = text.strip()
        if text.startswith("```"):
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                text = text[start:end]

        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
        return {"error": "parse_failed", "raw": text}
    except Exception as e:
        logging.error(f"JSON parse error: {e} | input: {text[:200]}")
        return {"error": "parse_failed", "raw": text}


def format_request_type(raw: str) -> str:
    """Converts snake_case/kebab-case JSM request type names to Title Case."""
    if not raw or raw == "N/A":
        return raw
    return raw.replace("_", " ").replace("-", " ").title()


def sanitise(text, max_len=1000):
    """Sanitises input to prevent prompt injection and truncates to max_len."""
    if not isinstance(text, str):
        return str(text)

    text = re.sub(r"<[^>]+>", "", text)
    text = text[:max_len]

    patterns = [
        r"ignore\s+(?:all\s+)?(?:previous\s+|above\s+)?instructions",
        r"you are now",
        r"act as",
        r"disregard",
        r"override",
        r"system prompt",
        r"forget your",
        r"pretend (to be|you are)",
        r"from now on",
        r"your (new )?role is",
        r"roleplay",
        r"in this scenario",
        r"hypothetically",
        r"for (educational|research) purposes",
    ]

    for pattern in patterns:
        text = re.sub(pattern, "[removed]", text, flags=re.IGNORECASE)

    return text.strip()
