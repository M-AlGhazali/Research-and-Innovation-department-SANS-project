"""Nullable versioned research contracts. No A3-A6 calculations are supplied."""
from dataclasses import dataclass

@dataclass(frozen=True)
class AircraftMetadata:
    icao24: str
    aircraft_type: str | None = None
    source: str | None = None
    retrieved_utc: str | None = None
    status: str = "unresolved"
    schema_version: int = 1

@dataclass(frozen=True)
class ModelLink:
    flight_id: str
    domain: str  # performance, weather, acoustics, population
    model_id: str | None = None
    model_version: str | None = None
    assumptions: tuple[str, ...] = ()
    substitution_source: str | None = None
    validation_reference: str | None = None
    uncertainty_note: str | None = None
    result_artifact: str | None = None
    status: str = "not_calculated"
    schema_version: int = 1

@dataclass(frozen=True)
class PerformanceLink:
    flight_id: str
    aircraft_type: str | None = None
    openap_aircraft_id: str | None = None
    engine_id: str | None = None
    mass_kg: float | None = None
    operating_assumptions: tuple[str, ...] = ()
    model_version: str | None = None
    validation_reference: str | None = None
    uncertainty_note: str | None = None
    result_artifact: str | None = None
    status: str = "not_calculated"
    schema_version: int = 1

@dataclass(frozen=True)
class WeatherSampleLink:
    flight_id: str
    observation_id: str
    source_dataset: str | None = None
    source_version: str | None = None
    timestamp_utc: str | None = None
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    vertical_coordinate_kind: str | None = None  # pressure / geopotential / geometric
    vertical_value: float | None = None
    vertical_unit: str | None = None
    interpolation_method: str | None = None
    preliminary: bool | None = None
    pressure_pa: float | None = None
    temperature_k: float | None = None
    wind_east_mps: float | None = None
    wind_north_mps: float | None = None
    status: str = "not_sampled"
    schema_version: int = 1

@dataclass(frozen=True)
class AcousticLink:
    flight_id: str
    anp_aircraft_id: str | None = None
    npd_id: str | None = None
    anp_version: str | None = None
    substituted: bool | None = None
    substitution_source: str | None = None
    doc29_implementation_version: str | None = None
    power_assumptions: tuple[str, ...] = ()
    reference_case_validation: str | None = None
    footprint_artifact: str | None = None
    uncertainty_note: str | None = None
    status: str = "not_calculated"
    schema_version: int = 1

@dataclass(frozen=True)
class PopulationExposureLink:
    flight_id: str
    population_raster_id: str | None = None
    population_vintage: str | None = None
    population_value_kind: str = "people_per_cell"
    population_crs: str | None = None
    noise_footprint_artifact: str | None = None
    noise_metric: str | None = None
    threshold_db: float | None = None
    spatial_method: str | None = None
    result_artifact: str | None = None
    uncertainty_note: str | None = None
    status: str = "not_calculated"
    schema_version: int = 1
