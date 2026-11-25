# Weather Integration and Aircraft Fuel Flow Estimation

## 1. Overview

This component focuses on integrating weather data with aircraft observations and estimating aircraft fuel consumption during departure and initial climb at King Abdulaziz International Airport (OEJN).

## 2. Data Sources

- **Aircraft Observations:** `observations.parquet`, containing aircraft identifiers (`icao24`), timestamps, geographic coordinates, altitude, ground speed, track, and vertical speed.
- **Flight Records:** `flights.parquet`, used to identify and select departure flights for the fuel-flow analysis.
- **External Aircraft Reference Data:** Used with the `icao24` identifiers to identify aircraft types and retrieve aircraft specifications, including Maximum Take-Off Weight (MTOW).
- **ERA5 Surface Weather:** Provides 2-meter temperature, 10-meter U/V wind components, and surface pressure.
- **ERA5 Pressure-Level Weather:** Provides atmospheric temperature, U/V wind components, and geopotential at different pressure levels.
- **OpenAP:** Used to estimate aircraft fuel flow.

## 3. Methodology

### 3.1 Aircraft Identification

The `icao24` identifier from the aircraft observations was matched with external aircraft reference data to identify aircraft types and retrieve their specifications, particularly MTOW.

**Maximum Take-Off Weight (MTOW)** is the maximum permitted total weight of an aircraft at take-off, specified by the aircraft manufacturer. It was used to estimate aircraft mass.

### 3.2 Weather Processing and Integration

ERA5 surface and pressure-level data were processed and matched with aircraft observations using timestamps and geographic coordinates.

The main weather calculations were:

**Wind Speed**

$$
WS = \sqrt{u^2 + v^2}
$$

**Temperature Conversion**

$$
T(^{\circ}C) = T(K) - 273.15
$$

**Surface Pressure Conversion**

$$
P(hPa) = \frac{P(Pa)}{100}
$$

**Geopotential Height**

$$
H(m) = \frac{\Phi}{9.80665}
$$

Where:
- **WS:** Wind speed (m/s).
- **u:** Eastward wind component (m/s).
- **v:** Northward wind component (m/s).
- **T:** Temperature, expressed in Kelvin or Celsius.
- **P:** Surface pressure, expressed in pascals or hectopascals.
- **H:** Geopotential height (m).
- **Φ:** Geopotential (m²/s²).
- **9.80665:** Standard gravitational acceleration (m/s²).

### 3.3 Aircraft Mass Estimation

Since the actual operating mass of each aircraft was unavailable, 80% of MTOW was assumed to estimate the aircraft mass. This percentage was selected as an approximation of the aircraft's operating weight rather than assuming that every aircraft operates at its maximum take-off weight. It is an estimation assumption and does not represent the actual weight of the aircraft.

$$
Mass_{estimated} = MTOW \times 0.80
$$

Where:
- **Mass estimated:** Estimated aircraft mass (kg).
- **MTOW:** Maximum Take-Off Weight (kg).
- **0.80:** Assumed percentage of MTOW (80%).

### 3.4 True Airspeed (TAS) Calculation

TAS was calculated using ground speed, aircraft track, and the wind component along the aircraft's direction of travel.

Pressure-level U/V wind components were used when available. If missing, 10-meter surface U/V wind components were used as a fallback.

First, the aircraft track angle was converted from degrees to radians:

$$
\theta = track\_deg \times \frac{\pi}{180}
$$

The along-track wind component was then calculated:

$$
W_{along} = u\sin(\theta) + v\cos(\theta)
$$

Finally, TAS was calculated:

$$
TAS_{kt} = GS_{kt} - (W_{along} \times 1.94384)
$$

Where:
- **TAS:** True Airspeed (knots).
- **GS:** Ground Speed (knots).
- **W along:** Wind component along the aircraft track (m/s).
- **u:** Eastward wind component (m/s).
- **v:** Northward wind component (m/s).
- **θ:** Aircraft track angle (radians).
- **1.94384:** Conversion factor from m/s to knots.

### 3.5 Fuel Flow Estimation

The OpenAP `FuelFlow.enroute()` model was used to estimate fuel flow for each aircraft observation.

The model inputs were:
- Aircraft type.
- Estimated aircraft mass (kg).
- True Airspeed (knots).
- Barometric altitude (feet).
- Barometric vertical speed (feet per minute).

The output was estimated fuel flow in kg/s.

The analysis considered departure observations at or below 10,000 feet.

### 3.6 Total Fuel Consumption

Total fuel consumption was estimated by integrating fuel flow over time using the trapezoidal rule:

$$
Fuel_{total} \approx
\sum_{i=1}^{n-1}
\frac{FF_i + FF_{i+1}}{2}
(t_{i+1} - t_i)
$$

Where:
- **Fuel total:** Estimated total fuel consumption (kg).
- **FF:** Fuel flow at each observation (kg/s).
- **t:** Observation time (seconds).
- **i:** Observation index.
- **n:** Total number of observations.

## 4. Key Results

- 622,080 aircraft observations were processed.
- 96.3% of observations were within ERA5 geographic coverage.
- Surface weather matching coverage: 92.46%.
- Pressure-level weather matching coverage: 85.28%.
- 226 departure candidates had supported aircraft specifications.
- 205 flights were successfully processed for fuel estimation.
- 21 candidates were excluded due to insufficient valid observations.

## 5. Assumptions

- **Aircraft mass:** Estimated as 80% of MTOW because actual operating mass was unavailable.
- **Wind fallback:** Surface U/V wind components were used when pressure-level U/V components were missing.
- **Weather matching:** Matched ERA5 weather values were assumed to represent conditions at the aircraft observation's time and location.
- **Fuel estimation:** OpenAP outputs were treated as estimates rather than actual measured fuel consumption.

## 6. Limitations

- **Geographic coverage:** Some aircraft observations were outside ERA5 spatial coverage, preventing weather matching.
- **Missing pressure-level data:** Pressure-level matching coverage was lower than surface matching coverage, requiring surface wind components as a fallback for TAS calculations.
- **Estimated aircraft mass:** The 80% MTOW assumption may differ from actual aircraft operating mass.
- **Model-based fuel estimates:** OpenAP estimates fuel flow rather than using actual aircraft fuel measurements.
- **Limited flight phase:** The analysis covers departure and initial climb observations at or below 10,000 feet, not the entire flight.
- **Excluded candidates:** 21 candidates could not be processed because of insufficient valid observations.

## 7. Output

The resulting dataset combines aircraft observations with matched weather variables and includes calculated TAS, estimated aircraft mass, and fuel-flow estimates. Total fuel consumption was calculated for successfully processed flights.
