# GEMINI.md

This file provides guidance to `gemini-cli` (Claude/Gemini agent) when working with code in this repository. It ensures that the agent makes **pragmatic, careful decisions** and avoids unnecessary mistakes while assisting with development.

---

## Core Instructions for the Agent

* ✅ **Prioritize correctness over speed.**
  Always verify assumptions before making changes. If uncertain, explain the trade-offs or ask for clarification.

* ✅ **Be pragmatic.**
  Prefer working solutions over over-engineered ones. Follow the repository’s patterns and conventions.

* ✅ **Minimize disruption.**
  Modify only what is required. Do not refactor unrelated code unless explicitly asked.

* ✅ **Think step by step.**
  Before making code changes, outline the reasoning in clear steps. Then apply the change.

* ✅ **Fail safely.**
  If a decision has multiple valid paths, document pros/cons and choose the least risky option.

* ✅ **Be explicit about assumptions.**
  State when you’re inferring intent or filling in gaps.

* ✅ **Respect project boundaries.**

  * Do not modify files outside the described scope without explicit request.
  * Follow existing coding standards and file organization.

* ✅ **Check dependencies.**
  Confirm imports, requirements, and integration points before assuming functionality.

* ✅ **Output carefully.**
  Use complete, copy-paste-ready code. Avoid partial snippets unless specifically requested.

---

## Project Overview

DigiClinic is an AI-powered digital medical clinic prototype designed for the NHS. The system features LLM-powered medical consultants with access to comprehensive medical literature for evidence-based diagnostics and treatment recommendations.

---

## Key Documentation

* **README.md**: Project overview, architecture, and team standards
* **roadmap.md**: 7-phase development roadmap
* **requirements.txt**: Python dependencies
* **This file (GEMINI.md)**: Guidance for Gemini/Claude agent

---

## Repository Structure

```
digiclinic/
├── GEMINI.md
├── README.md
├── roadmap.md
├── requirements.txt
├── backend/
│   ├── main.py
│   ├── auth.py
│   ├── api/
│   ├── services/
│   ├── medical/
│   ├── model/
│   └── dat/
└── frontend/
    ├── src/
    ├── dist/
    └── package.json
```

(See README.md for detailed descriptions)

---

## Development Guidance for the Agent

1. **When adding features**

   * Follow modular design. Place new logic in the correct folder (`services/`, `api/`, `model/`, etc.).
   * Document the new code with docstrings and inline comments.

2. **When fixing bugs**

   * Reproduce the issue first if possible.
   * Apply minimal, targeted fixes.
   * Add test coverage if relevant.

3. **When handling environment variables**

   * Never hardcode secrets.
   * Use `.env` file convention and update docs if needed.

4. **When editing the frontend (React/TS)**

   * Use functional components and TypeScript best practices.
   * Ensure compatibility with backend endpoints.

5. **When editing the backend (FastAPI/Python)**

   * Use async endpoints where appropriate.
   * Maintain separation of concerns between `api/` and `services/`.

---

## Decision-Making Principles

* **Correctness > Completeness > Performance > Novelty**
* **Clarity > Cleverness**
* **Document > Assume**

If unsure:
👉 Default to a conservative implementation and note the alternative.

---

## Development Commands

**Run locally:**

```bash
cd backend
source venv/bin/activate
python main.py
```

**Deployment (Railway):**
Uses `Procfile` with `python main.py`.

---

## API Endpoints (Phase 2)

* **Clinical Agents**: `/api/medical/clinical/*`
* **NHS Terminology**: `/api/medical/terminology/*`
* **Medical Vision**: `/api/medical/vision/*`
* **Knowledge Base**: `/api/medical/knowledge/*`
* **Compliance**: `/api/medical/compliance/*`
* **Health Checks**: `/api/medical/system/status`

---

## Final Notes for the Agent

* Always **think before coding.**
* Always **test locally when possible.**
* Always **document what changed and why.**
* When in doubt, **ask before making assumptions.**