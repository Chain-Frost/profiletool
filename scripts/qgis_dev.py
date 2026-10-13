"""Load the working checkout when QGIS starts with --code."""

import importlib.util
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

import qgis.utils
from qgis.core import Qgis
from qgis.utils import iface

root_value = globals().get("PROFILETOOL_DEV_ROOT") or os.environ.get("PROFILETOOL_DEV_ROOT")
root = Path(root_value) if root_value else Path(__file__).resolve().parents[1]
status_path = Path(tempfile.gettempdir()) / "profiletool-qgis-dev-status.json"
status = {"qgis_version": Qgis.QGIS_VERSION, "checkout": str(root)}

try:
    previous = qgis.utils.plugins.get("profiletool") or getattr(iface, "profiletool_dev", None)
    if previous is not None:
        previous.unload()
    for name in list(sys.modules):
        if name == "profiletool" or name.startswith("profiletool."):
            del sys.modules[name]
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location(
        "profiletool", root / "__init__.py", submodule_search_locations=[str(root)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["profiletool"] = module
    spec.loader.exec_module(module)
    plugin = module.classFactory(iface)
    # Keep the instance accessible from the QGIS Python console.
    iface.profiletool_dev = plugin
    plugin.initGui()
    plugin.run()
    qgis.utils.plugins["profiletool"] = plugin
    if "profiletool" not in qgis.utils.active_plugins:
        qgis.utils.active_plugins.append("profiletool")
    status["loaded"] = True
except Exception:
    status["loaded"] = False
    status["traceback"] = traceback.format_exc()
    traceback.print_exc()
finally:
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
