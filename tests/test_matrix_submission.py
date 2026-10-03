import hashlib
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
import poster
import run_category_matrix as matrix


class MatrixSubmissionTests(unittest.TestCase):
    def test_completed_case_cannot_be_relabelled_as_a_new_product(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            poster.write(root/'assets/products/categories/products.json',[])
            product={'product_category':'womenswear','garment_type':'dress','display_mode':'auto','sha256':'new-product'}
            poster.write(root/'assets/products/manifest.json',[product])
            poster.write(root/'samples/categories/check/womenswear/state.json',{'input_sha256':'old-product','status':'COMPLETED'})
            argv=['run_category_matrix.py','--tag','check','--manifest','assets/products/manifest.json']
            with patch.object(matrix,'ROOT',root),patch.object(sys,'argv',argv),patch.object(matrix,'request') as request:
                with self.assertRaisesRegex(ValueError,'different product'):matrix.main()
                request.assert_not_called()

    def test_monitor_restart_recovers_same_receipt_and_uploaded_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);image=root/'assets/products/input.png';image.parent.mkdir(parents=True);image.write_bytes(b'verified input')
            target=root/'samples/test/womenswear';target.mkdir(parents=True)
            product={'product_category':'womenswear','garment_type':'dress','display_mode':'hanging','brief':'test','local_path':'assets/products/input.png','sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
            with patch.object(matrix,'ROOT',root),patch.object(poster,'upload',return_value='unique-upload.png') as upload,patch.object(matrix,'request',return_value={'prompt_id':'same-receipt'}) as submit:
                first=matrix.submit_once('http://localhost:8191',product,target)
                second=matrix.submit_once('http://localhost:8191',product,target)
            self.assertEqual(first,second);self.assertEqual(upload.call_count,1);self.assertEqual(submit.call_count,1)
            graph=poster.read(target/'submission.json')['prompt']
            self.assertEqual(graph['1']['inputs']['image'],'unique-upload.png')
            self.assertEqual(graph['2']['class_type'],'ClothingDirectorLoop')
            self.assertEqual(graph['2']['inputs']['garment_type'],'dress')
            with patch.object(matrix,'ROOT',root),patch.object(matrix,'request') as submit:
                changed={**product,'sha256':'changed'}
                with self.assertRaises(ValueError):matrix.submit_once('http://localhost:8191',changed,target)
                submit.assert_not_called()


if __name__=='__main__':unittest.main()
