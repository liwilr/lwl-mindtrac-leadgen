"""Puts the repository's LeadGen_Tools folder (leadgen_config.py, kw_update.py) on the import path.
LEADGEN_TOOLS overrides the location (tests)."""
import os, sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
TOOLS = os.environ.get("LEADGEN_TOOLS") or os.path.join(_REPO, "LeadGen_Tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
