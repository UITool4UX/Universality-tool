"""Security audit — machine-checkable enforcement of the security contract.

Contract owner: ``docs/architecture.md`` §5 (module row) and §12
("Enforcement (machine + process)"), with the forbidden-construct list in
``docs/validation-and-security.md`` ("Forbidden constructs") and the
permitted-edge table in ``docs/architecture.md`` §6.

Standard library only (``ast``, ``pathlib``, ``sys``). This tool inspects
source text — it never imports, executes, installs, or runs the audited
code. It is deliberately import-free of the project: ``tests/*`` drives it
as a subprocess.

Checks:

(a) Forbidden constructs (``docs/validation-and-security.md``):

    - forbidden calls:     ``eval(``, ``exec(``, ``compile(``,
                            ``__import__(``, ``input(``
    - forbidden os calls:  ``os.system(``, ``os.popen(``
    - forbidden imports:   ``pickle``, ``subprocess``, ``importlib``
                            (any submodule)
    - shell flag:          any ``shell=True`` keyword argument, anywhere

(b) Import policy (``docs/architecture.md`` §6 — the permitted-edge table
    is exhaustive; anything else is a violation):

    - each listed module may import only its listed project-internal
      edges (``domain``: none; ``calculation``: domain; ``validation``:
      domain + calculation; ``services``: domain + calculation +
      validation + diagnostics; ``diagnostics``: none; the package
      ``__init__``: services + domain + calculation + validation;
      ``ui.app``: ``ui.ui_model`` + ``universality`` (public API only);
      ``ui.ui_model``: ``universality`` (public API only); ``ui`` /
      ``scripts/*``: none)
    - a project module **not listed** in the §6 table may import no
      project module (fail-closed: a new module needs a contract entry —
      file + changelog + approval — before it may import project code)
    - no third-party imports anywhere, except the documented framework
      exception: ``streamlit`` in ``ui/app.py`` (and in ``tests/*``,
      which drive the AppTest harness)
    - ``tests/*`` are exempt from the project-edge table (they may import
      any production module) but are still third-party-checked

Scope of check (a): ``universality/``, ``ui/``, ``scripts/`` — all
shipping and tooling code. ``tests/`` are exempt from (a) (verified test
code that never ships; e.g. this audit's own test drives it via
``subprocess`` without ``shell=True``) but are covered by (b).

Usage::

    python scripts/security_audit.py [ROOT]

Prints one line per finding (``path:line: rule: message``) and exits with
the number of findings (0 = clean). ROOT defaults to the repository root
(the parent of ``scripts/``). A missing ROOT is a usage error (exit 2).
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

#: Python 3.10+ — the authoritative stdlib module set.
STDLIB = sys.stdlib_module_names

#: Project-internal top-level packages/directories (import-policy scope).
PROJECT_ROOTS = ("universality", "ui", "scripts", "tests")

#: Directories whose .py files get the forbidden-construct check (a).
FORBIDDEN_SCAN_DIRS = ("universality", "ui", "scripts")

# ---------------------------------------------------------------------------
# (a) Forbidden constructs — docs/validation-and-security.md
# ---------------------------------------------------------------------------

#: Builtin calls that are never permitted in this codebase.
FORBIDDEN_CALLS = frozenset({"eval", "exec", "compile", "__import__", "input"})

#: Top-level modules whose mere import is forbidden (unsafe
#: deserialization / shell execution / dynamic-import machinery).
FORBIDDEN_IMPORTS = frozenset({"pickle", "subprocess", "importlib"})

#: ``os.<attr>(`` calls that are forbidden.
FORBIDDEN_OS_ATTRS = frozenset({"system", "popen"})

# ---------------------------------------------------------------------------
# (b) Import policy — docs/architecture.md §6 (exhaustive edge table)
# ---------------------------------------------------------------------------

#: Permitted project-internal edges, keyed by module name.
PERMITTED_EDGES = {
    "universality.domain": frozenset(),
    "universality.calculation": frozenset({"universality.domain"}),
    "universality.validation": frozenset(
        {"universality.domain", "universality.calculation"}
    ),
    "universality.services": frozenset(
        {
            "universality.domain",
            "universality.calculation",
            "universality.validation",
            "universality.diagnostics",
        }
    ),
    "universality.diagnostics": frozenset(),
    # The package __init__ (public API): re-exports only.
    "universality": frozenset(
        {
            "universality.services",
            "universality.domain",
            "universality.calculation",
            "universality.validation",
        }
    ),
    # The UI imports the universality package **public API only** (the
    # bare package — never a submodule) plus its intra-band model.
    "ui.app": frozenset({"ui.ui_model", "universality"}),
    "ui.ui_model": frozenset({"universality"}),
    "ui": frozenset(),
    # scripts/*: stdlib only, never project code (architecture.md §5).
    "scripts.security_audit": frozenset(),
}


@dataclass(frozen=True)
class Finding:
    """One audit finding (stable, printable, test-comparable)."""

    path: str  # POSIX path relative to the audited root
    line: int
    rule: str  # forbidden-call | forbidden-import | forbidden-shell | import-policy | third-party-import
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _is_module_file(root: Path, dotted: str) -> bool:
    """True if ``dotted`` names a module/package file under ``root``."""
    parts = dotted.split(".")
    if not parts or any(not p for p in parts):
        return False
    return (root.joinpath(*parts).with_suffix(".py")).is_file() or (
        root.joinpath(*parts, "__init__.py")
    ).is_file()


def _module_name(path: Path, root: Path) -> str:
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_of(path: Path, root: Path) -> str:
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        return ".".join(parts)  # relative level 1 from __init__ = the package itself
    return ".".join(parts[:-1])


def _resolve(node: ast.Import | ast.ImportFrom, package: str, root: Path) -> list[str]:
    """All project-relevant module names one import statement refers to.

    ``from ui import ui_model`` resolves to ``ui.ui_model`` when that
    submodule file exists (the effective import), else to the package.
    Relative imports resolve against the file's package.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if node.level > 0:
        pkg_parts = package.split(".")
        base_parts = (
            pkg_parts
            if node.level == 1
            else pkg_parts[: len(pkg_parts) - (node.level - 1)]
        )
        base = ".".join(base_parts)
        if node.module:
            return [f"{base}.{node.module}" if base else node.module]
        return [
            f"{base}.{alias.name}" if base else alias.name for alias in node.names
        ]
    targets: list[str] = []
    for alias in node.names:
        if node.module:
            submodule = f"{node.module}.{alias.name}"
            targets.append(submodule if _is_module_file(root, submodule) else node.module)
        else:  # from . import x with level == 0 is invalid Python; be safe
            targets.append(alias.name)
    return targets


class _Checker(ast.NodeVisitor):
    """One file: forbidden constructs (when active) + import policy."""

    def __init__(
        self,
        path: Path,
        root: Path,
        module_name: str,
        forbidden_active: bool,
    ) -> None:
        self.path = path
        self.root = root
        self.module_name = module_name
        self.forbidden_active = forbidden_active
        self.package = _package_of(path, root)
        self.findings: list[Finding] = []

    def _add(self, node: ast.AST, rule: str, message: str) -> None:
        self.findings.append(
            Finding(
                path=self.path.relative_to(self.root).as_posix(),
                line=node.lineno,
                rule=rule,
                message=message,
            )
        )

    # -- (a) forbidden constructs ----------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        if self.forbidden_active:
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                self._add(
                    node,
                    "forbidden-call",
                    f"{func.id}() is forbidden (validation-and-security.md, "
                    "Forbidden constructs)",
                )
            elif (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
                and func.attr in FORBIDDEN_OS_ATTRS
            ):
                self._add(
                    node,
                    "forbidden-call",
                    f"os.{func.attr}() is forbidden (validation-and-security.md, "
                    "Forbidden constructs)",
                )
            for keyword in node.keywords:
                if (
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    self._add(
                        node,
                        "forbidden-shell",
                        "shell=True is forbidden (shell execution of "
                        "user-derived content is a shell-injection vector)",
                    )
        self.generic_visit(node)

    # -- (b) import policy -------------------------------------------------

    def _check_import(self, node: ast.Import | ast.ImportFrom) -> None:
        for target in dict.fromkeys(_resolve(node, self.package, self.root)):
            top = target.split(".")[0]
            if self.forbidden_active and top in FORBIDDEN_IMPORTS:
                self._add(
                    node,
                    "forbidden-import",
                    f"import of {target} is forbidden (validation-and-security.md, "
                    "Forbidden constructs)",
                )
                continue
            if top in PROJECT_ROOTS:
                self._check_project_edge(node, target)
            elif top not in STDLIB:
                self._check_third_party(node, target)
            # stdlib: always fine

    def _check_project_edge(self, node: ast.AST, target: str) -> None:
        if self.module_name.startswith("tests."):
            return  # tests may import any production module (architecture.md §6)
        if self.module_name.startswith("scripts."):
            self._add(
                node,
                "import-policy",
                f"scripts/* may not import project code "
                f"(architecture.md §5: stdlib only); import of {target} violates it",
            )
            return
        permitted = PERMITTED_EDGES.get(self.module_name)
        if permitted is None:
            self._add(
                node,
                "import-policy",
                f"module {self.module_name} is not listed in the architecture.md "
                f"§6 edge table — a contract entry (file + changelog + approval) "
                f"is required before it may import {target}",
            )
            return
        if target not in permitted:
            allowed = ", ".join(sorted(permitted)) or "none"
            self._add(
                node,
                "import-policy",
                f"{self.module_name} may not import {target} "
                f"(permitted edges: {allowed}; architecture.md §6)",
            )

    def _check_third_party(self, node: ast.AST, target: str) -> None:
        top = target.split(".")[0]
        if top == "streamlit" and (
            self.module_name == "ui.app" or self.module_name.startswith("tests.")
        ):
            return  # the documented framework exception
        self._add(
            node,
            "third-party-import",
            f"third-party import {top!r} is not permitted (standard library "
            "first, architecture.md §11; streamlit is the only documented "
            "exception, ui/app.py only)",
        )

    def visit_Import(self, node: ast.Import) -> None:
        self._check_import(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self._check_import(node)
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Audit entry points
# ---------------------------------------------------------------------------

def _scan_file(path: Path, root: Path, forbidden_active: bool) -> list[Finding]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    checker = _Checker(
        path=path,
        root=root,
        module_name=_module_name(path, root),
        forbidden_active=forbidden_active,
    )
    checker.visit(tree)
    return checker.findings


def audit_file(path: Path, root: Path) -> list[Finding]:
    """Audit one ``.py`` file under ``root`` (public function API)."""
    forbidden_active = path.relative_to(root).parts[0] in FORBIDDEN_SCAN_DIRS
    return _scan_file(path, root, forbidden_active)


def audit_tree(root: Path) -> list[Finding]:
    """Audit every project ``.py`` file under ``root`` (public function API)."""
    root = root.resolve()
    findings: list[Finding] = []
    for directory in PROJECT_ROOTS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            findings.extend(audit_file(path, root))
    findings.sort(key=lambda f: (f.path, f.line, f.rule, f.message))
    return findings


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("usage: python scripts/security_audit.py [ROOT]", file=sys.stderr)
        return 2
    if len(argv) == 2:
        root = Path(argv[1])
    else:
        root = Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print(f"audit: root not found: {root}", file=sys.stderr)
        return 2
    findings = audit_tree(root)
    for finding in findings:
        print(finding.render())
    if findings:
        print(f"security audit: {len(findings)} finding(s)")
    else:
        print("security audit: OK — no findings")
    return len(findings)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
