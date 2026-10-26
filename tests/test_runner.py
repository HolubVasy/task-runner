import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import runner  # noqa: E402

FAKE = Path(__file__).resolve().parent / "fake_claude.py"


def make_repo(root):
    repo = Path(root) / "repo"
    repo.mkdir()
    for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"], ["git", "config", "user.name", "t"],
                ["git", "commit", "-q", "--allow-empty", "-m", "init"]):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    return repo


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = make_repo(self.tmp.name)
        self.env = {"FAKE_STATE": str(Path(self.tmp.name) / "state"), "FAKE_STATUSES": "done"}
        for key, value in self.env.items():
            os.environ[key] = value
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("FAKE_STATE", "FAKE_STATUSES", "FAKE_TOUCH",
                                                                   "FAKE_COST", "FAKE_SLEEP")])

    def cfg(self, **kw):
        base = dict(repo=self.repo, task="T1", claude_cmd=[sys.executable, str(FAKE)], logs=Path(self.tmp.name) / "logs",
                    billing="max", max_runs=5)
        base.update(kw)
        return runner.Config(**base)

    def journal(self):
        path = Path(self.tmp.name) / "logs" / "T1" / "journal.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()]

    def test_parse_status(self):
        text = 'work\n{"status": "continue", "summary": "x"}'
        self.assertEqual(runner.parse_status(text)["status"], "continue")
        self.assertEqual(runner.parse_status("no json")["status"], "unknown")
        self.assertEqual(runner.parse_status('{"status": "weird"}')["status"], "unknown")
        self.assertEqual(runner.parse_status('{"status": "done"}\ntrailing text')["status"], "done")

    def test_billing_max_removes_the_key_and_api_requires_it(self):
        env = runner.child_env("max", {"ANTHROPIC_API_KEY": "k", "PATH": "p"})
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertIn("PATH", env)
        with self.assertRaises(SystemExit):
            runner.child_env("api", {"PATH": "p"})
        self.assertEqual(runner.child_env("api", {"ANTHROPIC_API_KEY": "k"})["ANTHROPIC_API_KEY"], "k")

    def test_done_at_the_first_run(self):
        self.assertEqual(runner.run_task(self.cfg()), "done")
        self.assertEqual([e["status"] for e in self.journal()], ["done"])

    def test_continue_then_done_when_the_work_changes_the_repository(self):
        os.environ["FAKE_STATUSES"] = "continue,done"
        os.environ["FAKE_TOUCH"] = "1"
        self.assertEqual(runner.run_task(self.cfg()), "done")
        self.assertEqual(len(self.journal()), 2)

    def test_stalled_when_nothing_changes(self):
        os.environ["FAKE_STATUSES"] = "continue"
        self.assertEqual(runner.run_task(self.cfg()), "stalled")
        self.assertEqual(len(self.journal()), 2)

    def test_a_question_stops_for_a_human(self):
        os.environ["FAKE_STATUSES"] = "question"
        self.assertEqual(runner.run_task(self.cfg()), "question")

    def test_total_budget_stops_the_loop(self):
        os.environ.update(FAKE_STATUSES="continue", FAKE_TOUCH="1", FAKE_COST="3")
        self.assertEqual(runner.run_task(self.cfg(max_usd_total=2)), "exhausted")
        self.assertEqual(len(self.journal()), 1)

    def test_a_silent_run_is_killed(self):
        os.environ["FAKE_SLEEP"] = "20"
        self.assertEqual(runner.run_task(self.cfg(silence_seconds=2)), "failed")
        self.assertIn("silent", self.journal()[0]["killed"])

    def test_the_model_flag_is_passed(self):
        args = Path(self.tmp.name) / "args"
        os.environ["FAKE_ARGS"] = str(args)
        self.addCleanup(lambda: os.environ.pop("FAKE_ARGS", None))
        runner.run_task(self.cfg())
        self.assertIn("--model sonnet", args.read_text())
        runner.run_task(self.cfg(model=""))
        self.assertNotIn("--model", args.read_text())

    def test_max_runs_ends_in_exhausted(self):
        os.environ.update(FAKE_STATUSES="continue", FAKE_TOUCH="1")
        self.assertEqual(runner.run_task(self.cfg(max_runs=2)), "exhausted")


if __name__ == "__main__":
    unittest.main()
