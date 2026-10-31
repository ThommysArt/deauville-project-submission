import unicodedata


def to_slug(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = "".join(c if c.isalnum() or c.isspace() else " " for c in text)
    return "-".join(text.split())
