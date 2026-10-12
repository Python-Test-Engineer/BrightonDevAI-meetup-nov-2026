"""Supervisor / Worker teaching web app.

Run:  uv run app.py   ->  http://127.0.0.1:5010

Two modes:
  scripted (default) - a fixed supervisor plan + worker scripts. No API key,
                       deterministic. Use this to teach the loop on stage.
  llm                - real OpenRouter calls. The supervisor really decomposes
                       the task, each worker really runs a ReAct loop with a
                       `lookup` tool, and the supervisor really synthesises.

The page renders the full run as an annotated transcript: every THINK, tool
CALL, tool RESULT and FINAL step is labelled with the teaching note that
explains what is happening and why.
"""

from __future__ import annotations

from flask import Flask, render_template, request

import engine

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", default_task=engine.DEFAULT_TASK)


@app.route("/run", methods=["POST"])
def run():
    task = (request.form.get("task") or "").strip()
    mode = request.form.get("mode", "scripted")
    if not task:
        task = engine.DEFAULT_TASK
    error = None
    result = None
    try:
        result = engine.run(task, mode=mode)
    except Exception as e:  # noqa: BLE001 - surface to the UI, don't crash
        error = f"{type(e).__name__}: {e}"

    # Group the flat event list into per-agent bands for clean rendering,
    # preserving the order in which agents first appeared.
    groups = []
    by_agent = {}
    if result is not None:
        for ev in result["events"]:
            if ev["agent"] not in by_agent:
                band = {"agent": ev["agent"], "items": []}
                by_agent[ev["agent"]] = band
                groups.append(band)
            by_agent[ev["agent"]]["items"].append(ev)

    return render_template("run.html", result=result, error=error,
                           groups=groups, task=task, mode=mode)


if __name__ == "__main__":
    print("Supervisor/Worker teaching app -> http://127.0.0.1:5010")
    app.run(debug=False, host="127.0.0.1", port=5010)
