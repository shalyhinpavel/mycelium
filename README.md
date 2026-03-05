# Mycelium: Reproducibility & Benchmarks
**The repository where it all started.**

Mycelium began as an open-source experiment to solve the context degradation ("amnesia") problem in LLMs using asynchronous cognitive snapshots. You can explore the original Gradio application and Gateway code in the earlier Git commits of this repository.

Today, Mycelium has evolved into a fully managed, industrial-grade Graph RAG engine capable of deterministic multi-hop reasoning. 

To maintain the spirit of open-source and builder-centric transparency, we have repurposed this repository into the **Mycelium Benchmark Suite**.

## The Leverage Rule
We don't believe in marketing charts. We believe in reproducible code.

Instead of hosting an interactive demo that hides latency and cost metrics, we provide you with the exact scripts and a Read-Only API key to run the benchmarks yourself.

### Included Datasets:
- **MuSiQue-Ans (100):** 100 multi-hop reasoning questions from the official MuSiQue dataset. Great for testing deep chain retrieval.
- **HotpotQA (Hard-100):** 100 challenging multi-hop examples from the HotpotQA dev set. Ideal for testing recall across broad context.

## Getting Started

1. **Clone this repository**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Ensure MYCELIUM_API_KEY is present
   ```
4. **Run Benchmarks:**

#### A. MuSiQue Benchmark (Deep Reasoning)
```bash
python scripts/benchmark_mycelium.py --dataset datasets/musique_100.json --personality MUSIQUE_BENCHMARK_100 --limit 100
```

#### B. HotpotQA Benchmark (Complex Retrieval)
```bash
python scripts/benchmark_mycelium.py --dataset datasets/hotpotqa_100.json --personality HOTPOT_HARD_100_2 --limit 100
```

### Which one to choose?
- **MuSiQue** is more difficult. It requires connecting 2-4 disconnected facts. Run this if you want to see how Mycelium handles "needle in a haystack" logic.
- **HotpotQA** is a standard for multi-hop RAG. Run this to compare Mycelium against your existing vector baselines.

*Wait for the final metrics (Hit Rate and MRR) to appear.*

## License
MIT License. Feel free to use these scripts to benchmark your own RAG systems against Mycelium.