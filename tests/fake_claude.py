"""A stand-in for the claude executable: reads the prompt, answers with a stream-json result.
FAKE_STATUSES is a comma list of statuses, one per run; FAKE_TOUCH=1 writes a file so the repository changes;
FAKE_COST is the cost of a run; FAKE_SLEEP makes the run silent for that many seconds first."""
import json
import os
import sys
import time

sys.stdin.read()
if os.environ.get("FAKE_ARGS"):
    open(os.environ["FAKE_ARGS"], "w").write(" ".join(sys.argv[1:]))
state = os.environ["FAKE_STATE"]
n = int(open(state).read()) + 1 if os.path.exists(state) else 1
open(state, "w").write(str(n))
time.sleep(float(os.environ.get("FAKE_SLEEP", "0")))
statuses = os.environ.get("FAKE_STATUSES", "done").split(",")
status = statuses[min(n, len(statuses)) - 1]
if os.environ.get("FAKE_TOUCH") == "1":
    open(f"touch-{n}.txt", "w").write("x")
answer = "worked\n" + json.dumps({"status": status, "summary": f"run {n}", "question": "which?" if status == "question" else None})
print(json.dumps({"type": "system", "subtype": "init"}), flush=True)
print(json.dumps({"type": "result", "result": answer, "total_cost_usd": float(os.environ.get("FAKE_COST", "0.01")),
                  "session_id": f"s{n}", "is_error": False}), flush=True)
