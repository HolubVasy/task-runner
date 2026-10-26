# Roadmap

## Verified
- The loop, the stop rules, the watch, the billing switch and the journal, with a fake `claude`
  (python -m unittest discover -s tests, 9 tests).
- Earlier, on a server (Linux): `claude -p` reads the prompt from stdin, accepts `--output-format stream-json`,
  `--verbose`, `--max-budget-usd`, `--permission-mode acceptEdits` and `--allowedTools`, and reports the cost in
  the final result event.

- On the owner's Windows machine (Claude Code 2.1.302): the unit tests pass, including the kill of a silent run, and `claude -p` reads the prompt from stdin and answers in JSON. The default model of that CLI is Opus 5.5, hence the `--model` option with sonnet as the default here.

## Not verified
- A real multi-run task on Windows with the allowed tools and the skill.
- That the standing prompt makes the model end with the status line every time. The runner treats a missing line as
  `unknown`, which counts as no progress.
- That Claude Code finds the skill file by the path in the prompt. It is read as a plain file.
- The allowed tools default is a guess. Tighten or widen it with `--allowed-tools`.

## Next
1. First supervised run on a small task, read the journal and the raw stream, tune the prompt.
2. A rule for the loop that looks at the difference of the checkpoint records, not only at any change.
3. Waiting for review comments the same way as for checks.
4. Several tasks in a queue, one after another, each by its own record. No parallel tasks until one is stable.

## Related
The factory polygon (poc-agent repository, folder polygon) played the roles of manager, orchestrator, supervisor
and worker on real tasks. Its lessons that apply here: the workplace is prepared by deterministic code, a stuck
loop is broken by a rule near where it happens, a stop leaves no tails, and an unreadable judgement is never passed
down as an empty instruction.
