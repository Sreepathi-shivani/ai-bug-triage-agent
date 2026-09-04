# Jira Bug-Filing Agent

Reads failing tests from JUnit XML reports (pytest, Selenium-via-pytest, or
Playwright's JUnit reporter), asks an LLM to triage each failure — writing a
clean bug summary/description and assigning a **priority** — then files it as
a Jira bug via the REST API.

## How it works

```
test run → JUnit XML report → parse_results.py → triage.py (LLM) → jira_client.py → Jira bug
```

1. **`parse_results.py`** extracts every failed/errored `<testcase>` from your
   JUnit XML report(s). Each failure gets a stable fingerprint (hash of test
   name + error message) used for dedup.
2. **`triage.py`** sends the failure (name, message, stack trace) to Claude,
   which returns a JSON object with `summary`, `description`, `priority`
   (one of `Highest`/`High`/`Medium`/`Low`/`Lowest`), and its `reasoning`.
3. **`jira_client.py`** creates the Jira issue via `POST /rest/api/3/issue`.
   Before filing, it searches Jira for an issue already labeled with this
   failure's fingerprint, so reruns of a still-broken test don't create
   duplicate tickets.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# then fill in .env with your real Jira URL, email, API token, project key,
# and Anthropic API key
```

Get a Jira API token from https://id.atlassian.com/manage-profile/security/api-tokens.

Get an Anthropic API key from https://console.anthropic.com.

**Priority names**: the `VALID_PRIORITIES` list in `triage.py` assumes Jira's
default scheme (`Highest`/`High`/`Medium`/`Low`/`Lowest`). Check your Jira
project's actual priority names under Project Settings → Priorities and
adjust the list if they differ (e.g. some teams use `P0`–`P4` or
`Blocker`/`Critical`/`Major`/`Minor`/`Trivial`).

## Generating the JUnit XML report from your test framework

- **pytest**: `pytest --junitxml=reports/results.xml`
- **Selenium** (run under pytest/unittest): same as above — Selenium itself
  doesn't produce a report format, whatever runner you use does.
- **Playwright**: `npx playwright test --reporter=junit` and set
  `PLAYWRIGHT_JUNIT_OUTPUT_NAME=reports/results.xml`

## Running the agent

```bash
# Preview what would be filed, without touching Jira:
python main.py "reports/*.xml" --dry-run

# Actually file bugs:
python main.py "reports/*.xml"
```

Wire the non-dry-run command into your CI pipeline as a step that runs after
your test suite (even on failure — e.g. `if: always()` in GitHub Actions).

## Notes / things to adjust for your setup

- **Duplicate detection** is fingerprint-based (test name + error message) and
  lives entirely in Jira labels — there's no local database, so it works fine
  across CI runs on ephemeral machines.
- **Priority accuracy** depends on the LLM having enough signal in the stack
  trace. If your test failures tend to be terse assertions with little
  context, consider having your test framework capture more diagnostic info
  (request/response bodies, screenshots, logs) into the failure message.
- The Jira `description` field uses Atlassian Document Format (ADF); the
  agent does a minimal plain-text-to-ADF conversion. For richer formatting
  (code blocks, bullet lists) you'd extend `_text_to_adf` in `jira_client.py`.
- This currently supports Jira **Cloud**. Jira **Server/Data Center** uses a
  different auth scheme (PAT or basic auth without the email field) and the
  description field takes plain text/wiki markup instead of ADF.
