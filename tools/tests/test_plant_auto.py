"""Photo-only auto mode: view codes from the EXIF shooting order (user rule, 2026-09-28)."""
import pytest
from PIL import Image

from tools import plant_auto as pa
from tools.leaf_light.common import StudyError


def _photo(path, when):
    im = Image.new('RGB', (32, 24), '#336633')
    ex = Image.Exif()
    ex[306] = when
    im.save(path, exif=ex)


def _folder(tmp_path, n=18, dup=False):
    d = tmp_path / 'raw'
    d.mkdir()
    names = [f'IMG_{9000 - 7 * i}.jpg' for i in range(n)]  # names run backwards against the shooting order
    for i, name in enumerate(names):
        _photo(d / name, f'2026:10:01 10:{(0 if dup and i < 2 else i):02d}:00')
    return d, names


def test_view_codes_follow_capture_time_not_file_names(tmp_path):
    d, names = _folder(tmp_path)
    rows = pa.order_photos(d)
    assert [r['view_code'] for r in rows] == pa.PROTOCOL
    assert [r['path'].name for r in rows] == names, 'first shot -> 01 even though its name sorts last'


def test_wrong_photo_count_and_tied_times_are_refused(tmp_path):
    d, _ = _folder(tmp_path, n=17)
    with pytest.raises(StudyError, match='17 photographs'):
        pa.order_photos(d)
    (tmp_path / 'b').mkdir()
    d2, _ = _folder(tmp_path / 'b', dup=True)
    with pytest.raises(StudyError, match='share a capture time'):
        pa.order_photos(d2)


def test_organised_names_and_mapping_match_the_importer(tmp_path):
    d, _ = _folder(tmp_path)
    source, mapping = pa.organise(pa.order_photos(d), 'dwt_77', '2026-10-01', tmp_path / 'out')
    text = mapping.read_text(encoding='utf-8').splitlines()
    assert text[0].startswith('plant_id,capture_date,input_index,view_code')
    assert 'dwt_77' + chr(92) + '261001' + chr(92) + 'dwt_77_261001_01.jpg' in text[1]
    assert (source / 'dwt_77' / '261001' / 'dwt_77_261001_28.jpg').exists()
