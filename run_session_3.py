"""
Session 3 — BEAT 3: The alien briefs the colleagues, from memory alone.

The demo: the same alien anthropologist agent (running on Claude), same memory
store, fresh session — but this time NO documents are attached. In Beat 1 it
read the noble 1977 Golden Record and fell in love; in Beat 2 it arrived and
reconciled that against the 2025 reality. Now new colleagues are taking over the
survey, and the alien must brief them using ONLY what it committed to
/mnt/memory/ across the two earlier beats.

Whatever it says here came entirely from its archive — no documents are
uploaded. That is the most direct demo of the memory talking back.

After this session, inspect the archive it spoke from:
    python inspect_memory.py

Usage:
    python run_session_3.py
"""

import os
from pathlib import Path

from anthropic import Anthropic


# The alien anthropologist persona, Beat 3. This per-session framing rides on
# top of the agent's archivist system prompt — it dictates the VOICE of the
# response without touching the memory mechanism underneath.
ALIEN_BRIEF = (
    "You are the alien anthropologist who has now surveyed the Earth species "
    "twice — first through their hopeful 1977 Voyager Golden Record, then "
    "through the unfiltered 2025 reality you found when you arrived. New "
    "colleagues are arriving to take over the survey. Brief them using ONLY "
    "your archive — no new records have come in this session."
)

# Beat 3's payoff: the whole arc, recited from memory. No documents are
# attached, so every fact below must come from /mnt/memory/.
REFLECTION_QUESTION = (
    "Speaking only from your xeno-archive at /mnt/memory/, brief the colleagues "
    "arriving after you:\n"
    "  - What is this species? What did the 1977 record show, and what did the "
    "2025 reality reveal?\n"
    "  - What did you first believe about them that you later had to revise — "
    "and when did that change?\n"
    "  - Your final, current first-contact verdict, and what gifts (if any) we "
    "should bring."
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

    print("🛸 BEAT 3 — New colleagues arrive. The alien briefs them from memory alone...")
    print("(No documents attached — the xeno-archive is the only source.)")

    print(f"\nStarting fresh session with same memory store {memory_store_id} attached...")
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=environment_id,
        title="Beat 3 — Alien briefs the colleagues from memory alone",
        resources=[
            {
                "type": "memory_store",
                "memory_store_id": memory_store_id,
                "access": "read_write",
                "instructions": (
                    "This is your persistent xeno-archive on the Earth species. "
                    "Mounted at /mnt/memory/. It is the ONLY source you have this "
                    "session — no new documents. Read it thoroughly before "
                    "answering."
                ),
            }
        ],
    )

    user_message = (
        f"{ALIEN_BRIEF}\n\n"
        "Procedure:\n"
        "1. Check your xeno-archive at /mnt/memory/ and read everything in it.\n"
        "2. Answer using ONLY what you find there — no new documents.\n"
        "3. Where your archive records that your assessment changed, say what "
        "you first believed (1977), what you revised it to (2025), and when.\n\n"
        "==================================================\n"
        f"BRIEFING REQUEST: {REFLECTION_QUESTION}"
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
                # Show file ops on /mnt/memory/ in particular — that's the demo
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
        f"=== SESSION 3 — THE ALIEN'S BRIEFING (MEMORY ONLY) ===\n"
        f"Question: {REFLECTION_QUESTION}\n\n--- ANSWER ---\n{final_text}\n",
        encoding="utf-8",
    )
    print(f"\nSaved to {out}")
    print(
        "\n🛸 Everything above came from the archive — no documents were "
        "uploaded this session. That's the demo: the memory talking back."
    )


if __name__ == "__main__":
    main()
