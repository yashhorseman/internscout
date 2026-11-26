from evals.agreement import split_grades
from evals.label import preview, repeated_lines

ABOUT = "Acme is a company that has been doing wonderful things for a very long time indeed."


def test_preview_skips_the_introduction_a_company_repeats():
    postings = [("Acme", f"{ABOUT}\nRole number {n}: write the services that run our warehouses every day.") for n in range(4)]
    repeated = repeated_lines(postings)
    assert preview(postings[0][1], repeated["Acme"]) == "Role number 0: write the services that run our warehouses every day."


def test_preview_keeps_everything_for_a_company_with_few_postings():
    postings = [("Solo", f"{ABOUT}\nThe role."), ("Solo", f"{ABOUT}\nAnother role.")]
    assert ABOUT in preview(postings[0][1], repeated_lines(postings)["Solo"])


def test_preview_keeps_repeated_text_that_follows_the_role():
    ask = "Requirement shared by every posting: you can read and debug unfamiliar code."
    postings = [("Acme", f"{ABOUT}\nThe role\nRole number {n}: write the services that run our warehouses every day.\n{ask}")
                for n in range(4)]
    shown = preview(postings[0][1], repeated_lines(postings)["Acme"])
    assert shown.startswith("The role\nRole number 0") and shown.endswith(ask)


def test_check_sample_never_repeats_pairs_already_checked():
    from evals.label import check_sample

    grades = {"q1": {n: 0 for n in range(10)}}
    first = set(check_sample(grades, 4))
    assert not first & set(check_sample(grades, 6, exclude=first))


def test_corrections_do_not_change_the_blind_grades():
    rows = [{"query_id": "q1", "job_id": 1, "grade": 2},
            {"query_id": "q1", "job_id": 1, "grade": 0, "after_seeing_ai": True}]
    blind, corrected = split_grades(rows)
    assert blind == {("q1", 1): 2}
    assert corrected == {("q1", 1): 0}
