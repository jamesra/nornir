# Root pytest plugin for the umbrella workspace (see pytest.ini).
from __future__ import annotations

collect_ignore = [
    "nornir-pyre/tests/test_shaders_qt.py",
    "nornir-pyre/tests/test_vao_qt.py",
    "nornir-pyre/tests/test_vao_shaders_qt.py",
]
