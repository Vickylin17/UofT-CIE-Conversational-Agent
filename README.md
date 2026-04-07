# University of Toronto CIE Resource Hub Conversational Agent

Production-quality conversational AI system for the University of Toronto Centre for International Experience (CIE) Resource and Information Hub. The project combines web scraping, RAG, multi-turn action handling, safety guardrails, evaluation, and a Streamlit demo UI.

## What This Project Does

- Scrapes and cleans public CIE Resource Hub and related CIE event/support pages
- Builds a Chroma vector database for retrieval
- Answers knowledge questions with RAG and source attribution
- Supports multi-turn action flows with session memory
- Applies guardrails for out-of-scope and prompt-injection behavior
- Evaluates the agent on a 15-case test set
- Provides a Streamlit UI and CLI interface

## Assignment Compliance Snapshot

- Knowledge base size: 80 scraped documents
- Actions implemented: 4
- Multi-turn actions: yes
- Persistent session state: yes
- Evaluation set: 15 cases
- Latest evaluation result: 14/15 passing

Detailed requirement-by-requirement status is documented in requirements_audit.md.

## Tech Stack

Key libraries and frameworks used in this repository:

- `requests` and `beautifulsoup4` for crawling and HTML parsing
- `langchain-text-splitters` for recursive chunking
- `chromadb` for persistent vector storage
- `sentence-transformers` for local embeddings
- `openai` for OpenAI-compatible hosted LLM access
- `streamlit` for the chat demo
- `pydantic` for schemas and validation
- `tenacity` for retry handling
- `python-dotenv` for environment configuration
- `scikit-learn` for the hashing-based offline embedding fallback

## Repository Guide

### Root Files

- main.py: CLI entrypoint for pipeline, chat, single-question inference, and evaluation.
- config.py: Central configuration for scraping, embeddings, retrieval, paths, and hosted LLM settings.
- llm.py: OpenAI-compatible client wrapper used for the provided Qwen endpoint.
- schemas.py: Shared Pydantic models for documents, session state, retrieved sources, and responses.
- logging_utils.py: Shared logging setup.
- exceptions.py: Custom exception classes.
- requirements.txt: Python dependencies.
- .env.example: Example environment variables for local setup.

### Data And Artifacts

- data/raw_data.json: Raw structured scraped documents.
- data/cleaned_docs.json: Cleaned document corpus after normalization and deduplication.
- data/sessions.json: Persistent session memory store.
- chroma_db: Persisted Chroma vector database.
- evaluation/results.json: Latest evaluation summary and per-case outcomes.

### Application Packages

- data_pipeline: End-to-end ingestion stack: crawler, extractor, cleaner, chunker, embeddings, vector store, and pipeline runner.
- rag: Retrieval, context formatting, fallback answer generation, and source deduplication.
- tools: Mock actions: checklist, routing, advising preparation, and event recommendation.
- agent: Intent routing, slot filling, and main conversation orchestration.
- memory: JSON-backed session persistence.
- guardrails: Prompt injection detection, out-of-scope handling, disclaimers, and conversation niceties.
- evaluation: Evaluation schemas, metrics, runner, and test set.
- app: Streamlit UI for demoing the agent.

## Architecture Overview

1. The scraper starts from the CIE Resource Hub and related CIE event seeds, respects `robots.txt`, removes navigation/footer noise, and saves structured documents.
2. Cleaned sections are chunked with `RecursiveCharacterTextSplitter` and stored in Chroma with URL, title, category, and section metadata.
3. The agent classifies each user turn as `knowledge`, `action`, or `out_of_scope`.
4. Knowledge turns use retrieval plus a strict answer policy with source attribution.
5. Action turns invoke tool handlers and collect missing parameters over multiple turns when needed.
6. Session history and collected parameters persist in JSON so the same session can continue across runs.
7. Guardrails intercept prompt injection attempts, casual greetings, capability questions, unsupported topics, and immigration disclaimer cases.

## Setup

### 1. Create A Virtual Environment

First, cd to the folder where you saved this respository.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example file:

```bash
cp .env.example .env
```

Then set the hosted model credentials in `.env`:

```bash
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://rsm-8430-finalproject.bjlkeng.io/v1
LLM_MODEL=qwen3-30b-a3b-fp8
LLM_API_KEY=your_course_provided_token
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
CIE_MAX_PAGES=80
CIE_DELAY_SECONDS=1.0
RAG_TOP_K=4
```

Notes:

- `LLM_API_KEY` should be the token supplied for the course endpoint.
- The code uses the provided hosted endpoint for LLM tasks by default.
- Embeddings are local by default using `sentence-transformers`.
- If the hosted LLM is unavailable, the app falls back to heuristic routing and extractive answering, but the required course-compliant setup is to use the hosted endpoint.

## How To Run The Project

### Build The Data Pipeline

```bash
python3 main.py pipeline
```

This will:

- crawl the site
- save `data/raw_data.json`
- save `data/cleaned_docs.json`
- rebuild the `chroma_db` collection

### Ask One Question From The CLI

```bash
python3 main.py ask "What does the hub say about UHIP?"
```

### Start An Interactive CLI Chat

```bash
python3 main.py chat
```

### Continue A Saved Session

The memory store is persistent. You can reuse a session ID:

```bash
python3 main.py ask "I need a pre-arrival checklist." --session-id YOUR_SESSION_ID
python3 main.py ask "I'm a graduate student arriving soon." --session-id YOUR_SESSION_ID
```

### Run The Evaluation Suite

```bash
python3 main.py eval
```

This writes the summary and failure analysis to: results.json

### Launch The Streamlit Demo

```bash
streamlit run app/streamlit_app.py
```

If your shell resolves Streamlit to a different Python environment, use:

```bash
python3 -m streamlit run app/streamlit_app.py
```

## Supported User Requests

Examples of knowledge questions:

- `What does the hub say about UHIP?`
- `What does the hub say about finances for international students?`
- `Is there anything about student peer support?`

Examples of actions:

- `Give me a pre-arrival checklist`
- `Who should I contact about my study permit?`
- `Help me prepare for an advising appointment`
- `Recommend events about immigration`

## Evaluation Summary

Latest saved results in `evaluation/results.json`:

- Total cases: 15
- Pass rate: 14/15
- Average intent accuracy: 1.0
- Average faithfulness: 0.9222

Known remaining issue:

- The `knowledge-roadmap` case still returns a very short snippet from the Roadmap page, so its heuristic faithfulness score remains lower than the threshold.

## Safety And Reliability Features

- Prompt injection phrase detection and sanitization
- Out-of-scope refusal handling
- Automatic immigration disclaimer for immigration-specific responses
- Clarification prompts for vague or missing tool parameters
- Graceful `I don't know` fallback when the answer is not supported by retrieved evidence
- Source attribution for knowledge answers
- Persistent session memory in `data/sessions.json`

## Important Notes For Demo And Submission

- Run `python3 main.py pipeline` before demoing if the vector store has not been built yet.
- Keep your `.env` file private because it contains your hosted endpoint token.
- The repository currently covers the code, data pipeline, evaluation, and demo UI requirements.
- The non-code course deliverables still need to be prepared manually:
  - presentation deck PDF
  - backup demo video
  - optional public deployment
