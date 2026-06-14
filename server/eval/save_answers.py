# server/eval/save_answers.py
import json, sys, os, time

sys.path.insert(0, r"C:\Projects\Summly")

from dotenv import load_dotenv
load_dotenv(r"C:\Projects\Summly\.env")

from server.core.rag.chat import chat_with_meeting

MEETING_ID = 3

questions = [
    {
        "question": "Why are students skipping on Fridays?",
        "ground_truth": "Students find it hard to get out of bed on Fridays.",
    },
    {
        "question": "What idea was suggested to encourage students to come on Fridays?",
        "ground_truth": "A pancake breakfast was suggested to encourage students to come on Fridays.",
    },
    {
        "question": "Why are students getting sick?",
        "ground_truth": "Students are getting sick because it is getting colder outside and flu season is approaching.",
    },
    {
        "question": "What should be done to prevent students from getting sick?",
        "ground_truth": "Posters with health tips like washing hands should be put up since it is almost flu season.",
    },
    {
        "question": "How many days has John Smith missed?",
        "ground_truth": "John Smith has missed seven days already and it is only November.",
    },
    {
        "question": "Why has John Smith been absent?",
        "ground_truth": "John Smith has been stressed out because he has been helping his parents take care of his younger siblings during the day.",
    },
    {
        "question": "What was recommended for John Smith?",
        "ground_truth": "It was recommended that John Smith speak to the guidance counselor.",
    },
    {
        "question": "What will be done to help Johns family?",
        "ground_truth": "Free or low cost child care resources in the community will be found and shared with Johns family.",
    },
    {
        "question": "What is the main topic of this meeting?",
        "ground_truth": "The main topic is student attendance and helping chronically absent students.",
    },
    {
        "question": "Who will talk to John Smith after the meeting?",
        "ground_truth": "The guidance counselor will talk to John Smith after the meeting.",
    },
]

print(f"Getting real answers from Summly RAG (meeting_id={MEETING_ID})...\n")

saved = []
for i, item in enumerate(questions):
    print(f"  [{i+1}/10] {item['question'][:55]}...")
    
    try:
        result = chat_with_meeting(
            query=item["question"],
            meeting_id=MEETING_ID
        )
        
        saved.append({
            "question":      item["question"],
            "ground_truth":  item["ground_truth"],
            "answer":        result["answer"],
            "contexts":      [chunk["text"] for chunk in result["sources"]],
        })
        
        print(f"         ✓ {result['answer'][:70]}...")
        time.sleep(8)  # 8 sec gap — tokens bachao
        
    except Exception as e:
        print(f"         ✗ ERROR: {str(e)[:80]}")
        print(f"         Waiting 2 minutes for rate limit reset...")
        time.sleep(120)
        # retry
        try:
            result = chat_with_meeting(query=item["question"], meeting_id=MEETING_ID)
            saved.append({
                "question":     item["question"],
                "ground_truth": item["ground_truth"],
                "answer":       result["answer"],
                "contexts":     [chunk["text"] for chunk in result["sources"]],
            })
            print(f"         ✓ Retry successful!")
        except:
            print(f"         ✗ Retry failed, skipping...")

# Save to file
out_path = os.path.join(os.path.dirname(__file__), "saved_answers.json")
with open(out_path, "w") as f:
    json.dump(saved, f, indent=2)

print(f"\n✓ Saved {len(saved)} answers to eval/saved_answers.json")
print(f"Ab Step 2 karo — RAGAS scoring!")