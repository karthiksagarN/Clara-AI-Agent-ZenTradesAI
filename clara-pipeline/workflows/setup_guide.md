# n8n Workflow Setup Guide

## Prerequisites
- Docker and Docker Compose installed
- Ollama running locally with `llama3.1:8b` model pulled
- Python 3.10+ with dependencies installed

## Quick Start

### 1. Start n8n
```bash
cd clara-pipeline
docker-compose up -d
```

n8n will be available at `http://localhost:5678`
- Username: `admin`
- Password: `changeme`

### 2. Import Workflows

1. Open n8n at http://localhost:5678
2. Go to **Workflows** → **Import from File**
3. Import `n8n_pipeline_a.json` (Demo → v1)
4. Import `n8n_pipeline_b.json` (Onboarding → v2)

### 3. Configure Paths

The docker-compose.yml mounts these directories into the n8n container:
- `./recordings` → `/home/node/recordings`
- `./scripts` → `/home/node/scripts`
- `./outputs` → `/home/node/outputs`
- `./prompts` → `/home/node/prompts`

### 4. Run Workflows

**Pipeline A (Demo → v1):**
1. Place demo transcripts in `recordings/demo/`
2. Open Pipeline A workflow in n8n
3. Click **Execute Workflow**
4. Check `outputs/accounts/<id>/v1/` for results

**Pipeline B (Onboarding → v2):**
1. Place onboarding transcripts in `recordings/onboarding/`
2. Open Pipeline B workflow in n8n
3. Click **Execute Workflow**
4. Check `outputs/accounts/<id>/v2/` for results

### 5. Alternative: Run via CLI

If n8n is not available, you can run the pipelines directly:

```bash
# Pipeline A - single file
cd scripts
python3 run_pipeline_a.py ../recordings/demo/bens_electric_demo.txt --skip-transcription

# Pipeline B - single file
python3 run_pipeline_b.py ../recordings/onboarding/bens_electric_onboarding.txt --company "Ben's Electric" --skip-transcription

# Batch run all
python3 run_all.py --transcripts-only
```

## Workflow Architecture

### Pipeline A Flow
```
Manual Trigger → List Demo Files → Split → Run Pipeline A (per file) → Parse → Summary
```

### Pipeline B Flow
```
Manual Trigger → List Onboarding Files → Split → Derive Company → Run Pipeline B → Parse → Summary
```

Both workflows use n8n's Execute Command node to call the Python scripts.
This keeps logic in testable, versionable Python while n8n provides orchestration visibility.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No files found" | Check recordings directory has .txt files |
| Ollama connection error | Ensure Ollama is running: `ollama serve` |
| Python import errors | Install deps: `pip install -r requirements.txt` |
| n8n can't find scripts | Check docker-compose volume mounts |
