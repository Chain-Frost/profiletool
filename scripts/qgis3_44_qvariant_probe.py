"""Isolated QGIS 3.44 diagnostic for PyQt5 QVariant auto-conversion.

This intentionally modifies SIP's process-global QVariant conversion policy for
one disposable CI process. It is not a production workaround or compatibility
acceptance test.
"""

from __future__ import annotations

import sys

import pytest
from PyQt5 import sip
from PyQt5.QtCore import QVariant

if __name__ == "__main__":
    previous = sip.enableautoconversion(QVariant, False)
    print(f"Diagnostic only: previous QVariant autoconversion={previous}; set=False", flush=True)
    try:
        result = pytest.main([
            "-s",
            "-q",
            "/tests_directory/profiletool/tests/test_qgis_layer_lifecycle.py",
        ])
    finally:
        sip.enableautoconversion(QVariant, previous)
    sys.exit(int(result))
