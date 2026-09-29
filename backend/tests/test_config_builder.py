import pytest

from domain.locations.config_builder import LocationConfigBuilder
from domain.locations.errors import ConfigurationError


def test_build_success():
    config = (
        LocationConfigBuilder()
        .with_location_name("Lab Site A")
        .add_zone("Bench 1", 0.2, 0.45, {"watering": "08:00"})
        .add_zone("Bench 2", 0.3, 0.6)
        .build()
    )

    assert config.location.name == "Lab Site A"
    assert len(config.location.zones) == 2
    # Das Ergebnis ist ein tuple, damit niemand nachtraeglich Zonen anhaengt.
    assert isinstance(config.location.zones, tuple)
    # Ohne Zeitplan bleibt das Feld ein leeres Objekt, nicht None.
    assert config.location.zones[1].schedule == {}
    # Vor dem Speichern hat noch nichts eine id.
    assert config.location.id is None


def test_build_requires_name():
    builder = LocationConfigBuilder().add_zone("Bench 1", 0.2, 0.45)
    with pytest.raises(ConfigurationError):
        builder.build()


def test_build_rejects_blank_name():
    builder = LocationConfigBuilder().with_location_name("   ").add_zone("Bench 1", 0.2, 0.45)
    with pytest.raises(ConfigurationError):
        builder.build()


def test_build_requires_zones():
    builder = LocationConfigBuilder().with_location_name("Lab Site A")
    with pytest.raises(ConfigurationError):
        builder.build()


def test_build_rejects_invalid_thresholds():
    builder = LocationConfigBuilder().with_location_name("Lab Site A")
    builder.add_zone("Bench 1", 0.6, 0.3)
    with pytest.raises(ConfigurationError):
        builder.build()


def test_build_rejects_equal_thresholds():
    builder = LocationConfigBuilder().with_location_name("Lab Site A")
    builder.add_zone("Bench 1", 0.4, 0.4)
    with pytest.raises(ConfigurationError):
        builder.build()


def test_build_rejects_thresholds_outside_range():
    builder = LocationConfigBuilder().with_location_name("Lab Site A")
    builder.add_zone("Bench 1", 0.2, 1.5)
    with pytest.raises(ConfigurationError):
        builder.build()


def test_build_is_deterministic():
    def make():
        return (
            LocationConfigBuilder()
            .with_location_name("Lab Site A")
            .add_zone("Bench 1", 0.2, 0.45)
            .build()
        )

    assert make() == make()
