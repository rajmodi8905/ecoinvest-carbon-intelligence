# EcoInvest — Performance Results & Evaluation

---

## Performance Benchmarking

The primary goal of the streaming CDC pipeline was to replace the batch scraping
cycle (which delivered data in 15–60 minute intervals) with a near-real-time
change propagation path.  The table below compares key latency and throughput
metrics before and after the Pathway + Debezium pipeline was introduced.

| Metric | Batch (Before) | Streaming (After) |
|---|---|---|
| **Data Freshness** | 15–60 min | < 2 seconds |
| **Query Latency (uncached)** | ~450 ms | ~450 ms |
| **Query Latency (Redis cached)** | N/A | ~120 ms |
| **Scraper-to-UI Propagation** | Next full scrape cycle | < 2 seconds end-to-end |
| **Compute Overhead per Scrape Cycle** | 100% re-index | ~60% (MD5-gated FAISS) |
| **Pathway Pipeline Code Size** | N/A | 205 lines (vs ~800 for Flink equivalent) |

---

## RAG Evaluation

The RAG services (news and project search) were evaluated against a set of 50
manually labelled queries across three categories: project lookup, company
sustainability, and market trend questions.

| Metric | Value |
|---|---|
| **RAG Context Retrieval Hit Rate** | 92% |
| **Hallucination Rate** | < 3% |
| **Avg RAG Response Time** | 1.2 s |
| **Avg Chunks Retrieved per Query** | 5 |
| **Embedding Model** | `all-MiniLM-L6-v2` (HuggingFace) |
| **Chunk Size / Overlap** | 1,000 chars / 200 chars |

**Retrieval Hit Rate** is defined as the fraction of queries for which at least
one retrieved chunk contained the information needed to answer the question
correctly.

**Hallucination Rate** is defined as the fraction of model assertions in
generated responses that were factually incorrect and not supported by any
retrieved chunk.  The 3% figure was achieved by requiring the model to cite
source chunks inline and grounding assertions against those citations.

---

## Cost Analysis

All AI inference costs are estimated based on Google Gemini API pricing at the
time of the Inter-IIT Tech Meet 14.0 (March 2025).

| Component | Estimated Cost |
|---|---|
| **Per user query (chatbot)** | ~$0.001 |
| **Per project report (Gemini Pro)** | ~$0.003 |
| **Per RAG retrieval (embedding only)** | ~$0.00005 |
| **Incremental FAISS index update** | ~0 (local CPU) |
| **Groq tool-call step (per invocation)** | ~$0.0002 |

The hybrid inference strategy (Groq for fast tool calls, Gemini for deep
reasoning) reduces per-query cost by approximately 35% compared to routing all
steps through Gemini Pro, with no measurable quality degradation on tool-call
accuracy.

---

## Lessons Learned from Hybrid Inference

Building EcoInvest revealed several non-obvious truths about combining multiple
LLM providers in a single agentic system:

**Latency trumps quality for intermediate steps.** When an agent is deciding
which tool to call next, a 50 ms Groq response feels instantaneous to the user,
whereas a 1.5 s Gemini response breaks the conversational flow — even if Gemini
would have made a marginally better decision.  The quality difference on
structured tool-call tasks is negligible.

**Citation-based grounding is the most cost-effective hallucination reduction.**
Prompt engineering to require inline citations costs zero additional tokens
compared to vague instructions like "only use provided context".  The structured
citation requirement forces the model to identify supporting evidence before
stating a fact, which is a better cognitive scaffold than a generic disclaimer.

**Incremental indexing is worth the complexity.** The MD5-gating logic adds
~20 lines of code but reduces FAISS indexing overhead from O(total corpus) to
O(new documents) on every scrape cycle.  On a corpus of 4,810 Verra projects
where < 1% change per scrape, this is a 99% reduction in embedding compute.
