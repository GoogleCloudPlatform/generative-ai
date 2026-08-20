#!/usr/bin/env python3
"""Reconstruct the generated agent's build context and prove it still builds.

`check_deps.py` audits the bounds in PINNED_DEPS. This script answers the
question the bounds cannot: *does today's resolution actually build and
import?* Both real outages -- mcp 2.0.0 and a2a-sdk 1.x -- slipped past the
caps and were caught only by running the imports (AGENTS.md section 8.1).
Until this existed, the first execution of a new resolution was a
customer-facing demo build.

It writes a directory that mirrors what the setup script emits:

    requirements.txt          from PINNED_DEPS in app/Code.gs, per variant
    constraints.txt           caps only, mirroring the Code.gs generator
    dep_smoke_test.py         the __DEP_SMOKE_EOF__ heredoc, verbatim
    adk_agent/app/imports.py  every import statement in the agent template,
                              try/except context preserved
    Dockerfile                the real base image and the real check steps

The imports file is a *superset* across feature flags: the template branches
on environment variables at run time, so one run covers every demo
configuration.

Usage:
    python3 canary.py --out /tmp/canary            # write the context
    python3 canary.py --out /tmp/canary --run-venv # ... and run it in a venv
    python3 canary.py --variant computer-use --out /tmp/canary
    docker build -t ge-canary /tmp/canary          # the full image
"""

import argparse
import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path

from check_deps import (
    COMPUTER_USE_KEYS,
    NON_PIP_KEYS,
    VIEWER_KEYS,
    parse_pinned_deps,
)

HERE = Path(__file__).parent
CODE_GS = HERE / "app" / "Code.gs"
AGENT_SRC = HERE / "agent_template" / "adk_agent"

# Mirrors CONSTRAINT_KEYS in app/Code.gs. Kept in the same order so the emitted
# constraints.txt is byte-comparable with the generated one.
CONSTRAINT_KEYS = [
    "adk", "mcp", "genai", "a2a", "aiplatform", "storage", "scheduler",
    "tasks", "pubsub", "firestore", "logging", "dotenv", "dbDtypes", "otel",
    "playwright", "genaiComputerUse", "cuOtelGcpLogging",
    "cuOtelGcpResourceDetector",
]

# The A2UI v0.9 wiring the generated agent depends on. A plain module import
# cannot see a dropped symbol, and these four are exactly what agent.py and
# fast_api_app.py build the schema manager and the DataPart from. Kept in sync
# with the equivalent RUN line in the generated Dockerfile (Code.gs).
A2UI_INTERFACE_CHECK = (
    "from a2ui.schema.constants import VERSION_0_9; "
    "from a2ui.schema.catalog import CatalogConfig; "
    "from a2ui.schema.common_modifiers import remove_strict_validation; "
    "from a2ui.a2a.parts import create_a2ui_part; "
    "assert hasattr(CatalogConfig, 'from_path'), 'FAIL: CatalogConfig.from_path missing'; "
    # Pin the MIME the DataPart actually carries, not just the signature.
    # Gemini Enterprise renders 'application/json+a2ui' and ignores
    # 'application/a2ui+json'; the SDK picks between them off the version
    # kwarg, so a silent flip in that mapping turns every card into plain text
    # with nothing else to see.
    "_p = create_a2ui_part({'version': 'v0.9'}, version=VERSION_0_9); "
    "_m = (_p.root.metadata or {}).get('mimeType'); "
    "assert _m == 'application/json+a2ui', 'FAIL: unexpected A2UI mimeType ' + repr(_m); "
    "print('a2ui v0.9 interface OK (mimeType=' + _m + ')')"
)


def heredoc(name, lines):
    """Return the body of a quoted heredoc in Code.gs, verbatim."""
    body, inside = [], False
    for line in lines:
        if not inside:
            if "<<'" + name + "'" in line:
                inside = True
            continue
        if line.rstrip() == name:
            return body
        body.append(line)
    raise SystemExit("canary: heredoc " + name + " not found or unterminated")


def collect_imports():
    """Every non-optional import statement in the agent template.

    Imports inside a `try` are excluded, matching what `dep_smoke_test.py`
    does with the same construct: an integration the agent already degrades
    around is not something a canary should fail on. That is the whole
    mechanism behind the superset property, too -- Computer Use, the viewer
    and the OpenTelemetry exporters are all optional at import time, so one
    context covers configurations no single demo produces.
    """
    hard, optional = [], []
    for path in sorted(AGENT_SRC.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise SystemExit("canary: cannot parse " + str(path) + ": " + str(exc))

        guarded = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for inner in ast.walk(node):
                    if isinstance(inner, (ast.Import, ast.ImportFrom)):
                        guarded.add(id(inner))

        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            # level > 0 is a relative import of the agent's own package.
            if isinstance(node, ast.ImportFrom) and (node.level or not node.module):
                continue
            statement = ast.get_source_segment(source, node) or ""
            statement = re.sub(r"\s+", " ", statement).strip()
            if not statement:
                continue
            (optional if id(node) in guarded else hard).append(statement)

    seen, uniq = set(), []
    for statement in hard:
        if statement not in seen:
            seen.add(statement)
            uniq.append(statement)
    return uniq, sorted(set(optional))


def requirements_for(values, variant):
    order = [k for k, _ in values if k not in NON_PIP_KEYS and k not in VIEWER_KEYS]
    if variant != "computer-use":
        order = [k for k in order if k not in COMPUTER_USE_KEYS]
    table = dict(values)
    return [table[k] for k in order]


def constraints_for(table):
    """Caps only, deduplicated by name -- mirrors the Code.gs generator."""
    lines, seen = [], set()
    for key in CONSTRAINT_KEYS:
        spec = table.get(key)
        if not spec or " @ " in spec:
            continue
        match = re.match(r"^([A-Za-z0-9._-]+)(?:\[[^\]]*\])?(.*)$", spec)
        if not match:
            continue
        name, rest = match.group(1), match.group(2) or ""
        bounds = [p.strip() for p in rest.split(",")
                  if p.strip().startswith("<") or p.strip().startswith("==")]
        if not bounds or name in seen:
            continue
        seen.add(name)
        lines.append(name + ",".join(bounds))
    return lines


def write_context(out, variant):
    text = CODE_GS.read_text(encoding="utf-8")
    lines = text.split("\n")
    pairs = parse_pinned_deps(text)
    table = dict(pairs)

    if out.exists():
        shutil.rmtree(out)
    (out / "adk_agent" / "app").mkdir(parents=True)

    (out / "requirements.txt").write_text(
        "\n".join(requirements_for(pairs, variant)) + "\n", encoding="utf-8")
    (out / "constraints.txt").write_text(
        "\n".join(constraints_for(table)) + "\n", encoding="utf-8")
    (out / "dep_smoke_test.py").write_text(
        "\n".join(heredoc("__DEP_SMOKE_EOF__", lines)) + "\n", encoding="utf-8")

    hard, optional = collect_imports()
    (out / "adk_agent" / "__init__.py").write_text("", encoding="utf-8")
    (out / "adk_agent" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (out / "adk_agent" / "app" / "imports.py").write_text(
        '"""Superset of the imports in the agent template, across all flags."""\n'
        + "\n".join(hard) + "\n", encoding="utf-8")

    (out / "Dockerfile").write_text(
        "FROM " + table["pythonImage"] + "\n"
        "COPY --from=" + table["uvImage"] + " /uv /uvx /bin/\n"
        "RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*\n"
        "WORKDIR /app\n"
        "COPY requirements.txt constraints.txt ./\n"
        "RUN uv pip install --system -r requirements.txt\n"
        # constraints.txt guards the cloned-MCP installs and nothing else
        # exercises it. A duplicate package name or a stray extra makes the
        # file a hard error, which would surface only on a customer's build
        # of a demo that happens to clone an MCP server.
        "RUN uv pip install --system --dry-run -c constraints.txt "
        '"mcp>=1.24.0" > /dev/null && echo "constraints.txt OK"\n'
        "COPY . .\n"
        'RUN uv pip freeze | grep -iE "^(google-adk|a2ui|mcp|google-genai|a2a-sdk)"'
        " | tee /app/.dep-versions\n"
        "RUN python dep_smoke_test.py\n"
        'RUN python -c "' + A2UI_INTERFACE_CHECK + '"\n',
        encoding="utf-8")

    # --run-venv drops a .venv into this directory; without this, a later
    # docker build on the same directory copies it into the image.
    (out / ".dockerignore").write_text(".venv\n__pycache__\n", encoding="utf-8")

    print("canary: wrote " + str(out) + " (variant: " + variant + ")")
    print("  " + str(len(hard)) + " import statements, "
          + str(len(optional)) + " skipped as try/except-guarded")
    return hard, optional


def run_venv(out, uv_version):
    """Resolve and run the smoke test in a venv -- the Docker-free fast path."""
    venv = out / ".venv"
    uv = ["uvx", "uv@" + uv_version]
    steps = [
        (uv + ["venv", "--python", "3.11", str(venv)], "create venv"),
        (uv + ["pip", "install", "--python", str(venv), "-q",
               "-r", str(out / "requirements.txt")], "install requirements"),
    ]
    for command, label in steps:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            print("canary: FAILED to " + label)
            print((proc.stderr or proc.stdout)[:4000])
            return 1

    python = str(venv / "bin" / "python")
    versions = subprocess.run(
        [python, "-c",
         "import importlib.metadata as m;"
         "print('\\n'.join('  ' + p + ' ' + m.version(p) for p in "
         "['google-adk','mcp','google-genai','a2a-sdk','a2ui-agent-sdk']))"],
        capture_output=True, text=True)
    print("resolved:")
    print(versions.stdout.rstrip())

    failed = 0
    for command, label in (
        ([python, "dep_smoke_test.py"], "dependency import smoke test"),
        ([python, "-c", A2UI_INTERFACE_CHECK], "a2ui interface check"),
    ):
        proc = subprocess.run(command, cwd=str(out), capture_output=True, text=True)
        output = (proc.stdout + proc.stderr).strip()
        print("\n== " + label + " ==")
        print("\n".join(l for l in output.split("\n")
                        if "UserWarning" not in l and "check_feature_enabled" not in l))
        if proc.returncode != 0:
            failed = 1
    return failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="/tmp/canary")
    parser.add_argument("--variant", choices=["base", "computer-use"], default="base")
    parser.add_argument("--run-venv", action="store_true")
    args = parser.parse_args()

    out = Path(args.out).resolve()
    write_context(out, args.variant)
    if not args.run_venv:
        return 0

    table = dict(parse_pinned_deps(CODE_GS.read_text(encoding="utf-8")))
    return run_venv(out, table.get("uvVersion", "0.11.17"))


if __name__ == "__main__":
    sys.exit(main())
