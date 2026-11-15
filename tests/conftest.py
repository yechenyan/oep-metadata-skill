"""Import the distributable skill code without editing installed packages."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/oep-metadata/scripts"
sys.path.insert(0, str(SCRIPTS))
