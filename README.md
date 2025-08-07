---
title: Mycelium
emoji: 🧠
colorFrom: indigo
colorTo: gray
sdk: gradio
sdk_version: 5.41.0
app_file: app.py
pinned: true
license: apache-2.0
short_description: Cognitive accelerator for medium-sized LLMs
---

![alt text](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

Mycelium: Solving the "Amnesia" and Long-Term Memory Problem in LLMs
Modern LLMs, including the latest models, suffer from context degradation. In long dialogues, they forget key facts, making them unreliable partners. Mycelium is a lightweight architecture that solves this problem by asynchronously distilling the dialogue into a structured "Cognitive Snapshot."
This allows the LLM to maintain a focused and relevant context for a virtually unlimited amount of time.
How does it work?
Instead of passing the entire "noise" of the dialogue history to the model, Mycelium works in the background to extract only the most important essence.

    participant User as "User"
    participant Gateway as "Mycelium Gateway"
    participant Engine as "LLM Engine"
    participant SnapshotDB as "Snapshot Storage"

    User->>Gateway: Request
    Gateway->>SnapshotDB: Load snapshot
    SnapshotDB-->>Gateway: Current snapshot
    
    Gateway->>Engine: Generate response (using snapshot)
    Engine-->>Gateway: Response
    
    Gateway-->>User: Send response (instantly)
    
    activate Gateway
    Gateway->>Gateway: Initiate background distillation
    deactivate Gateway
    
    Gateway->>Engine: Update snapshot (asynchronously)
    Engine-->>Gateway: Data for update
    
    Gateway->>SnapshotDB: Save new snapshot```