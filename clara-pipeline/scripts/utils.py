"""
Shared utilities for Clara Pipeline.
Handles logging, file I/O, slugification, and common operations.
"""

import os
import re
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from slugify import slugify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs")))
RECORDINGS_DIR = Path(os.getenv("RECORDINGS_DIR", str(BASE_DIR / "recordings")))
CHANGELOG_DIR = BASE_DIR / "changelog"
DB_DIR = BASE_DIR / "db"
PROMPTS_DIR = BASE_DIR / "prompts"
SCHEMAS_DIR = BASE_DIR / "schemas"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Ollama config
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Whisper config
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")


def setup_logging(name: str = "clara") -> logging.Logger:
    """Set up structured logging."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    return logger


logger = setup_logging()


def generate_account_id(company_name: str) -> str:
    """
    Generate a deterministic account_id from company name.
    Idempotent: same name always produces same ID.
    """
    slug = slugify(company_name, max_length=50)
    # Add short hash for uniqueness in edge cases
    short_hash = hashlib.md5(company_name.lower().encode()).hexdigest()[:6]
    return f"{slug}-{short_hash}"


def ensure_account_dirs(account_id: str, version: str = "v1") -> Path:
    """Create and return the output directory for an account version."""
    account_dir = OUTPUT_DIR / "accounts" / account_id / version
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir


def save_json(data: dict, filepath: Path) -> None:
    """Save JSON data with pretty formatting."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Saved: {filepath}")


def load_json(filepath: Path) -> dict:
    """Load JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_text(text: str, filepath: Path) -> None:
    """Save text file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    logger.info(f"Saved: {filepath}")


def load_text(filepath: Path) -> str:
    """Load text file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def load_prompt(prompt_name: str) -> str:
    """Load a prompt template from the prompts directory."""
    filepath = PROMPTS_DIR / prompt_name
    if not filepath.exists():
        raise FileNotFoundError(f"Prompt not found: {filepath}")
    return load_text(filepath)


def get_timestamp() -> str:
    """Get current ISO timestamp."""
    return datetime.now().isoformat()


def find_recordings(directory: Path, extensions: tuple = (".m4a", ".mp3", ".wav", ".webm", ".mp4")) -> list:
    """Find all audio/video files in a directory."""
    files = []
    if directory.exists():
        for ext in extensions:
            files.extend(directory.glob(f"*{ext}"))
    return sorted(files)


def find_transcripts(directory: Path) -> list:
    """Find all transcript .txt files in a directory."""
    if directory.exists():
        return sorted(directory.glob("*.txt"))
    return []


def extract_json_from_text(text: str) -> dict:
    """
    Extract JSON object from LLM response text.
    Handles cases where JSON is wrapped in markdown code blocks.
    """
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    # Try to find JSON object
    brace_start = text.find('{')
    brace_end = text.rfind('}')
    if brace_start != -1 and brace_end != -1:
        json_str = text[brace_start:brace_end + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try cleaning common LLM artifacts
            json_str = re.sub(r',\s*}', '}', json_str)  # trailing commas
            json_str = re.sub(r',\s*]', ']', json_str)  # trailing commas in arrays
            return json.loads(json_str)

    raise ValueError(f"Could not extract JSON from text:\n{text[:500]}")
