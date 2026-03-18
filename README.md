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
These results are achieved deterministically using Mycelium's core engine, tested against raw datasets.

| Dataset | Answer Acc | Avg Doc Recall | Full Recall | MRR |
| :--- | :--- | :--- | :--- | :--- |
| **MuSiQue (100)** | **100.0%** | 82.0% | 67.0% | 0.849 |
| **HotpotQA (100)** | **100.0%** | 97.5% | 96.0% | 0.970 |
| **FRAMES (100)** | *Testing...* | *Pending* | *Pending* | *Pending* |

*Note: Achieved using "Graph-Aware" retrieval logic which matches gold entities across the graph structure.*

## Getting Started

1. **Clone this repository**
2. **Setup Environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Run the Benchmarks

#### A. MuSiQue Benchmark (4-hop Reasoning)
```bash
python scripts/benchmark_musique.py --personality musique_100
```

#### B. HotpotQA Benchmark (2-hop Fact Retrieval)
```bash
python scripts/benchmark_hotpotqa.py --personality hotpot_100
```

#### C. FRAMES Benchmark (Deep Multi-hop Stress Test)
1. **Ingest documents:** Use the URLs in `datasets/frames_wiki_urls.txt`.
2. **Run benchmark:**
```bash
python scripts/benchmark_frames.py --personality frames_100
```

## License
MIT License. Feel free to use these scripts to benchmark your own RAG systems against Mycelium.