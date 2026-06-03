from core.rag.chat import chat_with_meeting, chat_across_meetings

print("=== Single Meeting Chat ===")
result = chat_with_meeting(
    query="What decisions were made?",
    meeting_id=4,
)
print(f"Answer: {result['answer']}")
print(f"Sources used: {len(result['sources'])}")

print()

print("=== Cross Meeting Chat ===")
result = chat_across_meetings(
    query="Any hiring plans mentioned?",
)
print(f"Answer: {result['answer']}")
print(f"Sources used: {len(result['sources'])}")