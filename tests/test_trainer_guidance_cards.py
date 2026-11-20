"""Regression coverage for safe trainer-card contextual guidance."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"GUI"/"workspace.html").read_text(encoding="utf-8")


class TrainerGuideTests(unittest.TestCase):
    def test_guidance_is_collapsible_and_uses_actual_engine_metadata(self):
        for expected in (
            'const engineGuidance={', 'image:[', 'video:[', 'audio:[',
            'multimodal:[', 'class="engine-help"', # class supplied through el()
            'engine-help-content', 'const family=category(trainer)',
            'im.loading="lazy"', 'details.append(summary,contents)',
            'card.append(im,label,', 'launchButton(trainer.id)',
            'Before opening this trainer',
            'This guide does not change its settings.'
        ):
            if expected=='class="engine-help"':
                continue
            with self.subTest(expected=expected):
                self.assertIn(expected,HTML)
        self.assertIn('el("details",undefined,"engine-help")',HTML)
        self.assertIn('function renderEngineCards(container,items)',HTML)

    def test_locales_cover_all_guide_copy(self):
        keys=('Image training checklist','Video training checklist','Audio training checklist',
              'Multimodal training checklist','Before opening this trainer',
              'Exact compatibility, recommended GPU memory and supported checkpoint features must be verified in the selected trainer. This guide does not change its settings.')
        for lang in ('es','pt','fr','de','it','ja','ko'):
            data=json.loads((ROOT/'GUI'/'locales'/f'{lang}.json').read_text(encoding='utf-8'))
            for key in keys:
                self.assertTrue(data.get(key),(lang,key))


if __name__=="__main__":
    unittest.main()
