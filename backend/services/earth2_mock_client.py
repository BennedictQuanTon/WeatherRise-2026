from backend.schemas.weather_schema import WeatherSchema
from backend.schemas.destination_schema import DestinationSchema
import random

class Earth2MockClient:
    def get_forecast(self, dest: DestinationSchema, date_str: str, time_str: str) -> WeatherSchema:
        # Simulate high-resolution output from NVIDIA Earth-2 CorrDiff model
        # Earth-2 would provide much more granular localized weather patterns
        base_temp = 28 + random.uniform(-2, 4)
        base_wind = 15 + random.uniform(0, 30)
        base_precip = random.choice([0, 10, 50, 90])
        
        return WeatherSchema(
            temperature_c=round(base_temp, 1),
            precipitation_probability=base_precip,
            wind_speed_kmh=round(base_wind, 1),
            humidity_percent=85,
            conditions="Cloudy (Earth-2 Simulated)" if base_precip > 30 else "Clear (Earth-2 Simulated)"
        )

earth2_mock = Earth2MockClient()
