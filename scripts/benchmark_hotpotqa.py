import argparse
import json
import os
import time
import requests
import re
import string
from typing import Any, Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_URL = "https://mycelium-service-e7auq33oka-ey.a.run.app/v1/search"
API_KEY = os.getenv("MYCELIUM_API_KEY", "sk_live_benchmark_viewer_here")
DEFAULT_PERSONALITY = "hotpot_100"

def normalize_text(s: str) -> str:
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)
    def white_space_fix(text):
        return ' '.join(text.split())
    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)
    def lower(text):
        return text.lower()
    return white_space_fix(remove_articles(remove_punc(lower(s))))

def load_test_cases(dataset_path: str, limit: int = 100) -> List[Dict[str, Any]]:
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
            
            query = item.get("question", item.get("query", ""))
            targets = [item.get("answer")] if "answer" in item else []
            
            gold_titles = set()
            if "supporting_facts" in item:
                # HotpotQA format: [["Title", line_idx], ...]
                for fact in item.get("supporting_facts", []):
                    if isinstance(fact, list) and len(fact) > 0:
                        gold_titles.add(fact[0])

            cases.append({
                "query": query,
                "targets": [t for t in targets if t and isinstance(t, str)],
                "gold_titles": [t for t in gold_titles if t],
                "id": item.get("id", item.get("_id", str(i)))
            })
        print(f"✅ Loaded {len(cases)} test cases from {dataset_path}")
        return cases
    except Exception as e:
        print(f"❌ Failed to load test cases: {e}")
        return []

def run_benchmark(dataset_path: str, personality_id: str, api_key: str, limit: int = 100):
    print(f"\n🍄 RUNNING HOTPOTQA BENCHMARK")
    print(f"Dataset: {dataset_path} | Personality: {personality_id}")
    print("=" * 60)
    
    cases = load_test_cases(dataset_path, limit)
    if not cases: return

    headers = {"X-API-Key": api_key}
    results = []
    
    for idx, case in enumerate(cases):
        query = case["query"]
        targets = case["targets"]
        gold_titles = set(case["gold_titles"])
        norm_targets = [normalize_text(t) for t in targets]
        
        start_ts = time.time()
        nodes = []
        try:
            payload = {
                "query": query,
                "personality_id": personality_id,
                "limit": 10,
                "hops": 3,
                "entity_top_k": 5,
                "w_resonance": 0.7,
                "w_reranker": 2.5,
                "rerank": True,
                "include_global": True
            }
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                nodes = response.json().get("results", [])
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        duration = time.time() - start_ts
        
        found_target = False
        mrr_score = 0.0
        retrieved_titles = []
        
        for i, node_data in enumerate(nodes):
            content = node_data.get("content", "")
            norm_content = normalize_text(content)
            metadata = node_data.get("metadata", {})
            
            extracted_titles = set()
            if metadata.get("title"): extracted_titles.add(metadata.get("title"))
            auto_rel = metadata.get("auto_relations", [])
            for rel in auto_rel:
                if "source" in rel: extracted_titles.add(rel["source"])
                if "target" in rel: extracted_titles.add(rel["target"])

            # Semantic Matching
            node_titles = set()
            clean_gold_titles = {gt.lower(): gt for gt in gold_titles}
            for t in extracted_titles:
                ct = t.lower()
                if ct in clean_gold_titles: node_titles.add(clean_gold_titles[ct])
                else: node_titles.add(t)

            for gt_lower, original_gt in clean_gold_titles.items():
                if len(gt_lower) > 3 and gt_lower in norm_content:
                    node_titles.add(original_gt)
            
            for t in node_titles: retrieved_titles.append(t)
            
            if not found_target:
                for nt in norm_targets:
                    if nt in norm_content:
                        found_target = True
                        break
            
            if mrr_score == 0:
                for t in node_titles:
                    if t in gold_titles: 
                        mrr_score = 1.0 / (i + 1)
                        break
        
        hits = [t for t in gold_titles if t in retrieved_titles]
        recall = len(hits) / len(gold_titles) if gold_titles else 0
        
        results.append({"recall": recall, "mrr": mrr_score, "ans_hit": found_target})
        status = "✅" if (found_target or recall == 1.0) else "❌"
        print(f"[{idx+1}/{len(cases)}] {status} Recall: {recall:.2f} | Ans: {'Yes' if found_target else 'No'} | {duration:.2f}s")
        time.sleep(0.5)

    samples = len(results)
    avg_recall = (sum(r['recall'] for r in results) / samples) * 100
    full_recall = (sum(1 for r in results if r['recall'] == 1.0) / samples) * 100
    accuracy = (sum(1 for r in results if r['ans_hit']) / samples) * 100
    mrr = sum(r['mrr'] for r in results) / samples

    print("\n" + "="*60)
    print(f"🏆 FINAL HOTPOTQA REPORT")
    print(f"Accuracy: {accuracy:.1f}% | Avg Recall: {avg_recall:.1f}% | Full Recall: {full_recall:.1f}% | MRR: {mrr:.3f}")
    print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="datasets/hotpotqa_100.json")
    parser.add_argument("--personality", default=DEFAULT_PERSONALITY)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    run_benchmark(args.dataset, args.personality, API_KEY, args.limit)
