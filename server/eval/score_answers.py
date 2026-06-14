# server/eval/score_answers.py
import json, sys, os, asyncio

sys.path.insert(0, r"C:\Projects\Summly")

from dotenv import load_dotenv
load_dotenv(r"C:\Projects\Summly\.env")

from groq import AsyncGroq
from ragas.llms import llm_factory
from ragas.embeddings import HuggingFaceEmbeddings as RagasHFEmbeddings
from ragas.metrics.collections import Faithfulness, AnswerRelevancy, ContextRecall
from ragas.dataset_schema import SingleTurnSample

# ── Setup ────────────────────────────────────────────────────────────
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
judge_llm = llm_factory(
    model="llama-3.3-70b-versatile",
    provider="openai",
    client=groq_client,
)
print("✓ Judge LLM ready")

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

# ── Load saved answers ────────────────────────────────────────────────
answers_path = os.path.join(os.path.dirname(__file__), "saved_answers.json")
with open(answers_path) as f:
    saved = json.load(f)

print(f"✓ Loaded {len(saved)} saved answers\n")

# Build samples
samples = []
for item in saved:
    samples.append(SingleTurnSample(
        user_input=item["question"],
        response=item["answer"],
        retrieved_contexts=item["contexts"],
        reference=item["ground_truth"],
    ))

# ── Score ─────────────────────────────────────────────────────────────
async def score_all(samples):
    scored = []
    for i, sample in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {sample.user_input[:50]}...")

        while True:
            try:
                faith = await faithfulness_metric.ascore(
                    user_input=sample.user_input,
                    response=sample.response,
                    retrieved_contexts=sample.retrieved_contexts,
                )
                relev = await answer_relevancy_metric.ascore(
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
                print(f"         faith={f:.2f}  relev={r:.2f}  recall={c:.2f}")
                await asyncio.sleep(10)  # 10 sec gap — tokens bachao
                break

            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    print(f"         ⏳ Rate limit — waiting 3 minutes...")
                    await asyncio.sleep(180)
                    print(f"         Retrying...")
                else:
                    print(f"         ERROR: {str(e)[:80]}")
                    scored.append({
                        "question":         sample.user_input,
                        "summly_answer":    sample.response,
                        "faithfulness":     None,
                        "answer_relevancy": None,
                        "context_recall":   None,
                    })
                    break

    return scored

print("Scoring with RAGAS...\n")
scored = asyncio.run(score_all(samples))

# ── Results ───────────────────────────────────────────────────────────
valid = [s for s in scored if s["faithfulness"] is not None]

if not valid:
    print("No valid scores!")
    sys.exit(1)

faith_avg  = sum(s["faithfulness"]     for s in valid) / len(valid)
relev_avg  = sum(s["answer_relevancy"] for s in valid) / len(valid)
recall_avg = sum(s["context_recall"]   for s in valid) / len(valid)
avg        = (faith_avg + relev_avg + recall_avg) / 3

print("\n" + "="*58)
print("   SUMMLY RAG EVALUATION — REAL DATA RAGAS SCORES")
print("="*58)
print(f"  Faithfulness:     {faith_avg:.3f}  ← answers don't contradict transcript")
print(f"  Answer Relevancy: {relev_avg:.3f}  ← answers are on-topic")
print(f"  Context Recall:   {recall_avg:.3f}  ← hybrid search finds right chunks")
print(f"  Overall Avg:      {avg:.3f}")
print("="*58)

# Save
out_dir = os.path.dirname(__file__)

with open(os.path.join(out_dir, "results.json"), "w") as f:
    json.dump(scored, f, indent=2)

summary = {
    "faithfulness":     round(faith_avg,  4),
    "answer_relevancy": round(relev_avg,  4),
    "context_recall":   round(recall_avg, 4),
    "overall_avg":      round(avg, 4),
    "num_questions":    len(valid),
    "meeting_id":       3,
    "judge_model":      "groq/llama-3.3-70b-versatile",
    "data_type":        "real_summly_answers",
}
with open(os.path.join(out_dir, "summary_scores.json"), "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n✓ Results saved to eval/results.json")
print(f"\n📌 RESUME BULLET:")
print(f'   "Built RAGAS evaluation pipeline for Summly RAG system.')
print(f'    Faithfulness: {faith_avg:.2f} | Answer Relevancy: {relev_avg:.2f} | Context Recall: {recall_avg:.2f}')
print(f'    Evaluated on real meeting transcripts using hybrid BM25/vector search."')