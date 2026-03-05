# Clara Pipeline — Automated Demo-to-Agent Configuration

> A fully automated, **zero-cost** pipeline that converts sales/demo call recordings into AI voice agent configurations (Retell-compatible), then refines them after onboarding calls — producing versioned Account Memos, Agent Specs, and structured Changelogs.

**Built for:** Clara AI Internship Assignment  
**Author:** Karthik Sagar  
**Repo:** [github.com/karthiksagarN/Clara-AI-Agent-ZenTradesAI](https://github.com/karthiksagarN/Clara-AI-Agent-ZenTradesAI)

---

## 🏗️ Architecture

```
recordings/
├── demo/          (5 transcripts)
└── onboarding/    (5 transcripts)
         ↓
    ┌─────────────────────────────┐
    │  Whisper (local, zero-cost) │  ← Only if audio files provided
    └─────────────────────────────┘
         ↓
    ┌─────────────────────────────┐
    │  Ollama + Llama 3.1 8B      │  ← Local LLM extraction
    │  (structured JSON output)    │
    └─────────────────────────────┘
         ↓
    ┌──────────────┐  ┌──────────────┐
    │ Account Memo │  │ Retell Agent │  ← Pipeline A output (v1)
    │ v1 (JSON)    │  │ Spec v1      │
    └──────────────┘  └──────────────┘
         ↓ (after onboarding)
    ┌──────────────┐  ┌──────────────┐  ┌───────────┐
    │ Account Memo │  │ Retell Agent │  │ Changelog │  ← Pipeline B output (v2)
    │ v2 (JSON)    │  │ Spec v2      │  │ (JSON+MD) │
    └──────────────┘  └──────────────┘  └───────────┘
         ↓
    ┌─────────────────────────────────────────────────┐
    │  GitHub (versioned outputs) + n8n (orchestration)│
    └─────────────────────────────────────────────────┘
```

### Zero-Cost Stack

| Component | Tool | Cost |
|-----------|------|------|
| Transcription | Whisper (local) | $0 |
| LLM Extraction | Ollama + Llama 3.1 8B | $0 |
| Orchestration | n8n (self-hosted Docker) | $0 |
| Storage | GitHub flat files | $0 |
| Task Tracking | GitHub Issues | $0 |
| Validation | JSON Schema (local) | $0 |

---

## 📋 Data Flow

### Pipeline A: Demo Call → v1 Agent
1. Ingest demo transcript (or transcribe audio via Whisper)
2. LLM extracts structured Account Memo JSON via Ollama (temperature 0.1, zero-hallucination prompt)
3. JSON Schema validation ensures data quality
4. Jinja2 agent prompt template is filled → Retell Agent Spec v1
5. Outputs saved to `clara-pipeline/outputs/accounts/<account-id>/v1/`
6. GitHub Issue created for tracking (optional)

### Pipeline B: Onboarding Call → v2 Agent
1. Ingest onboarding transcript
2. LLM extracts **only deltas** (changes) compared to v1 memo
3. Delta deep-merged onto v1 → produces v2 memo (onboarding always wins)
4. JSON Schema validation on v2
5. Agent spec regenerated from v2 memo
6. Structured changelog (JSON + Markdown) generated with before/after values
7. Outputs saved to `clara-pipeline/outputs/accounts/<account-id>/v2/`

---

## 🚀 Running Locally (Step-by-Step)

### Prerequisites

| Requirement | Version | How to Install |
|-------------|---------|----------------|
| **macOS or Linux** | — | — |
| **Python** | 3.10+ | Pre-installed on macOS; or `brew install python` |
| **Ollama** | Latest | [ollama.ai](https://ollama.ai) → Download for Mac |
| **Docker** | Latest | [docker.com](https://docker.com) (optional, for n8n) |
| **Git** | Any | Pre-installed on macOS; or `brew install git` |

### Step 1: Clone the Repository

```bash
git clone https://github.com/karthiksagarN/Clara-AI-Agent-ZenTradesAI.git
cd Clara-AI-Agent-ZenTradesAI/clara-pipeline
```

### Step 2: Install & Start Ollama

```bash
# If not already installed, download from https://ollama.ai
# Then pull the required model:
ollama pull llama3.1:8b

# Verify it's available:
ollama list
# Should show: llama3.1:8b

# Ollama runs automatically as a background service on macOS.
# If needed, start it manually:
ollama serve  # (skip if already running — "address already in use" is fine)
```

### Step 3: Create Python Virtual Environment

```bash
# From the clara-pipeline/ directory:
python3 -m venv venv
source venv/bin/activate

# Install all dependencies:
pip install -r requirements.txt
```

**Dependencies installed:**
- `requests` — HTTP client for Ollama API
- `openai-whisper` — Local audio transcription (only needed for audio files)
- `python-dotenv` — Environment variable loading from `.env`
- `jsonschema` — JSON Schema Draft-07 validation
- `python-slugify` — Slugify company names for deterministic account IDs
- `deepdiff` — Deep JSON diffing for changelogs
- `jinja2` — Template rendering for agent prompts
- `rich` — Pretty terminal output

### Step 4: Configure Environment

```bash
# Copy the example env file:
cp .env.example .env

# Edit .env with your settings (defaults work out of the box):
```

**Environment Variables Reference:**

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.1:8b` | LLM model for extraction |
| `WHISPER_MODEL` | `base` | Whisper model size (tiny/base/small/medium/large) |
| `OUTPUT_DIR` | `./outputs` | Where pipeline outputs are saved (relative to project root) |
| `RECORDINGS_DIR` | `./recordings` | Where transcripts are read from |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |
| `GITHUB_TOKEN` | *(empty)* | GitHub personal access token (optional, for issue tracking) |
| `GITHUB_REPO` | *(empty)* | GitHub repo in `owner/repo` format |
| `N8N_PORT` | `5678` | n8n web UI port |
| `N8N_BASIC_AUTH_USER` | `admin` | n8n login username |
| `N8N_BASIC_AUTH_PASSWORD` | `changeme` | n8n login password |

> **Note:** The default `.env` values work immediately — no configuration needed to run the pipeline locally.

### Step 5: Add Transcripts

Place transcript `.txt` files in the appropriate folders:

```
clara-pipeline/
└── recordings/
    ├── demo/
    │   ├── bens_electric_demo.txt        # Demo call transcript
    │   ├── company2_demo.txt
    │   └── ...
    └── onboarding/
        ├── bens_electric_onboarding.txt  # Onboarding call transcript
        ├── company2_onboarding.txt
        └── ...
```

### Step 6: Run Pipeline A (Demo → v1 Agent)

```bash
cd scripts

# Process a single demo transcript:
python3 run_pipeline_a.py ../recordings/demo/bens_electric_demo.txt --skip-transcription

# What happens:
#   1. Reads the demo transcript
#   2. Sends it to Ollama for structured extraction
#   3. Validates the extracted JSON against schema
#   4. Generates Retell Agent Spec from the account memo
#   5. Saves everything to outputs/accounts/<account-id>/v1/
```

The pipeline prints the `account_id` (e.g., `bens-electric-solutions-team-0876ff`). **Save this ID** — you'll need it for Pipeline B.

**Expected output files:**
```
outputs/accounts/<account-id>/v1/
├── memo.json          # Structured account data extracted from demo call
├── agent_spec.json    # Complete Retell-compatible agent configuration
└── transcript.txt     # Copy of the source transcript
```

### Step 7: Run Pipeline B (Onboarding → v2 Agent)

```bash
# Use the account-id from Pipeline A output:
python3 run_pipeline_b.py ../recordings/onboarding/bens_electric_onboarding.txt \
  --account-id <account-id-from-step-6> --skip-transcription

# Example with real ID:
python3 run_pipeline_b.py ../recordings/onboarding/bens_electric_onboarding.txt \
  --account-id bens-electric-solutions-team-0876ff --skip-transcription
```

**Expected output files:**
```
outputs/accounts/<account-id>/v2/
├── memo.json          # Updated account data (demo + onboarding merged)
├── agent_spec.json    # Updated Retell agent configuration
├── changelog.json     # Structured diff (what changed, old vs new values)
├── delta.json         # Raw delta extracted from onboarding call
└── transcript.txt     # Copy of the onboarding transcript
```

### Step 8: Run All Accounts (Batch Mode)

```bash
# Process all transcript pairs at once:
python3 run_all.py --transcripts-only

# Or use Make:
cd .. && make run-all
```

### Step 9: Verify Outputs

```bash
# View the generated account memo:
cat ../outputs/accounts/<account-id>/v1/memo.json | python3 -m json.tool

# View the agent spec:
cat ../outputs/accounts/<account-id>/v1/agent_spec.json | python3 -m json.tool

# View the changelog (v1 → v2 diff):
cat ../outputs/accounts/<account-id>/v2/changelog.json | python3 -m json.tool
```

---

## 🔧 n8n Orchestration (Optional)

n8n provides a visual workflow UI for triggering and monitoring the pipeline.

### Start n8n
```bash
# From the clara-pipeline/ directory:
docker-compose up -d

# Access the UI:
open http://localhost:5678
# Login: admin / changeme (configurable in .env)
```

### Import Workflows
1. Open n8n → Workflows → Import from File
2. Import `workflows/n8n_pipeline_a.json`
3. Import `workflows/n8n_pipeline_b.json`

### Stop n8n
```bash
docker-compose down
```

See [workflows/setup_guide.md](clara-pipeline/workflows/setup_guide.md) for detailed n8n setup instructions.

---

## 📁 Repository Structure

```
clara-pipeline/
├── docker-compose.yml          # n8n orchestration
├── Makefile                    # Quick commands (make setup, make run-all, etc.)
├── README.md                   # Documentation
├── requirements.txt            # Python dependencies
├── .env.example                # Environment config template
│
├── scripts/
│   ├── utils.py                # Shared utilities, logging, config, file I/O
│   ├── transcribe.py           # Whisper audio → text transcription
│   ├── extract.py              # Ollama LLM structured extraction (with retries)
│   ├── validate.py             # JSON Schema validation + business logic checks
│   ├── generate_agent.py       # Memo → Retell Agent Spec (Jinja2 templates)
│   ├── patch.py                # v1 + delta → v2 deep merge + changelog generation
│   ├── run_pipeline_a.py       # Pipeline A orchestrator (Demo → v1)
│   ├── run_pipeline_b.py       # Pipeline B orchestrator (Onboarding → v2)
│   ├── run_all.py              # Batch runner for all transcript pairs
│   ├── github_issues.py        # GitHub Issues creation for tracking
│   └── generate_diff_viewer.py # Bonus: HTML visual diff viewer
│
├── prompts/
│   ├── demo_extraction.txt     # Demo call extraction prompt (zero-hallucination)
│   ├── onboarding_extraction.txt # Onboarding delta-only extraction prompt
│   └── agent_prompt_template.txt # Jinja2 Retell agent system prompt template
│
├── schemas/
│   ├── account_memo.schema.json  # JSON Schema Draft-07 for account memos
│   └── agent_spec.schema.json    # JSON Schema Draft-07 for agent specs
│
├── workflows/
│   ├── n8n_pipeline_a.json     # n8n visual workflow (Pipeline A)
│   ├── n8n_pipeline_b.json     # n8n visual workflow (Pipeline B)
│   └── setup_guide.md          # n8n setup instructions
│
├── recordings/
│   ├── demo/                   # Input: demo call transcripts (.txt) or audio
│   └── onboarding/             # Input: onboarding call transcripts (.txt) or audio
│
├── outputs/
│   └── accounts/<id>/
│       ├── v1/                 # Pipeline A outputs (memo, agent_spec, transcript)
│       └── v2/                 # Pipeline B outputs (memo, agent_spec, changelog, delta)
│
├── changelog/
│   └── <id>_changes.md         # Per-account human-readable changelogs
│
└── tests/
    └── test_pipeline.py        # Unit tests
```

---

## 🎯 Key Design Decisions

### Idempotency
- `account_id` is derived deterministically from company name (slugified + short MD5 hash)
- Running the same transcript twice overwrites outputs — never creates duplicates
- Example: "Ben's Electric Solutions Team" → `bens-electric-solutions-team-0876ff`

### Zero-Hallucination Extraction
- Extraction prompts explicitly instruct: *"If a field is not mentioned in the transcript, set it to null. Do NOT infer, guess, or assume."*
- Missing/unknown fields are collected into `questions_or_unknowns` for human follow-up
- JSON Schema validation catches structural issues before outputs are saved
- LLM temperature set to 0.1 for maximum consistency

### Conflict Resolution (v1 → v2)
- Onboarding data **always wins** over demo data when merging
- Old values are preserved in the changelog with reason `"onboarding_override"`
- Deep merge handles nested objects (e.g., updated business hours sub-fields)

### Separation of Concerns
- **Python scripts** — all business logic (testable, versionable, CI-ready)
- **Prompt templates** — external `.txt` files (iterate prompts without code changes)
- **JSON Schemas** — validation contracts for data quality enforcement
- **n8n workflows** — visual orchestration layer (triggers, monitoring, manual reruns)

---

## 🔍 Retell Agent Setup (Manual Steps)

Since Retell's free tier may not support programmatic agent creation:

1. Create a free account at [retellai.com](https://retellai.com)
2. Navigate to **Agents → Create New Agent**
3. Copy the `system_prompt` from `outputs/accounts/<id>/v2/agent_spec.json`
4. Paste into the agent's **System Prompt** field
5. Configure voice settings as specified in the `voice_style` field
6. Set up call transfer targets from `call_transfer_protocol.targets`

The `agent_spec.json` output is structured to match Retell's configuration format.

---

## 📊 Bonus Features

### HTML Diff Viewer
Visual side-by-side comparison of v1 → v2 changes:
```bash
cd scripts && python3 generate_diff_viewer.py
# Open outputs/diff_viewer.html in a browser
```

### Batch Summary Metrics
After `run_all.py`, check `outputs/summary_report.json` for:
- Success/failure counts per pipeline stage
- Per-account processing results and timings
- Validation warnings

---

## 🧪 Running Tests

```bash
# From clara-pipeline/:
source venv/bin/activate
python3 -m pytest tests/ -v

# Or use Make:
make test
```

---

## ⚠️ Known Limitations

1. **LLM Extraction Quality** — Llama 3.1 8B may occasionally produce imperfect JSON. The pipeline has retry logic (3 attempts) and JSON repair, but manual review is recommended.
2. **Account Matching** — Onboarding files are matched to demo accounts by `account_id`. Use `--account-id` flag in Pipeline B for reliable matching.
3. **Whisper Transcription** — Audio quality affects transcription accuracy. Use provided transcripts when available (`--skip-transcription` flag).
4. **n8n Docker** — Requires Docker installed. All CLI scripts work independently without n8n.

---

## 🚀 Production Improvements

With production access and budget, I would add:
- **Retell API integration** for direct agent creation/updates (no manual copy-paste)
- **Webhook triggers** in n8n for automatic processing on file upload
- **PostgreSQL/Supabase** for queryable storage instead of flat JSON files
- **Confidence scoring** for LLM extractions with human-in-the-loop review
- **CI/CD pipeline** with automated testing on every PR
- **Monitoring dashboard** with extraction quality metrics and drift detection
- **Multi-language support** for transcription and prompt localization

---

## 📝 License

This project was created as an assignment submission for Clara Answers.
