# Start here: v1.1 generative automotive assessment

This release adds **AI Assessment**. It calls a real local Ollama model to extract assets and draft threats from your NEW description. It stores the complete assessment in `ai_assessments`, including input, evidence snapshot, model digest and review. It does not read `threat_patterns.json` for this flow and has no canned fallback.

## Recommended today: Docker Compose in WSL

1. Extract the updated ZIP into a NEW folder. Your current `.venv-wsl` and SQLite database stay in the old folder. Do not overwrite or remove them. The new Docker project has its own persistent volumes.
2. Stop your currently running native app with Ctrl+C so port 8000 is free.
3. Open WSL in the new extracted project directory (the one containing `compose.ai.yaml`). Verify Docker Desktop is running with WSL integration enabled:

```bash
docker --version
docker compose version
```

4. Create the configuration only if it does not already exist:

```bash
cp -n .env.example .env
```

Edit `.env` and set a unique alphanumeric `POSTGRES_PASSWORD`. Avoid URL-special characters because the password is used in the connection URL. Keep the password unchanged once the database volume is initialized.

5. Start the three services:

```bash
docker compose -f compose.ai.yaml up -d --build
```

6. Download the actual model into the Ollama volume (one-time internet download):

```bash
docker compose -f compose.ai.yaml exec ollama ollama pull qwen2.5:3b-instruct
```

7. Open http://localhost:8000. Select **AI Assessment** and click **Check connection**. Confirm both **Model ready** and **PostgreSQL persistence is active**.
8. Enter a title. Paste `Input_Data/new_system_bluetooth.txt` into the description box, or load that text file. Select **1** threat for the first smoke run. Click **Generate and save assessment**. CPU inference may take minutes; the page polls the saved job.
9. Inspect the extracted assets, scenario, assumptions, citations, mitigation, requirement and verification. Expand the evidence snapshot. Record a human review and export the JSON.
10. Refresh the browser and reopen the saved assessment. Try `new_system_charging.txt` to show it processes a different system. These input descriptions are examples, not fixed expected outputs.

## Verify the actual PostgreSQL records

```bash
docker compose -f compose.ai.yaml exec db psql -U tara -d tara -c "SELECT id, title, status, created_at FROM ai_assessments ORDER BY created_at DESC;"
```

Show this in your video to demonstrate database persistence. The complete JSON is in the `payload` column; PostgreSQL can query it with `payload::jsonb`.

## Record genuine local evidence before submission

After successful generation:

```bash
docker compose -f compose.ai.yaml exec app python Code/verify_ai_deployment.py --require-postgres --output /tmp/ai_deployment_verification.json
docker compose -f compose.ai.yaml cp app:/tmp/ai_deployment_verification.json Evaluation_Results/ai_deployment_verification.json
```

This verifies a real model is installed and at least one successful generation exists in PostgreSQL. It records actual model identity and saved results. It does not claim expert correctness.

Record a new 5-10 minute video showing model readiness, the new description, generation, source evidence, database row, review and reload. The bundled older video demonstrates v1.0 offline behavior only.

## Troubleshooting

```bash
docker compose -f compose.ai.yaml ps
docker compose -f compose.ai.yaml logs --tail=80 app ollama db
```

- Model missing: rerun the model pull command and Check connection.
- Port 8000 occupied: stop the old native server or old app container. Do not delete database volumes.
- Generation failed validation: no output is accepted. Try 1 threat and a clearer description. Check the displayed failure. There is no silent rule-based fallback.
- Slow CPU: use 1-2 threats; first inference loads the model. The default service timeout is 600 seconds.
- Out of memory: close other heavy applications or increase Docker/WSL memory. The model's weights alone are not the full runtime memory requirement.
- Docker unavailable: install/configure Docker Desktop with WSL integration, or use the native option below.

## Native WSL option (local Ollama + PostgreSQL already installed)

Use the known working virtualenv. Install/run Ollama according to its official installation instructions, pull `qwen2.5:3b-instruct`, and keep `ollama serve` running. Create an approved local PostgreSQL database with pgvector available, then set:

```bash
export OLLAMA_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=qwen2.5:3b-instruct
export DATABASE_URL='postgresql://tara:YOUR_PASSWORD@127.0.0.1:5432/tara'
./.venv-wsl/bin/python Code/run.py
```

If DATABASE_URL is unset, the page works with SQLite and explicitly shows that PostgreSQL is inactive. This is useful for model testing, but it does not satisfy a demonstration specifically claiming PostgreSQL storage.

## What remains a human responsibility

All generated assessments are drafts. Risks stay Unassessed; the LLM does not assign certified risk ratings. Citation IDs and relationships are validated, not factual entailment. Review existing controls carefully for model errors. Faculty signatures, student contributions and official report formatting remain pending. No pretrained model weights are bundled. The model, packages and container downloads need internet initially; after caching, this flow uses only local services.
