"""Makes a tiny throwaway git repository with a three step task, to try the runner with a real claude.
Usage: python scripts/make_scratch.py C:\\work\\scratch"""
import subprocess
import sys
from pathlib import Path

FILES = {
    "CLAUDE.md": "# Rules\n\nCommit your work with git after each step, message `S000 step N`. Never push. Touch no file outside this task.\n",
    "SKILL.md": ("# Task handoff\n\n1. Read docs/tasks/S000/task.md and the last entry of docs/tasks/S000/session.md.\n"
                 "2. Do EXACTLY ONE step per run, the first step not yet recorded as done in session.md. Not two steps.\n"
                 "3. Append an entry to session.md with the step number, what you did and the next step. Commit.\n"
                 "4. Status continue while steps remain, done after step 3 is recorded.\n"),
    "docs/tasks/S000/task.md": ("# S000 Scratch task\n\nStep 1. Create hello.py with a function greet(name) returning the text Hello, NAME.\n"
                                "Step 2. Create test_hello.py with a unittest for greet.\n"
                                "Step 3. Run python -m unittest and record the result as acceptance in session.md.\n"),
    "docs/tasks/S000/session.md": "# Session history\n\nNo step is done yet.\n",
}


def main(target):
    root = Path(target)
    root.mkdir(parents=True, exist_ok=True)
    for name, text in FILES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=scratch", "-c", "user.email=s@s", "commit", "-q", "-m", "scratch task S000"]):
        subprocess.run(cmd, cwd=root, check=True)
    print(f"scratch repository ready: {root}")


if __name__ == "__main__":
    main(sys.argv[1])
