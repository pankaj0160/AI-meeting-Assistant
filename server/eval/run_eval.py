# eval/run_eval.py — REAL DATA VERSION
import json, sys, os, asyncio
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, project_root)


from dotenv import load_dotenv
load_dotenv(r"C:\Projects\Summly\.env")

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings import HuggingFaceEmbeddings as RagasHFEmbeddings
from ragas.metrics.collections import Faithfulness, AnswerRelevancy, ContextRecall
from ragas.dataset_schema import SingleTurnSample

# ── Judge LLM ────────────────────────────────────────────────────────
# OpenAI ki jagah AsyncGroq use karo
from groq import AsyncGroq

groq_async_client = AsyncGroq(
    api_key=os.getenv("GROQ_API_KEY"),
)
judge_llm = llm_factory(
    model="llama-3.3-70b-versatile",
    provider="openai",        # Groq is OpenAI-compatible
    client=groq_async_client,
)
print("✓ LLM ready")

embeddings_model = RagasHFEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2"
)
print("✓ Embeddings ready")

faithfulness_metric     = Faithfulness(llm=judge_llm)
answer_relevancy_metric = AnswerRelevancy(
    llm=judge_llm,
    embeddings=embeddings_model,
    strictness=1,
)
context_recall_metric   = ContextRecall(llm=judge_llm)
print("✓ Metrics ready")

# ── Real transcript from DB ───────────────────────────────────────────
MEETING_ID = 3  # Weekly Meeting Example

# Real questions based on the actual transcript
golden_data = [
    {
        "question": "Why are students skipping on Fridays?",
        "ground_truth": "Students find it hard to get out of bed on Fridays.",
        "contexts": ["I've heard some of my mentees talking about how it's really hard to get out of bed on Fridays."]
    },
    {
        "question": "What idea was suggested to encourage students to come on Fridays?",
        "ground_truth": "A pancake breakfast was suggested to encourage students to come on Fridays.",
        "contexts": ["It might be good if we did something like a pancake breakfast to encourage them to come."]
    },
    {
        "question": "Why are students getting sick?",
        "ground_truth": "Students are getting sick because it is getting colder outside and flu season is approaching.",
        "contexts": ["It might also be because a lot of students have been getting sick now that it's getting colder outside."]
    },
    {
        "question": "What should be done to prevent students from getting sick?",
        "ground_truth": "Posters with health tips like washing hands should be put up since it is almost flu season.",
        "contexts": ["We should put up posters with tips for not getting sick since it's almost flu season."]
    },
    {
        "question": "How many days has John Smith missed?",
        "ground_truth": "John Smith has missed seven days already and it is only November.",
        "contexts": ["He's missed seven days already and it's only November."]
    },
    {
        "question": "Why has John Smith been absent?",
        "ground_truth": "John Smith has been stressed out because he has been helping his parents take care of his younger siblings during the day.",
        "contexts": ["He's been dealing with helping his parents take care of his younger siblings during the day."]
    },
    {
        "question": "What was recommended for John Smith?",
        "ground_truth": "It was recommended that John Smith speak to the guidance counselor.",
        "contexts": ["It might actually be a good idea if he spoke to the guidance counselor a little bit."]
    },
    {
        "question": "What will be done to help John's family?",
        "ground_truth": "Free or low cost child care resources in the community will be found and shared with John's family.",
        "contexts": ["I'll look for some free or low cost resources in the community to share with John and he can share them with his family."]
    },
    {
        "question": "What is the main topic of this meeting?",
        "ground_truth": "The main topic is student attendance and helping chronically absent students.",
        "contexts": ["So I have our list of chronically absent students here and I've been noticing a troubling trend."]
    },
    {
        "question": "Who will talk to John Smith after the meeting?",
        "ground_truth": "The guidance counselor will talk to John Smith after the meeting.",
        "contexts": ["I can talk to John today if you want to send him to my office after you meet with him."]
    },
]

# ── Get REAL answers from Summly's RAG system ────────────────────────
print(f"\nGetting real answers from Summly RAG (meeting_id={MEETING_ID})...")

from server.core.rag.chat import chat_with_meeting

samples = []
for item in golden_data:
    print(f"  Asking: {item['question'][:55]}...")
    result = chat_with_meeting(query=item["question"], meeting_id=MEETING_ID)
    
    real_answer  = result["answer"]
    real_contexts = [chunk["text"] for chunk in result["sources"]]
    
    print(f"  Answer: {real_answer[:80]}...")
    
    samples.append(SingleTurnSample(
        user_input=item["question"],
        response=real_answer,           # REAL Summly answer
        retrieved_contexts=real_contexts, # REAL chunks from hybrid_search
        reference=item["ground_truth"],
    ))

print(f"\n✓ Got {len(samples)} real answers from Summly")

# ── Score with RAGAS ─────────────────────────────────────────────────
async def score_all(samples):
    scored = []
    for i, sample in enumerate(samples):
        print(f"  Sample {i+1}/{len(samples)}...", end=" ", flush=True)

        while True:
            try:
                faith  = await faithfulness_metric.ascore(
                    user_input=sample.user_input,
                    response=sample.response,
                    retrieved_contexts=sample.retrieved_contexts,
                )
                relev  = await answer_relevancy_metric.ascore(
                    user_input=sample.user_input,
                    response=sample.response,
                )
                recall = await context_recall_metric.ascore(
                    user_input=sample.user_input,
                    retrieved_contexts=sample.retrieved_contexts,
                    reference=sample.reference,
                )

                f = round(float(faith.value),  3)
                r = round(float(relev.value),  3)
                c = round(float(recall.value), 3)

                scored.append({
                    "question":         sample.user_input,
                    "summly_answer":    sample.response,
                    "faithfulness":     f,
                    "answer_relevancy": r,
                    "context_recall":   c,
                })
                print(f"faith={f:.2f}  relev={r:.2f}  recall={c:.2f}")
                await asyncio.sleep(3)
                break

            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    print(f"\n  ⏳ Rate limit — waiting 60 sec...")
                    await asyncio.sleep(60)
                    print(f"  Retrying...", end=" ", flush=True)
                else:
                    print(f"  ERROR: {str(e)[:100]}")
                    scored.append({
                        "question":         sample.user_input,
                        "summly_answer":    sample.response,
                        "faithfulness":     None,
                        "answer_relevancy": None,
                        "context_recall":   None,
                    })
                    break

    return scored

print(f"\nScoring with RAGAS...\n")
scored = asyncio.run(score_all(samples))

# ── Results ──────────────────────────────────────────────────────────
valid = [s for s in scored if s["faithfulness"] is not None]
faith_avg  = sum(s["faithfulness"]     for s in valid) / len(valid)
relev_avg  = sum(s["answer_relevancy"] for s in valid) / len(valid)
recall_avg = sum(s["context_recall"]   for s in valid) / len(valid)

print("\n" + "="*58)
print("   SUMMLY RAG EVALUATION — REAL DATA RAGAS SCORES")
print("="*58)
print(f"  Faithfulness:     {faith_avg:.3f}  (answers don't contradict transcript)")
print(f"  Answer Relevancy: {relev_avg:.3f}  (answers are on-topic)")
print(f"  Context Recall:   {recall_avg:.3f}  (hybrid search finds right chunks)")
print(f"  Overall Avg:      {(faith_avg+relev_avg+recall_avg)/3:.3f}")
print("="*58)

# Save
out_dir = os.path.dirname(__file__)
with open(os.path.join(out_dir, "results.json"), "w") as f:
    json.dump(scored, f, indent=2)

summary = {
    "faithfulness":     round(faith_avg,  4),
    "answer_relevancy": round(relev_avg,  4),
    "context_recall":   round(recall_avg, 4),
    "overall_avg":      round((faith_avg+relev_avg+recall_avg)/3, 4),
    "num_questions":    len(valid),
    "meeting_id":       MEETING_ID,
    # FIX: was hardcoded "gpt-4o-mini" — a leftover from before the judge
    # LLM was switched to Groq (see judge_llm above). score_answers.py
    # already had this corrected; run_eval.py hadn't been, so a fresh run
    # of this script would have silently mislabeled its own output.
    "judge_model":      "groq/llama-3.3-70b-versatile",
    "embedding_model":  "sentence-transformers/all-MiniLM-L6-v2",
    "data_type":        "real_summly_answers",
}
with open(os.path.join(out_dir, "summary_scores.json"), "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n✓ Results saved!")
print(f"\n📌 RESUME BULLET:")
print(f'   "Implemented RAGAS evaluation pipeline achieving {faith_avg:.2f} faithfulness,')
print(f'    {relev_avg:.2f} answer relevancy and {recall_avg:.2f} context recall')
print(f'    on real meeting transcripts using hybrid BM25/vector search."')