# UAF POC — Unified Automation Framework Proof of Concept

An end-to-end, AI-driven test automation pipeline powered by **Claude Code** and the **Claude Agentic Framework**. The pipeline targets the [Todo App](https://isvalid-todo-app.onrender.com/) — a full-stack React + Node.js task management application — and integrates with **Jira** for story management and a **Playwright** framework for test execution.

---

## Table of Contents

- [Overview](#overview)
- [Target Application](#target-application)
- [Pipeline Architecture](#pipeline-architecture)
- [Agents](#agents)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Pipeline](#running-the-pipeline)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)

---

## Overview

The UAF POC demonstrates how a multi-agent Claude system can automate the entire software testing lifecycle — from crawling source code and validating a live app, through writing Jira acceptance criteria and generating structured test cases, to producing executable Playwright scripts and running them at scale.

Each agent is a specialist with a defined role, a fixed set of tools, and clear hand-off artefacts. Human-in-the-loop (HIL) checkpoints are built into the agents that require domain judgment before writing back to external systems.

---

## Target Application

| Property | Value |
|---|---|
| Live App | https://isvalid-todo-app.onrender.com/ |
| Source Code | https://github.com/pawansx-22/todoApp |
| API Docs (Swagger) | https://isvalid-todo-app.onrender.com/api/docs/ |
| Jira Board | ToDoApp – Kanban Board (`KAN` project) |
| Tech Stack | React 18, Node.js/Express, PostgreSQL, Prisma, JWT, Swagger/OpenAPI 3 |

---

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Orchestrator                              │
│                  (Claude Code CLI / SDK)                         │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
 ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
 │  Agent 1    │    │   Agent 2    │    │    Agent 3      │
 │  Crawling   │───▶│  App Valid.  │───▶│  Jira Agent     │
 │  Agent      │    │  Agent       │    │  (HIL ✋)       │
 └─────────────┘    └──────────────┘    └────────┬────────┘
        │                  │                      │
        ▼                  ▼                      ▼
     spec.md         app_validation          Gherkin AC
                     _report.md             → Jira issues
                                                  │
                                                  ▼
                                     ┌─────────────────────┐
                                     │     Agent 4         │
                                     │  Test Case Creation │
                                     │  (HIL ✋)           │
                                     └──────────┬──────────┘
                                                │
                                                ▼
                                     ┌─────────────────────┐
                                     │     Agent 5         │
                                     │  Test Script Gen.   │
                                     │  → UAF / Playwright │
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

## Agents

All agents are defined as Claude Code sub-agent markdown files in `.claude/agents/`.

### Agent 1 — Crawling Agent (`crawling-agent.md`)

Crawls `pawansx-22/todoApp` via the GitHub API. Reads the repo tree, backend routes, Prisma schema, Swagger spec, and frontend router. Writes a comprehensive `spec.md` that acts as the single source of truth for all downstream agents.

**Output:** `spec.md`

---

### Agent 2 — App Validation Agent (`app-validation-agent.md`)

Navigates the live Todo App using **Playwright MCP** (headed browser). Registers a test account, visits every route, captures screenshots, and records console errors. Validates the live app behaviour against `spec.md`.

**Input:** `spec.md`
**Output:** `app_validation_report.md`, `screenshots/`

---

### Agent 3 — Jira Agent (`jira-agent.md`) ✋ HIL

Reads all open `Story` issues from the `KAN` Jira project. For each story, drafts **Gherkin Given/When/Then acceptance criteria** using `spec.md` and `app_validation_report.md` as context. Presents all drafts for human review before writing approved AC back to each Jira issue description.

**Input:** `spec.md`, `app_validation_report.md`, Jira KAN stories
**Output:** AC written to Jira issue descriptions

---

### Agent 4 — Test Case Creation Agent (`test-case-creation-agent.md`) ✋ HIL

Prompts the user for a KAN story number. Reads its Gherkin AC from Jira, then generates structured test cases in the following format:

| Step No. | Step Summary | Action | Expected Result | Test Data |
|---|---|---|---|---|

Recommends concrete test data for every step (valid credentials, boundary values, invalid payloads). After human approval, writes the test cases to the existing `Test Cases` Jira subtask and saves a local `.md` copy.

**Input:** KAN story (user-specified), `spec.md`, `app_validation_report.md`
**Output:** Test cases in Jira subtask + `test_cases_KAN-<number>.md`

---

### Agent 5 — Test Script Generation Agent *(planned)*

Converts approved test cases into executable Playwright TypeScript specs, integrated into the [UAF framework](https://github.com/subhadipbhatta/UAF). Generates Page Object JSON definitions and spec files mapped to Jira story IDs.

---

### Agent 6 — Test Execution Agent *(planned)*

Runs the full Playwright suite at scale, parses JSON results, and posts pass/fail status back to Jira as comments.

---

## Prerequisites

| Tool | Purpose |
|---|---|
| [Claude Code](https://claude.ai/code) | CLI for running agents |
| `gh` CLI | GitHub API access (Agent 1) |
| Playwright MCP (`@playwright/mcp`) | Browser automation (Agent 2) |
| Atlassian MCP | Jira read/write (Agents 3 & 4) |
| Node.js / npm | Playwright MCP dependencies |
| Python 3 | `set-playwright-mode.sh` helper |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/subhadipbhatta/UAF_POC.git
cd UAF_POC
```

### 2. Configure credentials

Copy the config template and fill in your values:

```bash
cp config.json.example config.json   # config.json is git-ignored
```

`config.json` fields:

```json
{
  "playwright": { "mode": "headed" },
  "jira": {
    "cloudId": "<your-atlassian-cloud-id>",
    "site": "<your-site>.atlassian.net"
  },
  "testAccount": {
    "email": "<test-email>",
    "password": "<test-password>"
  }
}
```

### 3. Set Playwright mode

```bash
# Run Playwright in headed mode (required for Agent 2)
./scripts/set-playwright-mode.sh headed

# Or headless
./scripts/set-playwright-mode.sh headless
```

Restart Claude Code after changing mode.

### 4. Install Playwright MCP

```bash
npx @playwright/mcp@latest install
```

---

## Running the Pipeline

Agents are invoked from the Claude Code CLI using `@<agent-name>`:

```
# Step 1 — crawl the source repo
@crawling-agent

# Step 2 — validate the live app
@app-validation-agent

# Step 3 — draft and write Jira AC (HIL)
@jira-agent

# Step 4 — generate test cases for a specific story (HIL)
@test-case-creation-agent
```

Each agent is stateless — it reads its input artefacts fresh each run. Agents 3 and 4 pause for human review before writing to Jira.

---

## Project Structure

```
UAF_POC/
├── .claude/
│   └── agents/
│       ├── crawling-agent.md           # Agent 1
│       ├── app-validation-agent.md     # Agent 2
│       ├── jira-agent.md               # Agent 3
│       └── test-case-creation-agent.md # Agent 4
├── scripts/
│   └── set-playwright-mode.sh          # Toggle Playwright headed/headless
├── screenshots/                        # Agent 2 output (git-ignored content)
├── spec.md                             # Agent 1 output — source of truth
├── app_validation_report.md            # Agent 2 output
├── test_cases_KAN-<N>.md              # Agent 4 output (one file per story)
├── config.json                         # Local config — git-ignored
├── .gitignore
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent runtime | Claude Code (claude-sonnet-4-6) |
| Browser automation | Playwright MCP (`@playwright/mcp`) |
| Jira integration | Atlassian MCP |
| GitHub API | `gh` CLI |
| Target app — frontend | React 18, TypeScript, Vite, Material UI |
| Target app — backend | Node.js, Express, TypeScript |
| Target app — database | PostgreSQL 16 via Prisma ORM |
| Target app — auth | JWT Bearer tokens |
