"""Central place for reading configuration from environment variables (.env)."""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


class Config:
    # Jira
    JIRA_BASE_URL = _require("JIRA_BASE_URL").rstrip("/")
    JIRA_EMAIL = _require("JIRA_EMAIL")
    JIRA_API_TOKEN = _require("JIRA_API_TOKEN")
    JIRA_PROJECT_KEY = _require("JIRA_PROJECT_KEY")
    JIRA_ISSUE_TYPE = os.getenv("JIRA_ISSUE_TYPE", "Bug")

    # LLM
    ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # Dedup
    DEDUP_STORE_PATH = os.getenv("DEDUP_STORE_PATH", ".filed_bugs.json")
