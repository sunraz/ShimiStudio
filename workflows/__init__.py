"""
ShimiStudio Workflows Package v2.0
Imports and exposes all workflow functions from ShimiStudio/workflows.py.
"""

import importlib.util
from pathlib import Path

_py_file = Path(__file__).parent.parent / "workflows.py"
if _py_file.exists():
    _spec = importlib.util.spec_from_file_location("workflows_file", _py_file)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

    for _attr in dir(_mod):
        if not _attr.startswith("_"):
            globals()[_attr] = getattr(_mod, _attr)
