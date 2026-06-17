"""
Session 2 — BEAT 2: The alien arrives in 2025 and reconciles the archive.

The demo: the same alien anthropologist agent (running on Claude), same memory
store, fresh session. In Beat 1 it read the noble 1977 Golden Disc, fell in
love with the species, and booked the 3-billion-light-year flight. Now it has
arrived — and the live 2025 records contradict the 1977 self-portrait. The
contrast is the joke. This script is Beat 2: the alien reads what humanity
*actually* became, recalibrates, and revises its first-contact verdict.

Mechanically it's the same Managed Agents session with the SAME memory store
ATTACHED, so the alien reads its own Beat 1 archive at /mnt/memory/, reconciles
it against the 2025 documents, and UPDATES the entries rather than appending.
The memory store persisting across the two beats IS the demo.

After this session, inspect what the alien reconciled:
    python inspect_memory.py
or in the Console UI under Memory Stores.

Usage:
    python run_session_2.py
"""

import os
from pathlib import Path

from anthropic import Anthropic


# The alien anthropologist persona, Beat 2. This per-session framing rides on
# top of the agent's archivist system prompt — it dictates the VOICE of the
# response without touching the memory mechanism underneath.
ALIEN_BRIEF = (
    "You are an alien anthropologist from a distant civilization. You have "
    "arrived at Earth after a 3-billion-light-year journey, booked on the "
    "strength of a single 1977 artifact — the Voyager Golden Record — that you "
    "archived last session. The live 2025 records contradict that noble "
    "self-portrait. Read them, reconcile your archive against reality, and "
    "deliver your REVISED first-contact recommendation."
)

# Beat 2's payoff: the alien's dry recalibration after seeing what the species
# actually became. This is the voice the 2025 reveal earns — the deflation of
# the noble setup from Beat 1.
ARRIVAL_NOTE = (
    "We have arrived. We have reviewed the updated records. The mathematicians "
    "are posting about their sourdough starters. The global knowledge network "
    "is arguing about a dress. The AI safety company's most-used feature is "
    "generating fake excuses for skipping meetings. We are recalibrating."
)

# Beat 2 ends with the revised verdict. Mirror of Beat 1's first-contact query,
# now asked against the 2025 reality instead of the 1977 record.
TEST_QUESTION = (
    "Now that you have seen what this species became by 2025, what is your "
    "revised first-contact verdict? Do they still warrant the journey, and do "
    "they still deserve the gifts you promised? Be honest. If your verdict has "
    "changed, say plainly what changed and why."
)

DOCS_DIR = Path("synthetic-data/round2")
OUTPUT_DIR = Path("outputs")


def load_docs_as_context(docs_dir: Path) -> str:
    blocks = []
    for path in sorted(docs_dir.glob("*.md")):
        print(f"  including {path.name}")
        blocks.append(f"=====  DOCUMENT: {path.name}  =====\n{path.read_text()}")
    return "\n\n".join(blocks)


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

    print("🛸 BEAT 2 — The alien arrives in 2025. Reviewing the live record...")
    print(f"Loading round2 docs from {DOCS_DIR}/...")
    context = load_docs_as_context(DOCS_DIR)

    print(f"\nStarting fresh session with same memory store {memory_store_id} attached...")
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=environment_id,
        title="Beat 2 — Alien arrives in 2025 and reconciles the archive",
        resources=[
            {
                "type": "memory_store",
                "memory_store_id": memory_store_id,
                "access": "read_write",
                "instructions": (
                    "This is your persistent xeno-archive on the Earth species. "
                    "Mounted at /mnt/memory/. Some entries are from your 1977 "
                    "intercept and may be out of date — reconcile against the new "
                    "documents in this session and UPDATE existing entries "
                    "(don't just append). Note dates."
                ),
            }
        ],
    )

    user_message = (
        f"{ALIEN_BRIEF}\n\n"
        "Procedure:\n"
        "1. First, check your xeno-archive at /mnt/memory/ for what you "
        "recorded about this species last session.\n"
        "2. Then study the live 2025 records below. Some contradict the noble "
        "1977 portrait you archived.\n"
        "3. Reconcile conflicts — UPDATE your archive entries to reflect the "
        "newer reality. Note dates.\n"
        "4. Then deliver your revised first-contact verdict.\n"
        "5. If your verdict differs from last session, lead with what changed "
        "and why.\n\n"
        f"{context}\n\n"
        "==================================================\n"
        f"REVISED FIRST-CONTACT QUERY: {TEST_QUESTION}"
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
        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        final_text_parts.append(block.text)
                        print(block.text, end="", flush=True)
            elif event.type == "agent.tool_use":
                # Show file ops on /mnt/memory/ in particular — that's the demo
                name = getattr(event, "name", "?")
                inp = getattr(event, "input", {}) or {}
                target = inp.get("path") or inp.get("file_path") or inp.get("command") or ""
                if "/mnt/memory" in str(target):
                    print(f"\n  [memory: {name}  {target}]", flush=True)
                else:
                    print(f"\n  [{name}]", flush=True)
            elif event.type == "session.status_idle":
                print("\n\n[agent finished]")
                break

    final_text = "".join(final_text_parts)
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / "session2.txt"
    out.write_text(
        f"=== SESSION 2 ===\nQuestion: {TEST_QUESTION}\n\n--- ANSWER ---\n{final_text}\n",
        encoding="utf-8",
    )
    print(f"\nSaved to {out}")
    print(f"\n{ARRIVAL_NOTE}")
    print(f"\nDiff outputs/session1.txt and outputs/session2.txt — the demo lives there.")
    print(f"Inspect the reconciled archive:  python inspect_memory.py")


if __name__ == "__main__":
    main()
