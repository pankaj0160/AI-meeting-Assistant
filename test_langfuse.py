# test_langfuse.py — run this to verify Langfuse is working
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from dotenv import load_dotenv
load_dotenv()

# Test agents
from server.core.intelligence.agents import (
    run_summary_agent,
    run_action_item_agent,
)

sample_transcript = """
Alice opened the meeting to discuss the Q3 product roadmap.
Bob presented the timeline: deployment is planned for Q2 due to testing needs.
Sarah will review the Q3 budget and report back by Monday.
The team decided to hire two backend engineers for the new infrastructure.
James will schedule a design review by end of week.
"""

print("Testing summary agent...")
summary = run_summary_agent(sample_transcript)
print(f"Summary: {summary[:100]}...")

print("\nTesting action item agent...")
actions = run_action_item_agent(sample_transcript)
print(f"Found {len(actions)} action items")
for a in actions:
    print(f"  - {a.task} (owner: {a.owner})")

print("\n✓ Done! Check your Langfuse dashboard at cloud.langfuse.com")