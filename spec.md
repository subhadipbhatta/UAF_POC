# UAF POC – Unified Automation Framework Proof of Concept

## Project Overview

This POC demonstrates an end-to-end, AI-driven test automation pipeline using Claude Code and the Claude Agentic Framework. The pipeline targets the **Todo App** — a full-stack React + Node.js task management application — and integrates with Jira for story management and the UAF Playwright framework for test execution.

---

## Target Application

| Property | Value |
|---|---|
| **Live App** | https://isvalid-todo-app.onrender.com/ |
| **Source Code** | https://github.com/pawansx-22/todoApp |
| **API Docs (Swagger)** | https://isvalid-todo-app.onrender.com/api/docs/ |
| **Jira Board** | ToDoApp – Kanban Board |
| **Test Framework** | https://github.com/subhadipbhatta/UAF |

---

## Application Analysis

### Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Material UI (MUI), Emotion |
| Backend | Node.js, Express, TypeScript |
| Database | PostgreSQL 16 (via Prisma ORM) |
| Auth | JWT Bearer tokens |
| API Docs | Swagger / OpenAPI 3.0.3 |
| PWA | Workbox service worker, offline support |
| Testing | Vitest (unit), Playwright (e2e) |

### Database Schema (Prisma)

**User**
- `id` (UUID), `email` (unique), `passwordHash`, `name?`, `profilePicture?`
- `emojisStyle` (default: `"apple"`), `theme` (default: `"system"`), `darkmode` (default: `"auto"`)
- `settings` (JSON), `colorList` (JSON array), `createdAt`, `updatedAt`
- Relations: `tasks[]`, `categories[]`, `favoriteCategories[]`

**Task**
- `id` (UUID), `done` (bool), `pinned` (bool), `name`, `description?`, `emoji?`
- `color` (default: `#248eff`), `date`, `deadline?`, `position?`, `sharedBy?`, `lastSave?`
- Relations: `categories[]` (many-to-many via `TaskCategory`)

**Category**
- `id` (UUID), `name`, `emoji?`, `color` (default: `#248eff`), `lastSave?`
- Relations: `tasks[]` (many-to-many), `favorites[]`

**TaskCategory** — join table (`taskId`, `categoryId`)

**FavoriteCategory** — join table (`userId`, `categoryId`)

---

## API Specification

**Base URL:** `https://isvalid-todo-app.onrender.com/api`

**Authentication:** All protected endpoints require `Authorization: Bearer <JWT>` header.

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Health check → `{ status: "ok" }` |

### Authentication

| Method | Path | Auth | Description | Key Fields |
|---|---|---|---|---|
| POST | `/auth/register` | None | Register new user | `email` (required), `password` min 6 chars, `name?` max 100 chars |
| POST | `/auth/login` | None | Login with credentials | `email`, `password` |

**Auth Response schema:**
```json
{
  "token": "<JWT>",
  "user": { "id": "<uuid>", "email": "<email>", "name": "<string|null>" }
}
```

**Error codes:** `400` Validation, `401` Invalid credentials, `409` Email taken, `429` Rate limited

### User

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/user` | Bearer | Get current user full profile |
| PUT | `/user` | Bearer | Update profile (name, profilePicture, emojisStyle, theme, darkmode, settings, colorList, favoriteCategories) |

**UserProfile response** includes: `name`, `createdAt`, `profilePicture`, `emojisStyle`, `theme`, `darkmode`, `settings`, `colorList`, `categories[]`, `tasks[]`, `favoriteCategories[]`, `deletedTasks[]`, `deletedCategories[]`

### Tasks

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/tasks` | Bearer | List all tasks for current user |
| POST | `/tasks` | Bearer | Create a task (`name` required, max 500 chars) |
| PUT | `/tasks/{id}` | Bearer | Update a task by UUID |
| DELETE | `/tasks/{id}` | Bearer | Delete a task by UUID → `{ success: true }` |

**Task schema fields:** `id`, `done`, `pinned`, `name`, `description?`, `emoji?`, `color`, `date`, `deadline?`, `position?`, `sharedBy?`, `lastSave?`, `category[]`

### Categories

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/categories` | Bearer | List all categories for current user |
| POST | `/categories` | Bearer | Create a category (`name` required, max 200 chars) |
| PUT | `/categories/{id}` | Bearer | Update a category by UUID |
| DELETE | `/categories/{id}` | Bearer | Delete a category by UUID → `{ success: true }` |

**Category schema fields:** `id`, `name`, `emoji?`, `color`, `lastSave?`

---

## Frontend Routes

| Route | Page | Description |
|---|---|---|
| `/` | Home | Main task list view |
| `/add` | AddTask | Create a new task |
| `/task/:id` | TaskDetails | View / edit a specific task |
| `/categories` | Categories | Manage categories |
| `/user` | UserProfile | User profile & settings |
| `/share` | Share | Share tasks via link / QR code |
| `/sync` | Sync | P2P WebRTC task sync |
| `/transfer` | Transfer | Task transfer between devices |
| `/purge` | Purge | Bulk delete / purge tasks |
| `*` | NotFound | 404 page |

### Key Application Features

1. **Task Management** — Create, read, update, delete tasks with name, description, emoji, color, deadline, pinned state
2. **Categories** — Organize tasks into colored/emoji categories; mark as favorites
3. **Share Tasks** — Share via deep-link or QR code (`/share?task=...`)
4. **P2P Sync** — WebRTC-based cross-device sync with auto-merge on conflicts
5. **User Profile** — Avatar, emoji style, theme (color + dark mode), custom color list
6. **Import / Export** — JSON file import/export for backup and transfer
7. **PWA** — Installable, offline-capable; custom splash screens; update prompt
8. **AI Emoji Suggestions** — On-device via Chrome Gemini Nano (experimental)
9. **Task Reading Aloud** — SpeechSynthesis API with voice selection
10. **Dark Theme** — System, light, or dark; multiple color themes

---

## UAF Test Automation Framework

**Repo:** https://github.com/subhadipbhatta/UAF

The UAF (Unified Automation Framework) is a Python-based test framework using Playwright for UI automation and `requests` / Playwright API Context for REST testing.

### Key Framework Concepts

- **Page Object Model (POM)** — Auto-generated from JSON definitions in `pagejsons_playwright/`
- **Project structure** — Each project lives under `src/projects/<project_name>/` (copy from `configuration/project_template/`)
- **Spec files** — Playwright TypeScript specs in `specs/`
- **Configuration** — Project-level `properties/` and `reports/` directories
- **Hybrid testing** — UI + API combined with a single Playwright browser instance

### Project Setup (from UAF README)

```python
import shutil
shutil.copytree("configuration/project_template", "src/projects/todo_app")
```

---

## Multi-Agent Pipeline Architecture

The POC implements six specialist Claude agents orchestrated via Claude Code, each with a defined role, inputs, outputs, and human-in-the-loop checkpoints.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Orchestrator                              │
│                  (Claude Code CLI / SDK)                         │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
 ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
 │  Agent 1    │    │   Agent 2    │    │    Agent 3      │
 │  Crawling   │───▶│  App Valid.  │    │  Jira Agent     │
 │  Agent      │    │  Agent       │    │  (HIL)          │
 └─────────────┘    └──────────────┘    └────────┬────────┘
        │                  │                      │
        ▼                  ▼                      ▼
     spec.md          UI capture            Acceptance
                      + findings            Criteria
                                                  │
                                                  ▼
                                     ┌─────────────────────┐
                                     │     Agent 4         │
                                     │  Test Case Creation │
                                     │  (HIL)              │
                                     └──────────┬──────────┘
                                                │
                                                ▼
                                     ┌─────────────────────┐
                                     │     Agent 5         │
                                     │  Test Script Gen.   │
                                     │  → UAF/Playwright   │
                                     └──────────┬──────────┘
                                                │
                                                ▼
                                     ┌─────────────────────┐
                                     │     Agent 6         │
                                     │  Test Execution     │
                                     │  at Scale           │
                                     └─────────────────────┘
```

---

## Agent Specifications

---

### Agent 1 — Crawling Agent

**Purpose:** Analyze the source code and API documentation to produce `spec.md` — the ground truth for all downstream agents.

**Inputs:**
- GitHub repo: `https://github.com/pawansx-22/todoApp`
- Swagger spec: `https://isvalid-todo-app.onrender.com/api/docs/`

**Tools:** `WebFetch`, `Bash` (gh CLI), `Write`

**Process:**
1. Recursively fetch and parse the GitHub repo file tree
2. Read key backend files: `swagger.ts`, `routes/`, `schemas/`, `prisma/schema.prisma`
3. Read key frontend files: `router.tsx`, `pages/`, `src/contexts/`, `src/services/`
4. Fetch live Swagger JSON from the running app
5. Synthesize into `spec.md`

**Output:** `UAF_POC/spec.md` (this document)

**Human-in-loop:** No — fully automated

---

### Agent 2 — App Validation Agent

**Purpose:** Register into the live app, navigate all routes, and capture UI state as evidence. Validates the live app matches the spec.

**Inputs:**
- Live app URL: `https://isvalid-todo-app.onrender.com/`
- `spec.md` (from Agent 1)

**Tools:** `mcp__playwright__*` (browser navigation, snapshots, screenshots)

**Process:**
1. Navigate to the app homepage and take a screenshot
2. Register a new test account via the UI (or POST `/api/auth/register`)
3. Login and capture the authenticated state
4. Navigate each route: `/`, `/add`, `/categories`, `/user`, `/share`, `/sync`, `/purge`
5. Perform a CRUD cycle: create task → view task → edit task → delete task
6. Create a category, assign it to a task, mark as favorite
7. Capture screenshots and accessibility snapshots at each step
8. Produce `UAF_POC/app_validation_report.md` with findings

**Output:**
- `UAF_POC/app_validation_report.md`
- `UAF_POC/screenshots/` directory with named captures

**Human-in-loop:** No — fully automated; alerts on discrepancies vs spec

---

### Agent 3 — Jira Agent

**Purpose:** Connect to the ToDoApp Jira board, retrieve all user stories, and draft acceptance criteria for each story in Gherkin (Given/When/Then) format.

**Inputs:**
- Jira board: ToDoApp – Kanban Board
- `spec.md` (context)

**Tools:** `mcp__claude_ai_Atlassian_Rovo__*` (Jira search, issue read/write)

**Process:**
1. Authenticate with Jira via Atlassian MCP
2. Query all issues on the ToDoApp Kanban board (`searchJiraIssuesUsingJql`)
3. For each user story:
   - Read the story description and existing acceptance criteria
   - Cross-reference with `spec.md` to ensure completeness
   - Draft acceptance criteria in Gherkin format
   - **[HIL]** Present draft to user for review and approval
   - On approval, write the accepted criteria back to the Jira issue via `addCommentToJiraIssue` or `editJiraIssue`
4. Produce `UAF_POC/jira_stories.json` — a structured export of all stories + finalized AC

**Output:**
- `UAF_POC/jira_stories.json`
- Updated Jira issues with acceptance criteria

**Human-in-loop:** YES — after drafting AC for each story, pause and wait for user approval before writing back to Jira

**AC Format (Gherkin):**
```gherkin
Given <initial context>
When <action taken>
Then <expected outcome>
And <additional assertion>
```

---

### Agent 4 — Test Case Creation Agent

**Purpose:** Transform accepted Jira acceptance criteria into structured, reviewable high-level test cases.

**Inputs:**
- `UAF_POC/jira_stories.json` (from Agent 3)
- `spec.md` (API + UI reference)
- `UAF_POC/app_validation_report.md` (UI evidence)

**Tools:** `mcp__claude_ai_Atlassian_Rovo__*`, `Write`, `Edit`

**Process:**
1. Load all finalized user stories and AC from `jira_stories.json`
2. For each story, generate high-level test cases covering:
   - Happy path scenarios
   - Negative / error scenarios
   - Boundary value cases
   - API-level validations
3. **[HIL]** Present test cases to user for review, accept edits/additions
4. On approval, write test cases to `UAF_POC/test_cases.md`
5. Optionally attach test cases as Jira comments under the respective story

**Output:** `UAF_POC/test_cases.md`

**Human-in-loop:** YES — user reviews and approves/edits test cases per story before finalizing

**Test Case Format:**

| Scenario | Action Steps | Expected Result |
|---|---|---|
| Register with valid email | 1. Navigate to app 2. Click Register 3. Enter valid email + password (min 6 chars) 4. Submit | User is registered and JWT returned; redirected to home |
| Register with duplicate email | 1. Register with an already-used email | HTTP 409 error; user sees "Email already registered" message |

---

### Agent 5 — Test Script Generation Agent

**Purpose:** Convert approved test cases into executable Playwright test scripts, integrated into the UAF framework structure.

**Inputs:**
- `UAF_POC/test_cases.md` (from Agent 4)
- `UAF_POC/jira_stories.json` (story context)
- UAF repo: `https://github.com/subhadipbhatta/UAF`
- `spec.md` (API + route reference)

**Tools:** `Bash` (gh CLI), `Write`, `Edit`, `WebFetch`

**Process:**
1. Clone/read the UAF framework structure (`src/`, `specs/`, `configuration/project_template/`)
2. Create a new UAF project: `src/projects/todo_app/`
3. Generate Page Object JSON definitions for each page:
   - `LoginPage`, `RegisterPage`, `HomePage`, `AddTaskPage`, `TaskDetailsPage`, `CategoriesPage`, `UserProfilePage`
4. Run POM generator to produce Python page objects
5. Generate Playwright TypeScript spec files under `specs/todo_app/`:
   - `auth.spec.ts` — Registration, Login, JWT handling
   - `tasks.spec.ts` — CRUD operations, pinning, deadlines, categories
   - `categories.spec.ts` — Create, update, delete, favorite
   - `user_profile.spec.ts` — Profile update, theme/dark mode
   - `share.spec.ts` — Share link generation and task import
   - `api.spec.ts` — Direct API contract tests (all endpoints)
6. Each spec maps to one or more test cases from `test_cases.md`; Jira story IDs annotated in comments

**Output:**
- `UAF_POC/generated_scripts/` (or PRed into the UAF repo)
  - `specs/todo_app/*.spec.ts`
  - `src/projects/todo_app/pagejsons_playwright/*.json`
  - `src/projects/todo_app/pageobjects/`

**Naming convention:** `TC-<JiraID>_<scenario_slug>` in test titles

**Script template pattern:**
```typescript
import { test, expect } from '@playwright/test';

// Jira: TODO-<N> – <Story Title>
test.describe('Authentication', () => {
  test('TC-001 Register with valid credentials', async ({ page, request }) => {
    // Action Steps from test_cases.md
    // ...
    // Expected result assertions
    // ...
  });
});
```

**Human-in-loop:** No — automated generation; but scripts are placed in a review branch before merging

---

### Agent 6 — Test Execution Agent

**Purpose:** Execute the full Playwright test suite at scale, report results, and optionally update Jira with pass/fail status.

**Inputs:**
- Generated test scripts (from Agent 5)
- UAF framework (`playwright.config.ts`, environment config)
- Target environment: `https://isvalid-todo-app.onrender.com/`

**Tools:** `Bash` (playwright CLI, npm), `mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue`

**Process:**
1. Install dependencies: `npm install --legacy-peer-deps` + `playwright install`
2. Configure `playwright.config.ts` with base URL and reporter settings
3. Execute tests: `npx playwright test specs/todo_app/ --reporter=html,json`
4. Parse JSON results: extract pass/fail counts, failed test names, error messages
5. Generate `UAF_POC/execution_report.md` summary
6. For each failed test, post a comment to the corresponding Jira story with failure details
7. Support parallel execution via Playwright workers (configurable: `--workers=N`)
8. Support tag-based execution: `--grep @smoke`, `--grep @regression`, `--grep @api`

**Output:**
- `UAF_POC/execution_report.md`
- `playwright-report/` (HTML report)
- Jira comments with test results per story

**Scale strategy:**
- Parallel workers via Playwright's built-in `--workers` flag
- Sharding for CI: `--shard=1/4`, `--shard=2/4`, etc.
- Docker-based execution for isolation

**Human-in-loop:** No — fully automated; alerts user on failures for triage

---

## Implementation Plan

### Phase 1 — Foundation (Agents 1 & 2)
- [x] Agent 1: Crawl source code + Swagger → `spec.md` *(this document)*
- [ ] Agent 2: Launch Playwright, register/login, capture app screenshots → `app_validation_report.md`

### Phase 2 — Story Analysis (Agent 3)
- [ ] Agent 3: Connect to Jira, read all stories, draft + review AC (HIL), write back to Jira

### Phase 3 — Test Design (Agent 4)
- [ ] Agent 4: Load stories + AC, generate test cases in table format, review with user (HIL)

### Phase 4 — Script Generation (Agent 5)
- [ ] Agent 5: Generate UAF-compatible Playwright scripts from test cases, map to Jira IDs

### Phase 5 — Execution (Agent 6)
- [ ] Agent 6: Execute tests at scale, report results, update Jira

---

## Claude Code Integration

All agents are implemented as Claude Code sub-agents using:
- **Claude Code CLI** — interactive HIL sessions (Agents 3, 4)
- **Claude SDK** (`claude-sonnet-4-6` or `claude-opus-4-6`) — programmatic agent orchestration
- **MCP Servers:**
  - `@playwright/mcp` — browser automation (Agent 2, 5, 6)
  - `@anthropic/mcp-atlassian-rovo` — Jira read/write (Agent 3, 4, 6)
- **Agent Tool** — spawning specialist sub-agents from an orchestrator
- **Human-in-loop** — `AskUserQuestion` tool pauses execution for review/approval

### Orchestrator Entry Point

```typescript
// UAF_POC/orchestrator.ts
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

async function runPipeline() {
  // Phase 1: Crawling (automated)
  // Phase 2: App Validation (automated)
  // Phase 3: Jira AC (HIL)
  // Phase 4: Test Cases (HIL)
  // Phase 5: Script Gen (automated)
  // Phase 6: Execution (automated)
}
```

---

## File & Directory Structure

```
UAF_POC/
├── spec.md                          # This document (Agent 1 output)
├── app_validation_report.md         # Agent 2 output
├── screenshots/                     # Agent 2 screenshots
├── jira_stories.json                # Agent 3 output
├── test_cases.md                    # Agent 4 output
├── generated_scripts/               # Agent 5 output
│   ├── specs/
│   │   └── todo_app/
│   │       ├── auth.spec.ts
│   │       ├── tasks.spec.ts
│   │       ├── categories.spec.ts
│   │       ├── user_profile.spec.ts
│   │       ├── share.spec.ts
│   │       └── api.spec.ts
│   └── src/
│       └── projects/
│           └── todo_app/
│               ├── pagejsons_playwright/
│               └── pageobjects/
├── execution_report.md              # Agent 6 output
├── orchestrator.ts                  # Pipeline entry point
└── agents/
    ├── crawling_agent.ts
    ├── app_validation_agent.ts
    ├── jira_agent.ts
    ├── test_case_agent.ts
    ├── script_gen_agent.ts
    └── execution_agent.ts
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Claude Agents via SDK | Enables stateful, tool-using agents with streaming HIL |
| Playwright MCP for Agent 2 | Native browser control without separate Selenium infra |
| Atlassian MCP for Agent 3 | Direct Jira read/write without custom OAuth wiring |
| HIL on Agents 3 & 4 | AC and test cases require domain knowledge + approval |
| UAF as the test target framework | Reuses existing Playwright infrastructure; POM auto-gen reduces script writing overhead |
| Jira IDs in test titles | Enables traceability from test run failures back to user stories |
| JSON test results + Jira comments | Closes the loop: Jira becomes the single source of truth for test status |
