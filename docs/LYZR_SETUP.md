# LifeOS — Lyzr Multi-Agent Triad Configuration

LifeOS harnesses the **Lyzr Agent Studio** platform to orchestrate collaborative multi-agent intelligence. This document explains how the Lyzr Agent Triad is configured and how Composio tool execution connects to real-world APIs.

---

## 1. Lyzr Studio Overview

Lyzr provides managed agent execution environments with tool bindings and persistent memory context.

LifeOS utilizes three collaborative agent personas:
1. **Lyzr Manager Agent** (Primary Orchestrator)
2. **Lyzr Fact Finder Agent** (Context & Entity Specialist)
3. **Lyzr Data Analyst Agent** (Temporal & Mathematical Specialist)

---

## 2. Agent Triad Configuration

In your `.env` or cloud environment:

```ini
LYZR_API_KEY=your_lyzr_api_key_here
LYZR_API_URL=https://agent-prod.studio.lyzr.ai/v3/inference/chat/
LYZR_TOOL_EXECUTE_URL=https://agent-prod.studio.lyzr.ai/v3/inference/tools/execute

# Agent IDs (Created in Lyzr Studio)
LYZR_MANAGER_AGENT_ID=your_manager_agent_id
LYZR_FACT_FINDER_AGENT_ID=your_fact_finder_agent_id
LYZR_DATA_ANALYST_AGENT_ID=your_data_analyst_agent_id
LYZR_USER_ID=user@example.com
```

---

## 3. Agent Responsibilities & Personas

### A. Lyzr Manager Agent
- **Role**: Root orchestrator of the 10-node pipeline.
- **System Directive**: Decomposes spoken user goals into executable sub-tasks, assigns responsibilities to Fact Finder and Data Analyst, assesses action risk level, and generates structured execution plans.
- **Output Schema**:
  ```json
  {
    "summary": "Check calendar and report availability for tomorrow",
    "required_specialists": ["data_analyst"],
    "proposed_actions": [
      {
        "action_type": "read_calendar",
        "title": "Check Google Calendar for Tomorrow",
        "risk_level": "low"
      }
    ]
  }
  ```

### B. Lyzr Fact Finder Agent
- **Role**: Entity resolution and semantic fact verification.
- **System Directive**: Extracts recipient emails, event titles, explicit constraints, and queries past conversation context.

### C. Lyzr Data Analyst Agent
- **Role**: Mathematical computation, schedule analysis, and ISO 8601 / RFC3339 boundary calculation.
- **System Directive**: Evaluates busy windows, computes free minutes between meetings during work hours (9:00 AM - 6:00 PM), and formats output in human-readable breakdowns.

---

## 4. Composio Tool Bindings (Google Calendar, Tasks, Gmail)

Tool execution is bridged via Composio APIs embedded inside the Lyzr ecosystem:
- **`GOOGLECALENDAR_LIST_EVENTS`**: Fetches real-time events for given `timeMin` and `timeMax`.
- **`GOOGLETASKS_CREATE_TASK`**: Creates tasks under user's primary task list.
- **`GMAIL_CREATE_DRAFT`**: Creates draft email without sending, awaiting user review.

---

## 5. Fail-Safe Fallback Mechanics

If any Lyzr agent endpoint experiences transient timeouts or rate limits:
1. `WorkflowService` falls back to a deterministic semantic parser (`_fallback_planning()`).
2. Standard action templates are staged using extracted transcript entities.
3. The pipeline continues progressing without stranding the user.
