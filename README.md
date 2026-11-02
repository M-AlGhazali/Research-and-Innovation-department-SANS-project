# OEJN_Aircraft_Fuel_Weather
# Weather Integration and Aircraft Fuel Flow Estimation

## 1. Overview

This component focuses on integrating weather data with aircraft observations and estimating fuel consumption during departure and initial climb at King Abdulaziz International Airport (OEJN).

## 2. Data Sources

- **Aircraft Observations:** `observations.parquet`, containing aircraft identifiers (`icao24`), timestamps, positions, altitude, ground speed, track, and vertical speed.
- **Flight Records:** `flights.parquet`, used alongside the aircraft observations.
- **External Aircraft Reference Data:** Used with `icao24` to identify aircraft types and retrieve aircraft specifications, including MTOW.
- **ERA5 Surface Data:** 2-meter temperature, 10-meter wind components (U/V), and surface pressure.
- **ERA5 Pressure-Level Data:** Atmospheric temperature, wind components (U/V), and geopotential at different pressure levels.
- **OpenAP:** Used for aircraft fuel-flow estimation.

## 3. Methodology

### 3.1 Aircraft Identification

The `icao24` identifier from the observations was matched with external aircraft reference data to identify aircraft types and retrieve their specifications, particularly Maximum Take-Off Weight (MTOW).

### 3.2 Weather Processing and Integration

ERA5 surface and pressure-level data were processed and matched with aircraft observations using timestamps and geographic coordinates.

The main weather calculations were:

**Wind speed:**

\[
WS=\sqrt{u^2+v^2}
\]

**Temperature conversion:**

\[
T(^{\circ}C)=T(K)-273.15
\]

**Surface pressure conversion:**

\[
P(hPa)=\frac{P(Pa)}{100}
\]

**Geopotential height:**

\[
H(m)=\frac{\Phi}{9.80665}
\]

### 3.3 Aircraft Mass Estimation

Actual aircraft operating mass was unavailable. Therefore, estimated mass was calculated as:

\[
Mass_{estimated}=MTOW\times0.80
\]

### 3.4 True Airspeed (TAS) Calculation

TAS was calculated using ground speed, aircraft track, and the wind component along the aircraft's direction of travel.

Pressure-level U/V wind components were used when available. If missing, 10-meter surface U/V components were used as a fallback.

First, the track angle was converted to radians:

\[
\theta=track\_deg\times\frac{\pi}{180}
\]

Then, the along-track wind component was calculated:

\[
W_{along}=u\sin(\theta)+v\cos(\theta)
\]

Finally:

\[
TAS_{kt}=GS_{kt}-(W_{along}\times1.94384)
\]

Where:
- \(GS\): Ground speed in knots.
- \(u,v\): Wind components in m/s.
- \(W_{along}\): Wind component along the aircraft track.
- 1.94384: Conversion factor from m/s to knots.

### 3.5 Fuel Flow Estimation

OpenAP's `FuelFlow.enroute()` model was used to estimate fuel flow for each aircraft observation.

The model inputs were:
- Aircraft type.
- Estimated aircraft mass (kg).
- TAS (knots).
- Barometric altitude (feet).
- Barometric vertical speed (feet per minute).

The output was fuel flow in kg/s.

The analysis considered departure observations at or below 10,000 feet.

### 3.6 Total Fuel Consumption

Total fuel consumption was estimated by integrating fuel flow over time using the trapezoidal rule:

\[
Fuel_{total}\approx
\sum_{i=1}^{n-1}
\frac{FF_i+FF_{i+1}}{2}
(t_{i+1}-t_i)
\]

Where:
- \(FF_i\): Fuel flow at observation \(i\), in kg/s.
- \(t_i\): Observation time in seconds.
- Total fuel is calculated in kilograms.

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
- **Aircraft identification:** The `icao24` identifier was used to match aircraft observations with external aircraft reference data.
- **Wind fallback:** Surface U/V wind components were used when pressure-level U/V components were missing.
- **Weather representation:** Matched ERA5 weather values were assumed to represent conditions at the aircraft observation's time and location.
- **Fuel estimation:** OpenAP fuel-flow outputs were treated as estimates, not actual measured fuel consumption.

## 6. Limitations

- **Limited weather period:** ERA5 data cover October 1, 2026, with 24 hourly time points; therefore, results do not represent different days or seasons.
- **Spatial coverage:** Some aircraft observations were outside ERA5 geographic coverage, preventing weather matching.
- **Missing weather data:** Pressure-level matching coverage was lower than surface matching coverage, requiring surface wind components as a fallback in TAS calculations.
- **Estimated aircraft mass:** The 80% MTOW assumption may differ from actual aircraft operating mass.
- **Model-based fuel estimates:** OpenAP estimates fuel flow rather than using actual aircraft fuel measurements.
- **Limited flight phase:** The analysis covers departure and initial climb observations at or below 10,000 feet, not the entire flight.
- **Excluded candidates:** 21 candidates could not be processed because of insufficient valid observations.

## 7. Output

The resulting dataset combines aircraft observations with matched weather variables and includes calculated TAS, estimated aircraft mass, and fuel-flow estimates. Total fuel consumption was calculated for successfully processed flights.
