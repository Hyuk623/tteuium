from datetime import datetime, timedelta
from product.device_contract.seed_demo import sensor_values, KST


def test_mock_environment_is_deterministic_and_follows_local_day():
    night=datetime(2026,10,18,2,tzinfo=KST)
    noon=night.replace(hour=12)
    assert sensor_values(noon)==sensor_values(noon)
    assert set(sensor_values(noon)) == {'temperature_c', 'humidity_pct'}
    assert sensor_values(noon)['temperature_c'] > sensor_values(night)['temperature_c']
    for hour in range(14*24):
        v=sensor_values(night+timedelta(hours=hour))
        assert 19 < v['temperature_c'] < 27
        assert 49 < v['humidity_pct'] < 69
