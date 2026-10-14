"""Keep the static form interface synchronized with the authoritative .ui file."""

import ast
import xml.etree.ElementTree as ET
from pathlib import Path


def test_profile_form_attributes_match_designer_widgets_and_layouts() -> None:
    """Each generated form field must have the exact Qt Designer class type."""
    root = Path(__file__).resolve().parents[1]
    designer = ET.parse(root / "ui" / "profiletool.ui").getroot()  # noqa: S314 -- Parse the trusted tracked form.
    expected = {e.attrib["name"]: e.attrib["class"] for kind in ("widget", "layout") for e in designer.iter(kind)}
    root_widget = designer.find("widget")
    assert root_widget is not None
    expected.pop(root_widget.attrib["name"])
    tree = ast.parse((root / "ui" / "profiletool_form_types.py").read_text(encoding="utf-8"))
    form = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Ui_ProfileTool")
    actual = {
        node.target.id: ast.unparse(node.annotation)
        for node in form.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert actual == expected
