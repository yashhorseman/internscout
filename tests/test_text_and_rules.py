from app.ingest.classify import classify_level, parse_country
from app.ingest.text import content_hash, html_to_text


def test_bullets_keep_their_line_breaks():
    html = "<h3>Requirements</h3><ul><li><p>Python</p></li><li>SQL&nbsp;&amp; Git</li></ul><p>Bye</p>"
    assert html_to_text(html) == "Requirements\n\n- Python\n- SQL & Git\n\nBye"


def test_scripts_are_dropped():
    assert html_to_text("<p>Hi</p><script>alert(1)</script>") == "Hi"


def test_hash_ignores_surrounding_space_and_sees_real_changes():
    assert content_hash("A", None, "text") == content_hash(" A ", "", "text\n")
    assert content_hash("A", "Pune", "text") != content_hash("A", "Delhi", "text")


def test_levels():
    assert classify_level("Software Engineering Internship") == "intern"
    assert classify_level("Backend Intern, 2027") == "intern"
    assert classify_level("Internal Auditor") == "unknown"
    assert classify_level("International Tax Analyst") == "unknown"
    assert classify_level("Senior Associate") == "senior"
    assert classify_level("New Grad Software Engineer") == "entry"
    assert classify_level("Software Engineer") == "unknown"


def test_countries():
    assert parse_country("Bengaluru-VTP, India") == "IN"
    assert parse_country("Gurgaon") == "IN"
    assert parse_country("Mohali, IND") == "IN"
    assert parse_country("Palo Alto, CA") == "US"
    assert parse_country("Remote, Canada; Remote, United States") is None
    assert parse_country("Remote - US") == "US"
    assert parse_country("Indianapolis, Indiana") is None
    assert parse_country("Bengaluru; London") is None  # two countries: do not guess
    assert parse_country("Join us remotely") is None
    assert parse_country(None) is None


def test_repair_mojibake_fixes_only_broken_sequences():
    from app.ingest.text import repair_mojibake

    broken = "Thrive’s café ₹5".encode("utf-8").decode("latin-1")
    assert repair_mojibake(broken) == "Thrive’s café ₹5"
    assert repair_mojibake("Thrive’s café ₹5 Âge") == "Thrive’s café ₹5 Âge"
