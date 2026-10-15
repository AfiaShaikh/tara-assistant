# Release 1.1 addition

See START_HERE_AI.md. Code/ai_assessment.py implements generation for fresh descriptions. static/ai.js displays jobs, outputs and reviews. PostgreSQL stores full snapshots in ai_assessments. The remaining notes below describe the original baseline.

# Implementation and viva guide

## Modules
- `engine.py`: validated architecture schema, stable token hashing, BM25 retrieval, optional Ollama answer adapter, pattern matching, candidate graph paths, educational risk calculation and change traversal.
- `storage.py`: SQLite default; PostgreSQL/pgvector optional. Shared structured payload contract, parameterized SQL, record IDs and vector upserts.
- `app.py`: FastAPI routes, ingestion, review concurrency checks, audit events and CSV/JSON exports.
- `static/`: local HTML/CSS/JavaScript UI, no CDN dependency. User/model text is escaped before display.
- `evaluate.py`: top-1, recall@3, MRR@3, abstention and citation resolution evaluation.
- `tests/test_system.py`: functional/API/regression tests.

## Deliberate simplifications
The academic app uses a small HTML/JavaScript frontend instead of Streamlit to keep runtime dependencies light and serve one local port. It uses SQLite by default so the submitted offline demonstration does not depend on a running database container. PostgreSQL/pgvector is an explicit optional backend. The retrieval baseline uses lexical BM25 and token-hash vectors rather than downloaded embedding weights. These deviations from the proposed production architecture are explicit and testable.

## Core data flow
Validated architecture JSON -> normalized component/interface/asset records -> tag-to-pattern matches -> draft findings with evidence -> reviewed ratings and educational risk lookup -> register and audit history.

Text or PDF -> text extraction -> 1,200-character windows with 100-character overlap -> metadata -> SQLite chunks / optional pgvector candidates -> BM25 + cosine ranking -> extractive passage or optional Ollama generation -> evidence references.

## API map
GET /api/state; POST /api/architecture; POST /api/select; POST /api/analyze; POST /api/findings/{id}/review; POST /api/ask; POST /api/documents; POST /api/compare; GET /api/audit; GET /api/export/csv; GET /api/export/json. The machine-readable API schema is at /openapi.json; CDN-based Swagger UI is disabled for the offline distribution.

## Definitions students should explain
- TARA: threat analysis and risk assessment.
- Asset vs component: firmware integrity is an asset property; the ECU is the component holding it.
- Damage vs threat scenario: consequence versus potential cause.
- Retrieval vs generation: finding evidence versus composing a response.
- Token hashing vs semantic embeddings: stable lexical features do not capture synonyms like a learned embedding model can.
- Candidate path vs exploit: graph reachability does not establish vulnerability or bypass controls.
- Risk method: this release uses an educational product matrix, not a standards-certified method.
- Traceability: IDs connect architecture assets, threat patterns, draft controls and verification proposals.
- Review concurrency: revision numbers reject overwriting a stale browser view.
- Citation resolution vs correctness: an existing source ID can still be irrelevant to a claim.

## Evaluation interpretation
The tests demonstrate selected software properties, not completeness of automotive threat coverage. The retrieval questions were authored with the handbook and are vulnerable to authoring bias. Paraphrase errors are useful evidence of lexical retrieval limits. No reported metric represents pretrained LLM quality, expert approval or automotive compliance.

## Known gaps
No arbitrary diagram understanding; no OCR; no automatic validated architecture extraction from prose; no novel threat discovery; no multi-user RBAC; no tamper-proof audit; no empirical attack-feasibility assessment; no real vehicle execution; no expert-reviewed benchmark; no end-to-end model/database-container validation in the build environment. The small local app is not production-hardened for untrusted uploads.

## Before final evaluation
Install and run the exact submitted package on the evaluation machine. Re-run tests. If demonstrating Ollama, record the actual model manifest and evaluate that mode separately. Do not replace offline metrics with model claims. Fill in contributions, PRNs and faculty details; attach signed pages; replace the provisional report format if the prescribed template differs. Watch the video end-to-end and record a student-narrated version if narration is required.
