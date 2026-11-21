"""Comparator run readiness and post-Bridge LoRA selection regression checks."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ComparatorStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"GUI"/"workspace.html").read_text(encoding="utf-8")

    def test_ready_requires_prepared_token_and_matching_workflow(self):
        for marker in (
            "function compareIsReady(){",
            "!!generationToken&&!generationDirty&&!generationBusy&&!generationPreparing",
            '$("generation-workflow").value===$("compare-workflow").value',
            "function compareEditableLoaders(){",
            'f.name==="strength_model"',
            'other.name==="lora_name"&&other.kind==="choice"',
            "function updateCompareRunState(){",
            '!$("compare-confirm").checked',
        ):
            with self.subTest(marker=marker):self.assertIn(marker,self.html)

    def test_selection_is_not_lost_on_change(self):
        for marker in (
            'if(select.value!==old)$("compare-confirm").checked=false',
            '$("compare-node").onchange=()=>{$("compare-confirm").checked=false;updateCompareRunState();}',
            '$("compare-confirm").onchange=updateCompareRunState;',
            'function updateCheckpointCount(){updateCompareRunState();}',
            'if(compareIsReady())for(const f of compareEditableLoaders()){',
        ):
            with self.subTest(marker=marker):self.assertIn(marker,self.html)

    def test_diagnoses_missing_lora_or_uneditable_inputs(self):
        for marker in (
            'const graph=JSON.parse($("generation-graph").textContent||"{}")',
            "const loaders=Object.values(graph).filter",
            'lora_name y strength_model editables',
            'No compatible standard LoRA loader found.',
        ):
            with self.subTest(marker=marker):self.assertIn(marker,self.html)

if __name__=="__main__":
    unittest.main()
