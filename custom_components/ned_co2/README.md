# NED CO₂ — Home Assistant Integration

This custom integration fetches **CO₂ intensity of electricity consumption in the Netherlands** from the [NED API](https://api.ned.nl/v1).

It creates sensors for:
- **Current slot EF**: the emission factor (kg CO₂/kWh) for the current timeslot.
- **Forecast minimum EF**: the greenest (lowest EF) timeslot within the forecast window.
- **Forecast greenest start/end**: timestamps for that optimal window.

## Installation

### HACS (recommended)
1. In HACS → Integrations → ⋮ → **Custom repositories**  
   Add repository URL of this project. Category: **Integration**.
2. Install and restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.  
   Search for **NED CO₂**.

### Manual
1. Copy `custom_components/ned_co2` into your `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add integration via UI.

## Configuration

When adding the integration, you’ll be asked for:

- **API key** (`X-AUTH-TOKEN`) from your NED account
- **Point** (default: `0` = NL total)
- **Granularity** (`5` = hourly, `4` = 15‑min)
- **Window days** (how many days ahead to fetch forecast, default 2)
- **Local timezone filter** (true = CET/CEST times, false = UTC)

## Entities created

- `sensor.ned_co2_current_slot`  
  State = current slot emission factor (kg/kWh), updates automatically.  
  Attributes: slot start/end UTC timestamps.

- `sensor.ned_co2_forecast_min`  
  State = minimum EF in forecast window.  

- `sensor.ned_co2_forecast_best_start` (timestamp)  
- `sensor.ned_co2_forecast_best_end` (timestamp)  

## Example ApexCharts card

```yaml
type: custom:apexcharts-card
header:
  title: CO₂ Intensity
graph_span: 48h
series:
  - entity: sensor.ned_co2_current_slot
    name: Current EF
    type: line
    curve: stepline
  - entity: sensor.ned_co2_forecast_min
    name: Greenest forecast
    type: line
    curve: straight
    extend_to: false
    data_generator: |
      const s = hass.states['sensor.ned_co2_forecast_min']?.state;
      const start = hass.states['sensor.ned_co2_forecast_best_start']?.state;
      const end   = hass.states['sensor.ned_co2_forecast_best_end']?.state;
      const ef = parseFloat(s);
      if (!start || !end || Number.isNaN(ef)) return [];
      return [[new Date(start), ef], [new Date(end), ef]];
```

## Notes
- This uses NED `type=27` (Electricity Mix CO₂ EF).
- Ensure your NED subscription includes both **current** and **forecast** data.
- Default update interval: 5 minutes.
- See, https://ned.nl/nl/handleiding-api
---

⚡️ Minimize your footprint: run appliances when the forecast EF is lowest!
