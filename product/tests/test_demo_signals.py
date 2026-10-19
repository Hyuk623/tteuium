from datetime import datetime, timedelta
from product.device_contract.seed_demo import sensor_values, KST


def test_mock_environment_is_deterministic_and_follows_local_day():
    night=datetime(2026,10,18,2,tzinfo=KST)
    noon=night.replace(hour=12)
    assert sensor_values(noon)==sensor_values(noon)
    assert sensor_values(night)['light_lux'] < 10
    assert sensor_values(noon)['light_lux'] > 4200
    for hour in range(14*24):
        v=sensor_values(night+timedelta(hours=hour))
        assert 19 < v['temperature_c'] < 27
        assert 49 < v['humidity_pct'] < 69
        assert 0 <= v['light_lux'] < 10000
        assert 35 < v['water_level_pct'] < 89


def test_mock_reservoir_declines_and_refills():
    refill=datetime(2026,1,1,9,tzinfo=KST)
    before=sensor_values(refill-timedelta(minutes=1))['water_level_pct']
    after=sensor_values(refill)['water_level_pct']
    next_day=sensor_values(refill+timedelta(days=1))['water_level_pct']
    assert after-before > 50
    assert after-next_day > 12
