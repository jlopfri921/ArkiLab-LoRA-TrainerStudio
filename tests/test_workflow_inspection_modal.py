"""Regression: workflow inspection modal must work from ComfyUI Comparator.

The workflow library module is hidden while navigating the LoRA Comparator.
Native showModal() can create a blocking backdrop around a visually hidden
dialog when the dialog is nested inside that module.
"""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class WorkflowInspectionModalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui=(ROOT/"GUI"/"workspace.html").read_text(encoding="utf-8")

    def test_dialog_is_outside_workflow_section_and_comfy_zone(self):
        ui=self.ui
        dialog=ui.index('<dialog id="workflow-details"')
        workspace=ui.index('<div class="comfy-module" data-module="workflows"')
        next_section=ui.index('<div class="comfy-module" data-module="generation"',workspace)
        global_dialog=ui.index('<dialog id="editor"')
        self.assertLess(workspace,next_section)
        self.assertLess(next_section,dialog)
        self.assertLess(dialog,global_dialog)
        self.assertEqual(ui.count('<dialog id="workflow-details"'),1)

    def test_modal_is_accessible_from_comparator_and_closable(self):
        ui=self.ui
        for token in (
            'id="workflow-details-title"',
            'id="workflow-close"',
            'id="compare-inspect"',
            'if(w)inspectWorkflow(w)',
            'dialog.showModal();$("workflow-close").focus()',
            '$("workflow-close").onclick=()=>$("workflow-details").close()',
            '#workflow-details::backdrop',
        ):
            with self.subTest(token=token):
                self.assertIn(token,ui)

if __name__=="__main__":
    unittest.main()
