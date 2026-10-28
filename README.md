# ABAP Lifecycle Studio

One workspace for SAP ABAP and CRM developers and AMS teams. It takes a ticket from Jira or the
service desk, searches Confluence, past tickets and the current SAP code, recommends a solution with
its sources, plans and drafts the code change, and writes the result back to Confluence so the next
similar ticket is solved faster. People approve every step.

This is **Phase 1**. See [What Phase 1 covers](#what-phase-1-covers).

## Run it

Needs Python 3.12 (3.13 also works) and Node 20+.

```bash
# backend
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Demo mode is on by default: five sample tickets, Confluence pages, SAP
code and a sample model, so the whole flow works without any real system. Try:

1. Role **AMS consultant** → open **INC-4471** → *Start analysis* → *Hand off to developer*
2. Role **Tech lead** → *Approve plan*
3. Role **Developer** → review the code diff → *Approve change*
4. Role **Tech lead** → *Publish*. The new page is now in **Knowledge**.

**INC-4480** shows an incident solved without code. **O2C-170** shows a new requirement.

Tests: `cd backend && .venv/Scripts/python -m pytest`

## Connect real systems

As **Admin**:

- **Models**: add any provider (Anthropic, OpenAI, Azure OpenAI, AWS Bedrock, Google Vertex AI, or any
  OpenAI-compatible URL such as vLLM, Ollama or a company gateway). Give each model a data level:
  `public`, `code` or `production`. The gateway never sends a model more than its level allows.
- **Connections**: Jira (Cloud or Data Center), Confluence (Cloud or Data Center), SAP via ADT
  (NetWeaver 7.40+, S/4HANA, ABAP Cloud) or RFC (older releases; needs the SAP NW RFC SDK and
  `pyrfc`). *Test* detects the SAP release and its profile.
- Secrets are references such as `env:JIRA_TOKEN`; set the variable on the server. See
  `backend/.env.example`.

A real connection always replaces the demo one of the same type. Set `STUDIO_DEMO_MODE=false` to
turn off demo data completely.

## How it is built

| Part | Where | Notes |
|---|---|---|
| Lifecycle flow | `backend/app/orchestrator/graph.py` | LangGraph. Four approval gates use `interrupt()`; flows are checkpointed in SQLite and survive restarts. |
| Stage agents | `backend/app/agents/stages.py` | Knowledge, impact, plan, build, document, publish. |
| Model gateway | `backend/app/llm/` | LiteLLM under the hood; data-level policy and fallback. |
| Connectors | `backend/app/connectors/` | Jira, Confluence, SAP ADT, SAP RFC, release profiles. |
| Knowledge index | `backend/app/knowledge.py` | SQLite FTS5 over Confluence, resolved tickets and pages the studio publishes. |
| Roles | `backend/app/roles.py` | Who may decide at each gate. |
| UI | `frontend/src/` | React + TypeScript. Help texts in `help.ts`. |

## What Phase 1 covers

Works now:

- Ticket intake from Jira / Jira Service Management, or demo tickets
- Knowledge check with sources from Confluence, resolved tickets and current SAP code
- Impact analysis (where-used via ADT; open transports in demo data only)
- Solution plan / RICEFW list, code drafts as diffs against the current source, release-aware syntax
- Confluence page drafts; publishing (create and update) and immediate re-indexing
- Seven roles with their own home screens and rights, audit trail, model registry, connections

Not yet (Phase 2 and later):

- Writing code to SAP, activation, transports, ATC runs, ABAP Unit runs
- Single sign-on (Phase 1 uses a role picker and trusts it, so run it only on a trusted network)
- Embeddings / semantic search, production signals for AMS, ServiceNow, Eclipse ADT plugin
- Long model calls run inside the request; a job queue comes with Phase 2

The real Jira, Confluence and SAP connectors follow the public APIs but have not yet been tested
against your systems.
