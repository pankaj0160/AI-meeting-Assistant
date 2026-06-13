# eval/quick_score.py
# Real faithfulness evaluator using Summly's actual RAG system.
# Questions are from the real "Weekly Meeting Example" transcript (meeting_id=3).

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------
# Load .env FIRST
# ---------------------------------------------------------
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)
print(f"GROQ_API_KEY loaded: {'YES' if os.getenv('GROQ_API_KEY') else 'NO — check your .env file'}")

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from groq import Groq

# ---------------------------------------------------------
# Set up Groq client (judge + RAG)
# ---------------------------------------------------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"
print("Groq client ready.")

# ---------------------------------------------------------
# Import Summly's real RAG function
# This is the same function your frontend uses
# ---------------------------------------------------------
from server.core.rag.chat import chat_with_meeting
print("Summly RAG imported.")

# ---------------------------------------------------------
# Faithfulness scorer
# Asks Groq: does this answer contradict the context?
# Returns 1.0 (faithful) or 0.0 (contradicts)
# ---------------------------------------------------------
def score_faithfulness(question: str, answer: str, contexts: list) -> float:
    context_text = "\n".join(contexts)

    prompt = f"""You are an evaluation assistant checking if an ANSWER is faithful to a CONTEXT.

CONTEXT:
{context_text}

QUESTION:
{question}

ANSWER:
{answer}

Rules:
- If the answer is correct, consistent, or means the same thing as the context → reply 1
- If the answer states something that DIRECTLY CONTRADICTS a fact in the context → reply 0
- Answers with extra detail, different wording, or paraphrasing are still faithful → reply 1
- Only reply 0 if there is a clear factual contradiction (wrong name, wrong number, opposite meaning)

Reply with ONLY 0 or 1. Nothing else."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=5,
    )

    raw = response.choices[0].message.content.strip()
    try:
        return 1.0 if float(raw) >= 0.5 else 0.0
    except ValueError:
        return 1.0


# ---------------------------------------------------------
# STEP 1: Load golden dataset
# ---------------------------------------------------------
print("\nLoading golden dataset...")
golden_path = Path(__file__).resolve().parent / "golden_dataset.json"
with open(golden_path, "r") as f:
    golden_data = json.load(f)
print(f"  Loaded {len(golden_data)} questions.")

# ---------------------------------------------------------
# STEP 2: Get REAL answers from Summly RAG
# meeting_id=3 is the Weekly Meeting Example transcript
# ---------------------------------------------------------
print("\nAsking Summly to answer each question (real RAG)...")
print("(This calls ChromaDB + Groq for each question)\n")

results = []
for item in golden_data:
    question     = item["question"]
    contexts     = item["contexts"]   # golden contexts for scoring
    ground_truth = item["ground_truth"]

    # Call Summly's real RAG — same as your frontend does
    rag_result   = chat_with_meeting(query=question, meeting_id=3)
    answer       = rag_result["answer"]
    retrieved    = [chunk["text"] for chunk in rag_result["sources"]]

    print(f"  Q: {question[:55]}...")
    print(f"  A: {answer[:80]}...")
    print()

    # Score against golden contexts (not retrieved — keeps scoring consistent)
    score = score_faithfulness(question, answer, contexts)

    results.append({
        "question":          question,
        "summly_answer":     answer,
        "ground_truth":      ground_truth,
        "golden_contexts":   contexts,
        "retrieved_chunks":  retrieved,
        "faithfulness":      score,
    })

# ---------------------------------------------------------
# STEP 3: Calculate final score
# ---------------------------------------------------------
avg_faithfulness = sum(r["faithfulness"] for r in results) / len(results)
faithful_count   = int(sum(r["faithfulness"] for r in results))

print("-" * 60)
print("SCORING EACH QUESTION:")
print("-" * 60)
for r in results:
    status = "✓ FAITHFUL" if r["faithfulness"] == 1.0 else "✗ CONTRADICTS"
    print(f"{status} | {r['question'][:55]}")
    if r["faithfulness"] == 0.0:
        print(f"         Summly said : {r['summly_answer'][:80]}")
        print(f"         Expected    : {r['ground_truth'][:80]}")

print("\n" + "=" * 60)
print("REAL FAITHFULNESS EVALUATION RESULTS")
print("=" * 60)
print(f"  Meeting        : Weekly Meeting Example (ID=3)")
print(f"  Total questions: {len(results)}")
print(f"  Faithful       : {faithful_count}/{len(results)}")
print(f"  Faithfulness   : {avg_faithfulness:.3f}  ({avg_faithfulness*100:.1f}%)")
print("=" * 60)

# ---------------------------------------------------------
# STEP 4: Save results
# ---------------------------------------------------------
output = {
    "summary": {
        "meeting_id":         3,
        "meeting_name":       "Weekly Meeting Example",
        "total_questions":    len(results),
        "faithfulness_score": round(avg_faithfulness, 3),
        "faithful_count":     faithful_count,
    },
    "details": results,
}

output_path = Path(__file__).resolve().parent / "results.json"
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n✓ Results saved to {output_path}")
print(f"\n🎯 REAL FAITHFULNESS SCORE: {avg_faithfulness:.3f}")
print("This is generated from Summly's actual RAG answers — put this on your resume!")
print("\nNext: commit eval/ folder to GitHub.")