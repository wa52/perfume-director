import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import resume_category_batch as recovery


class CategoryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.run=self.root/'runs/live/abc';self.run.mkdir(parents=True)
        self.image=self.run/'poster.png';self.image.write_bytes(b'intact selected evidence')
        self.plan={'id':'concept-1','signature':'same-plan','initial_spec':{'title':'approved'},'reference_ids':['r1']}
        self.item={**self.plan,'run_dir':str(self.run),'selected':{'poster':'poster.png',
            'sha256':hashlib.sha256(self.image.read_bytes()).hexdigest()}}

    def verify(self,item):
        with patch.object(recovery,'ROOT',self.root):
            return recovery.verified_selections({'directions':[item]},[self.plan])

    def test_identical_plan_and_intact_image_can_be_reused(self):
        result=self.verify(self.item)
        self.assertEqual(result['directions'],[self.item])
        self.assertIsNot(result['directions'][0],self.item)

    def test_changed_plan_or_selected_bytes_are_rejected(self):
        item=copy.deepcopy(self.item);item['signature']='different-plan'
        with self.assertRaises(ValueError):self.verify(item)
        self.image.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.verify(self.item)

    def test_selected_path_outside_run_is_rejected(self):
        item=copy.deepcopy(self.item);item['selected']['poster']='../../outside.png'
        with self.assertRaises(ValueError):self.verify(item)
