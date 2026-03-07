# Mycelium: Reproducibility & Benchmarks
**The repository where it all started.**

🌐 **[Visit the official website: myceliummemory.tech](https://www.myceliummemory.tech/)**

Mycelium began as an open-source experiment to solve the context degradation ("amnesia") problem in LLMs using asynchronous cognitive snapshots. You can explore the original Gradio application and Gateway code in the earlier Git commits of this repository.

Today, Mycelium has evolved into a fully managed, industrial-grade **Graph RAG engine** capable of deterministic multi-hop reasoning. 

To maintain the spirit of open-source and builder-centric transparency, we have repurposed this repository into the **Mycelium Benchmark Suite**.

## The Leverage Rule
We don't believe in marketing charts. We believe in reproducible code.

Instead of hosting an interactive demo that hides latency and cost metrics, we provide you with the exact scripts and Read-Only API keys to run the benchmarks yourself.

### Verified "Gold Standard" Metrics
These results are achieved deterministically using Mycelium's core engine, tested against raw datasets without iterative agent loops.

| Dataset | Type | Avg Recall@10 | Full Recall (All Docs) | MRR (Mean Reciprocal Rank) |
| :--- | :--- | :--- | :--- | :--- |
| **MuSiQue (100)** | Deep Multi-hop (2-4 facts) | **88.0%** | 80.0% | **0.469** |
| **HotpotQA (Hard-100)** | Complex 2-hop Retrieval | **92.5%** | **88.0%** | **0.750** |

*Note: Achieved entirely using `PHYSIC_RESONANCE` graph physics, mathematically finding connections with `w_boost=0.0` (zero per-query inference costs during search).*

## Getting Started

1. **Clone this repository**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   *The `.env.example` file already contains the Public Read-Only API keys for the benchmarks. You just need to copy it!*

## Run the Benchmarks

#### A. MuSiQue Benchmark (Deep Reasoning)
MuSiQue is more difficult. It requires connecting 2-4 disconnected facts. Run this if you want to see how Mycelium handles "needle in a haystack" logic.
```bash
python scripts/benchmark_mycelium.py --dataset datasets/musique_100.json --personality MUSIQUE_BENCHMARK_100 --limit 100
```

#### B. HotpotQA Benchmark (Complex Retrieval)
HotpotQA is a standard for multi-hop RAG. Run this to compare Mycelium against your existing vector baselines.
```bash
python scripts/benchmark_mycelium.py --dataset datasets/hotpotqa_100.json --personality hotpot_hard_100_2 --limit 100
```

*Wait for the final metrics (Hit Rate and MRR) to appear.*

## License
MIT License. Feel free to use these scripts to benchmark your own RAG systems against Mycelium.