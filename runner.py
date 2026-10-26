#!/usr/bin/env python3
"""task-runner: runs Claude Code headless (claude -p) on ONE Git task until it is done, blocked, stalled or out of
budget. The state of the task lives in the target repository (its checkpoint records); every run starts fresh from
that checkpoint. The runner decides when to stop by rule; the model decides what to do. Standard library only."""
import argparse
import hashlib
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

STATUSES = ("done", "continue", "waiting", "blocked", "question")
EXIT = {"done": 0, "blocked": 2, "question": 2, "stalled": 3, "exhausted": 4, "failed": 5}
DEFAULT_TOOLS = ("Read,Edit,Write,Glob,Grep,Bash(git:*),Bash(gh:*),Bash(python:*),Bash(python3:*),"
                 "Bash(pytest:*),Bash(dir:*),Bash(ls:*)")
DEFAULT_SKILL = ".agents/skills/job-search-tasks/SKILL.md"

PROMPT = """Task {task}. You work headless on one task of the repository in the current directory.
1. Read the skill file {skill} and follow it to resume the task from its recorded checkpoint. The repository's own rules (CLAUDE.md) apply.
2. Do the next meaningful step of the task and record the checkpoint the way the skill says.
3. Stay inside the task. Never print or store secrets. Never send a message on the owner's behalf. Do not start another task.
4. End your answer with exactly one JSON line and nothing after it:
{{"status": "done|continue|waiting|blocked|question", "summary": "...", "question": null, "waiting_for": null, "pr": null}}
done means the acceptance of the task is recorded. continue means a next step remains and a fresh run can take it. waiting with waiting_for "ci" and a pr number means checks of that pull request must finish first. blocked or question means a human decision is needed, put it in question.
{extra}"""


@dataclass
class Config:
    repo: Path
    task: str
    skill: str = DEFAULT_SKILL
    claude_cmd: list = field(default_factory=lambda: [shutil.which("claude") or "claude"])
    max_runs: int = 5
    max_usd_per_run: float = 2.0
    max_usd_total: float = 10.0
    max_minutes: int = 40
    silence_seconds: int = 300
    stall_runs: int = 2
    ci_timeout_minutes: int = 45
    billing: str = "max"
    model: str = "sonnet"
    allowed_tools: str = DEFAULT_TOOLS
    logs: Path = field(default_factory=lambda: Path.home() / ".task-runner")
    note: str = ""


def parse_status(text):
    """The last line of the answer that is a JSON object with a known status, else unknown."""
    for line in reversed(str(text or "").splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if isinstance(data, dict) and data.get("status") in STATUSES:
                return data
    return {"status": "unknown"}


def child_env(billing, base=None):
    """max: the subscription is used, so the API key is removed. api: the key must exist and is kept."""
    env = dict(os.environ if base is None else base)
    if billing == "max":
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
    elif billing == "api" and not env.get("ANTHROPIC_API_KEY"):
        raise SystemExit("billing api needs ANTHROPIC_API_KEY in the environment")
    return env


def fingerprint(repo):
    """What the work changed: the HEAD commit and the uncommitted state."""
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True).stdout
        except OSError:
            return ""
    return hashlib.sha256((git("rev-parse", "HEAD") + git("status", "--porcelain")).encode()).hexdigest()


def kill_tree(proc):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _read_lines(stream, lines):
    for line in iter(stream.readline, ""):
        lines.put(line)
    lines.put(None)


def run_claude(cfg, prompt, raw_log):
    """One headless run under the watch: silence or wall time kills the whole process tree."""
    cmd = cfg.claude_cmd + ["-p", "--output-format", "stream-json", "--verbose", "--max-budget-usd",
                            str(cfg.max_usd_per_run), "--permission-mode", "acceptEdits",
                            "--allowedTools", cfg.allowed_tools]
    if cfg.model:
        cmd += ["--model", cfg.model]
    group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(cmd, cwd=cfg.repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", env=child_env(cfg.billing), **group)
    lines = queue.Queue()
    threading.Thread(target=_read_lines, args=(proc.stdout, lines), daemon=True).start()
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except OSError:
        pass
    started = last = time.time()
    result, killed = {}, None
    with open(raw_log, "a", encoding="utf-8") as log:
        while True:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                line = ""
            if line is None:
                break
            if line:
                last = time.time()
                log.write(line)
                try:
                    event = json.loads(line)
                except ValueError:
                    event = {}
                if event.get("type") == "result":
                    result = event
            now = time.time()
            if now - last > cfg.silence_seconds:
                killed = f"silent for {int(now - last)} s"
            elif now - started > cfg.max_minutes * 60:
                killed = f"ran for {int(now - started)} s"
            if killed:
                kill_tree(proc)
                break
    proc.wait()
    proc.stdout.close()
    return {"result": str(result.get("result", "")), "cost": float(result.get("total_cost_usd") or 0),
            "session": result.get("session_id"), "is_error": bool(result.get("is_error")), "killed": killed,
            "seconds": int(time.time() - started)}


def wait_ci(repo, pr, timeout_minutes, poll_seconds=60):
    """Waits for the checks of a pull request (gh pr checks: 0 passed, 8 pending, other failed)."""
    deadline = time.time() + timeout_minutes * 60
    while True:
        done = subprocess.run(["gh", "pr", "checks", str(pr)], cwd=repo, capture_output=True, text=True)
        if done.returncode != 8:
            return {"state": "passed" if done.returncode == 0 else "failed", "output": done.stdout[-1500:]}
        if time.time() > deadline:
            return {"state": "timeout", "output": done.stdout[-1500:]}
        time.sleep(poll_seconds)


def journal(cfg, entry):
    folder = cfg.logs / cfg.task
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / "journal.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return folder


def run_task(cfg, poll_seconds=60):
    """The loop. Returns the end state name: done, blocked, question, stalled, exhausted or failed."""
    folder = cfg.logs / cfg.task
    spent, unchanged, extra = 0.0, 0, cfg.note
    for n in range(1, cfg.max_runs + 1):
        before = fingerprint(cfg.repo)
        prompt = PROMPT.format(task=cfg.task, skill=cfg.skill, extra=f"\nNote for this run: {extra}\n" if extra else "")
        folder.mkdir(parents=True, exist_ok=True)
        run = run_claude(cfg, prompt, folder / f"run-{n}.jsonl")
        status = parse_status(run["result"])
        spent += run["cost"]
        changed = fingerprint(cfg.repo) != before
        unchanged = 0 if changed else unchanged + 1
        journal(cfg, {"run": n, "status": status.get("status"), "summary": status.get("summary"), "cost": run["cost"],
                      "spent": round(spent, 4), "seconds": run["seconds"], "killed": run["killed"], "changed": changed,
                      "session": run["session"], "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        print(f"run {n}: {status.get('status')} cost {run['cost']:.2f} total {spent:.2f} changed {changed}", flush=True)
        extra = ""
        if run["killed"] or (run["is_error"] and status["status"] == "unknown"):
            return "failed"
        if status["status"] == "done":
            return "done"
        if status["status"] in ("blocked", "question"):
            print("needs a human:", status.get("question") or status.get("summary"), flush=True)
            return status["status"]
        if spent >= cfg.max_usd_total:
            return "exhausted"
        if unchanged >= cfg.stall_runs:
            return "stalled"
        if status["status"] == "waiting" and status.get("waiting_for") == "ci" and status.get("pr"):
            ci = wait_ci(cfg.repo, status["pr"], cfg.ci_timeout_minutes, poll_seconds)
            extra = f"Checks of pull request {status['pr']} finished: {ci['state']}.\n{ci['output']}"
    return "exhausted"


def parse_args(argv):
    p = argparse.ArgumentParser(description="Run Claude Code headless on one Git task until it is done or must stop.")
    p.add_argument("--repo", required=True, help="path to the target repository checkout")
    p.add_argument("--task", required=True, help="task id as in the repository, for example S115")
    p.add_argument("--skill", default=DEFAULT_SKILL, help="path of the task skill file inside the repository")
    p.add_argument("--max-runs", type=int, default=5)
    p.add_argument("--max-usd-per-run", type=float, default=2.0, help="cap passed to claude --max-budget-usd")
    p.add_argument("--max-usd-total", type=float, default=10.0)
    p.add_argument("--max-minutes", type=int, default=40, help="wall time of one run")
    p.add_argument("--silence-seconds", type=int, default=300, help="a run silent this long is killed")
    p.add_argument("--stall-runs", type=int, default=2, help="runs in a row without any change before stopping")
    p.add_argument("--billing", choices=("max", "api"), default="max",
                   help="max removes ANTHROPIC_API_KEY so the subscription pays; api keeps it")
    p.add_argument("--model", default="sonnet", help="model alias for claude --model; empty uses the CLI default (Opus uses the Max limits fastest)")
    p.add_argument("--allowed-tools", default=DEFAULT_TOOLS)
    p.add_argument("--logs", default=str(Path.home() / ".task-runner"))
    p.add_argument("--note", default="", help="a note for the first run")
    p.add_argument("--claude-cmd", default="", help="override the claude executable, for tests")
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    cmd = [a.claude_cmd] if a.claude_cmd else [shutil.which("claude") or "claude"]
    cfg = Config(repo=Path(a.repo), task=a.task, skill=a.skill, claude_cmd=cmd, max_runs=a.max_runs,
                 max_usd_per_run=a.max_usd_per_run, max_usd_total=a.max_usd_total, max_minutes=a.max_minutes,
                 silence_seconds=a.silence_seconds, stall_runs=a.stall_runs, billing=a.billing, model=a.model,
                 allowed_tools=a.allowed_tools, logs=Path(a.logs), note=a.note)
    if not (cfg.repo / ".git").exists():
        raise SystemExit(f"{cfg.repo} is not a git checkout")
    end = run_task(cfg)
    print(f"end: {end}  journal: {cfg.logs / cfg.task / 'journal.jsonl'}")
    return EXIT[end]


if __name__ == "__main__":
    sys.exit(main())
