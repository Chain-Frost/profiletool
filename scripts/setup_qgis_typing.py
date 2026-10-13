"""Extract matching official PyQt definitions without installing Qt binaries."""

# ruff: noqa: INP001 -- Standalone editor setup utility.
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from qgis.PyQt.QtCore import PYQT_VERSION_STR

root = Path(__file__).resolve().parents[1]
destination = root / ".vscode" / "qgis-type-stubs"
wheels = destination / "wheels"
wheels.mkdir(parents=True, exist_ok=True)
if not PYQT_VERSION_STR.startswith("6."):
    message = "This setup helper currently targets the installed QGIS/PyQt6 environment."
    raise SystemExit(message)

subprocess.run(  # noqa: S603 -- Fixed pip download command using this interpreter.
    [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--no-deps",
        "--only-binary=:all:",
        f"PyQt6=={PYQT_VERSION_STR}",
        "--dest",
        str(wheels),
    ],
    check=True,
)
matches = list(wheels.glob(f"pyqt6-{PYQT_VERSION_STR}-*.whl"))
if len(matches) != 1:
    message = "Expected exactly one matching PyQt6 wheel in the typing cache."
    raise SystemExit(message)
wheel = matches[0]
extracted = []
with zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        member = Path(name)
        if member.parts[0] != "PyQt6" or member.suffix != ".pyi":
            continue
        target = destination / member
        target.parent.mkdir(parents=True, exist_ok=True)
        text = archive.read(name).decode("utf-8")
        # SIP's official QtCore stub uses an unimported Any in this alias.
        # Qualify its intended type; keep the callback signature unchanged.
        text = text.replace("collections.abc.Callable[..., Any]", "collections.abc.Callable[..., typing.Any]")
        if "collections.abc." in text:
            text = "import collections.abc\n" + text
        target.write_text(text, encoding="utf-8")
        extracted.append(name)
package = destination / "PyQt6"
(package / "__init__.pyi").write_text(
    "# Analysis-only package for matching official PyQt6 definitions.\n", encoding="utf-8"
)
manifest = {
    "package": "PyQt6",
    "version": PYQT_VERSION_STR,
    "source": f"https://pypi.org/project/PyQt6/{PYQT_VERSION_STR}/",
    "wheel": wheel.name,
    "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    "definitions": extracted,
    "normalization": "Qualify unimported callback Any as typing.Any and explicitly import collections.abc when referenced.",
}
(destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Extracted {len(extracted)} matching definitions to {destination}")
