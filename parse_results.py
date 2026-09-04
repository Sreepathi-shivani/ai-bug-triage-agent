"""
Parses JUnit-style XML test reports into a list of failures.

Works for:
  - pytest:      pytest --junitxml=results.xml
  - Selenium:    (run via pytest/unittest, which emits the same JUnit XML)
  - Playwright:  npx playwright test --reporter=junit --output=results.xml
"""
import glob
import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List


@dataclass
class TestFailure:
    suite: str
    test_name: str
    classname: str
    message: str
    stack_trace: str
    duration: float = 0.0
    kind: str = "failure"  # "failure" or "error"
    fingerprint: str = field(default="", init=False)

    def __post_init__(self):
        # Stable hash of what identifies "the same bug" across reruns,
        # so we don't file duplicate Jira tickets for the same failing test.
        basis = f"{self.classname}::{self.test_name}::{self.message[:200]}"
        self.fingerprint = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _text(el, default=""):
    return (el.text or default).strip() if el is not None else default


def parse_junit_file(path: str) -> List[TestFailure]:
    failures: List[TestFailure] = []
    tree = ET.parse(path)
    root = tree.getroot()

    # A JUnit file can be <testsuite> at the root, or <testsuites> wrapping many.
    suites = root.findall(".//testsuite") if root.tag != "testsuite" else [root]
    if not suites:
        suites = [root]

    for suite in suites:
        suite_name = suite.attrib.get("name", "unknown-suite")
        for case in suite.findall("testcase"):
            test_name = case.attrib.get("name", "unknown-test")
            classname = case.attrib.get("classname", suite_name)
            duration = float(case.attrib.get("time", 0) or 0)

            fail_el = case.find("failure")
            error_el = case.find("error")
            node = fail_el if fail_el is not None else error_el
            if node is None:
                continue  # passed or skipped

            failures.append(
                TestFailure(
                    suite=suite_name,
                    test_name=test_name,
                    classname=classname,
                    message=node.attrib.get("message", "").strip() or _text(node)[:300],
                    stack_trace=_text(node),
                    duration=duration,
                    kind="failure" if fail_el is not None else "error",
                )
            )
    return failures


def parse_all(glob_pattern: str) -> List[TestFailure]:
    """Parse every JUnit XML file matching a glob pattern (e.g. 'reports/*.xml')."""
    all_failures: List[TestFailure] = []
    for path in sorted(glob.glob(glob_pattern)):
        all_failures.extend(parse_junit_file(path))
    return all_failures
