# NEW: v1.1 AI Assessment

**Read START_HERE_AI.md first for the Ollama + PostgreSQL setup.** The new AI Assessment page generates structured assessments from fresh system descriptions. The existing offline workspace remains available as a baseline. The original bundled video covers only that baseline; record the new AI flow after local validation.

# TARA Studio - Automotive Cybersecurity Assessment Assistant

**Release 1.0: tested offline academic prototype, with optional unvalidated deployment/model adapters.**

This package implements a single-user research workflow for a synthetic OTA system. It is not an automotive compliance tool. No faculty approval, student signature, real vehicle result or pretrained-model evaluation is claimed.

## Quick start (Windows PowerShell)

Open a terminal inside this extracted folder. Python 3.11 or 3.12 is recommended (tested on 3.12).

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Code\requirements.txt
.\.venv\Scripts\python.exe Code\run.py
```

Open http://127.0.0.1:8000. No API key is required. Initial installation needs internet; subsequent baseline runs do not. Keep this localhost-only application off public networks.

## Linux / WSL

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r Code/requirements.txt
.venv/bin/python Code/run.py
```

## Demonstration workflow

1. Inspect the synthetic v1 architecture and asset inventory.
2. Generate candidate threats (4 patterns match v1). These are drafts with no assigned risk.
3. Review a finding, enter illustrative ratings and a rationale, and save it.
4. Ask `How do we prevent rollback to old firmware versions?` in Evidence explorer. Inspect KB-02.
5. Ask a clearly unrelated weather question to show abstention.
6. Import `Input_Data/architecture_v2.json` or select Load sample v2. Generate its 5 findings.
7. Compare v1 to v2 and mark affected older findings as needing reassessment.
8. Inspect the audit trail; export CSV and JSON.

## Tests and evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest Code\tests -q
.\.venv\Scripts\python.exe Code\evaluate.py
```

The supplied evidence records the actual run. Read `Evaluation_Results/metrics.json`, including the limitations and separate paraphrase results. The benchmark is synthetic and not independent. Re-running evaluation overwrites its output files.

## Optional local LLM (not exercised in this build)

Install Ollama separately and review the model-specific license. A proposed modest model is `qwen2.5:3b-instruct`; its adequacy must be measured, not assumed. Model weights are not included. First download needs internet and additional disk/RAM.

```powershell
ollama pull qwen2.5:3b-instruct
$env:OLLAMA_MODEL="qwen2.5:3b-instruct"
.\.venv\Scripts\python.exe Code\model_probe.py
.\.venv\Scripts\python.exe Code\run.py
```

Keep Ollama running locally. In Evidence explorer choose Local Ollama. The adapter calls `/api/generate` with temperature 0 and JSON output, and rejects unknown citation IDs. Citation membership alone does not prove factual correctness. The probe writes the actual installed tag, digest and runtime version; do not submit a made-up digest. Model/provider failure is explicit, never silently passed off as successful generation.

In the original offline workspace, architecture ingestion uses validated JSON and threats use pattern matching. The NEW AI Assessment page separately extracts assets and drafts context-specific threats from text through Ollama. It does not automatically replace the structured architecture graph.

## Optional PostgreSQL + pgvector (not exercised in this build)

Docker is not required for the tested baseline. For the PostgreSQL deployment, copy `.env.example` to `.env`, set a unique alphanumeric password, then run:

```bash
docker compose up --build
```

This stores structured records and token-hash vectors in PostgreSQL. Vector cosine retrieves candidates; BM25 re-ranks them. This uses lexical hashed vectors, not pretrained semantic embeddings. SQLite mode ranks the whole small corpus. The Compose image tag is mutable; record its digest after pulling for exact reproducibility. No PostgreSQL port is exposed to the host.

Compose does not automatically configure Ollama. Test native local mode first. For containers, configure a reachable approved local endpoint explicitly; container localhost is not host localhost.

## Persistence and scope

Native mode writes `Code/runtime/tara.db`. Preserve this directory to retain work. Use a new `TARA_DB` path for an empty workspace rather than deleting existing work. This is one project per database; it has no multi-user authentication or role-based access. Reviewer names are self-declared. Audit records are application history, not tamper-proof evidence.

## Submission status

- Implemented and tested: offline retrieval, architecture validation, deterministic threats, synthetic risk rules, review/version checks, change impact, local persistence, text/PDF evidence ingestion, exports.
- Included but unvalidated end-to-end: PostgreSQL/pgvector, Docker, Ollama generation.
- Pending student/faculty: names, PRNs, contributions, report-format alignment, approvals, signatures, and final local environment verification.
- The report and synopsis now follow the supplied TECH PULSE FY-26 templates.

Rename the folder to `PCCOE_<StudentName>_<PRN>_CS3_AIML` before final submission. Do not claim this AI-assisted implementation was independently authored; complete the contribution and assistance disclosure accurately.

## Before claiming pretrained-model results

With the installed Ollama model configured, run:

```powershell
.\.venv\Scripts\python.exe Code\evaluate_llm.py
```

This records actual model identity, real outputs, failures, latency and source IDs. Complete `Evaluation_Results/llm_human_review.csv` with a reviewer. It does not overwrite or mislabel the offline benchmark. Then update the report and record a demo showing the model mode.

## Optional authoring utilities

`Code/helpers/build_reports.py` regenerates the report and synopsis DOCX files after installing `Code/requirements-authoring.txt`. Bundled DejaVu fonts include their license. `Code/helpers/record_demo.cjs` uses separately installed Playwright/Chromium to generate a captioned browser walkthrough; FFmpeg encodes the frames. These tools are not needed to run the submitted application.
