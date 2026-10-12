"""Supervisor / Worker engine - the teaching core.

This module is deliberately framework-free. It implements the two agent
patterns we are teaching:

  WORKER    = a single ReAct loop:  think -> call tool -> observe result
              -> (repeat) -> final answer.
              A worker is dumb about the big picture; it focuses on ONE
              well-scoped sub-task and is given a small toolset.

  SUPERVISOR = the orchestrator. It does NOT do the work itself. Instead it
              runs its OWN mini-loop over the plan:

                1. PLAN      - read the task, break it into sub-tasks
                2. DISPATCH  - hand each sub-task to a fresh worker
                3. COLLECT   - wait for every worker to finish
                4. SYNTHESIZE- merge the worker outputs into one answer

  supervisor-worker = divide & conquer: one thinker who delegates to many
              focused workers, then combines the results.

Everything a run does is recorded as a flat list of EVENTS so the web app can
render the whole thing as an annotated, teaching-labelled transcript.

Two backends produce identical event streams:
  - SCRIPTED (default): a fixed, hand-written plan + worker scripts. Zero
    network, zero API key, deterministic - safe for a live demo.
  - LLM       : real OpenRouter calls. The supervisor really breaks the task
    down, each worker really runs a ReAct loop with a `lookup` tool, and the
    supervisor really writes the final synthesis.

KINDS of event (what the UI labels and colours):
  supervisor_think / plan / dispatch / collect / synthesize
  worker_think / worker_tool / worker_result / worker_final / supervisor_final
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Demo knowledge base - the only "world" the scripted workers can observe.
# A real supervisor-worker system would point workers at real tools (APIs,
# files, web search); here one canned `lookup` tool keeps the demo offline.
# ---------------------------------------------------------------------------
KB = {
    "attractions": (
        "Brighton Pier, Royal Pavilion, North Laine (independent shops), "
        "British Airways i360, Brighton Beach, Sea Life, Hove Lawns"
    ),
    "best_stations": (
        "Pier station (most bikes, nearest seafront), "
        "Churchill Square (near shopping), "
        "Brighton Station (main rail hub, good return point)"
    ),
    "routes": (
        "Pier -> Hove Lawns along the seafront (flat, ~3km); "
        "North Laine loop (shops + Pavilion); "
        "i360 -> Pier return"
    ),
    "pricing": (
        "Beryl Brighton: ~£1 unlock + ~£1/hr (prices vary, check app). "
        "Download the Beryl app, scan QR on the bike, dock to end the ride."
    ),
    "weather_rule": (
        "On a windy seafront day, prefer the North Laine loop over Hove."
    ),
}


def lookup(key: str) -> str:
    """The single tool every worker may call. Returns canned facts."""
    return KB.get(key, "No info for %r" % key)


# ---------------------------------------------------------------------------
# Event / transcript model
# ---------------------------------------------------------------------------
@dataclass
class Event:
    agent: str            # "supervisor" or the worker's name
    kind: str             # one of the KINDS above
    text: str             # what happened / what the agent 'said'
    explain: str = ""     # teaching note shown next to the event

    def to_dict(self):
        return {"agent": self.agent, "kind": self.kind,
                "text": self.text, "explain": self.explain}


class Transcript:
    """Flat log of everything that happened, plus ordering metadata."""

    def __init__(self):
        self.events: list[Event] = []
        self.worker_order: list[str] = []

    def add(self, agent, kind, text, explain=""):
        if kind.startswith("worker_") and agent not in self.worker_order:
            self.worker_order.append(agent)
        self.events.append(Event(agent, kind, text, explain))

    def dicts(self):
        return [e.to_dict() for e in self.events]


# ---------------------------------------------------------------------------
# WORKER - one focused ReAct loop over one sub-task
# ---------------------------------------------------------------------------
class Worker:
    def __init__(self, name: str, role: str, script: list[dict] | None = None):
        self.name = name
        self.role = role            # short phrase: what this worker is for
        # scripted steps: [{kind, ...}]; None means "use real LLM"
        self.script = script

    # -- scripted loop ------------------------------------------------------
    def _run_scripted(self, tr: Transcript, tools):
        for step in self.script:
            kind = step["kind"]
            if kind == "think":
                tr.add(self.name, "worker_think", step["text"],
                       "The worker THINKS: it reasons about what to do next.")
            elif kind == "tool":
                key = step["key"]
                result = tools(key)
                tr.add(self.name, "worker_tool",
                       "call tool: lookup(%s)" % key,
                       "It ACTS: picks the one focused tool it was given.")
                tr.add(self.name, "worker_result", repr(result),
                       "It OBSERVES the tool's result and continues the loop.")
            elif kind == "final":
                tr.add(self.name, "worker_final", step["text"],
                       "No more tools needed -> the loop STOPS with a final "
                       "answer for the supervisor.")
        return self.script[-1]["text"]

    # -- real LLM loop ------------------------------------------------------
    def _run_llm(self, tr: Transcript, tools, question: str, max_steps=4):
        from llm import chat

        messages = [
            {"role": "system",
             "content": f"You are a FOCUSED WORKER agent called '{self.name}'."
                         f" Role: {self.role}. You may call the `lookup` tool "
                         "to fetch Brighton facts. Do NOT try to solve the "
                         "whole task - answer ONLY your sub-question, then "
                         "finish with a short plain-text answer."},
            {"role": "user", "content": question},
        ]
        tool_schemas = [{
            "type": "function",
            "function": {
                "name": "lookup",
                "description": "Fetch a canned fact from the demo knowledge "
                               "base (keys: attractions, best_stations, "
                               "routes, pricing, weather_rule).",
                "parameters": {"type": "object",
                               "properties": {"key": {"type": "string"}},
                               "required": ["key"]},
            },
        }]

        answer = ""
        for step in range(1, max_steps + 1):
            reply = chat(messages, tools=tool_schemas)
            msg = reply["choices"][0]["message"]
            if msg.get("content"):
                tr.add(self.name, "worker_think", msg["content"],
                       "The worker THINKS (real model output).")
            calls = msg.get("tool_calls") or []
            if not calls:
                answer = msg.get("content") or ""
                break
            messages.append(msg)
            for tc in calls:
                args = json.loads(tc["function"]["arguments"] or "{}")
                key = args.get("key", "")
                tr.add(self.name, "worker_tool",
                       "call tool: lookup(%s)" % key,
                       "It ACTS by calling its tool.")
                result = tools(key)
                tr.add(self.name, "worker_result", repr(result),
                       "It OBSERVES the result and keeps looping.")
                messages.append({"role": "tool",
                                 "tool_call_id": tc["id"],
                                 "content": result})
        if answer:
            tr.add(self.name, "worker_final", answer,
                   "Loop ends -> final answer handed up to the supervisor.")
        return answer

    def run(self, tr: Transcript, question: str, mode: str):
        """Run this worker's loop and return its final answer string."""
        if mode == "llm" and self.script is None:
            return self._run_llm(tr, lookup, question)
        return self._run_scripted(tr, lookup)


# ---------------------------------------------------------------------------
# SUPERVISOR - plan, dispatch, collect, synthesize
# ---------------------------------------------------------------------------
@dataclass
class Supervisor:
    task: str
    mode: str = "scripted"

    def _plan_scripted(self) -> list[tuple[str, str]]:
        # (worker_name, sub-question) for the canned Brighton-tour task
        return [
            ("routes",
             "Suggest 3 short, scenic Beryl bike routes around Brighton."),
            ("stations",
             "Which Beryl stations are best to start from and return to?"),
            ("tips",
             "Give practical tips for using Beryl (booking, pricing, docking)."),
        ]

    def _plan_llm(self, tr: Transcript) -> list[tuple[str, str]]:
        from llm import chat

        messages = [
            {"role": "system",
             "content": "You are a SUPERVISOR agent. Your ONLY job is to break "
                        "the user's task into 2-4 independent sub-tasks that "
                        "can each be answered by a separate focused worker. "
                        "Reply with STRICT JSON only: "
                        '[{"name": "short_lowercase", "question": "..."}]'},
            {"role": "user", "content": self.task},
        ]
        raw = chat(messages)["choices"][0]["message"]["content"]
        tr.add("supervisor", "supervisor_think",
               "Breaking the task into sub-tasks (real model output).")
        try:
            plan = json.loads(raw)
        except Exception:  # noqa: BLE001 - model didn't return clean JSON
            plan = [{"name": "worker", "question": self.task}]
        tr.add("supervisor", "plan",
               "Plan: " + json.dumps([
                   {"worker": p.get("name", "w"), "question": p.get("question", "")}
                   for p in plan]))
        return [(p.get("name", "w"), p.get("question", "")) for p in plan]

    def _build_workers(self, plan_names: list[str]) -> list[Worker]:
        # Scripted mode: give each planned worker a hand-written script.
        scripts = {
            "routes": [
                {"kind": "think",
                 "text": "I need the key Brighton attractions to anchor routes."},
                {"kind": "tool", "key": "attractions"},
                {"kind": "think",
                 "text": "I also recall the canned route suggestions."},
                {"kind": "tool", "key": "routes"},
                {"kind": "final",
                 "text": "Route 1: Pier -> Hove Lawns along the seafront "
                         "(flat, ~3km). Route 2: North Laine loop (shops + "
                         "Royal Pavilion). Route 3: i360 -> Pier return."},
            ],
            "stations": [
                {"kind": "think",
                 "text": "I should fetch the recommended stations."},
                {"kind": "tool", "key": "best_stations"},
                {"kind": "final",
                 "text": "Start at Pier station (most bikes, right on the "
                         "seafront) and return to Brighton Station or "
                         "Churchill Square depending on your onward plan."},
            ],
            "tips": [
                {"kind": "think", "text": "Let me pull the pricing info."},
                {"kind": "tool", "key": "pricing"},
                {"kind": "final",
                 "text": "Download the Beryl app, scan the QR, unlock (~£1 + "
                         "~£1/hr, check the app), ride, then dock at any "
                         "station to end. Dock fully or the ride keeps "
                         "charging."},
            ],
        }
        return [Worker(name, "focuses on: " + question, scripts.get(name))
                for name, question in
                zip(plan_names, [q for _, q in self._plan_scripted()])] \
            if self.mode == "scripted" else \
            [Worker(name, "a focused sub-task worker") for name in plan_names]

    def run(self) -> Transcript:
        tr = Transcript()

        tr.add("supervisor", "supervisor_think",
               "Read the task and decide whether to delegate.",
               "The SUPERVISOR starts. It does not dive into the work - it "
               "first decides how to package the task.")
        tr.add("supervisor", "plan",
               "Decompose: split the task into independent sub-tasks, one per "
               "worker.",
               "PLAN STEP: break the problem into focused, independently "
               "answerable pieces. Parallelism only works if sub-tasks don't "
               "depend on each other.")

        if self.mode == "llm":
            plan = self._plan_llm(tr)
            workers = self._build_workers([p[0] for p in plan])
            paired = [(workers[i], plan[i][1]) for i in range(len(plan))]
        else:
            plan = self._plan_scripted()
            workers = self._build_workers([p[0] for p in plan])
            paired = [(workers[i], plan[i][1]) for i in range(len(plan))]

        tr.add("supervisor", "dispatch",
               "Dispatch each sub-task to a fresh worker.",
               "DISPATCH STEP: the supervisor hands each sub-task to a NEW "
               "worker of its own. The supervisor pauses talking and lets the "
               "workers do the real work - often in parallel.")

        answers = {}
        for w, question in paired:
            tr.add("supervisor", "dispatch",
                   "-> worker '%s' (incoming sub-task)" % w.name)
            answers[w.name] = w.run(tr, question, self.mode)

        tr.add("supervisor", "collect",
               "All workers have reported back.",
               "COLLECT STEP: every worker has stopped its loop and returned "
               "a final answer. The supervisor waits for ALL of them before "
               "moving on - it cannot synthesise a partial picture "
               "meaningfully.")

        tr.add("supervisor", "synthesize",
               "Merge the worker answers into one coherent response.",
               "SYNTHESIZE STEP: the supervisor combines the pieces, resolves "
               "any overlap, keeps the good bits and writes the final answer "
               "back to the user.")

        final = self._synthesize(answers)
        tr.add("supervisor", "supervisor_final", final,
               "The supervisor's own final answer is the deliverable. The "
               "workers never talk to the user - everything goes through the "
               "supervisor.")
        return tr

    def _synthesize(self, answers: dict[str, str]) -> str:
        if self.mode == "llm":
            from llm import chat

            block = "\n\n".join(f"[{k}] {v}" for k, v in answers.items())
            messages = [
                {"role": "system",
                 "content": "You are the SUPERVISOR. Merge the workers' "
                            "reports into ONE friendly, well-structured final "
                            "answer for the user."},
                {"role": "user", "content": self.task + "\n\nWORKER "
                                            "REPORTS:\n" + block},
            ]
            raw = chat(messages)["choices"][0]["message"]["content"]
            return raw or ("\n\n".join(answers.values()))
        return (
            "Here's your half-day Beryl bikeshare tour of Brighton:\n\n"
            "  ROUTES (from the 'routes' worker)\n" + answers.get("routes", "") + "\n\n"
            "  BEST STATIONS (from the 'stations' worker)\n" + answers.get("stations", "") + "\n\n"
            "  PRACTICAL TIPS (from the 'tips' worker)\n" + answers.get("tips", "") + "\n"
        )


def run(task: str, mode: str = "scripted") -> dict:
    """Top-level entry: run the supervisor-worker system, return a renderable
    dict with the task, the transcript events, and the final answer."""
    supervisor = Supervisor(task, mode=mode)
    tr = supervisor.run()
    return {
        "task": task,
        "mode": mode,
        "events": tr.dicts(),
        "workers": tr.worker_order,
        "final": [e for e in tr.events if e.kind == "supervisor_final"][-1].text,
    }


DEFAULT_TASK = (
    "Help me plan a half-day Brighton city tour using Beryl bikeshare: "
    "suggest 3 ride routes, the best start/return stations, and practical "
    "booking tips."
)
