# 5-10 minute student demonstration script

The included video, if present, is an automated screen walkthrough with on-screen captions, not a recording of a student presenting. Record your own narration if required by faculty. Do not describe optional model/database paths as validated without testing them locally.

0:00-0:35 - Introduce the synthetic OTA use case and educational scope. Identify the backend, gateway, ECU and assets. Explain that no live vehicle is connected.
0:35-1:10 - Show the input JSON and source handbook. Explain source IDs, versions and unknown controls.
1:10-2:00 - Generate threats. Open one finding. Explain asset, damage scenario, assumptions, controls and candidate graph path.
2:00-2:40 - Enter illustrative impact/feasibility ratings, reviewer name and rationale. Save. Explain why the matrix is educational and why human review matters.
2:40-3:30 - Ask a rollback question. Show KB-02 and its source text. Explain extraction, chunking, BM25, token hashing and the difference between the baseline and optional LLM mode.
3:30-3:50 - Ask an out-of-domain weather question. Show abstention. Discuss lexical retrieval limits.
3:50-4:40 - Load v2. Compare architectures, mark affected old findings stale, and show the new diagnostic asset/threat.
4:40-5:10 - Inspect audit trail and export register. Explain stable IDs and review history.
5:10-5:45 - Show actual evaluation metrics, failed paraphrase queries and 27 passing tests. State small synthetic benchmark limits and untested optional integrations.
5:45-6:15 - Explain each student's actual contribution and remaining work. State all installation/runtime dependencies. Close with report and source-code folder structure.
