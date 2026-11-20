"""Restrict remote Dashboard promotions to the two approved first-party projects."""
import ast
import unittest
from pathlib import Path
from urllib.parse import urlparse

# Foundation CI intentionally runs without Flask. Exercise just the pure
# validation functions, without importing server routes or mocking Flask.
source = (Path(__file__).resolve().parents[1] / "scripts" / "promotions_feed.py").read_text(encoding="utf-8")
module = ast.parse(source)
selected = [
    node for node in module.body
    if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in ("_text", "_validate"))
    or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ALLOWED_REPOS" for t in node.targets))
]
namespace = {"urlparse": urlparse}
exec(compile(ast.Module(body=selected, type_ignores=[]), "<promotions-validator>", "exec"), namespace)
_validate = namespace["_validate"]


def item(url):
    return {"id": "test", "enabled": True,
            "title": {"es": "Prueba"}, "description": {"es": "Descripción"},
            "url": url}


class PromotionUrlTests(unittest.TestCase):
    def test_only_approved_github_repositories_are_accepted(self):
        approved = (
            "https://github.com/jlopfri921/OrkiLab-LoRA-TrainerStudio",
            "https://github.com/jlopfri921/orkicad-ai",
        )
        invalid = (
            "https://github.com/jlopfri921/orkiedu",
            "https://github.com/other-owner/orkicad-ai",
            "https://github.com/jlopfri921/orkicad-ai/issues",
            "https://github.com/jlopfri921/orkicad-ai?utm_source=tracker",
            "https://orkiup.com/",
            "http://github.com/jlopfri921/orkicad-ai",
            "https://github.com.evil.invalid/jlopfri921/orkicad-ai",
        )
        result = _validate({"version": 1, "items": [item(u) for u in (*approved, *invalid)]})
        self.assertEqual([entry["url"] for entry in result], list(approved))


if __name__ == "__main__":
    unittest.main()
