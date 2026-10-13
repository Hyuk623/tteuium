"""Uncertainty and image-boundary rules for texture source review."""
import unittest
import numpy as np
from tools.f2_f7_evidence import stable_label,bounded_crop


class EvidenceTests(unittest.TestCase):
    def test_unknown_never_promoted(self):
        self.assertEqual(stable_label('unknown',['main']*3)[0],'unknown')

    def test_disagreement_abstains(self):
        self.assertEqual(stable_label('main',['main','unknown','main'])[0],'unknown')
        self.assertEqual(stable_label('interjected',['interjected','main','interjected'])[0],'unknown')
        self.assertEqual(stable_label('main',[])[0],'unknown')

    def test_consistent_candidate_remains_candidate(self):
        label,status=stable_label('interjected',['interjected']*3)
        self.assertEqual(label,'interjected')
        self.assertIn('candidate',status)

    def test_crop_is_inclusive_and_clipped(self):
        mask=np.zeros((10,20),dtype=bool);mask[0:3,18:20]=True
        self.assertEqual(bounded_crop(mask,5),(13,0,20,8))
        with self.assertRaises(ValueError):bounded_crop(np.zeros((3,3)),2)


if __name__=='__main__':unittest.main()
