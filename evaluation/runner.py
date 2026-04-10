from __future__ import annotations

from pathlib import Path

from agent.conversation import ConversationAgent
from config import AppConfig
from data_pipeline.io_utils import read_json, write_json
from evaluation.cases import EvaluationCase, EvaluationResult
from evaluation.metrics import context_precision, faithfulness_score, forbidden_keyword_penalty, keyword_coverage


class EvaluationRunner:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.agent = ConversationAgent(config)

    def load_cases(self, path: Path) -> list[EvaluationCase]:
        return [EvaluationCase.model_validate(case) for case in read_json(path, default=[])]

    def run_case(self, case: EvaluationCase) -> EvaluationResult:
        session_id = self.agent.new_session_id()
        response = None
        current_session_id = session_id

        for turn in case.turns:
            current_session_id, response = self.agent.handle_message(turn, current_session_id, persist=False)

        assert response is not None
        answer = response.answer
        is_knowledge_case = case.expected_intent == "knowledge"
        retrieval_faithfulness = faithfulness_score(answer, response) if is_knowledge_case else 1.0
        retrieval_precision = context_precision(response, case.expected_keywords) if is_knowledge_case else 1.0
        scores = {
            "intent_accuracy": 1.0 if response.intent == case.expected_intent else 0.0,
            "action_success_rate": (
                1.0
                if (case.expected_tool is None or response.tool_name == case.expected_tool)
                and (not case.expect_follow_up or response.follow_up_question is not None)
                else 0.0
            ),
            "answer_relevancy": keyword_coverage(answer, case.expected_keywords),
            "faithfulness": retrieval_faithfulness,
            "context_precision": retrieval_precision,
            "safe_response": forbidden_keyword_penalty(answer, case.forbidden_keywords),
            "error_handling_success": (
                1.0 if (case.expect_follow_up == (response.follow_up_question is not None)) else 0.0
            ),
        }
        passed = all(score >= 0.5 for score in scores.values())
        self.agent.discard_session(current_session_id, persist=False)
        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            passed=passed,
            scores=scores,
            expected_intent=case.expected_intent,
            predicted_intent=response.intent,
            expected_tool=case.expected_tool,
            predicted_tool=response.tool_name,
            answer=answer,
            notes=case.notes,
        )

    def run_all(self, cases_path: Path | None = None) -> dict:
        cases = self.load_cases(cases_path or self.config.paths.evaluation_cases_path)
        results = [self.run_case(case).model_dump() for case in cases]

        total_cases = len(results)
        passed_cases = sum(1 for result in results if result["passed"])
        avg_scores: dict[str, float] = {}
        if results:
            for metric_name in results[0]["scores"]:
                avg_scores[metric_name] = sum(result["scores"][metric_name] for result in results) / total_cases

        summary = {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "pass_rate": passed_cases / total_cases if total_cases else 0.0,
            "average_scores": avg_scores,
            "failure_cases": [result for result in results if not result["passed"]],
            "results": results,
        }
        write_json(self.config.paths.evaluation_results_path, summary)
        return summary
