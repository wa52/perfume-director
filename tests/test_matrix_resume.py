import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import poster
import test_product_matrix as matrix


class MatrixResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.batch = self.root / 'abc123'
        self.plans = [dict(id=f'concept-{i}', name=f'Direction {i}', brief='brief',
                           initial_spec={}, reference_ids=[]) for i in range(1, 5)]
        poster.write(self.batch/'request.json', {'directions': self.plans})
        poster.write(self.batch/'Planning-references.json', [])
        poster.write(self.batch/'Product-copy.json', {n: '' for n in poster.TEXT_LAYERS})
        self.prior = []
        for plan in self.plans:
            run = self.root/plan['id']
            run.mkdir()
            (run/'poster.png').write_bytes(b'existing output')
            self.prior.append({**plan, 'run_dir': str(run), 'status': 'NEEDS_REVIEW',
                               'selected': {'version': 1, 'poster': 'poster.png'}})

    def test_completed_directions_reuse_outputs_without_model_or_render_calls(self):
        with patch.object(poster, 'run') as execute:
            matrix.resume_four({}, 'product', 'brief', self.batch,
                               {'directions': self.prior}, lambda _: None)
        execute.assert_not_called()
        result = poster.read(self.batch/'result.json')
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['directions'], self.prior)

    def test_only_incomplete_direction_restarts_and_preserves_its_old_location(self):
        interrupted = self.root/'interrupted'
        interrupted.mkdir()
        (interrupted/'partial.txt').write_text('keep this evidence')
        fresh = self.root/'fresh'
        poster.write(fresh/'result.json', {'status':'NEEDS_REVIEW',
                     'selected': {'version': 2, 'poster':'poster.png'}})
        previous = {'directions': self.prior[:3], 'direction_index':4,
                    'run_dir':str(interrupted)}
        with patch.object(poster, 'run', return_value=fresh) as execute:
            matrix.resume_four({}, 'product', 'brief', self.batch, previous, lambda _:None)
        execute.assert_called_once()
        result = poster.read(self.batch/'result.json')
        self.assertEqual(result['directions'][:3], self.prior[:3])
        self.assertEqual(result['directions'][3]['interrupted_run_dir'], str(interrupted))
        self.assertEqual((interrupted/'partial.txt').read_text(), 'keep this evidence')

    def test_child_finished_before_runner_interruption_is_recovered(self):
        child = self.prior[3]
        poster.write(Path(child['run_dir'])/'result.json',
                     {k:child[k] for k in ('status','selected')})
        previous = {'directions':self.prior[:3], 'direction_index':4,
                    'run_dir':child['run_dir']}
        with patch.object(poster, 'run') as execute:
            matrix.resume_four({}, 'product', 'brief', self.batch, previous, lambda _:None)
        execute.assert_not_called()
        self.assertEqual(len(poster.read(self.batch/'result.json')['directions']),4)

    def test_missing_selected_image_is_not_counted_as_reusable(self):
        (Path(self.prior[0]['run_dir'])/'poster.png').unlink()
        with patch.object(poster, 'run', side_effect=RuntimeError('renderer unavailable')) as execute:
            matrix.resume_four({}, 'product', 'brief', self.batch,
                               {'directions':self.prior}, lambda _:None)
        execute.assert_called_once()
        self.assertEqual(poster.read(self.batch/'result.json')['status'],'PARTIAL')


if __name__ == '__main__':
    unittest.main()
