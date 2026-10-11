LIKE_ESCAPE = "\\"


def escape_like(term: str) -> str:
    """Neutralize LIKE wildcards so user input is matched literally."""
    return (
        term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", LIKE_ESCAPE + "%")
        .replace("_", LIKE_ESCAPE + "_")
    )
