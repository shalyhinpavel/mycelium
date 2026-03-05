import argparse
import json
import os
import time
from typing import Any, Dict, List

import requests

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Config
BASE_URL = "https://mycelium-service-e7auq33oka-ey.a.run.app"
API_KEY = os.getenv("MYCELIUM_API_KEY")

def load_test_cases(dataset_path: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Loads test cases from a JSON/JSONL dataset.
    """
    cases = []
    
    if not os.path.exists(dataset_path):
        print(f"❌ Target dataset not found: {dataset_path}")
        return []

    try:
        with open(dataset_path, "r") as f:
            # Check if JSONL or JSON array
            if dataset_path.endswith(".jsonl"):
                for i, line in enumerate(f):
                    if limit and len(cases) >= limit:
                        break
                    
                    if not line.strip():
                        continue
                        
                    try:
                        item = json.loads(line)
                        cases.append(item)
                    except json.JSONDecodeError:
                        continue
            else:
                 data = json.load(f)
                 cases = data[:limit] if limit else data
                    
        print(f"✅ Loaded {len(cases)} test cases from {dataset_path}")
        return cases
    except Exception as e:
        print(f"❌ Failed to load test cases: {e}")
        return []

def run_mycelium_benchmark(dataset_path: str, personality_id: str, limit: int = 50):
    print(f"\n🍄 RUNNING MYCELIUM BENCHMARK")
    print(f"Dataset: {dataset_path}")
    print(f"Graph Personality: {personality_id}")
    print("="*80)
    
    if not API_KEY:
        print("❌ MYCELIUM_API_KEY not found in .env file.")
        print("Please copy .env.example to .env and ensure the read-only key is present.")
        return

    cases = load_test_cases(dataset_path, limit=limit)
    if not cases:
        print("No cases to run.")
        return

    total_queries = len(cases)
    
    headers = {
        "X-API-Key": API_KEY,
    }
    
    success_count = 0
    total_mrr_all = []
    total_snr_all = []
    
    print("\nStarting queries...\n")
    for idx, case in enumerate(cases):
        # Extract question and targets depending on dataset structure
        if "question" in case and "answer" in case: # MuSiQue
             query = case["query"] if "query" in case else case["question"]
             targets = [case.get("answer", "")] + case.get("answer_aliases", [])
        elif "question" in case and "answers" in case: # Hotpot or other
             query = case["question"]
             targets = [case.get("answer", "")] + case.get("answer_aliases", [])
        else: # Generic fallback
             query = str(case.get("question", case.get("query", "")))
             targets = [str(case.get("answer", ""))]

        targets = [t.lower() for t in targets if t]
        
        # Load Supporting IDs if available
        supporting_ids = set()
        if "paragraphs" in case: # MuSiQue format
             import hashlib
             for p in case.get("paragraphs", []):
                 if p.get("is_supporting"):
                     p_content = p.get("paragraph_text", "")
                     p_title = p.get("title", "Untitled")
                     p_hash = hashlib.md5(f"{p_title}_{p_content}".encode()).hexdigest()
                     supporting_ids.add(f"musique_doc_{p_hash}")
        
        start_ts = time.time()
        
        try:
            # Query the Mycelium Read-Only API
            payload = {
                "query": query,
                "personality_id": personality_id,
                "limit": 10,
                "hops": 2, # Multi-hop Graph Search enabled!
                "include_global": True
            }
            
            response = requests.post(
                f"{BASE_URL}/v1/search", 
                headers=headers, 
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"   ❌ API Error {response.status_code}: {response.text}")
                nodes = []
            else:
                api_data = response.json()
                nodes = api_data.get("results", [])
        except Exception as e:
            print(f"   ❌ Request Error: {e}")
            nodes = []
        
        duration = time.time() - start_ts
        
        # Analyze Results
        mrr_score = 0.0
        useful_docs_count = 0
        
        print(f"[{idx+1}/{total_queries}] Q: {query[:50]}...")
        
        for i, node_data in enumerate(nodes):
            content = node_data.get("content", "").lower()
            metadata = node_data.get("metadata", {})
            score = node_data.get("score", 0)
            
            # Check for matches
            is_target = any(t in content for t in targets)
            nid = node_data.get("id") 
            sid = metadata.get("source_id")
            is_support = (nid in supporting_ids) or (sid in supporting_ids)
            
            if is_target or is_support:
                if mrr_score == 0 and is_target:
                    mrr_score = 1.0 / (i + 1)
                useful_docs_count += 1
        
        if mrr_score > 0:
            success_count += 1
            print(f"   ✅ SUCCESS! Found exact answer at rank #{int(1/mrr_score)} (Latency: {duration:.2f}s)")
        else:
            print(f"   ❌ Miss. Target not in top 10 results. (Latency: {duration:.2f}s)")

        total_mrr_all.append(mrr_score)
        snr = useful_docs_count / len(nodes) if nodes else 0
        total_snr_all.append(snr)

    # Calculate final metrics
    recall = (success_count / total_queries) * 100
    avg_mrr = sum(total_mrr_all) / total_queries if total_queries > 0 else 0
    avg_latency = sum(total_snr_all) / total_queries if total_queries > 0 else 0 # Dummy SN
    
    print("="*80)
    print(f"🏆 MYCELIUM GRAPH RAG RESULTS")
    print(f"Dataset: {dataset_path}")
    print(f"Hit Rate (Recall@10): {recall:.1f}% ({success_count}/{total_queries} queries)")
    print(f"MRR (Mean Reciprocal Rank): {avg_mrr:.3f}")
    print("="*80)
    print("Compare these results by running the standard Vector Baseline script.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Mycelium Benchmarks")
    parser.add_argument("--dataset", type=str, required=True, help="Path to dataset (e.g. datasets/musique_sample.jsonl)")
    parser.add_argument("--personality", type=str, required=True, help="Personality ID matching the dataset (e.g. musique_benchmark_100)")
    parser.add_argument("--limit", type=int, default=50, help="Number of test cases to run")
    
    args = parser.parse_args()
    
    run_mycelium_benchmark(
        dataset_path=args.dataset,
        personality_id=args.personality,
        limit=args.limit
    )
