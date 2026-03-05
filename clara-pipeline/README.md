# Clara Pipeline — Automated Demo-to-Agent Configuration

> An automated zero-cost pipeline that converts sales/demo call recordings into AI voice agent configurations, then refines them after onboarding calls.

---

## 🏗️ Architecture

```
recordings/
├── demo/          (5 transcripts)
└── onboarding/    (5 transcripts)
         ↓
    ┌─────────────────────────────┐
    │  Whisper (local, zero-cost) │  ← Only if audio provided
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

## 📋 Data Flow

### Pipeline A: Demo Call → v1 Agent
1. Ingest demo transcript (or transcribe audio via Whisper)
2. LLM extracts structured Account Memo JSON (Ollama)
3. Schema validation ensures data quality
4. Agent prompt template is filled → Retell Agent Spec v1
5. Outputs saved to `outputs/accounts/<id>/v1/`
6. GitHub Issue created for tracking

### Pipeline B: Onboarding Call → v2 Agent
1. Ingest onboarding transcript
2. LLM extracts **only deltas** compared to v1 memo
3. Delta patched onto v1 → produces v2 memo
4. Schema validation on v2
5. Agent spec regenerated from v2 memo
6. Changelog (JSON + Markdown) generated
7. Outputs saved to `outputs/accounts/<id>/v2/`

---

## 🚀 Quick Start

### Prerequisites
- **macOS/Linux** with Python 3.10+
- **Ollama** installed ([ollama.ai](https://ollama.ai))
- **Docker** (optional, for n8n orchestration)

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/clara-pipeline.git
cd clara-pipeline

# Install Python dependencies
pip install -r requirements.txt

# Pull the LLM model
ollama pull llama3.1:8b
```

Or use the Makefile:
```bash
make setup
```

### 2. Add Transcripts

Place your transcript files:
```
recordings/
├── demo/
│   ├── bens_electric_demo.txt
│   ├── company2_demo.txt
│   └── ...
└── onboarding/
    ├── bens_electric_onboarding.txt
    ├── company2_onboarding.txt
    └── ...
```

### 3. Run the Pipeline

**Batch (all files):**
```bash
make run-all
# or
cd scripts && python3 run_all.py --transcripts-only
```

**Single file:**
```bash
# Pipeline A (demo → v1)
cd scripts
python3 run_pipeline_a.py ../recordings/demo/bens_electric_demo.txt --skip-transcription

# Pipeline B (onboarding → v2)
python3 run_pipeline_b.py ../recordings/onboarding/bens_electric_onboarding.txt \
  --company "Ben's Electric" --skip-transcription
```

### 4. Check Outputs

```
outputs/accounts/bens-electric-abc123/
├── v1/
│   ├── memo.json          # Extracted account data
│   ├── agent_spec.json    # Retell agent configuration
│   └── transcript.txt     # Source transcript
└── v2/
    ├── memo.json          # Updated account data
    ├── agent_spec.json    # Updated agent config
    ├── changelog.json     # Structured diff
    ├── delta.json          # Raw extraction delta
    └── transcript.txt     # Onboarding transcript
```

---

## 🔧 n8n Orchestration (Optional)

### Start n8n
```bash
docker-compose up -d
# Opens at http://localhost:5678 (admin/changeme)
```

### Import Workflows
1. Open n8n → Workflows → Import from File
2. Import `workflows/n8n_pipeline_a.json`
3. Import `workflows/n8n_pipeline_b.json`

See [workflows/setup_guide.md](workflows/setup_guide.md) for details.

---

## 📁 Repository Structure

```
clara-pipeline/
├── docker-compose.yml          # n8n orchestration
├── Makefile                    # Quick commands
├── README.md                   # This file
├── requirements.txt            # Python deps
├── .env.example                # Environment config template
│
├── scripts/
│   ├── utils.py                # Shared utilities, logging, config
│   ├── transcribe.py           # Whisper audio transcription
│   ├── extract.py              # Ollama LLM extraction
│   ├── validate.py             # JSON Schema validation
│   ├── generate_agent.py       # Memo → Retell Agent Spec
│   ├── patch.py                # v1 → v2 diff + changelog
│   ├── run_pipeline_a.py       # Pipeline A runner
│   ├── run_pipeline_b.py       # Pipeline B runner
│   ├── run_all.py              # Batch runner
│   ├── github_issues.py        # GitHub Issues tracking
│   └── generate_diff_viewer.py # Bonus: HTML diff viewer
│
├── prompts/
│   ├── demo_extraction.txt     # Demo call extraction prompt
│   ├── onboarding_extraction.txt # Onboarding delta extraction
│   └── agent_prompt_template.txt # Retell agent system prompt
│
├── schemas/
│   ├── account_memo.schema.json  # Memo validation schema
│   └── agent_spec.schema.json    # Agent spec validation schema
│
├── workflows/
│   ├── n8n_pipeline_a.json     # n8n workflow export
│   ├── n8n_pipeline_b.json     # n8n workflow export
│   └── setup_guide.md          # n8n setup instructions
│
├── recordings/
│   ├── demo/                   # Demo transcripts/audio
│   └── onboarding/             # Onboarding transcripts/audio
│
├── outputs/
│   ├── accounts/<id>/v1/       # v1 outputs per account
│   ├── accounts/<id>/v2/       # v2 outputs per account
│   ├── summary_report.json     # Batch run metrics
│   └── diff_viewer.html        # Bonus: visual diff viewer
│
├── changelog/
│   └── <id>_changes.md         # Per-account markdown changelogs
│
└── tests/
    └── test_pipeline.py        # Unit tests
```

---

## 🎯 Key Design Decisions

### Idempotency
- `account_id` is derived deterministically from company name (slugified + short hash)
- Running twice overwrites, never duplicates

### No Hallucination
- Extraction prompts explicitly instruct: *"If a field is not mentioned, set it to null. Do NOT infer or assume."*
- Missing fields go to `questions_or_unknowns`
- Schema validation catches structural issues

### Conflict Resolution
- Onboarding data **always wins** over demo data
- Old values are logged in the changelog with reason `"onboarding_override"`

### Zero-Cost Stack
| Component | Tool | Cost |
|-----------|------|------|
| Transcription | Whisper (local) | $0 |
| LLM Extraction | Ollama + Llama 3.1 8B | $0 |
| Orchestration | n8n (self-hosted Docker) | $0 |
| Storage | GitHub flat files | $0 |
| Task Tracking | GitHub Issues | $0 |
| Validation | JSON Schema (local) | $0 |

### Separation of Concerns
- **Python scripts** contain all business logic (testable, versionable)
- **n8n** provides orchestration visibility and manual triggers
- **Prompts** are external files (easily iterable without code changes)
- **Schemas** ensure data quality at every step

---

## 🔍 Retell Agent Setup (Manual Steps)

Since Retell's free tier may not support programmatic agent creation:

1. Create a free account at [retellai.com](https://retellai.com)
2. Navigate to Agents → Create New Agent
3. Copy the `system_prompt` from `outputs/accounts/<id>/v2/agent_spec.json`
4. Paste into the agent's System Prompt field
5. Configure voice settings as specified in the `voice_style` field
6. Set up call transfer targets from `call_transfer_protocol.targets`

The `agent_spec.json` output matches the structure needed for Retell configuration.

---

## 📊 Bonus Features

### Diff Viewer (HTML)
Visual comparison of v1 → v2 changes:
```bash
make diff-viewer
# or
cd scripts && python3 generate_diff_viewer.py
```
Open `outputs/diff_viewer.html` in a browser.

### Batch Summary Metrics
After running all files, check `outputs/summary_report.json` for:
- Success/failure counts per pipeline
- Per-account processing results
- Validation warnings

---

## ⚠️ Known Limitations

1. **LLM Extraction Quality**: Ollama + Llama 3.1 8B may occasionally produce imperfect JSON. The pipeline has retry logic and JSON repair, but manual review is recommended.
2. **Account Matching**: Onboarding files are matched to demo accounts by company name. Consistent naming is important.
3. **Whisper Transcription**: Depends on audio quality. For best results, use provided transcripts when available.
4. **n8n Docker**: Requires Docker installed. CLI scripts work independently as an alternative.

## 🚀 Production Improvements

With production access, I would add:
- **Retell API integration** for direct agent creation/updates
- **Webhook triggers** in n8n for automatic processing on file upload
- **PostgreSQL/Supabase** for queryable storage instead of flat files
- **Confidence scoring** for LLM extractions
- **Human-in-the-loop review** step before agent deployment
- **CI/CD pipeline** for automated testing on new PRs
- **Monitoring dashboard** with extraction quality metrics
- **Multi-language support** for transcription and prompts

---

## 🧪 Running Tests

```bash
make test
# or
cd scripts && python3 -m pytest ../tests/ -v
```

---

## 📝 License

This project was created as an assignment submission for Clara Answers.
