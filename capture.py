#!/usr/bin/env python3
"""Run capture scenarios and write capture JSON for the 0x4142 blog.

Usage: python3 capture.py SCENARIO_DIR OUT_DIR

Each scenario is a TOML file, for example captures/part-01/elf-header.toml:

    title = "readelf: the ELF header"
    tool = "shell"
    cwd = "part-01"

    [[step]]
    label = "the ELF header"
    command = "readelf -h hello"

It becomes OUT_DIR/part-01/elf-header.json in the blog's capture format
(see "Capture format" in the blog README). JSON files in OUT_DIR that no
scenario produced are removed, so a post cannot reference a deleted
scenario. If any scenario fails, nothing is written or removed.
"""

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parent
MAX_COLUMNS = 80
TIMEOUT = 30
NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ENV = {
    **os.environ,
    "COLUMNS": str(MAX_COLUMNS),
    "LC_ALL": "C.UTF-8",
    "TERM": "xterm-256color",
}


class ScenarioError(Exception):
    pass


def _require(table: dict, key: str, where: str) -> None:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise ScenarioError(f"{where} missing '{key}'")


def load_scenario(path: Path) -> dict:
    with path.open("rb") as f:
        data = tomllib.load(f)
    _require(data, "title", f"{path}:")
    _require(data, "tool", f"{path}:")
    if data["tool"] != "shell":
        raise ScenarioError(
            f"{path}: tool '{data['tool']}' is not supported yet (only 'shell')"
        )
    steps = data.get("step")
    if not steps:
        raise ScenarioError(f"{path}: needs at least one [[step]]")
    for i, step in enumerate(steps, 1):
        _require(step, "label", f"{path}: step {i}")
        _require(step, "command", f"{path}: step {i}")
    return data


def _run(step: dict, cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["bash", "-c", step["command"]],
            cwd=cwd,
            env=ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
        )
    except (FileNotFoundError, NotADirectoryError):
        raise ScenarioError(f"cwd '{cwd.name}' does not exist")
    except subprocess.TimeoutExpired:
        raise ScenarioError(f"'{step['command']}' timed out after {TIMEOUT}s")
    if result.returncode != 0 and not step.get("allow_failure", False):
        raise ScenarioError(
            f"'{step['command']}' exited with {result.returncode}:\n{result.stdout}"
        )
    return result.stdout.rstrip("\n")


def capture(scenario: dict, lab_root: Path) -> dict:
    cwd = lab_root / scenario.get("cwd", ".")
    frames = [
        {
            "label": step["label"],
            "command": f"$ {step['command']}",
            "output": _run(step, cwd),
        }
        for step in scenario["step"]
    ]
    return {"version": 1, "title": scenario["title"], "frames": frames}


def wide_lines(result: dict) -> list[str]:
    warnings = []
    for i, frame in enumerate(result["frames"], 1):
        for n, line in enumerate(frame["output"].split("\n"), 1):
            width = len(ANSI.sub("", line))
            if width > MAX_COLUMNS:
                warnings.append(f"frame {i}, line {n}: {width} columns")
    return warnings


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 1
    scenario_dir, out_dir = Path(argv[1]), Path(argv[2])

    results = {}
    try:
        for path in sorted(scenario_dir.rglob("*.toml")):
            rel = path.relative_to(scenario_dir).with_suffix(".json")
            if not all(NAME.match(part) for part in rel.with_suffix("").parts):
                raise ScenarioError(
                    f"{path}: use lowercase letters, digits, '-' and '_' only"
                )
            results[rel] = capture(load_scenario(path), LAB_ROOT)
        if not results:
            raise ScenarioError(f"no scenarios found in {scenario_dir}")
    except (ScenarioError, tomllib.TOMLDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    written = set()
    for rel, result in results.items():
        for warning in wide_lines(result):
            print(f"warning: {rel}: {warning}", file=sys.stderr)
        target = out_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        written.add(target)
        print(f"wrote {target}")

    for stale in sorted(out_dir.rglob("*.json")):
        if stale not in written:
            stale.unlink()
            print(f"removed stale {stale}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
