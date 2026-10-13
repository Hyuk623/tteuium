"""Analytical invariants and uncertainty gates for the separate F2/F7 audit."""
import unittest
import numpy as np
from tools.f2_f7_analysis import metrics, fit_threshold, classify, largest
from tools.f2_compound_measurements import ratio_interval


class ShapeAuditTests(unittest.TestCase):
    def test_circle_and_elongation(self):
        a=np.linspace(0,2*np.pi,512,endpoint=False)
        circle=np.c_[np.cos(a),np.sin(a)]
        sh=metrics(circle)
        self.assertAlmostEqual(sh['norm_perimeter'],1.,places=2)
        self.assertGreater(metrics(circle*np.array([4.,1.]))['norm_perimeter'],sh['norm_perimeter'])
        self.assertAlmostEqual(sh['solidity'],1.,places=4)

    def test_rotation_scale_translation_invariance(self):
        a=np.linspace(0,2*np.pi,256,endpoint=False)
        r=1+.2*np.cos(7*a)
        p=np.c_[r*np.cos(a),r*np.sin(a)]
        angle=.63
        rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        x,y=metrics(p),metrics((p@rotation)*47+np.array([321.,97.]))
        for key in ('norm_perimeter','solidity','aspect'):
            self.assertAlmostEqual(x[key],y[key],places=4)

    def test_fit_has_no_external_score_input(self):
        rows=[dict(label='main',norm_perimeter=v) for v in [2.,2.5]]
        rows += [dict(label='interjected',norm_perimeter=v) for v in [1.1,1.2]]
        fit=fit_threshold(rows)
        self.assertEqual(fit['balanced_error'],0)
        self.assertGreater(fit['threshold'],1.2)
        self.assertLess(fit['threshold'],2.)
        with self.assertRaises(ValueError): fit_threshold(rows[:2])

    def test_abstention_and_quality_override(self):
        self.assertEqual(classify(1.3,1.3,.1)[0],'unknown')
        self.assertEqual(classify(1.1,1.3,.1)[0],'interjected')
        self.assertEqual(classify(2.1,1.3,.1,'compound')[0],'unknown')

    def test_ratio_uncertainty_bounds(self):
        lo,hi=ratio_interval(50,100,5)
        self.assertLess(lo,.5)
        self.assertGreater(hi,.5)
        self.assertAlmostEqual(lo,40/110)
        with self.assertRaises(ValueError): ratio_interval(50,10,5)

    def test_empty_and_degenerate_rejected(self):
        with self.assertRaises(ValueError): largest(np.zeros((10,10),dtype=np.uint8))
        with self.assertRaises(ValueError): metrics(np.zeros((4,2)))


if __name__=='__main__': unittest.main()
