"""Guard against UI stalls when switching to Project checkpoints.

The mode-change handler used to perform duplicated project-scoped library
queries and rebuild the selected workflow dropdown synchronously, while the
startup project loader could trigger the same work.
"""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ComparatorCheckpointModeRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui=(ROOT/"GUI"/"workspace.html").read_text(encoding="utf-8")

    def block(self,start,end):
        self.assertIn(start,self.ui)
        self.assertIn(end,self.ui)
        return self.ui.split(start,1)[1].split(end,1)[0]

    def test_mode_change_does_not_refetch_project_twice(self):
        body=self.block('function updateCheckpointMode(){','$("compare-mode").onchange')
        self.assertIn('updateCompareRunState()',body)
        self.assertNotIn('fillCompareWorkflows()',body)
        self.assertNotIn('loadCheckpointProjects()',body)
        self.assertNotIn('refreshCompare()',body)

        handler=self.block('$("compare-mode").onchange=async()=>{','$("compare-checkpoint-project").onchange')
        self.assertIn('if($("compare-checkpoint-project").options.length<=1)await loadCheckpointProjects()',handler)
        self.assertIn('else await loadCompareCompatibility()',handler)
        self.assertNotIn('loadCheckpointProjects();loadCompareCompatibility()',handler)

    def test_in_flight_detection_does_not_clear_workflow_selector(self):
        body=self.block('async function loadCompareCompatibility(){','$("compare-show-all").onchange')
        self.assertIn('if(run!==projectCompatibilityRequest',body)
        self.assertIn('projectCompareWorkflows=d.workflows;projectCompatibilityId=requested;',body)
        self.assertIn('fillCompareWorkflows()',body)
        before_fetch=body.split('const d=await api(',1)[0]
        self.assertNotIn('projectCompareWorkflows=[];',before_fetch.split('if(!checkMode()||!requested)',1)[-1])
        self.assertNotIn('fillCompareWorkflows();\n try{',body)

    def test_prepared_state_not_reset_when_switching_comparison_type(self):
        mode=self.block('function updateCheckpointMode(){','$("compare-mode").onchange')
        self.assertNotIn('generationToken=null',mode)
        self.assertNotIn('fillGeneration(',mode)
        self.assertIn('updateCompareRunState()',mode)

if __name__=="__main__":
    unittest.main()
