import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import capture as cap  # noqa: E402

ESC = "\x1b"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


SCENARIO = """
title = "two steps"
tool = "shell"

[[step]]
label = "first"
command = "printf 'a\\nb\\n'"

[[step]]
label = "second"
command = "echo oops >&2"
"""


class LoadScenarioTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_loads_a_valid_scenario(self):
        s = cap.load_scenario(write(self.dir / "ok.toml", SCENARIO))
        self.assertEqual(s["title"], "two steps")
        self.assertEqual(len(s["step"]), 2)

    def test_rejects_missing_title(self):
        path = write(self.dir / "x.toml", 'tool = "shell"\n[[step]]\nlabel="a"\ncommand="ls"\n')
        with self.assertRaisesRegex(cap.ScenarioError, "missing 'title'"):
            cap.load_scenario(path)

    def test_rejects_unsupported_tool(self):
        path = write(self.dir / "x.toml", 'title="t"\ntool="gdb"\n[[step]]\nlabel="a"\ncommand="ls"\n')
        with self.assertRaisesRegex(cap.ScenarioError, "not supported yet"):
            cap.load_scenario(path)

    def test_rejects_no_steps(self):
        path = write(self.dir / "x.toml", 'title="t"\ntool="shell"\n')
        with self.assertRaisesRegex(cap.ScenarioError, "at least one"):
            cap.load_scenario(path)

    def test_rejects_step_without_command(self):
        path = write(self.dir / "x.toml", 'title="t"\ntool="shell"\n[[step]]\nlabel="a"\n')
        with self.assertRaisesRegex(cap.ScenarioError, "step 1 missing 'command'"):
            cap.load_scenario(path)


class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.lab = Path(tempfile.mkdtemp())

    def scenario(self, *steps, cwd="."):
        return {"title": "t", "tool": "shell", "cwd": cwd, "step": list(steps)}

    def test_runs_commands_and_builds_frames(self):
        result = cap.capture(
            self.scenario({"label": "l", "command": "printf 'a\\nb\\n'"}), self.lab
        )
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["title"], "t")
        self.assertEqual(
            result["frames"],
            [{"label": "l", "command": "$ printf 'a\\nb\\n'", "output": "a\nb"}],
        )

    def test_includes_stderr(self):
        result = cap.capture(self.scenario({"label": "l", "command": "echo oops >&2"}), self.lab)
        self.assertEqual(result["frames"][0]["output"], "oops")

    def test_runs_in_cwd(self):
        (self.lab / "part-01").mkdir()
        result = cap.capture(
            self.scenario({"label": "l", "command": "basename $PWD"}, cwd="part-01"), self.lab
        )
        self.assertEqual(result["frames"][0]["output"], "part-01")

    def test_failing_command_raises(self):
        with self.assertRaisesRegex(cap.ScenarioError, "exited with 3"):
            cap.capture(self.scenario({"label": "l", "command": "exit 3"}), self.lab)

    def test_allow_failure_keeps_output(self):
        result = cap.capture(
            self.scenario({"label": "l", "command": "echo x; exit 3", "allow_failure": True}),
            self.lab,
        )
        self.assertEqual(result["frames"][0]["output"], "x")


class WideLinesTest(unittest.TestCase):
    def frame(self, output):
        return {"frames": [{"label": "l", "command": "$ x", "output": output}]}

    def test_flags_lines_over_80_columns(self):
        warnings = cap.wide_lines(self.frame("a" * 81))
        self.assertEqual(len(warnings), 1)
        self.assertIn("81 columns", warnings[0])

    def test_ignores_color_codes_when_measuring(self):
        colored = f"{ESC}[31m" + "a" * 80 + f"{ESC}[0m"
        self.assertEqual(cap.wide_lines(self.frame(colored)), [])


class MainTest(unittest.TestCase):
    def setUp(self):
        self.scenarios = Path(tempfile.mkdtemp())
        self.out = Path(tempfile.mkdtemp())

    def test_writes_capture_json(self):
        write(self.scenarios / "part-01" / "two.toml", SCENARIO)
        self.assertEqual(cap.main(["capture.py", str(self.scenarios), str(self.out)]), 0)
        data = json.loads((self.out / "part-01" / "two.json").read_text())
        self.assertEqual([f["label"] for f in data["frames"]], ["first", "second"])

    def test_prunes_stale_captures(self):
        write(self.scenarios / "part-01" / "two.toml", SCENARIO)
        stale = write(self.out / "part-01" / "gone.json", "{}")
        cap.main(["capture.py", str(self.scenarios), str(self.out)])
        self.assertFalse(stale.exists())

    def test_error_writes_and_prunes_nothing(self):
        write(self.scenarios / "part-01" / "ok.toml", SCENARIO)
        write(self.scenarios / "part-01" / "bad.toml", 'title="t"\ntool="shell"\n')
        stale = write(self.out / "part-01" / "gone.json", "{}")
        self.assertEqual(cap.main(["capture.py", str(self.scenarios), str(self.out)]), 1)
        self.assertTrue(stale.exists())
        self.assertFalse((self.out / "part-01" / "ok.json").exists())

    def test_rejects_names_the_blog_cannot_reference(self):
        write(self.scenarios / "Part-01" / "Two.toml", SCENARIO)
        self.assertEqual(cap.main(["capture.py", str(self.scenarios), str(self.out)]), 1)


if __name__ == "__main__":
    unittest.main()
