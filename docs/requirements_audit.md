# Final Project Requirements Audit

This audit checks the repository against the requirements listed in `Final Project Details.pdf`.

## Code And Runtime Requirements

- Knowledge base with minimum 50 public documents: met
  - The live pipeline scraped 80 public CIE pages and stored them in `data/raw_data.json` and `data/cleaned_docs.json`.
- Respect robots.txt and ethical data use: met in code
  - The crawler checks `robots.txt`, uses delays, and avoids duplicate fetches.
- Intent classification and routing: met
  - Implemented in `agent/intent.py` and `agent/conversation.py`.
- Knowledge QA with RAG and source attribution: met
  - Implemented in `rag/retriever.py`, `rag/service.py`, and shown in the Streamlit UI.
- Minimum 3 actions: met
  - `pre_arrival_checklist`
  - `support_routing`
  - `advising_preparation`
  - `event_recommendation`
- At least one multi-turn action collecting 2+ parameters: met
  - Checklist and advising flows both collect multiple parameters over turns.
- Actions validate inputs and handle errors: met
  - Missing or vague parameters trigger follow-up questions.
- State persists across sessions: met
  - JSON-backed memory store in `memory/store.py`.
- Conversation memory inside a session: met
  - Session history is persisted and passed into the agent flow.
- Guardrails for out-of-scope and prompt injection: met
  - Implemented in `guardrails/policies.py`.
- Error handling and graceful fallback: met
  - Unknown or unsupported questions return `I don't know` or a clarification.
- Evaluation set of 10-15 tests: met
  - 15 cases in `evaluation/test_cases.json`.
- Report accuracy and failure analysis: met
  - Saved to `evaluation/results.json`.

## Technical Constraint

- Hosted LLM endpoint requirement: met in configuration
  - The code now defaults to the provided hosted endpoint:
    - Base URL: `https://rsm-8430-finalproject.bjlkeng.io/v1`
    - Model: `qwen3-30b-a3b-fp8`
  - Required environment variable: `LLM_API_KEY`

## Documentation Requirement

- README with setup instructions, dependencies, and architecture overview: met
  - See `README.md`.
- Major dependency attribution: met
  - Listed in `README.md`.

## Non-Code Deliverables Still Needed Outside This Repository Build

- Presentation deck PDF: not generated in code
- Backup demo video: not generated in code
- Optional public deployment: not included

These items are required by the assignment but must still be produced manually.
