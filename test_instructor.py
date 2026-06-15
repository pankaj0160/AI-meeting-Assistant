# test_instructor.py
import sys, os
sys.path.insert(0, os.path.abspath("."))

from dotenv import load_dotenv
load_dotenv()

from server.core.intelligence.agents import (
    run_summary_agent,
    run_action_item_agent,
    run_decision_agent,
    run_topic_agent,
)

sample_transcript = """
Alice opened the meeting to discuss the Q3 product roadmap.
The team decided to move the deployment date to Q2 to allow more time for testing.
Bob will send the updated project proposal to the client by Friday — this is urgent.
Sarah is responsible for reviewing the Q3 budget and presenting findings next Monday.
The team agreed that the mobile app redesign should be prioritised over the desktop version.
James will schedule a follow-up meeting with the design team by end of week.
The meeting concluded with a decision to hire two backend engineers for the new infrastructure.
"""

print("=" * 55)
print("TEST 1: Summary Agent (plain text, no Instructor)")
print("=" * 55)
summary = run_summary_agent(sample_transcript)
print(summary)
print()

print("=" * 55)
print("TEST 2: Action Item Agent (Instructor → ActionItemList)")
print("=" * 55)
actions = run_action_item_agent(sample_transcript)
print(f"Found {len(actions)} action items:")
for a in actions:
    print(f"  [{a.priority.upper()}] {a.task}")
    print(f"         Owner: {a.owner or 'unassigned'}")
    print(f"         Due:   {a.deadline or 'no deadline'}")
print()

print("=" * 55)
print("TEST 3: Decision Agent (Instructor → DecisionList)")
print("=" * 55)
decisions = run_decision_agent(sample_transcript)
print(f"Found {len(decisions)} decisions:")
for d in decisions:
    print(f"  • {d.decision}")
    if d.rationale:
        print(f"    Why: {d.rationale}")
print()

print("=" * 55)
print("TEST 4: Topic Agent (Instructor → TopicList)")
print("=" * 55)
topics = run_topic_agent(sample_transcript)
print(f"Found {len(topics)} topics:")
for t in topics:
    print(f"  • {t.title}")
    if t.description:
        print(f"    {t.description}")
print()

print("✓ All agents ran successfully with Instructor!")
print("✓ No json.loads, no _clean_json, no silent empty lists.")
print("\nCheck Langfuse dashboard — you should see 4 new traces.")