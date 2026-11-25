"""HTML to plain text, and the content hash used for change detection."""
import hashlib
import re
from html.parser import HTMLParser

BLOCK_TAGS = {"p", "div", "br", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "section"}
SKIP_TAGS = {"script", "style"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skipping += 1
        elif tag == "li":
            self.parts.append("\n- ")  # keep requirement lists readable
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skipping = max(0, self.skipping - 1)
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return clean_text("".join(parser.parts))


# a UTF-8 lead byte followed by the right number of continuation bytes, each read as latin-1
_MOJIBAKE = re.compile("[\xc2-\xdf][\x80-\xbf]|[\xe0-\xef][\x80-\xbf]{2}|[\xf0-\xf4][\x80-\xbf]{3}")


def repair_mojibake(text: str) -> str:
    """Undo UTF-8 that was decoded as latin-1 somewhere upstream ("â\\x80\\x99" -> "’")."""
    def decode(match: re.Match) -> str:
        try:
            return match.group().encode("latin-1").decode("utf-8")
        except UnicodeDecodeError:
            return match.group()

    return _MOJIBAKE.sub(decode, text)


def clean_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\xa0", " ")  # Postgres rejects NUL
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    # a bullet whose text sat inside <p> lands on the next line; rejoin it
    text = re.sub(r"(?m)^-\n+(?=[^-\n])", "- ", text)
    text = re.sub(r"(?m)^-$\n?", "", text)         # empty bullets
    text = re.sub(r"(?m)^(- .*)\n\n+(?=- )", r"\1\n", text)  # no gaps inside a list
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def content_hash(title: str, location_raw: str | None, description_text: str) -> str:
    joined = "|".join(part.strip() for part in (title, location_raw or "", description_text))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
