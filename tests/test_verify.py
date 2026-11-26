from app.agent.verify import supported

JOB = {"title": "Backend Intern", "company": "Acme", "location": "Bangalore, Karnataka",
       "country_code": "IN", "is_remote": None, "level": "intern",
       "description": "You will write Python and JavaScript services on PostgreSQL. We go fast."}


def test_location():
    assert supported("location", "Bengaluru", JOB)  # other spelling
    assert supported("location", "Bangalore, India", JOB)  # country from the code
    assert not supported("location", "Mumbai", JOB)
    assert not supported("location", "Bangalore, Germany", JOB)


def test_level():
    assert supported("level", "internship", JOB)
    assert not supported("level", "entry-level", JOB)
    assert not supported("level", "mid", JOB)


def test_remote_not_stated_is_not_supported():
    assert not supported("remote", "true", JOB)
    assert not supported("remote", "false", JOB)
    assert supported("remote", "true", {**JOB, "is_remote": True})
    assert supported("remote", "false", {**JOB, "is_remote": False})


def test_skills_are_whole_words():
    assert supported("skill", "Python", JOB)
    assert supported("skill", "Postgres", JOB)  # synonym
    assert not supported("skill", "Java", JOB)  # only JavaScript is there
    assert not supported("skill", "Golang", JOB)  # "go fast" is not the language
    assert supported("skill", "Go", {**JOB, "description": "Services in Go."})
    assert not supported("skill", "C", {**JOB, "description": "We use C++ daily."})


def test_company():
    assert supported("company", "acme", JOB)
    assert not supported("company", "Globex", JOB)
