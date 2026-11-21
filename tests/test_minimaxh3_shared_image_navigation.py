"""The MiniMax-H3 Image catalogue entry shares the MiniMax-H3 trainer UI.

The server pins the model to image mode; avoid inventing a second HTML trainer.
"""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"GUI"/"trainer_ui_minimaxh3.html").read_text(encoding="utf-8")
JS=(ROOT/"GUI"/"trainer_quick_nav.js").read_text(encoding="utf-8")


class MiniMaxH3SharedUITests(unittest.TestCase):
    def test_image_mode_is_pinned_from_server_settings(self):
        for part in (
            "if (data.h3_model_forced === 'image')",
            "window.H3_IMAGE = true;",
            "document.title = 'OrkiLab — MiniMax-H3 Image';",
            "model.value = 'image';",
            "applyH3ImageMode();",
            "const confirmedH3Mode = data.h3_model_forced === 'image' ? 'image' : 'video';",
            "document.body.dataset.orkiTrainerMode = confirmedH3Mode;",
            "document.dispatchEvent(new CustomEvent('orkilab:trainer-mode', {",
        ):
            with self.subTest(part=part):
                self.assertIn(part,HTML)
        self.assertIn('src="/trainer_quick_nav.js"',HTML)
        self.assertIn('src="/assets/orkilab-pilot.js"',HTML)

    def test_mode_hint_is_read_only_and_late_fetch_safe(self):
        for part in (
            "document.body.dataset.orkiEngine === 'minimaxh3'",
            "nav.append(modeInfo);",
            "modeInfo.hidden = true;",
            "event.detail?.mode",
            "document.addEventListener('orkilab:trainer-mode'",
            "document.body.dataset.orkiTrainerMode",
            "window.H3_IMAGE === true",
            "modeInfo.textContent = label(",
        ):
            with self.subTest(part=part):
                self.assertIn(part,JS)
        for forbidden in ("fetch(", "localStorage", "sessionStorage", "/api/train", "innerHTML"):
            self.assertNotIn(forbidden,JS)

    def test_translations_for_both_modes(self):
        keys=(
            "MiniMax-H3 Image: image and edit LoRAs. Video and audio controls are unavailable in this mode.",
            "MiniMax-H3: video and audio LoRAs."
        )
        for lang in ("es","pt","fr","de","it","ja","ko"):
            locale=json.loads((ROOT/"GUI"/"locales"/f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                with self.subTest(lang=lang,key=key):
                    self.assertTrue(locale.get(key))


if __name__=="__main__":
    unittest.main()
