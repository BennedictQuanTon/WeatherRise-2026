# Human Review — Path A Benchmark

Model: `nvidia/llama-3.1-nemotron-nano-8b-v1`

Mode: `mock`

Dry-run: `True`

Timestamp: `20260610_022105`


## tourism_high_rain_001

- Description: Da Nang trip planning with high rain risk.

- Weather source: `mock_canonical_file`

- Risk: `{'rain_risk': 'high', 'heat_risk': 'medium', 'wind_risk': 'low', 'trip_disruption_risk': 'high'}`

- Valid JSON: True

- Risk preserved: True

- Latency: 0 ms

- Error: None


### Final answer

DRY RUN — Rain risk is high, heat risk is medium, and wind risk is low. (Adjust outdoor activities based on the highest weather risk and keep suitable indoor backups.)


### Manual notes

- TODO: Add human review here.


## tourism_heat_risk_001

- Description: Da Nang outdoor plan with high heat risk.

- Weather source: `mock_canonical_file`

- Risk: `{'rain_risk': 'low', 'heat_risk': 'high', 'wind_risk': 'low', 'trip_disruption_risk': 'high'}`

- Valid JSON: True

- Risk preserved: True

- Latency: 0 ms

- Error: None


### Final answer

DRY RUN — Rain risk is low, heat risk is high, and wind risk is low. (Adjust outdoor activities based on the highest weather risk and keep suitable indoor backups.)


### Manual notes

- TODO: Add human review here.


## tourism_good_weather_001

- Description: Da Nang good outdoor weather case.

- Weather source: `mock_canonical_file`

- Risk: `{'rain_risk': 'low', 'heat_risk': 'low', 'wind_risk': 'low', 'trip_disruption_risk': 'low'}`

- Valid JSON: True

- Risk preserved: True

- Latency: 0 ms

- Error: None


### Final answer

DRY RUN — Rain risk is low, heat risk is low, and wind risk is low. (Adjust outdoor activities based on the highest weather risk and keep suitable indoor backups.)


### Manual notes

- TODO: Add human review here.
