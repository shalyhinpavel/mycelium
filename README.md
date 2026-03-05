# Mycelium: Reproducibility & Benchmarks
**The repository where it all started.**

Mycelium began as an open-source experiment to solve the context degradation ("amnesia") problem in LLMs using asynchronous cognitive snapshots. You can explore the original Gradio application and Gateway code in the earlier Git commits of this repository.

Today, Mycelium has evolved into a fully managed, industrial-grade Graph RAG engine capable of deterministic multi-hop reasoning. 

To maintain the spirit of open-source and builder-centric transparency, we have repurposed this repository into the **Mycelium Benchmark Suite**.

## The Leverage Rule
We don't believe in marketing charts. We believe in reproducible code.

Instead of hosting an interactive demo that hides latency and cost metrics, we provide you with the exact scripts and a Read-Only API key to run the benchmarks yourself.

### Included Benchmarks:
- **Vector-Only RAG vs. Graph-Enhanced RAG:** A demonstration of how traditional vector search fails on multi-hop reasoning questions, and how Mycelium's resonance propagation recovers the full evidence chain.

## Getting Started

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy the environment file: `cp .env.example .env`
4. Add your OpenAI API key (for the baseline vector comparison).
5. Run the scripts in the `/scripts` directory.

*Detailed instructions are provided inside each benchmark script.*

## License
MIT License. Feel free to use these scripts to benchmark your own RAG systems against Mycelium.