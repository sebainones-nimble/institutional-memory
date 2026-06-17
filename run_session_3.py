"""
Session 3 — The "what have you learned?" test (stretch goal S4).

Same agent, same memory store, fresh session. The key difference from
sessions 1 and 2: NO documents are uploaded. The only thing the agent has to
work from is its persistent memory at /mnt/memory/.

Whatever it answers here came entirely from what it chose to remember across
sessions 1 and 2 — so this is the most direct demo of the memory talking back.

Usage:
    python run_session_3.py
"""

import os
from pathlib import Path

from anthropic import Anthropic


REFLECTION_QUESTION = (
    "Don't read any new documents this session — there aren't any. Based only "
    "on what you've stored in your memory across our previous sessions, "
    "summarise everything you've learned about this domain. In particular:\n"
    "  - How does a newly arrived researcher get surface access to human memory, "
    "and how has that process changed over time?\n"
    "  - Who holds which roles on the Council right now, and who recently moved?\n"
    "  - Note anything you previously believed that is now out of date, and when "
    "it changed."
)

OUTPUT_DIR = Path("outputs")


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    for required in (".agent_id", ".environment_id", ".memory_store_id"):
        if not Path(required).exists():
            raise SystemExit(f"Missing {required}. Run create_agent.py first.")

    agent_id = Path(".agent_id").read_text().strip()
    environment_id = Path(".environment_id").read_text().strip()
    memory_store_id = Path(".memory_store_id").read_text().strip()

    client = Anthropic()

    print(f"\nStarting fresh session with same memory store {memory_store_id}...")
    print("(No documents uploaded — the agent must answer purely from memory.)")
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=environment_id,
        title="Session 3 — what have you learned?",
        resources=[
            {
                "type": "memory_store",
                "memory_store_id": memory_store_id,
                "access": "read_write",
                "instructions": (
                    "This is your persistent institutional memory. Mounted at "
                    "/mnt/memory/. It is the ONLY source you have this session. "
                    "Read it thoroughly before answering."
                ),
            }
        ],
    )

    user_message = (
        "Please:\n"
        "1. Check your memory store at /mnt/memory/ and read everything in it.\n"
        "2. Answer the question below using ONLY what you find there.\n"
        "3. If your memory recorded that something changed between sessions, "
        "say what the old value was, what the new value is, and the effective "
        "date.\n\n"
        "==================================================\n"
        f"QUESTION: {REFLECTION_QUESTION}"
    )

    final_text_parts: list[str] = []
    print("\nAgent working...\n")
    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": user_message}],
                }
            ],
        )
        debug_events = bool(os.environ.get("DEBUG_EVENTS"))
        for event in stream:
            etype = getattr(event, "type", "")
            if debug_events:
                print(f"\n>> event: {etype}", flush=True)
            if etype == "agent.message":
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        final_text_parts.append(block.text)
                        print(block.text, end="", flush=True)
            elif etype == "agent.tool_use":
                name = getattr(event, "name", "?")
                inp = getattr(event, "input", {}) or {}
                target = inp.get("path") or inp.get("file_path") or inp.get("command") or ""
                if "/mnt/memory" in str(target):
                    print(f"\n  [memory: {name}  {target}]", flush=True)
                else:
                    print(f"\n  [{name}]", flush=True)
            elif etype == "span.model_request_start":
                # No output streams while the model is thinking; show a
                # heartbeat so a long turn doesn't look like a freeze.
                print("\n  [thinking…]", flush=True)
            else:
                # The session is done when it goes idle. The exact event name
                # has varied across SDK versions, so match defensively rather
                # than waiting forever on one literal string.
                status = getattr(event, "status", None)
                if (
                    etype == "session.status_idle"
                    or etype.endswith(".idle")
                    or status in ("idle", "completed", "ended")
                ):
                    print("\n\n[agent finished]")
                    break

    final_text = "".join(final_text_parts)
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / "session3.txt"
    out.write_text(
        f"=== SESSION 3 — WHAT HAVE YOU LEARNED? ===\n"
        f"Question: {REFLECTION_QUESTION}\n\n--- ANSWER ---\n{final_text}\n"
    )
    print(f"\nSaved to {out}")
    print(
        "\nThis answer came entirely from memory — no docs were uploaded. "
        "That's the demo."
    )


if __name__ == "__main__":
    main()
