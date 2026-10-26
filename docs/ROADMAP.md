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
- [AI Development Factory MVP](https://app.notion.com/p/4023e7c2538a81d09d20de4ea4a678e5), the owner's plan and
  decisions. Its Stage 1 criterion is the target here: one task from the order to a checked pull request and a report,
  without the owner driving GitHub by hand. Its open items that touch this runner: the priority of consoles (Claude
  Max, then Codex CLI, then Gemini CLI), the paid API key as a reserve of the machine, and the ministry model of
  roles (position of the unit versus job description of the employee).
The factory polygon (poc-agent repository, folder polygon) played the roles of manager, orchestrator, supervisor
and worker on real tasks. Its lessons that apply here: the workplace is prepared by deterministic code, a stuck
loop is broken by a rule near where it happens, a stop leaves no tails, and an unreadable judgement is never passed
down as an empty instruction.
