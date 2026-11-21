"""Regression: Comparator Bridge preparation must be actionable and visible.

Previously the Compare section disabled the preparation action for unverified
FLUX.3 UI workflows, while preparation progress lived only in the hidden
Generation Studio section.
"""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ComparatorBridgePreparationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui=(ROOT/"GUI"/"workspace.html").read_text(encoding="utf-8")

    def test_bridge_progress_visible_in_comparator(self):
        for marker in (
            'id="compare-bridge-progress"',
            'id="compare-bridge-step"',
            'id="compare-bridge-count"',
            'id="compare-bridge-fill"',
            'id="compare-bridge-detail"',
            'id="compare-bridge-cancel"',
            'if(bridgeViaComparator){',
            '$("compare-bridge-progress").hidden=false',
            '$("compare-bridge-detail").textContent=$("bridge-progress-detail").textContent',
            '$("compare-bridge-cancel").onclick=()=>$("bridge-cancel").click()',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker,self.ui)

    def test_unverified_workflow_can_be_prepared_but_not_executed(self):
        self.assertIn('if(scoped&&w.compatibility?.status==="incompatible"){',self.ui)
        self.assertNotIn('if(checkMode()&&$("compare-checkpoint-project").value&&w?.compatibility?.status!=="candidate")return;',self.ui)
        self.assertIn('bridgeViaComparator=w.format==="ui"',self.ui)
        self.assertIn('if(bridgeViaComparator)await $("generation-bridge").onclick()',self.ui)
        self.assertIn('if(!generationToken)throw Error($("generation-status").textContent||t("Workflow preparation failed"))',self.ui)
        self.assertIn('if(scoped&&w.compatibility?.status==="incompatible"){',self.ui)
        self.assertIn('La compatibilidad del modelo se comprobará sobre el workflow convertido',self.ui)
        self.assertIn('if compatibility["status"] != "candidate"',(ROOT/"scripts"/"generation_studio.py").read_text(encoding="utf-8"))

    def test_browser_button_is_not_silently_disabled(self):
        self.assertIn(
            '$("compare-prepare").disabled=compareRunning||generationBusy||generationPreparing||!w;',
            self.ui)
        self.assertIn('if($("generation-workflow").value!==id){',self.ui)
        self.assertIn('finally{bridgeViaComparator=false;updateCompareSelection();}',self.ui)

if __name__=="__main__":
    unittest.main()
