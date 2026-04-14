# University of Toronto CIE Resource Hub Conversational Agent

The gitHub repository URL is: https://github.com/Vickylin17/UofT-CIE-Conversational-Agent.git

The deployed agent URL is: https://uoft-cie-conversational-agent-rviilnh4286xgxtfzkf5ht.streamlit.app/

The backup demo video link is: https://utoronto-my.sharepoint.com/personal/manavdeepsingh_lamba_rotman_utoronto_ca/_layouts/15/stream.aspx?id=%2Fpersonal%2Fmanavdeepsingh%5Flamba%5Frotman%5Futoronto%5Fca%2FDocuments%2FLLM%2FB4EB5D77%2DC50A%2D43AB%2DA9A0%2D9FDA3C5CBACD%2EMP4&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&ga=1&referrer=StreamWebApp%2EWeb&referrerScenario=AddressBarCopied%2Eview%2E42d57c9d%2Dc74c%2D4c79%2Daa54%2Dd4ae86d57401

This project is a chat assistant for the University of Toronto Centre for International Experience (CIE) Resource Hub. It can answer questions grounded in the CIE knowledge base, guide users through multi-step actions, keep conversation history within a session, and provide a Streamlit chat interface for demo and testing.

## What The App Can Do

- Answer CIE Resource Hub questions with retrieved source links
- Generate pre-arrival checklists for different student types and arrival situations
- Route students to the most relevant CIE support page or service
- Prepare students for an advising appointment through a multi-turn flow
- Collect appointment booking details through a multi-turn intake flow
- Recommend relevant CIE events and sessions
- Remember earlier turns inside the same saved conversation

## Before You Start

You need:

- Python 3.11 or 3.12
- A terminal
- The course-provided LLM API token
- Internet access for the hosted model endpoint

Important:

- Always run commands from the project folder, not from the parent folder.
- Every time you open a new terminal window, you must activate the virtual environment again.
- You do **not** need to reinstall `requirements.txt` every time. Install once per virtual environment.

## One-Time Setup

### 1. Open Terminal And Go Into The Project Folder

Replace the path below with your own path if needed:

```bash
cd /path/to/UofT-CIE-Conversational-Agent
```

If you are already inside the project folder, keep using that terminal.

### 2. Create A Virtual Environment

Run this once:

```bash
python3 -m venv .venv
```

This creates a local Python environment inside the project.

### 3. Activate The Virtual Environment

```bash
source .venv/bin/activate
```

After activation, your terminal should show something like `(.venv)` at the beginning of the line.

### 4. Install Dependencies

Run this once after creating the virtual environment:

```bash
pip install -r requirements.txt
```

If the installation stops midway because of a network issue, run the same command again.

### 5. Create Your `.env` File

Copy the example file:

```bash
cp .env.example .env
```

Then open `.env` in a text editor and fill in your token:

```env
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://rsm-8430-finalproject.bjlkeng.io/v1
LLM_MODEL=qwen3-30b-a3b-fp8
LLM_API_KEY=your_course_provided_token (Your student number)
LLM_STRICT_MODE=true
LLM_TEMPERATURE=0.1
LLM_MAX_OUTPUT_TOKENS=1600

EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=https://rsm-8430-a2.bjlkeng.io
EMBEDDING_API_KEY=your_course_provided_token (Your student number)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_MODEL=all-MiniLM-L6-v2

CIE_MAX_PAGES=80
CIE_DELAY_SECONDS=1.0
RAG_TOP_K=4
```

Notes:

- If `.env` already exists, do not run the copy command again unless you want to overwrite it. Just edit the existing `.env` file.
- `LLM_API_KEY` is the most important field. Without it, the chat app will not work properly.
- If your embedding endpoint uses the same token, leaving `EMBEDDING_API_KEY` blank is fine.
- The app already forces a reasonably large response length in code, so long answers are less likely to be cut off.
- Do not upload or share your `.env` file because it contains your private token.

### 6. Build The Local Vector Database

Run:

```bash
python3 main.py pipeline
```

This step:

- scrapes and cleans the CIE site content
- writes `data/raw_data.json`
- writes `data/cleaned_docs.json`
- rebuilds the `chroma_db/` vector database

Do this at least once before using the app. If the knowledge base has changed and you want fresh retrieval results, run it again.

## Every Time You Reopen Terminal

If you close Terminal and come back later, do these steps again:

### 1. Go Back Into The Project Folder

```bash
cd /path/to/UofT-CIE-Conversational-Agent
```

### 2. Activate The Virtual Environment Again

```bash
source .venv/bin/activate
```

That is usually enough.

You normally do **not** need to run `pip install -r requirements.txt` again unless:

- you deleted `.venv`
- you are on a different computer
- the virtual environment is broken
- you get a `ModuleNotFoundError`

## Run The App

### Recommended Streamlit Command

Use this command from the project root:

```bash
./.venv/bin/python -m streamlit run app/streamlit_app.py
```

This is the safest version because it forces Streamlit to use the correct Python environment.

If that command works, Streamlit should print a local URL such as:

```text
http://localhost:8501
```

If the browser does not open automatically, copy that URL into your browser manually.

### Alternative

If your virtual environment is already activated, this also works:

```bash
python -m streamlit run app/streamlit_app.py
```

## Other Useful Commands

### Ask One Question In The Terminal

```bash
python3 main.py ask "What does the hub say about UHIP?"
```

### Start A CLI Chat

```bash
python3 main.py chat
```

### Run The Evaluation Suite

```bash
python3 main.py eval
```

This writes results to:

```text
evaluation/results.json
```

## Where Conversation Memory Is Stored

Saved chat sessions are stored outside the repo by default:

```text
~/Library/Application Support/UofT-CIE-Conversational-Agent/sessions.json
```

This means:

- your Streamlit conversations can persist across app restarts
- deleting the repo folder does not automatically delete saved session history
- if you want a fresh conversation state, you can start a new chat in the UI or delete the session file manually

If you want to override this location, set:

```env
CIE_SESSION_STORE_PATH=/your/custom/path/sessions.json
```

## Common Problems And Fixes

### Problem: `streamlit: command not found`

Use:

```bash
./.venv/bin/python -m streamlit run app/streamlit_app.py
```

### Problem: `ModuleNotFoundError`

Most likely causes:

- the virtual environment is not activated
- dependencies were not installed into this environment

Fix:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Problem: The App Opens But Answers `I don't know` Too Often

Possible causes:

- the pipeline was never built
- the vector database is stale
- `.env` is missing or the token is wrong

Fix:

```bash
python3 main.py pipeline
```

Then restart Streamlit.

Also confirm `.env` contains a valid `LLM_API_KEY`.

### Problem: Browser Does Not Open Automatically

Open the local URL printed in the terminal manually, usually:

```text
http://localhost:8501
```

### Problem: Old Answers Or Sessions Still Show Up

The app keeps saved sessions.

You can:

- start a new chat in the sidebar
- delete a saved chat from the sidebar
- remove the session file from `~/Library/Application Support/UofT-CIE-Conversational-Agent/`

### Problem: Embedding Dimension Mismatch In Chroma

If you see an error about embedding dimensions not matching, rebuild the vector store from scratch:

```bash
rm -rf chroma_db
python3 main.py pipeline
```

Then restart the app.

If you are not comfortable using `rm -rf`, you can also delete the `chroma_db` folder manually in Finder and then run:

```bash
python3 main.py pipeline
```

### Problem: Commands Behave Strangely When Run From The Parent Folder

Always run from the project root:

```bash
cd /path/to/UofT-CIE-Conversational-Agent
```

Do not run project commands from a parent folder that contains unrelated Python packages or folders.

## Main Files And What They Do

### Top-Level Files

- `main.py`
  CLI entry point. Runs the data pipeline, single-question mode, chat mode, and evaluation.

- `config.py`
  Central place for environment variables, file paths, model settings, and default app behavior.

- `llm.py`
  Wrapper around the hosted OpenAI-compatible chat model. Handles retries, structured JSON parsing, and fallback behavior.

- `schemas.py`
  Shared Pydantic models for sessions, sources, responses, retrieved documents, and internal data structures.

- `text_utils.py`
  Text normalization and lightweight pattern matching. This is where typo normalization and basic student/arrival detection live.

- `requirements.txt`
  Python dependency list.

### `agent/`

- `agent/conversation.py`
  Main orchestration layer. Handles greetings, guardrails, session memory recall, intent routing, action flows, and knowledge questions.

- `agent/intent.py`
  Intent classification logic. Decides whether a message is knowledge, action, or out-of-scope, and chooses the correct tool when needed.

- `agent/slot_filling.py`
  Extracts parameters from user input during multi-turn actions, such as student type, arrival status, booking topic, and advising details.

### `tools/`

- `tools/checklist.py`
  Builds structured pre-arrival checklists.

- `tools/routing.py`
  Routes a support question to the most relevant CIE service or page.

- `tools/advising.py`
  Runs the advising-preparation flow and formats the preparation summary.

- `tools/booking.py`
  Runs the appointment booking intake flow and validates collected details.

- `tools/events.py`
  Recommends CIE events and sessions.

- `tools/base.py`
  Shared base classes for all actions, including knowledge-grounded actions.

- `tools/registry.py`
  Registers the action tools so the conversation agent can call them.

### `rag/`

- `rag/retriever.py`
  Retrieves relevant documents from the vector database using lexical and semantic signals.

- `rag/service.py`
  Builds answers from retrieved documents, cleans source references, and applies fallback answer behavior.

- `rag/prompting.py`
  Formats retrieved context and short conversation history before sending them to the model.

### `data_pipeline/`

- `data_pipeline/pipeline.py`
  Runs the full scrape-clean-chunk-index pipeline.

- `data_pipeline/scraper.py`
  Crawls the CIE site.

- `data_pipeline/extractor.py`
  Pulls structured content out of raw HTML.

- `data_pipeline/cleaner.py`
  Cleans and normalizes extracted content.

- `data_pipeline/chunker.py`
  Splits cleaned documents into retrieval chunks.

- `data_pipeline/embeddings.py`
  Creates embeddings using the hosted endpoint or local fallback.

- `data_pipeline/vector_store.py`
  Writes and queries the Chroma vector database.

- `data_pipeline/io_utils.py`
  Shared JSON read/write helpers.

### `memory/`

- `memory/store.py`
  Saves and loads chat sessions from JSON. This is what allows saved chats to persist across app restarts.

### `guardrails/`

- `guardrails/policies.py`
  Greeting handling, capability questions, prompt injection detection, out-of-scope checks, and immigration disclaimer triggers.

### `app/`

- `app/streamlit_app.py`
  The Streamlit user interface. Handles the chat layout, task buttons, saved chat sidebar, loading spinner, and source rendering.

### `evaluation/`

- `evaluation/test_cases.json`
  Test prompts used for evaluation and regression checks.

- `evaluation/runner.py`
  Runs the evaluation set end-to-end.

- `evaluation/metrics.py`
  Calculates simple pass/fail metrics such as keyword coverage and context precision.

### Generated Data And Folders

- `data/raw_data.json`
  Raw scraped content.

- `data/cleaned_docs.json`
  Cleaned and normalized corpus used before chunking.

- `chroma_db/`
  Local persistent vector database used for retrieval.

- `evaluation/results.json`
  Saved evaluation output from the most recent run.

## Suggested First Demo Path

If you want a simple sanity-check after setup, test in this order:

1. `What does the hub say about UHIP?`
2. `Who should I contact about my study permit?`
3. `I want to book an individual appointment`
4. `Give me a pre-arrival checklist for a PhD student arriving next year`
5. `What did you say earlier about UHIP?` inside the same chat session

If these all work, the main pieces of the app are running correctly.
