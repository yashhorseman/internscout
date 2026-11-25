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
