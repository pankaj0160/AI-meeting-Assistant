# eval/score_answers.py

import json
import os
import sys
import time
import warnings
warnings.filterwarnings("ignore")

# ── Path setup ────────────────────────────────────────────────────────────────
script_dir   = os.path.dirname(os.path.abspath(__file__))
server_dir   = os.path.dirname(script_dir)
project_root = os.path.dirname(server_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import nest_asyncio
nest_asyncio.apply()

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(project_root, ".env"))

groq_key = os.getenv("GROQ_API_KEY")
if not groq_key:
    print("✗ GROQ_API_KEY not found in .env")
    sys.exit(1)

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

judge_llm = LangchainLLMWrapper(ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=groq_key,
    temperature=0,
    max_retries=2,
))
print("✓ Judge LLM ready")

embeddings_model = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
)
print("✓ Embeddings ready")

faithfulness.llm            = judge_llm
answer_relevancy.llm        = judge_llm
answer_relevancy.embeddings = embeddings_model
context_recall.llm          = judge_llm
if hasattr(answer_relevancy, "strictness"):
    answer_relevancy.strictness = 1
print("✓ Metrics configured\n")

saved_path = os.path.join(script_dir, "saved_answers.json")
with open(saved_path, "r") as f:
    saved = json.load(f)

# ── Load existing partial results so we don't re-score already done ones ──────
results_path = os.path.join(script_dir, "results.json")
already_done = {}
if os.path.exists(results_path):
    with open(results_path, "r") as f:
        existing = json.load(f)
    # Only keep ones that actually have scores (not errored)
    already_done = {
        r["question"]: r for r in existing
        if r.get("faithfulness") is not None
    }
    if already_done:
        print(f"✓ Resuming — {len(already_done)} questions already scored, skipping them\n")

print(f"Scoring with RAGAS ({len(saved) - len(already_done)} remaining)...\n")

# ── DELAY between questions (seconds) ────────────────────────────────────────
# Groq free tier: 100k tokens/day, ~6k tokens/min
# 8 seconds between questions keeps us well under the per-minute limit
DELAY_SECONDS = 8

all_scores = []

for i, item in enumerate(saved, 1):
    q = item["question"]

    # Skip if already scored in a previous run
    if q in already_done:
        s = already_done[q]
        all_scores.append(s)
        print(f"  [{i:2}/{len(saved)}] SKIP (already done): {q[:45]}...")
        print(f"         faith={s['faithfulness']:.2f}  relevancy={s['answer_relevancy']:.2f}  recall={s['context_recall']:.2f}")
        continue

    print(f"  [{i:2}/{len(saved)}] {q[:52]}...")

    row = {
        "question":     item["question"],
        "answer":       item["answer"],
        "contexts":     item["contexts"],
        "ground_truth": item["ground_truth"],
    }

    try:
        result = evaluate(
            dataset          = Dataset.from_list([row]),
            metrics          = [faithfulness, answer_relevancy, context_recall],
            raise_exceptions = False,
            show_progress    = False,
        )

        def safe_float(val):
            if val is None: return None
            if isinstance(val, list): val = val[0] if val else None
            if val is None: return None
            try:
                f = float(val)
                return round(f, 3) if f == f else None
            except: return None

        f_val = safe_float(result["faithfulness"])
        r_val = safe_float(result["answer_relevancy"])
        c_val = safe_float(result["context_recall"])

        all_scores.append({
            "question":         q,
            "answer":           item["answer"],
            "faithfulness":     f_val,
            "answer_relevancy": r_val,
            "context_recall":   c_val,
        })

        f_str = f"{f_val:.2f}" if f_val is not None else " nan"
        r_str = f"{r_val:.2f}" if r_val is not None else " nan"
        c_str = f"{c_val:.2f}" if c_val is not None else " nan"
        print(f"         faith={f_str}  relevancy={r_str}  recall={c_str}")

    except Exception as e:
        err = str(e)
        print(f"         ERROR: {err[:80]}")

        if "rate_limit" in err or "429" in err or "Rate limit" in err:
            # Extract wait time from error message if possible
            import re
            wait_match = re.search(r'try again in (\d+)m(\d+)', err)
            if wait_match:
                wait_mins = int(wait_match.group(1))
                wait_secs = int(wait_match.group(2)) + 10  # add 10s buffer
                total_wait = wait_mins * 60 + wait_secs
            else:
                total_wait = 120  # default 2 min if we can't parse

            print(f"\n  ⏳ Rate limit hit! Waiting {total_wait} seconds before retrying...")
            print(f"     (Don't close the terminal — auto-resuming)\n")

            # Save progress so far before waiting
            with open(results_path, "w") as f:
                json.dump(all_scores, f, indent=2)
            print(f"  ✓ Progress saved ({len(all_scores)} done so far)")

            time.sleep(total_wait)

            # Retry this same question once after waiting
            try:
                result = evaluate(
                    dataset          = Dataset.from_list([row]),
                    metrics          = [faithfulness, answer_relevancy, context_recall],
                    raise_exceptions = False,
                    show_progress    = False,
                )
                f_val = safe_float(result["faithfulness"])
                r_val = safe_float(result["answer_relevancy"])
                c_val = safe_float(result["context_recall"])

                all_scores.append({
                    "question":         q,
                    "answer":           item["answer"],
                    "faithfulness":     f_val,
                    "answer_relevancy": r_val,
                    "context_recall":   c_val,
                })
                f_str = f"{f_val:.2f}" if f_val is not None else " nan"
                r_str = f"{r_val:.2f}" if r_val is not None else " nan"
                c_str = f"{c_val:.2f}" if c_val is not None else " nan"
                print(f"  ✓ Retry succeeded: faith={f_str}  relevancy={r_str}  recall={c_str}")

            except Exception as e2:
                print(f"  ✗ Retry also failed: {str(e2)[:80]}")
                print(f"  Saving progress and stopping. Run again tomorrow to resume.")
                with open(results_path, "w") as f:
                    json.dump(all_scores, f, indent=2)
                sys.exit(0)
        else:
            all_scores.append({
                "question": q, "answer": item["answer"],
                "faithfulness": None, "answer_relevancy": None,
                "context_recall": None, "error": err,
            })

    # Save progress after every question
    with open(results_path, "w") as f:
        json.dump(all_scores, f, indent=2)

    # Delay between questions to avoid hitting rate limit
    if i < len(saved):
        print(f"         (waiting {DELAY_SECONDS}s before next question...)")
        time.sleep(DELAY_SECONDS)

# ── Summary ───────────────────────────────────────────────────────────────────
valid = [s for s in all_scores if s.get("faithfulness") is not None]

if not valid:
    print("\n✗ No valid scores yet.")
    sys.exit(1)

def safe_avg(scores, key):
    vals = [s[key] for s in scores if s.get(key) is not None]
    return sum(vals) / len(vals) if vals else 0.0

avg_faith  = safe_avg(valid, "faithfulness")
avg_relev  = safe_avg(valid, "answer_relevancy")
avg_recall = safe_avg(valid, "context_recall")

def rating(s):
    if s >= 0.85: return "🟢 Good"
    if s >= 0.70: return "🟡 Fair"
    return "🔴 Needs work"

print("\n" + "=" * 60)
print("      SUMMLY RAG EVALUATION — RAGAS SCORES")
print("=" * 60)
print(f"\n  Faithfulness:      {avg_faith:.3f}   {rating(avg_faith)}")
print(f"  Answer Relevancy:  {avg_relev:.3f}   {rating(avg_relev)}")
print(f"  Context Recall:    {avg_recall:.3f}   {rating(avg_recall)}")
print(f"\n  Overall Average:   {(avg_faith + avg_relev + avg_recall) / 3:.3f}")
print(f"  Scored {len(valid)}/{len(saved)} questions successfully")
print("=" * 60)

summary = {
    "faithfulness":     round(avg_faith,  4),
    "answer_relevancy": round(avg_relev,  4),
    "context_recall":   round(avg_recall, 4),
    "overall_avg":      round((avg_faith + avg_relev + avg_recall) / 3, 4),
    "num_questions":    len(saved),
    "scored":           len(valid),
    "judge_model":      "groq/llama-3.3-70b-versatile",
    "embedding_model":  "sentence-transformers/all-MiniLM-L6-v2",
}

summary_path = os.path.join(script_dir, "summary_scores.json")
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n✓ Detailed results → eval/results.json")
print(f"✓ Summary scores   → eval/summary_scores.json")
print(f"\n📌 Resume bullet:")
print(f'   "Achieved RAGAS faithfulness {summary["faithfulness"]}, '
      f'answer relevancy {summary["answer_relevancy"]}, '
      f'context recall {summary["context_recall"]}"')