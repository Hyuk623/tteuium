# User-parameter monthly growth

This is a 30-calendar-day arithmetic scenario from an entered current state. It is not a calibrated biological forecast. The user explicitly requested editable parameters because cultivar, planting dates, temporal observations and environment records are absent. No crop coefficients are prefilled.

## Run

From this project directory:

```powershell
python -m tools.monthly_growth serve --port 8855
python -m tools.monthly_growth template --out build/monthly_blank
python -m tools.monthly_growth run --input build/monthly_blank/input.json --out build/monthly_result
```

The first command opens a localhost API at http://127.0.0.1:8855/. Open that URL in the browser. The template is intentionally incomplete; fill its parameters before using `run`. Every output directory must be new and inside this project's `build/`.

The Korean UI provides current-state, growth-rate, new-compound and environment tabs. Edit arbitrary daily environments in the input JSON editor. Common environment changes require pressing the apply-to-30-days button. A modified input marks existing results stale and disables saving until recalculated. Save writes inputs, results, daily/compound/environment CSVs, a standalone inspection viewer and input/output/code hashes. The saved viewer is offline and inspectable; recalculation uses the local Python server or CLI, not a second JavaScript model.

## Explicit numerical contract

Required initial data: stem height (mm), and each entered compound's ID, attachment height (mm), azimuth (degrees), signed elevation (degrees), axis length and blade width (mm), one-sided tissue area (cm2), and unfolded fraction (0..1). Unknown planting dates and cultivar remain null. An empty compound list explicitly means no initial compounds, not unknown foliage. IDs identify scenario records, not automatically confirmed physical organs.

The growth mapping supplies each dimension's rate per development day and cap, the unfolding rate, and the elevation rate/target. Zero is a deliberate user input. For dimension x and development age a since the forecast origin or new-leaf event:

```text
x(a) = min(cap, initial_x + rate * a)
unfolded(a) = min(1, initial_unfolded + unfolding_rate * a)
display_spread_width = blade_width * unfolded
elevation(a) = initial_elevation + sign(target - initial_elevation)
               * min(abs(target - initial_elevation), angular_rate * a)
```

Existing leaf ages are unknown; elapsed development starts from the entered current state. One-sided tissue area is independent of display spread. Fixed azimuth and attachment heights, apical-only stem elongation and no senescence are model assumptions, not conclusions about real tomatoes. Empty or missing values never become zero. The model does not enforce or infer a relationship between axis length, area and width; the user must supply compatible assumptions.

New-compound generation is explicitly enabled or disabled. If enabled, supply the next emergence time, interval (both positive development days), first azimuth, divergence angle, and birth dimensions/elevation/unfolding. Events occur at their exact within-day time. Each new compound attaches at stem height at birth and grows only for the remaining development time. No leaflet count or optical tissue mesh is generated.

## Environment response

Each of the 30 days contains a required nonnegative development multiplier and optional temperature C, relative humidity %, PPFD micromol/m2/s, photoperiod h, EC mS/cm, pH and CO2 ppm.

`response.mode=manual` records environment but uses only the entered daily multiplier. `response.mode=curves` additionally requires at least one explicit response table under `response.curves`. Keys are environment field names; values are arrays of `{value, multiplier}` in strictly increasing input-value order. At least two knots are required. Piecewise-linear interpolation computes each enabled factor. Daily advancement is:

```text
development_increment = daily_multiplier * product(enabled_environment_factors)
```

This multiplicative interaction is an explicit scenario assumption, not fitted physiology. Missing values for enabled curves or environmental values outside supplied knot domains stop calculation. No extrapolation, optimal temperature, light saturation or EC penalty is silently invented. Disabled environmental variables do not affect development. PPFD and photoperiod are separate optional factors; there is no automatic DLI/carbon-balance conversion.

## Limits and validation

31 states include day zero. Actual dates appear only when the user enters a forecast start date; filenames and today's date do not supply biological observation dates. Outputs retain `validated_growth=false`, `suitable_for_ppfd=false` and unavailable uncertainty. Scenario state is not ingested as observed data by the existing compound forecast tools. No real reconstruction, GroIMP transport, causal directional-light response, flowering or harvest forecast is performed.

The 300-compound limit and HTTP input-size limit are resource safeguards, not biological thresholds. Later scientific work must establish appropriate response forms, calibrate identifiable coefficients with observations, and compare independent 7/14/21/30-day targets with baselines. The current software tests establish arithmetic behavior only.

```powershell
python -X utf8 -m pytest tools/tests/test_monthly_growth.py tools/tests/test_compound_growth.py tools/tests/test_compound_surface.py tools/tests/test_growth_simulator.py -q
```
