from __future__ import annotations

import argparse
import json
import logging
import sys

from agent.conversation import ConversationAgent
from config import load_config
from data_pipeline.pipeline import run_pipeline
from evaluation.runner import EvaluationRunner
from exceptions import ConfigurationError
from logging_utils import configure_logging


LOGGER = logging.getLogger(__name__)


def run_chat(agent: ConversationAgent) -> None:
    session_id = agent.new_session_id()
    print(f"Session ID: {session_id}")
    print("Type 'exit' to stop.")
    while True:
        message = input("\nYou: ").strip()
        if message.lower() in {"exit", "quit"}:
            break
        _, response = agent.handle_message(message, session_id)
        print(f"\nAssistant: {response.answer}")
        if response.sources:
            print("Sources:")
            for source in response.sources:
                print(f"- {source.title} | {source.section} | {source.url}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UofT CIE Resource Hub conversational agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("pipeline", help="Run scraping, cleaning, chunking, and Chroma indexing")

    ask_parser = subparsers.add_parser("ask", help="Ask a single question")
    ask_parser.add_argument("question", help="Question or action request for the agent")
    ask_parser.add_argument("--session-id", dest="session_id", default=None)

    subparsers.add_parser("chat", help="Start an interactive CLI chat session")
    subparsers.add_parser("eval", help="Run the evaluation suite")
    return parser


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()

    if args.command == "pipeline":
        stats = run_pipeline(config)
        print(json.dumps(stats, indent=2))
        return

    try:
        agent = ConversationAgent(config)
        if args.command == "ask":
            session_id, response = agent.handle_message(args.question, args.session_id)
            payload = {
                "session_id": session_id,
                "answer": response.answer,
                "intent": response.intent,
                "tool_name": response.tool_name,
                "guardrails": response.guardrails,
                "sources": [source.model_dump() for source in response.sources],
                "metadata": response.metadata,
            }
            print(json.dumps(payload, indent=2))
            return

        if args.command == "chat":
            run_chat(agent)
            return

        if args.command == "eval":
            summary = EvaluationRunner(config).run_all()
            print(json.dumps(summary, indent=2))
            return
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
