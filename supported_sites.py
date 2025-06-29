"""
Runtime-generated list of all sites supported by the current yt-dlp build.

SUPPORTED_SITES: List[Tuple[str, str]]
    (Display-name, homepage URL) pairs, suitable for populating a sidebar.

The list is built at import-time by inspecting yt-dlp extractors, so it always
matches the installed version.
"""
from __future__ import annotations

import re
from typing import List, Tuple, Sequence

from yt_dlp.extractor import gen_extractors


def _patterns(valid_url_field) -> List[str]:
    """Return a list of regex patterns from _VALID_URL (may be str or Sequence)."""
    if isinstance(valid_url_field, str):
        return [valid_url_field]
    if isinstance(valid_url_field, Sequence):
        # flatten nested tuples/lists
        out: list[str] = []
        for item in valid_url_field:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, Sequence):
                out.extend([s for s in item if isinstance(s, str)])
        return out
    return []


def _domain_from_regex(pattern: str) -> str | None:
    m = re.search(r"https?://(?:www\.)?([^/]+)/", pattern)
    return m.group(1) if m else None


_sites: list[Tuple[str, str]] = []

for ie in gen_extractors():
    if ie.IE_NAME == "generic":
        continue  # skip fallback extractor

    host: str | None = None
    if hasattr(ie, "_VALID_URL"):
        for pat in _patterns(ie._VALID_URL):
            host = _domain_from_regex(pat)
            if host:
                break
    host = host or f"{ie.IE_NAME}.com"
    display = ie.IE_NAME.replace("_", " ").title()
    url = f"https://{host}"
    pair = (display, url)
    if pair not in _sites:  # deduplicate when many extractors share domain
        _sites.append(pair)

SUPPORTED_SITES: List[Tuple[str, str]] = sorted(_sites, key=lambda t: t[0].lower())
