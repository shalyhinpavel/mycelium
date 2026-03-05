import argparse
import json
import os
import time
import requests
from typing import Any, Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Config
BASE_URL = "https://mycelium-service-e7auq33oka-ey.a.run.app"
API_KEY = os.getenv("MYCELIUM_API_KEY")

def load_test_cases(dataset_path: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Loads test cases from HotpotQA or MuSiQue JSON files.
    Standardizes them into a unified format for the benchmark.
    """
    if not os.path.exists(dataset_path):
        print(f"❌ File not found: {dataset_path}")
        return []

    try:
        with open(dataset_path, "r") as f:
            data = json.load(f)
            
        cases = []
        for i, item in enumerate(data):
            if limit and len(cases) >= limit:
                break
            
            # 1. Extract Question
            query = item.get("question", item.get("query", ""))
            
            # 2. Extract Answer Targets (Answers + Aliases)
            targets = []
            if "answer" in item:
                targets.append(item["answer"])
            if "answer_aliases" in item:
                targets.extend(item["answer_aliases"])
            
            # 3. Extract Supporting Titles (Standard Gold Metric)
            gold_titles = set()
            
            # MuSiQue Format
            if "paragraphs" in item:
                for p in item.get("paragraphs", []):
                    if p.get("is_supporting"):
                        gold_titles.add(p.get("title", ""))
            
            # HotpotQA Format
            if "supporting_facts" in item:
                for fact in item.get("supporting_facts", []):
                    gold_titles.add(fact[0])

            cases.append({
                "query": query,
                "targets": [t.lower().strip() for t in targets if t and isinstance(t, str)],
                "gold_titles": [t for t in gold_titles if t],
                "id": item.get("id", item.get("_id", str(i)))
            })
            
        print(f"✅ Loaded {len(cases)} test cases from {dataset_path}")
        return cases
    except Exception as e:
        print(f"❌ Failed to load test cases: {e}")
        return []

def run_benchmark(dataset_path: str, personality_id: str, limit: int = 50, args=None):
    if not API_KEY:
        print("❌ Error: MYCELIUM_API_KEY not found in .env file.")
        return

    print(f"\n🍄 RUNNING MYCELIUM BENCHMARK (GOLD-ALIGNED)")
    print(f"Dataset: {dataset_path}")
    print(f"Graph Personality: {personality_id}")
    print("=" * 80)
    
    cases = load_test_cases(dataset_path, limit)
    if not cases:
        return

    total_queries = len(cases)
    headers = {"X-API-Key": API_KEY}
    answer_acc_count = 0
    full_recall_count = 0
    total_mrr_all = []
    total_recall_all = []
    failed_cases = []
    answer_acc_count = 0
    
    print("\nStarting queries...\n")
    user_id = getattr(args, "user_id", None)
    
    for idx, case in enumerate(cases):
        query = case["query"]
        targets = case["targets"]
        gold_titles = set(case["gold_titles"])
        
        start_ts = time.time()
        
        nodes = [] # Initialize nodes for each case
        retries = 3
        while retries > 0:
            try:
                # Query the Mycelium API with GOLD Standard Parameters
                payload = {
                    "query": query,
                    "personality_id": personality_id,
                    "limit": 10,
                    "hops": 3,              # Back to 3-hop for Recall recovery
                    "entity_top_k": 5,      # High-precision anchor extraction
                    "resonance_decay": 0.3, # Deeper flow for bridge discovery
                    "resonance_power": 1.5, # Slightly sharper peaks
                    "w_static": 0.1,        # Minimal noise
                    "w_resonance": 0.7,     # Stronger bridges
                    "w_reranker": 2.2,      # Semantic validation
                    "w_boost": 0.0,         # Pure Physics base
                    "auto_tag_extraction": True,
                    "deep_search_threshold": 0.55,
                    "rerank": True,
                    "include_global": True
                }
                if user_id:
                    payload["user_id"] = user_id
                
                response = requests.post(f"{BASE_URL}/v1/search", headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    nodes = response.json().get("results", [])
                    break # Success, exit retry loop
                elif response.status_code == 429:
                    print(f"   ⚠️ Rate limit (429). Retrying in 5s... ({retries-1} left)")
                    time.sleep(5)
                    retries -= 1
                else:
                    print(f"   ❌ API Error {response.status_code}: {response.text}")
                    break # Non-retryable error, exit retry loop
            except requests.exceptions.Timeout:
                print(f"   ❌ Request timed out. Retrying... ({retries-1} left)")
                time.sleep(2)
                retries -= 1
            except requests.exceptions.ConnectionError as e:
                print(f"   ❌ Connection Error: {e}. Retrying... ({retries-1} left)")
                time.sleep(2)
                retries -= 1
            except Exception as e:
                print(f"   ❌ Unexpected Request Error: {e}")
                break # Other unexpected errors, exit retry loop
            
        duration = time.time() - start_ts
        
        # --- Scoring ---
        found_target = False
        mrr_score = 0.0
        retrieved_titles = []
        
        for i, node_data in enumerate(nodes):
            metadata = node_data.get("metadata", {})
            content = node_data.get("content", "").lower()
            title = metadata.get("title", "")
            retrieved_titles.append(title)
            
            # 1. Answer Check
            if not found_target and any(t in content for t in targets):
                found_target = True
            
            # 2. MRR (Standard: First Gold Doc Hit)
            if mrr_score == 0 and title in gold_titles:
                mrr_score = 1.0 / (i + 1)
        
        # Document Recall Check
        hits = [t for t in gold_titles if t in retrieved_titles]
        recall = len(hits) / len(gold_titles) if gold_titles else 0
        
        if found_target:
            answer_acc_count += 1
        if recall == 1.0:
            full_recall_count += 1
            
        total_mrr_all.append(mrr_score)
        total_recall_all.append(recall)

        if recall < 1.0:
            failed_cases.append({
                "idx": idx + 1,
                "query": query,
                "recall": recall,
                "mrr": mrr_score,
                "gold_titles": list(gold_titles),
                "retrieved_titles": retrieved_titles[:5] # Sample top 5
            })

        # Success = Either answer found OR full document recall
        is_success = found_target or (recall == 1.0)
        status = f"✅ SUCCESS" if is_success else "❌ MISS"
        
        print(f"[{idx+1}/{total_queries}] Q: {query[:50]}...")
        print(f"   {status} | Recall: {recall:.2f} | Ans Hit: {'Yes' if found_target else 'No'} | {duration:.2f}s")

    # --- Final Report ---
    avg_recall = (sum(total_recall_all) / total_queries) * 100 if total_queries > 0 else 0
    full_recall_rate = (full_recall_count / total_queries) * 100 if total_queries > 0 else 0
    ans_accuracy = (answer_acc_count / total_queries) * 100 if total_queries > 0 else 0
    avg_mrr = sum(total_mrr_all) / total_queries if total_queries > 0 else 0

    print("=" * 80)
    print("🏆 FINAL MYCELIUM PERFORMANCE REPORT")
    print("=" * 80)
    print(f"📊 Samples:       {total_queries}")
    print(f"🎯 Answer Acc:    {ans_accuracy:.1f}%")
    print(f"🔎 Avg Doc Recall: {avg_recall:.1f}%")
    print(f"🔥 Full Recall:   {full_recall_rate:.1f}% (Internal Gold Standard)")
    print(f"📉 Mean RR:       {avg_mrr:.3f}")
    print("=" * 80)

    # Save Failures
    with open("benchmark_failures.json", "w") as f:
        json.dump(failed_cases, f, indent=2)
    print(f"📂 Saved {len(failed_cases)} failures to benchmark_failures.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, required=True, help="Path to JSON dataset")
    parser.add_argument("--personality", type=str, required=True, help="Personality ID")
    parser.add_argument("--limit", type=int, default=50, help="Number of samples to test")
    parser.add_argument("--user_id", type=str, default=None, help="User ID for admin override")
    args = parser.parse_args()
    run_benchmark(args.dataset, args.personality, args.limit, args=args)
