import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import poster


class SavedStateTests(unittest.TestCase):
    def test_disk_write_failure_keeps_previous_state_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'summary.json';old={'status':'RUNNING'};poster.write(target,old)
            original=Path.write_text
            def fail_after_partial_write(path,text,*args,**kwargs):
                original(path,text[:10],*args,**kwargs)
                raise OSError('simulated disk failure')
            with patch.object(Path,'write_text',fail_after_partial_write):
                with self.assertRaises(OSError):poster.write(target,{'status':'COMPLETED'})
            self.assertEqual(poster.read(target),old)
            self.assertEqual(list(Path(folder).glob('*.tmp')),[])

    def test_readers_never_see_a_half_written_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'summary.json';old={'status':'RUNNING','version':1}
            poster.write(target,old)
            halfway=threading.Event();release=threading.Event();errors=[]
            original=Path.write_text
            def slow_write(path,text,*args,**kwargs):
                original(path,text[:len(text)//2],*args,**kwargs)
                halfway.set();release.wait(2)
                return original(path,text,*args,**kwargs)
            def update():
                try:poster.write(target,{'status':'COMPLETED','version':2,'payload':'x'*4000})
                except Exception as error:errors.append(error)
            with patch.object(Path,'write_text',slow_write):
                worker=threading.Thread(target=update);worker.start()
                try:
                    self.assertTrue(halfway.wait(2))
                    try:observed=poster.read(target)
                    except json.JSONDecodeError:observed='HALF_WRITTEN_JSON'
                finally:release.set();worker.join(3)
            self.assertFalse(errors)
            self.assertEqual(observed,old)
            self.assertEqual(poster.read(target)['status'],'COMPLETED')


if __name__=='__main__':unittest.main()
