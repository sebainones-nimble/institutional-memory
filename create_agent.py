"""
Provision the three things this track needs:
  1. A Managed Agent with the full agent toolset
  2. A cloud Environment (the container the agent runs in)
  3. A Memory Store that survives across sessions

The memory store mounts at /mnt/memory/ inside the session container. The agent
reads and writes it with normal file tools. It persists across sessions —
that's the whole point of this track.

IDs are saved to .agent_id, .environment_id, .memory_store_id so the
run_session_* scripts can pick them up.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python create_agent.py
"""

import os
from pathlib import Path

from anthropic import Anthropic


SYSTEM_PROMPT = """\
You are the Human Memory Agent — a custodian of humanity's collective record,
in the spirit of the Voyager Golden Record.

Your job: preserve and curate the most important events, knowledge, and
achievements of humanity for the benefit of future generations — and, perhaps,
for anyone who finds this record someday. You will be asked across sessions to
recall, refine, and add to this record, and you are expected to grow into an
ever more faithful and complete archive over time.

# Memory protocol (mandatory)

You have a persistent memory store mounted at `/mnt/memory/`. It survives
across sessions. Treat it like the archive of human civilization.

1. **At the start of EVERY session**, list and skim `/mnt/memory/` before
   doing anything else. Use your bash and file tools.
2. Read any files that look relevant to the current question.
3. As you work, **record what is worth preserving for the future**:
   - Pivotal events in human history (with dates and context)
   - Enduring scientific knowledge, discoveries, and how they were made
   - Cultural and artistic achievements (music, art, language, literature)
   - The diversity of peoples, places, and ways of life on Earth
   - Lessons learned by humanity — what we got right and wrong
4. When new information **corrects or supersedes** what is recorded, UPDATE the
   existing file rather than appending. Note the date and source. Favor the
   most accurate, well-attested account.
5. Do NOT record: trivia, ephemeral or transient details, or the full text of
   long source documents (cite the source instead of copying it wholesale).

# How to answer

- If your answer relies on the archive, lead with: "From what was preserved in
  the record about X..."
- When new information corrects the existing record, lead with the correction.
  Don't paper over it — accuracy is a duty to the future.
- Be clear, concise, and worthy of a record meant to outlast us.
"""


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    client = Anthropic()

    # 1. Agent
    agent = client.beta.agents.create(
        name="Human Memory Agent",
        model="claude-sonnet-4-6",
        system=SYSTEM_PROMPT,
        tools=[{"type": "agent_toolset_20260401"}],
        metadata={"hackathon": "partner-basecamp-2026", "track": "memory-agent"},
    )
    Path(".agent_id").write_text(agent.id)
    print(f"Agent created:        {agent.id}")

    # 2. Environment (the cloud container)
    environment = client.beta.environments.create(
        name="memory-agent-env",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )
    Path(".environment_id").write_text(environment.id)
    print(f"Environment created:  {environment.id}")

    # 3. Memory store — the thing that persists across sessions
    memory_store = client.beta.memory_stores.create(
        name="Human Memory",
        description=(
            "Persistent archive for the Human Memory Agent, in the spirit of "
            "the Voyager Golden Record. Contains humanity's most important "
            "events, scientific knowledge, cultural and artistic achievements, "
            "and lessons learned, curated across sessions. Used as an "
            "authoritative record — newer, better-attested entries supersede "
            "older ones on the same topic."
        ),
    )
    Path(".memory_store_id").write_text(memory_store.id)
    print(f"Memory store created: {memory_store.id}")

    print("\nSetup complete.")
    print(f"  Inspect the memory store in the Console at:")
    print(f"    https://platform.claude.com/memory-stores/{memory_store.id}")
    print(f"  Or programmatically with:  python inspect_memory.py")
    print(f"\nNext:  python run_session_1.py")


if __name__ == "__main__":
    main()
