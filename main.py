"""
Bug-filing agent: reads test failures from JUnit XML reports, uses an LLM to
triage each one (summary + description + priority), and files a Jira bug -
skipping failures that were already filed in a previous run.

Usage:
    python main.py "reports/*.xml"
    python main.py "reports/*.xml" --dry-run
    python main.py "reports/*.xml" --mock --dry-run
"""
import argparse
import sys

import jira_client
from config import Config
from parse_results import parse_all
from triage import triage_failure, mock_triage_failure


def main():
    parser = argparse.ArgumentParser(description="File Jira bugs from failing tests.")
    parser.add_argument(
        "report_glob",
        help="Glob pattern for JUnit XML report(s), e.g. reports/*.xml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Triage failures and print what would be filed, without calling Jira.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use free offline rule-based triage instead of calling the Anthropic API.",
    )
    args = parser.parse_args()
    triage_fn = mock_triage_failure if args.mock else triage_failure

    failures = parse_all(args.report_glob)
    if not failures:
        print(f"No failing/erroring tests found matching {args.report_glob}.")
        return

    print(f"Found {len(failures)} failing test(s). Triaging...\n")

    filed, skipped, failed = 0, 0, 0

    for failure in failures:
        fingerprint_label = f"fp-{failure.fingerprint}"
        print(f"-> {failure.classname}::{failure.test_name}")

        try:
            if not args.dry_run:
                existing = jira_client.find_existing_issue(fingerprint_label)
                if existing:
                    print(f"   already filed as {existing['key']}, skipping.\n")
                    skipped += 1
                    continue

            result = triage_fn(failure)
            print(f"   priority: {result.priority}  ({result.reasoning})")
            print(f"   summary:  {result.summary}")

            if args.dry_run:
                print("   [dry-run] would file this bug.\n")
                continue

            issue = jira_client.create_bug(
                summary=result.summary,
                description=result.description,
                priority=result.priority,
                labels=["automated-test-failure", fingerprint_label],
            )
            print(f"   filed: {Config.JIRA_BASE_URL}/browse/{issue['key']}\n")
            filed += 1

        except Exception as e:
            print(f"   ERROR triaging/filing this failure: {e}\n", file=sys.stderr)
            failed += 1

    print(f"Done. Filed: {filed}, Skipped (duplicate): {skipped}, Errors: {failed}")


if __name__ == "__main__":
    main()
