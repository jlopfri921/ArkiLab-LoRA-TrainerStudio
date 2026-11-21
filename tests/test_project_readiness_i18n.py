"""Project training actions and dataset readiness must be localized and truthful."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
class ProjectReadinessI18nChecks(unittest.TestCase):
    def test_workspace_uses_prepared_dataset_state_instead_of_obsolete_export_text(self):
        html=(ROOT/"GUI"/"workspace.html").read_text(encoding="utf-8")
        for token in (
            't(projectId?"Train project":"Open trainer")',
            'p.dataset_prepared_path?"images have captions. Dataset prepared for training."',
            'captioned<total?"images have captions. Finish the descriptions and prepare the dataset before training."',
            '"images have captions. Prepare the dataset before training."',
            't(datasetState)',
        ):
            with self.subTest(token=token):
                self.assertIn(token,html)
        self.assertNotIn('t("images have captions. A trainer-specific export is still required.")',html)

    def test_every_supported_locale_translates_action_and_status(self):
        keys=(
            "Train project",
            "images have captions. Dataset prepared for training.",
            "images have captions. Finish the descriptions and prepare the dataset before training.",
            "images have captions. Prepare the dataset before training.",
            "No images indexed for this project yet.",
        )
        for locale in ("es","pt","fr","de","it","ja","ko"):
            messages=json.loads((ROOT/"GUI"/"locales"/(locale+".json")).read_text(encoding="utf-8"))
            for key in keys:
                with self.subTest(locale=locale,key=key):
                    self.assertTrue(messages.get(key), f"{locale}: {key}")
        spanish=json.loads((ROOT/"GUI"/"locales"/"es.json").read_text(encoding="utf-8"))
        self.assertEqual(spanish["Train project"],"Entrenar proyecto")
        self.assertIn("Dataset preparado para entrenar",spanish[keys[1]])


if __name__=="__main__":
    unittest.main()
