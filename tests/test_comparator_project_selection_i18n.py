"""Regression checks for retaining the prepared LoRA on project switch."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ComparatorSelectionAndI18n(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"GUI"/"workspace.html").read_text(encoding="utf-8")
        cls.backend=(ROOT/"scripts"/"generation_studio.py").read_text(encoding="utf-8")

    def test_prepared_workflow_is_kept_across_project_filters(self):
        body=self.html.split('function fillCompareWorkflows(){',1)[1].split('function updateCompareSelection(){',1)[0]
        self.assertIn('const pinned=catalog.find(w=>w.id===old)||workflows.find(w=>w.id===old)',body)
        self.assertIn('if(pinned)list.unshift(pinned)',body)
        self.assertIn('if([...select.options].some(x=>x.value===old))select.value=old',body)
        self.assertIn('function selectedCompareWorkflow(){',self.html)
        self.assertIn('const w=selectedCompareWorkflow();',self.html)
        self.assertIn('w=selectedCompareWorkflow();',self.html)

    def test_lora_node_not_cleared_by_project_scoped_catalog(self):
        body=self.html.split('function refreshCompare(){',1)[1].split('let checkpointList=[];',1)[0]
        self.assertIn('if(compareIsReady())for(const f of compareEditableLoaders())',body)
        self.assertIn('if([...select.options].some(o=>o.value===old))select.value=old',body)
        self.assertIn('else if(select.options.length===2)select.selectedIndex=1',body)
        self.assertIn('if(select.value!==old)$("compare-confirm").checked=false',body)
        self.assertIn('projectCompareWorkflows=d.workflows;projectCompatibilityId=requested;',self.html)

    def test_server_validates_actual_prepared_prompt_after_bridge(self):
        self.assertIn('compatibility = assess_workflow(item[4], row[0], discovered["engine"], row[1])',self.backend)
        self.assertIn('if compatibility["status"] != "candidate"',self.backend)
        self.assertNotIn('compatibility = assess_workflow(json.loads(saved), row[0], discovered["engine"], row[1])',self.backend)

    def test_comparator_menu_translated_everywhere(self):
        expected={
            "es":"Comparador LoRA","pt":"Comparador LoRA","fr":"Comparateur LoRA",
            "de":"LoRA-Vergleich","it":"Comparatore LoRA",
            "ja":"LoRA 比較","ko":"LoRA 비교기"
        }
        self.assertIn('href="#compare"',self.html)
        self.assertIn('>LoRA Comparator</a>',self.html)
        for lang,label in expected.items():
            obj=json.loads((ROOT/"GUI"/"locales"/(lang+".json")).read_text(encoding="utf-8"))
            with self.subTest(lang=lang):
                self.assertEqual(obj["LoRA Comparator"],label)
                for key in ("Select LoRA node","Confirm comparison","Run comparison","Project"):
                    self.assertTrue(obj.get(key))

if __name__=="__main__":
    unittest.main()
