"""Security audit tests — ``scripts/security_audit.py`` over the source tree.

Contract: ``docs/architecture.md`` §10 (this test module: "runs the security
audit over the source tree; asserts zero findings") and §12 ("Run in every
test run"). The audit is driven as a subprocess (never ``shell=True``) so
the CLI contract — one finding line per violation on stdout, exit code =
number of findings, 0 = clean, 2 = usage error — is tested exactly as CI
would run it. The audit tool is stdlib-only and never imports the project.

The negative-control fixtures plant one violation at a time in a temporary
tree and assert the matching rule is reported — pinning the detectors
themselves, not just the current tree.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "security_audit.py"
REQUIREMENTS = ROOT / "requirements.txt"

#: The Streamlit version the suite is validated against. requirements.txt
#: must pin exactly this line; changing it is a dependency review, not an
#: edit (architecture.md §11, stdlib first; streamlit is the only
#: documented third-party dependency).
EXPECTED_STREAMLIT_PIN = "streamlit==1.62.0"


def run_audit(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        capture_output=True,
        text=True,
        timeout=120,
    )


def write_tree(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class TestAuditTool(unittest.TestCase):
    def test_script_exists_and_is_stdlib_only(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        for line in SCRIPT.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                top = stripped.split()[1].split(".")[0]
                self.assertIn(top, sys.stdlib_module_names, msg=stripped)

    def test_repository_tree_is_clean(self) -> None:
        result = run_audit(ROOT)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("no findings", result.stdout)

    def test_usage_error_on_missing_root(self) -> None:
        result = run_audit(ROOT / "does-not-exist-audit-root")
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)

    def test_clean_fixture_tree_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tree(
                root,
                {
                    "universality/__init__.py": "",
                    "universality/domain.py": "import math\n",
                    # permitted edge: calculation -> domain (architecture.md §6)
                    "universality/calculation.py": (
                        "from universality.domain import X\n"
                    ),
                },
            )
            result = run_audit(root)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


class TestDetectorsFireOnPlantedViolations(unittest.TestCase):
    """One violation per fixture; the matching rule must be reported."""

    CASES: tuple[tuple[str, str, str], ...] = (
        # (fixture relative path, fixture content, expected rule substring)
        (
            "universality/domain.py",
            "import pickle\n",
            "forbidden-import",
        ),
        (
            "universality/domain.py",
            "x = eval('1')\n",
            "forbidden-call",
        ),
        (
            "universality/domain.py",
            "x = exec('x = 1')\n",
            "forbidden-call",
        ),
        (
            "universality/domain.py",
            "x = __import__('os')\n",
            "forbidden-call",
        ),
        (
            "universality/services.py",
            "import os\nos.system('ls')\n",
            "forbidden-call",
        ),
        (
            "ui/app.py",
            "def run(args):\n    return go(args, shell=True)\n",
            "forbidden-shell",
        ),
        (
            "ui/ui_model.py",
            "import requests\n",
            "third-party-import",
        ),
        (
            # domain may import nothing project-internal (architecture.md §6)
            "universality/domain.py",
            "from universality.services import evaluate\n",
            "import-policy",
        ),
        (
            # the UI may import the universality public API only — never a
            # submodule (architecture.md §6)
            "ui/ui_model.py",
            "from universality.validation import validate\n",
            "import-policy",
        ),
        (
            # a module not listed in the §6 table is fail-closed
            "universality/insights.py",
            "from universality.domain import X\n",
            "import-policy",
        ),
        (
            # scripts/*: stdlib only, never project code
            "scripts/security_audit.py",
            "from universality.domain import X\n",
            "import-policy",
        ),
    )

    def test_each_planted_violation_is_reported(self) -> None:
        for relative, content, expected_rule in self.CASES:
            with self.subTest(case=relative + ":" + expected_rule):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    base = {
                        "universality/__init__.py": "",
                        "universality/domain.py": "import math\n",
                        "ui/__init__.py": "",
                    }
                    if "scripts/" in relative:
                        base.pop("ui/__init__.py", None)
                    base[relative] = content
                    write_tree(root, base)
                    result = run_audit(root)
                self.assertGreater(
                    result.returncode, 0,
                    msg=f"expected findings for {relative}\n{result.stdout}",
                )
                self.assertIn(expected_rule, result.stdout, msg=result.stdout)
                self.assertIn(relative, result.stdout, msg=result.stdout)

    def test_third_party_import_in_domain_is_reported(self) -> None:
        # numpy-style third-party import in the core: stdlib-only contract.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tree(
                root,
                {
                    "universality/__init__.py": "",
                    "universality/domain.py": "import numpy\n",
                },
            )
            result = run_audit(root)
        self.assertGreater(result.returncode, 0, msg=result.stdout)
        self.assertIn("third-party-import", result.stdout)
        self.assertIn("numpy", result.stdout)


class TestDependencyManifest(unittest.TestCase):
    """F-3 regression: the single third-party dependency is pinned."""

    def test_requirements_pins_exactly_the_validated_streamlit(self) -> None:
        self.assertTrue(REQUIREMENTS.is_file())
        lines = [
            line.strip()
            for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        self.assertIn(EXPECTED_STREAMLIT_PIN, lines)
        # streamlit is the ONLY third-party dependency (architecture.md §11).
        self.assertEqual(len(lines), 1, msg=str(lines))


if __name__ == "__main__":
    unittest.main()
