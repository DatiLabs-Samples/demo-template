# General Guidelines — AWS Demo Template

This document defines conventions and patterns for AWS demo projects using:
- Backend: Python + FastAPI
- Frontend: Vite.js + React + TypeScript
- UI: AWS Cloudscape Design System

## Getting Started

### Local Development

```bash
# Backend
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt && cp .env.example .env  # use requirements.txt for runtime-only
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. Vite proxy forwards `/api`, `/ws`, `/health` to the backend at `:8000`.

### Pipeline Setup (one-time)

**Prerequisites:**
1. An AWS account with CDK bootstrapped (`cdk bootstrap`)
2. A GitHub CodeConnection created in the AWS Console (CodePipeline → Settings → Connections)

**Step 1 — Create a GitHub CodeConnection**

Go to [AWS CodeConnections console](https://console.aws.amazon.com/codesuite/settings/connections) → Create connection → GitHub → authorize. Copy the Connection ARN.

**Step 2 — Deploy the pipeline**

```bash
cd infra
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export CDK_DEFAULT_ACCOUNT=1111111111111
export CDK_DEFAULT_REGION=us-east-1
export PROJECT_NAME=my-demo
export GITHUB_REPO=DatiLabs-Samples/my-demo
export CONNECTION_ARN=arn:aws:codeconnections:us-east-1:123456789012:connection/xxx

cdk deploy --all
```

This is the only manual deploy. After this, the pipeline is self-mutating — it updates itself from the repo.

**Step 3 — Verify**

Push a commit to `dev`. Check AWS Console → CodePipeline to see it trigger automatically.

**How it works:**
- CodeConnection handles GitHub ↔ AWS authentication (no tokens or secrets needed)
- CodeBuild runs with an IAM role that CDK creates automatically
- The env vars above are baked into the CloudFormation template at synth time — only needed during this one-time setup
- After setup: push to `dev` → auto-deploys dev. PR merge to `main` → auto-deploys prod.

---

## Backend-Frontend Communication

### REST API

All REST endpoints live under the `/api` prefix. Use relative URLs in the frontend (Vite proxy handles routing to backend).

```
GET    /api/health              → always present
GET    /api/{resource}          → list
POST   /api/{resource}          → create/invoke
GET    /api/{resource}/{id}     → get single
WS     /ws/{feature}            → WebSocket endpoints
```

### WebSocket Message Protocol

All messages are JSON with a `type` field:

```json
{"type": "start", "prompt_id": "retail"}
{"type": "audio", "data": "<base64>"}
{"type": "text", "data": "Hello!", "role": "ASSISTANT"}
{"type": "error", "data": "Something failed"}
{"type": "stopped"}
```

## Environment Configuration

- `backend/.env` — actual values (git-ignored)
- `backend/.env.example` — template with placeholders (committed)
- Every env var has a sensible default for local dev
- NEVER put AWS credentials in `.env`. Use `AWS_PROFILE` to reference `~/.aws/credentials`
- For production, use IAM roles (ECS task role, Lambda execution role)

## Development Workflow

See [Getting Started](#getting-started) above.

## Git Conventions

### Branches

```
main              # Production. Protected (PRs only from dev). Auto-deploys via CodePipeline.
dev               # Development. Auto-deploys via CodePipeline.
feat/{short-desc} # New features — branch from dev, PR back to dev
fix/{short-desc}  # Bug fixes — branch from dev, PR back to dev
hotfix/{desc}     # Urgent prod fixes — branch from main, PR to main AND dev
```

Flow: `feat/xxx` → PR → `dev` (auto-deploys) → PR → `main` (auto-deploys to prod)

### Commits

Format: `<type>: <short description>` (imperative mood, under 72 chars)

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python files | snake_case | `chat_service.py` |
| Python classes | PascalCase | `ChatService` |
| Python vars/funcs | snake_case | `send_message` |
| React components | PascalCase.tsx | `Dashboard.tsx` |
| Hooks | use*.ts | `useWebSocket.ts` |
| Services/utils | camelCase.ts | `api.ts` |
| TS interfaces | PascalCase | `ChatMessage` |
| API endpoints | lowercase-hyphens | `/api/chat-sessions` |
| Env vars (backend) | UPPER_SNAKE | `AWS_REGION` |
| Env vars (frontend) | VITE_UPPER_SNAKE | `VITE_API_URL` |

## Error Handling

Backend returns consistent JSON:
```json
{"error": "Human-readable message", "detail": "Optional technical detail"}
```

Frontend uses Cloudscape `Flashbar` for transient notifications and `Alert` for persistent errors.

WebSocket errors are sent as messages: `{"type": "error", "data": "description"}`.

## Security

- No hardcoded secrets — use `.env` locally, IAM roles in production
- CORS: allow only `http://localhost:5173` in dev, exact domain in prod
- Pydantic models for ALL request bodies (automatic validation)
- Never log secrets or full audio payloads
- Pin exact dependency versions

## AWS Service Integration

- Centralize boto3 session creation with `AWS_PROFILE` + `AWS_REGION` from config
- Wrap each AWS service in its own module with error handling
- boto3 is synchronous — use `run_in_executor` for async FastAPI endpoints
- For Smithy-based SDKs (e.g., Nova Sonic), bridge credentials via boto3 first

## Cloudscape Design System

Reference: https://cloudscape.design/

Key principles:
- Always import components individually: `import Button from "@cloudscape-design/components/button"`
- App shell: `TopNavigation` + `AppLayout` (with `SideNavigation`, `Flashbar`, `BreadcrumbGroup`)
- Pages: `ContentLayout` + `Header` + `Container` + `SpaceBetween`
- Dark/light mode: `applyMode(Mode.Dark)` from `@cloudscape-design/global-styles`
- Accessible by default — maintain by using `ariaLabel` on icon buttons and `FormField` wrappers

Essential packages:
```
@cloudscape-design/components
@cloudscape-design/global-styles
@cloudscape-design/collection-hooks
@cloudscape-design/design-tokens
```
