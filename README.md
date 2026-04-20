# General Guidelines — AWS Demo Template

This document defines conventions and patterns for AWS demo projects using:
- Backend: Python + FastAPI
- Frontend: Vite.js + React + TypeScript
- UI: AWS Cloudscape Design System

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

```bash
# Backend
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

Vite proxy in `vite.config.ts` forwards `/api`, `/ws`, `/health` to `http://localhost:8000`.

## Git Conventions

### Branches

```
main              # Production. Protected. Deploys via CodePipeline → prod.
dev               # Development/staging. Protected. Deploys via CodePipeline → staging.
feat/{short-desc} # New features — branch from dev, PR back to dev
fix/{short-desc}  # Bug fixes — branch from dev, PR back to dev
hotfix/{desc}     # Urgent prod fixes — branch from main, PR to main AND dev
```

Flow: `feat/xxx` → PR → `dev` (auto-deploys to staging) → PR → `main` (auto-deploys to prod)

### Commits

Format: `<type>: <short description>` (imperative mood, under 72 chars)

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Examples: `feat: add chat streaming`, `fix: handle WS disconnect`, `chore: update deps`

### Deployment (AWS CodePipeline)

- Push to `dev` → CodePipeline triggers staging deployment automatically
- PR merged to `main` → CodePipeline triggers production deployment automatically
- Never deploy manually. All deployments go through the pipeline.
- Pipeline stages: Source → Test → Build → Deploy

### Pipeline Setup

**Prerequisites:**
1. An AWS account with CDK bootstrapped (`cdk bootstrap`)
2. A GitHub CodeConnection created in the AWS Console (CodePipeline → Settings → Connections)

**Step 1 — Set GitHub Secrets**

Go to your repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Description | Example |
|--------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | IAM user access key (for CDK deploy only) | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key | `wJal...` |
| `CDK_DEFAULT_ACCOUNT` | AWS Account ID | `123456789012` |
| `CDK_DEFAULT_REGION` | AWS Region | `us-east-1` |
| `PROJECT_NAME` | Project name (used for stack naming) | `my-demo` |
| `GITHUB_REPO` | This repo's org/name | `DatiLabs-Samples/my-demo` |
| `CONNECTION_ARN` | CodeConnection ARN for GitHub | `arn:aws:codeconnections:us-east-1:123456789012:connection/xxx` |

**Step 2 — Deploy the pipeline (one-time)**

```bash
cd infra
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export CDK_DEFAULT_ACCOUNT=<from secrets>
export CDK_DEFAULT_REGION=<from secrets>
export PROJECT_NAME=<from secrets>
export GITHUB_REPO=<from secrets>
export CONNECTION_ARN=<from secrets>

cdk deploy --all
```

**Step 3 — Approve the GitHub connection**

After the first deploy, go to AWS Console → CodePipeline → Settings → Connections → find your connection → click "Update pending connection" → authorize GitHub access.

**After setup:** every push to `dev` auto-deploys to dev. Every PR merge to `main` auto-deploys to prod. No manual steps.

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
