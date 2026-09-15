import pytest

from domain.sensors.creators import get_creator


def test_moisture_creator_defaults():
    sensor = get_creator("moisture").create_sensor()
    assert sensor.device_type == "moisture_sensor"
    assert "moisture_threshold" in sensor.default_config


def test_light_creator_defaults():
    sensor = get_creator("light").create_sensor()
    assert sensor.device_type == "light_sensor"
    # Lichtsensor nutzt eine andere Einheit als der Feuchtigkeitssensor.
    assert sensor.default_config["unit"] == "lux"


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        get_creator("temperature")
