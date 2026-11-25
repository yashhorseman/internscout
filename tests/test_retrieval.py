"""Twenty tiny jobs where the right answers are known."""
from datetime import datetime, timezone

import pytest

from app.ingest.models import JobPosting
from app.ingest.store import upsert
from app.retrieval.search import keyword_terms, rrf, search

TOPICS = ["python", "design", "sales", "mlops"]


def vector(topic, weight=1.0):
    v = [0.0] * 768
    v[TOPICS.index(topic)] = weight
    v[100] = 1 - weight
    return v


JOBS = [  # (title, description, location, topic)
    ("Python Backend Intern", "Build APIs with Python and Postgres", "Bengaluru, India", "python"),
    ("Senior Python Engineer", "Python services", "London, UK", "python"),
    ("Snake Charmer Platform Developer", "Services in a popular scripting language", "Pune, India", "python"),
    ("Product Designer", "Figma and user research", "Remote", "design"),
    ("Design Intern", "Figma", "Mumbai, India", "design"),
    ("Account Executive", "Sell software", "New York", "sales"),
    ("ML Platform Engineer", "Model deployment pipelines", "Berlin, Germany", "mlops"),
] + [(f"Account Executive {i}", "Quota carrying sales role", "Chicago", "sales") for i in range(13)]


@pytest.fixture
def jobs(db):
    for i, (title, text, location, topic) in enumerate(JOBS):
        upsert(db, JobPosting(source="greenhouse", board="demo", source_job_id=str(i), company="Demo",
                              title=title, location_raw=location, description_text=text,
                              is_remote=True if location == "Remote" else None,
                              apply_url="u", source_url="u", raw={}), datetime.now(timezone.utc))
        db.execute("update jobs set embedding = %s::vector, embedding_stale = false"
                   " where source_job_id = %s", (str(vector(topic, 1 - i * 0.001)), str(i)))
    return db


def titles(hits):
    return [h.title for h in hits]


def test_keyword_finds_words_but_not_meaning(jobs):
    found = titles(search(jobs, "python", mode="keyword"))
    assert set(found) == {"Python Backend Intern", "Senior Python Engineer"}


def test_semantic_finds_meaning(jobs):
    found = titles(search(jobs, "anything", vector("python"), k=3, mode="semantic"))
    assert "Snake Charmer Platform Developer" in found


def test_hybrid_ranks_results_found_by_both_first(jobs):
    found = titles(search(jobs, "python", vector("python"), k=3, mode="hybrid"))
    assert set(found[:2]) == {"Python Backend Intern", "Senior Python Engineer"}
    assert found[2] == "Snake Charmer Platform Developer"


def test_or_matches_a_natural_query_where_and_does_not(jobs):
    query = "backend internship in bangalore using python"
    assert search(jobs, query, mode="keyword", match="or")
    assert search(jobs, query, mode="keyword", match="and") == []


@pytest.mark.parametrize("mode", ["keyword", "semantic", "hybrid"])
def test_filters_apply_in_every_mode(jobs, mode):
    hits = search(jobs, "python figma", vector("python"), {"level": "intern", "country_code": "IN"},
                  mode=mode)
    assert set(titles(hits)) == {"Python Backend Intern", "Design Intern"}


def test_company_filter_ignores_case(jobs):
    assert search(jobs, "python", mode="keyword", filters={"company": "demo"})
    assert search(jobs, "python", mode="keyword", filters={"company": "other"}) == []


def test_closed_jobs_never_appear(jobs):
    jobs.execute("update jobs set status = 'closed' where title = 'Python Backend Intern'")
    for mode in ("keyword", "semantic", "hybrid"):
        assert "Python Backend Intern" not in titles(search(jobs, "python", vector("python"), mode=mode))


def test_rerank_uses_the_scorer(jobs):
    def prefer_senior(query, passages):
        return [1.0 if p.startswith("Senior") else 0.0 for p in passages]

    hits = search(jobs, "python", vector("python"), k=1, mode="hybrid_rerank", scorer=prefer_senior)
    assert titles(hits) == ["Senior Python Engineer"]


def test_hostile_input_is_harmless(jobs):
    nasty = "'); drop table jobs; -- python & | ! ( : *"
    assert search(jobs, nasty, mode="keyword")
    assert search(jobs, "!!! ... +++", mode="keyword") == []
    assert jobs.execute("select count(*) from jobs").fetchone()[0] == len(JOBS)


def test_terms_keep_language_names():
    assert keyword_terms(["C++", "C#", "Node.js", "full-stack.", "python", "Python"]) == [
        "c++", "c#", "node.js", "full", "stack", "python"]


def test_unknown_filter_or_mode_is_an_error(jobs):
    with pytest.raises(ValueError):
        search(jobs, "x", mode="keyword", filters={"salary": 1})
    with pytest.raises(ValueError):
        search(jobs, "x", mode="semantic")


def test_rrf_adds_both_lists():
    assert [job_id for job_id, _ in rrf([[1, 2], [2, 3]])] == [2, 1, 3]
