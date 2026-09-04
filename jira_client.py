"""Thin wrapper over the Jira Cloud REST API (v3) for creating bug issues."""
import requests
from requests.auth import HTTPBasicAuth

from config import Config


def _headers():
    return {"Accept": "application/json", "Content-Type": "application/json"}


def _auth():
    return HTTPBasicAuth(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)


def _text_to_adf(text: str) -> dict:
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    content = [
        {"type": "paragraph", "content": [{"type": "text", "text": p.strip()}]}
        for p in paragraphs
    ] or [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]
    return {"type": "doc", "version": 1, "content": content}


def create_bug(summary: str, description: str, priority: str, labels=None) -> dict:
    url = f"{Config.JIRA_BASE_URL}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": Config.JIRA_PROJECT_KEY},
            "summary": summary,
            "description": _text_to_adf(description),
            "issuetype": {"name": Config.JIRA_ISSUE_TYPE},
            "priority": {"name": priority},
            "labels": labels or ["automated-test-failure"],
        }
    }
    resp = requests.post(url, json=payload, headers=_headers(), auth=_auth(), timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"Jira issue creation failed ({resp.status_code}): {resp.text}")
    return resp.json()


def find_existing_issue(fingerprint_label: str):
    url = f"{Config.JIRA_BASE_URL}/rest/api/3/search/jql"
    jql = (
        f'project = "{Config.JIRA_PROJECT_KEY}" '
        f'AND labels = "{fingerprint_label}" '
        f'ORDER BY created DESC'
    )
    resp = requests.get(
        url, params={"jql": jql, "maxResults": 1}, headers=_headers(), auth=_auth(), timeout=30
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Jira search failed ({resp.status_code}): {resp.text}")
    issues = resp.json().get("issues", [])
    return issues[0] if issues else None
