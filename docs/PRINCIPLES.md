# Principles

## 1. Definitions
1.1. Task: a folder in a Git repository with its description, checks and history.
1.2. Checkpoint: the record in Git that says where a task stopped and what comes next.
1.3. Run: one headless invocation that resumes a task from its checkpoint and ends with a status line.
1.4. Status: one of done, continue, waiting, blocked, question, or unknown when the line is missing.
1.5. Runner: the program that starts runs one after another and decides when to stop.
1.6. Stop: the end state of the runner: done, needs a human, stalled, out of runs or money, failed.

## 2. Norms
2.1. The state of a task lives in Git. A run keeps nothing the next run needs in a model's memory.
2.2. The runner decides when to stop, by rule. The model decides what to do inside a run. The runner never judges
     the content of the work, the model never decides the stop.
2.3. Every run is bounded in money, in wall time and in silence. A run over a bound is killed with its whole
     process tree.
2.4. A loop is a stop. Runs in a row that change nothing in the repository end the work.
2.5. A question or a block goes to a human and ends the work. The runner does not answer it.
2.6. One task at a time. Another task is another start of the runner.
2.7. The runner grants no authority. What a run may do is the allowed tools list and the target repository's own
     rules, including merge and deploy rules.
2.8. The wallet that pays is chosen explicitly, never by accident of the environment (docs/BILLING.md).

## 3. Special part
3.1. Defaults: 5 runs, 10 USD in total, 2 USD, 40 minutes and 300 silent seconds per run, 2 unchanged runs as a loop.
3.2. The first target is the job search bot repository and its skill job-search-tasks.
