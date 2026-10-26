"""Shared settings and API-key loading (this computer's key store, see LeadGen_Tools/leadgen_secrets.py) for the
hunter-apollo-v3 scripts."""

import hashlib
import os

MAX_PATH = 240  # stay under Windows' 260-character path limit

OUTPUT_FIELDS = [
    "company", "domain", "email", "type", "first_name", "last_name",
    "position", "seniority", "department", "confidence", "linkedin",
    "source", "match_confidence", "match_reason",
]
RELEVANT_DEPARTMENTS = {"executive", "sales", "marketing", "procurement"}


def cache_file(cache_dir, name):
    """<cache_dir>/<name>, with the name cut short and given a hash suffix when the full path would pass MAX_PATH
    (long session scratchpad paths otherwise make the cache write fail on Windows). Same name -> same file."""
    path = os.path.join(cache_dir, name)
    room = MAX_PATH - len(os.path.abspath(cache_dir)) - 1
    if len(os.path.abspath(path)) <= MAX_PATH or room < 24:
        return path
    stem, ext = os.path.splitext(name)
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:12]
    return os.path.join(cache_dir, stem[:room - len(digest) - len(ext) - 1] + "_" + digest + ext)


def load_api_key(name):
    """The key from this computer's key store (environment variable, system keychain or DPAPI file), via the
    repository's LeadGen_Tools/leadgen_secrets.py. Keys are never read from files in the repository or run folder."""
    import sys
    tools = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "LeadGen_Tools"))
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import leadgen_secrets
    return leadgen_secrets.get(name)
