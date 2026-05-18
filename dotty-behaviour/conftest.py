"""pytest rootdir marker — adds dotty-behaviour/ to sys.path so tests can
import the flat top-level modules (`config`, `main`, `perception.*`,
`routes.*`) directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
