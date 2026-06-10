"""pytest configuration: make both backend/ and project root importable."""
from __future__ import annotations
import sys
from pathlib import Path

# Project root (contains worker_dft/)
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# backend/ (contains app/)
_BACKEND = Path(__file__).parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
