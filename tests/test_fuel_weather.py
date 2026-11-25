"""Pure-math checks for the A3/A4 fuel stage; no OpenAP/xarray/ERA5 needed."""
import numpy as np
import pytest
from sans_a2.fuel_weather import isa_pressure_hpa, true_airspeed_kt, integrate_fuel_kg


def test_isa_pressure_reference_points():
    assert isa_pressure_hpa(0) == pytest.approx(1013.25)
    assert isa_pressure_hpa(10000) == pytest.approx(696.8, abs=0.5)  # ISA table
    assert isa_pressure_hpa(18000) == pytest.approx(506.0, abs=0.5)


def test_tas_headwind_tailwind_crosswind():
    # Track north (0 deg): v is along-track
    assert true_airspeed_kt(200, 0, 0, -10)[()] == pytest.approx(200 + 10 * 1.94384)  # headwind -> TAS > GS
    assert true_airspeed_kt(200, 0, 0, 10)[()] == pytest.approx(200 - 10 * 1.94384)   # tailwind -> TAS < GS
    assert true_airspeed_kt(200, 0, 10, 0)[()] == pytest.approx(200)                   # pure crosswind ignored
    # Track east (90 deg): u is along-track
    assert true_airspeed_kt(200, 90, 5, 0)[()] == pytest.approx(200 - 5 * 1.94384)


def test_trapezoid_fuel_integral():
    t = np.array([0, 1000, 3000])  # ms
    ff = np.array([1.0, 1.0, 2.0])  # kg/s
    assert integrate_fuel_kg(t, ff) == pytest.approx(1.0 * 1 + 1.5 * 2)


def test_departure_segment_stops_at_first_10000_ft_crossing():
    import pandas as pd
    from sans_a2.fuel_weather import departure_segment
    obs = pd.DataFrame({"timestamp_ms": [0, 1, 2, 3, 4], "barometric_altitude_ft": [500, 6000, 10000, 10400, 9800]})
    assert departure_segment(obs, 10000)["timestamp_ms"].tolist() == [0, 1, 2]  # the later dip to 9,800 ft is not departure
    assert departure_segment(obs.iloc[:3], 10000)["timestamp_ms"].tolist() == [0, 1, 2]  # never above: all kept
