import black


def format_with_black(source_code: str) -> tuple[str, bool]:
    """
    Runs black formatting on a string of Python source code, in-process
    (no subprocess, no shell-out) — deterministic and safe, unlike asking
    an LLM to guess/reconstruct a "corrected" file.

    Returns (formatted_code, changed) where `changed` is True if black
    actually modified anything.
    """
    try:
        formatted = black.format_str(source_code, mode=black.Mode())
    except black.NothingChanged:
        return source_code, False
    except Exception:
        return source_code, False

    return formatted, formatted != source_code