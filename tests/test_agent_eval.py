from evals.agent_report import wilson
from evals.judge import explanations
from evals.label_claims import report


def test_wilson_interval():
    low, high = wilson(0, 20)
    assert low == 0 and 0.15 < high < 0.17
    low, high = wilson(10, 20)
    assert round(low, 2) == 0.30 and round(high, 2) == 0.70


def test_judge_checks_each_explanation_once_and_skips_unknown_ids():
    run = {"id": "q1", "seen": [1], "first_answer": {"recommendations": [
        {"job_id": 1, "why": "Uses Python."}, {"job_id": 9, "why": "Invented."}]},
        "cards": [{"job_id": 1, "why": "Uses Python.", "evidence": "x"},
                  {"job_id": 1, "why": "Matches your search terms.", "evidence": ""}]}
    assert explanations([run]) == [("q1", 1, "Uses Python.")]


def test_judge_agreement_report():
    mine = [{"id": "q", "job_id": n, "why": "w", "label": label}
            for n, label in enumerate(["unsupported", "partly", "supported", "supported"])]
    judged = [{"id": "q", "job_id": n, "why": "w", "supported": ok}
              for n, ok in enumerate([False, True, True, False])]
    text = report(mine, judged)
    assert "judge recall: 50%" in text and "judge precision: 50%" in text and "do not use" in text
