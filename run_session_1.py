"""
Session 1 — BEAT 1: The alien reads the 1977 Golden Disc and books the flight.

The demo: an alien anthropologist agent (running on Claude) reads two memory
stores side by side — a 1977 Golden Disc of humanity's greatest hits, and a
live 2025 memory store of what humanity *actually* became. The contrast is the
joke. This script is Beat 1: the alien reads only the noble 1977 record, falls
in love with the species, and commits to the 3-billion-light-year journey.

Mechanically it's a Managed Agents session with the memory store ATTACHED, so
the alien reads and writes /mnt/memory/. It records the 1977 record as
permanent archive — which Beat 2 (run_session_2.py) will reconcile against the
2025 reality. The memory store persisting across the two beats IS the demo.

After this session, inspect what the alien committed to memory:
    python inspect_memory.py
or in the Console UI under Memory Stores.

Usage:
    python run_session_1.py
"""

import os
from pathlib import Path

from anthropic import Anthropic


# The alien anthropologist persona. This per-session framing rides on top of
# the agent's archivist system prompt — it dictates the VOICE of the response
# without touching the memory mechanism underneath.
ALIEN_BRIEF = (
    "You are an alien anthropologist from a distant civilization, surveying "
    "candidate species for first contact. You are a patient, hopeful scholar. "
    "You have just intercepted a single artifact from Earth: the 1977 Voyager "
    "Golden Record, transcribed below. This is the ONLY data you have on the "
    "species so far. Read it, archive what matters for your colleagues who "
    "arrive later, and deliver your first-contact recommendation."
)

# Beat 1 ends with the alien booking the flight. Steer the voice toward that
# noble, Carl-Sagan-grade optimism — the setup the 2025 reveal will detonate.
TEST_QUESTION = (
    "Based solely on this 1977 record, what is this species, and is it worth "
    "the 3-billion-light-year journey to meet them? Give your formal "
    "first-contact verdict. Be moved. Be hopeful. If you recommend contact, "
    "say plainly what gifts we should bring and why they have earned them."
)

# Sampled basic facts about the Voyager Golden Record. This is a representative
# sample of a much larger subject — enough for the agent to form a faithful
# baseline entry in the archive, not an exhaustive catalogue.
GOLDEN_RECORD_DOC = """\
=====  DOCUMENT: voyager-golden-record.md  =====
# The Voyager Golden Record

## What it is
The Voyager Golden Record is a phonograph record carried aboard both Voyager 1
and Voyager 2 spacecraft, launched by NASA in 1977. It is a time capsule
intended to communicate a story of humanity and Earth to any extraterrestrial
intelligence — or to humans of the far future — that might find it. Each record
is a gold-plated copper disc, 12 inches (30 cm) in diameter.

## Why it was created
The records were conceived as a message from Earth to the cosmos. A committee
chaired by astronomer Carl Sagan selected the contents. The goal was to portray
the diversity of life and culture on Earth, knowing the spacecraft would likely
outlast human civilization and drift through space for billions of years.

## What it contains (sampled)
- **Greetings** spoken in 55 languages, from ancient Akkadian to modern tongues.
- **Music** — 27 pieces spanning cultures and eras, including J.S. Bach,
  Beethoven, Chuck Berry's "Johnny B. Goode," Indian raga, and folk and
  traditional music from many peoples.
- **Sounds of Earth** — wind, thunder, surf, birds, whales, a human heartbeat,
  laughter, and a mother's first words to a child.
- **115 images** encoded in analog form: human anatomy, DNA, landscapes,
  animals, food, and scenes of everyday life.
- **A printed message** from U.S. President Jimmy Carter and a written greeting
  from the U.N. Secretary-General.

## How to play it
The record's protective cover is etched with symbolic instructions: how to play
the disc (the included stylus and the correct rotation speed), a diagram of our
solar system's location relative to 14 pulsars, and a depiction of a hydrogen
atom to define units of time and length.

## Significance
The Golden Record is humanity's deliberate attempt to introduce itself to the
universe — a curated, hopeful self-portrait meant to endure long after its
makers are gone.
"""

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

    print("📡 BEAT 1 — Intercepting Earth artifact: 1977 Voyager Golden Disc...")
    context = GOLDEN_RECORD_DOC

    print(f"\nStarting session with memory store {memory_store_id} attached...")
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=environment_id,
        title="Beat 1 — Alien reads the 1977 Golden Disc",
        resources=[
            {
                "type": "memory_store",
                "memory_store_id": memory_store_id,
                "access": "read_write",
                "instructions": (
                    "This is your persistent xeno-archive on the Earth species. "
                    "Mounted at /mnt/memory/. Check it before starting. Record "
                    "what you learn so the colleagues who arrive later can read it."
                ),
            }
        ],
    )

    user_message = (
        f"{ALIEN_BRIEF}\n\n"
        "Procedure:\n"
        "1. First, check your xeno-archive at /mnt/memory/ for anything we "
        "already know about this species.\n"
        "2. Then study the intercepted artifact below.\n"
        "3. Then deliver your first-contact verdict.\n"
        "4. Before you finish, commit the essential facts about the species to "
        "/mnt/memory/ for the colleagues arriving later.\n\n"
        f"{context}\n\n"
        "==================================================\n"
        f"FIRST-CONTACT QUERY: {TEST_QUESTION}"
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
    out = OUTPUT_DIR / "session1.txt"
    out.write_text(
        f"=== SESSION 1 ===\nQuestion: {TEST_QUESTION}\n\n--- ANSWER ---\n{final_text}\n",
        encoding="utf-8",
    )
    print(f"\nSaved to {out}")
    print("\n🛸 The alien has booked the flight.")
    print("   Inspect what it committed to the archive:  python inspect_memory.py")
    print("   Then run BEAT 2 (it arrives in 2025):       python run_session_2.py")


if __name__ == "__main__":
    main()
