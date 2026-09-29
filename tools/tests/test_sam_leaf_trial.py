"""Coordinate integrity and preservation of holes for the SAM trial adapter."""
import numpy as np
import pytest
from tools.sam_leaf_trial import crop_prompt,restore_mask,contour_rows
from tools.leaf_light.common import StudyError


def test_prompts_and_predicted_pixels_return_to_original_coordinates():
    case={'crop_xyxy_px':[20,10,60,40]}
    trial={'points':[{'x_px':35,'y_px':25,'label':1}], 'box_xyxy_px':[22,12,58,38]}
    crop,points,labels,box=crop_prompt(case,trial,(100,80))
    assert points.tolist()==[[15,15]] and labels.tolist()==[1]
    assert box.tolist()==[2,2,38,28]
    mask=np.zeros((30,40),bool);mask[15,15]=True
    full=restore_mask(mask,crop,(100,80))
    assert full.shape==(80,100) and full[25,35]==255 and np.count_nonzero(full)==1


def test_invalid_prompts_or_mask_size_cannot_shift_labels_silently():
    with pytest.raises(StudyError,match='Point outside'):
        crop_prompt({'crop_xyxy_px':[10,10,30,30]},{'points':[{'x_px':2,'y_px':20,'label':1}]},(50,50))
    with pytest.raises(StudyError,match='dimensions'):
        restore_mask(np.zeros((10,10)),(10,10,30,30),(50,50))


def test_disconnected_visible_regions_and_holes_are_preserved():
    mask=np.zeros((100,100),np.uint8);mask[10:50,10:50]=255;mask[20:30,20:30]=0;mask[70:90,70:90]=255
    before=mask.copy();rows=contour_rows(mask,1.0)
    assert len({r['ring_index'] for r in rows})==3
    assert len({r['ring_index'] for r in rows if r['parent_ring_index']>=0})==1
    np.testing.assert_array_equal(mask,before)
