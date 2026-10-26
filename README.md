# task-runner

Runs Claude Code headless (`claude -p`) on ONE task of a Git repository, again and again, until the task is
done, needs a human, stalls, or runs out of money. You hand it a task number. It does the rest and stops by rule.

## Why

An interactive chat spends the owner's attention and subscription on long autonomous work. Headless runs spend
neither: a run reads the task's recorded checkpoint in Git, takes the next step, records the checkpoint, and ends.
The next run starts fresh from the same record. State lives in Git, not in a model's memory, so a stop is
resumable and any run can be replaced.

## What it is not

Not a task tracker (tasks live in the target repository), not an orchestrator of many tasks, not a merge or deploy
tool. It grants no authority beyond the allowed tools list and the target repository's own rules.

## Quick start (Windows PowerShell)

Needs Python 3.10 or newer, `git`, the `gh` CLI (`gh auth login`) and Claude Code logged in
(`claude`, then `/login` with the Max account).

```
git clone https://github.com/HolubVasy/task-runner
cd task-runner
python runner.py --repo C:\work\linkedin-ai-job-cv-generator --task S115 --max-runs 3 --max-usd-per-run 2
```

Defaults: billing `max` (the subscription pays, see docs/BILLING.md), 5 runs, 10 USD in total, 40 minutes and
300 seconds of silence per run. The task skill is read from `.agents/skills/job-search-tasks/SKILL.md` of the
target repository, change it with `--skill`.

## What one run does

1. Reads the skill file and resumes the task from its checkpoint records.
2. Does the next meaningful step and records the checkpoint.
3. Ends with one JSON line: `{"status": "done|continue|waiting|blocked|question", "summary": "...", ...}`.

The runner then stops on `done`, `blocked`, `question`, a killed run, the money cap, or two runs in a row without
any change in the repository (a loop). On `waiting` for a pull request it waits for the checks with
`gh pr checks`, then starts the next run with their result. Exit codes: 0 done, 2 needs a human, 3 stalled,
4 out of runs or money, 5 failed or killed.

The journal of runs is `~/.task-runner/<task>/journal.jsonl`, each run's raw stream next to it.

## Tests

```
python -m unittest discover -s tests
```

They use a fake `claude` and cost nothing. The real `claude` flags and Windows behaviour are not covered by them,
see docs/ROADMAP.md.

## Documents

- docs/PRINCIPLES.md, the concept: definitions and norms.
- docs/BILLING.md, which wallet pays for what.
- docs/ROADMAP.md, what is verified and what comes next.
