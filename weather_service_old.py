"""
Weather service integration for contextual recommendations.
Supports multiple weather APIs with fallback options.
"""
import os
import logging
import requests
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("weather_service")

class WeatherCondition(Enum):
    """Standardized weather conditions for recommendations."""
    CLEAR = "clear"
    SUNNY = "sunny"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    FOG = "fog"
    WINDY = "windy"
    HOT = "hot"
    COLD = "cold"
    UNKNOWN = "unknown"

@dataclass
class WeatherData:
    """Weather data model for recommendations."""
    temperature_celsius: float
    temperature_fahrenheit: float
    condition: WeatherCondition
    description: str
    humidity: float
    wind_speed_kmh: float
    precipitation_chance: float
    feels_like_celsius: float
    timestamp: datetime
    location: Tuple[float, float]  # (lat, lon)
    
    @property
    def is_hot(self) -> bool:
        """Check if weather is considered hot (>25°C/77°F)."""
        return self.temperature_celsius > 25
    
    @property
    def is_cold(self) -> bool:
        """Check if weather is considered cold (<10°C/50°F)."""
        return self.temperature_celsius < 10
    
    @property
    def is_rainy(self) -> bool:
        """Check if weather involves rain."""
        return self.condition in [
            WeatherCondition.LIGHT_RAIN, 
            WeatherCondition.RAIN, 
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.THUNDERSTORM
        ] or self.precipitation_chance > 50
    
    @property
    def is_pleasant(self) -> bool:
        """Check if weather is pleasant for outdoor activities."""
        return (
            self.condition in [WeatherCondition.CLEAR, WeatherCondition.SUNNY, WeatherCondition.PARTLY_CLOUDY] and
            10 <= self.temperature_celsius <= 25 and
            self.precipitation_chance < 20
        )

class WeatherService:
    """Weather service with simulated weather data - no API keys required."""
    
    def __init__(self):
        # No API keys needed - using simulation
        self.cache = {}  # Simple in-memory cache
        self.cache_duration = timedelta(minutes=15)  # Cache for 15 minutes
        
        # Realistic weather patterns based on location and season
        self.location_patterns = {
            # Major cities with typical weather patterns
            'tropical': {'temp_base': 28, 'humidity': 80, 'rain_chance': 40},  # < 23° latitude
            'temperate': {'temp_base': 18, 'humidity': 65, 'rain_chance': 30},  # 23-40° latitude  
            'cold': {'temp_base': 8, 'humidity': 70, 'rain_chance': 25},       # 40-60° latitude
            'arctic': {'temp_base': -2, 'humidity': 75, 'rain_chance': 20},    # > 60° latitude
        }
        
        # Seasonal adjustments (Northern hemisphere bias)
        self.seasonal_adjustments = {
            'winter': {'temp': -8, 'rain': 10},  # Dec, Jan, Feb
            'spring': {'temp': 2, 'rain': 5},    # Mar, Apr, May
            'summer': {'temp': 8, 'rain': -10},  # Jun, Jul, Aug
            'fall': {'temp': -2, 'rain': 5},     # Sep, Oct, Nov
        }
        
        # Daily temperature curves
        self.hourly_temp_curve = {
            0: -4, 1: -5, 2: -5, 3: -6, 4: -6, 5: -5,  # Night (coldest around 4-5 AM)
            6: -3, 7: -1, 8: 2, 9: 5, 10: 7, 11: 9,    # Morning warming
            12: 10, 13: 11, 14: 11, 15: 10, 16: 8, 17: 6, # Afternoon (peak around 1-2 PM)
            18: 4, 19: 2, 20: 0, 21: -1, 22: -2, 23: -3  # Evening cooling
        }
    
    def _get_cache_key(self, lat: float, lon: float) -> str:
        """Generate cache key for location."""
        return f"{lat:.4f},{lon:.4f}"
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached data is still valid."""
        return datetime.now() - timestamp < self.cache_duration
    
    def _get_climate_zone(self, lat: float) -> str:
        """Determine climate zone based on latitude."""
        abs_lat = abs(lat)
        if abs_lat < 23:
            return 'tropical'
        elif abs_lat < 40:
            return 'temperate'
        elif abs_lat < 60:
            return 'cold'
        else:
            return 'arctic'
    
    def _get_season(self, date: datetime, lat: float) -> str:
        """Determine season based on date and hemisphere."""
        month = date.month
        
        # Northern hemisphere seasons
        if lat >= 0:
            if month in [12, 1, 2]:
                return 'winter'
            elif month in [3, 4, 5]:
                return 'spring'
            elif month in [6, 7, 8]:
                return 'summer'
            else:
                return 'fall'
        else:
            # Southern hemisphere - seasons are opposite
            if month in [12, 1, 2]:
                return 'summer'
            elif month in [3, 4, 5]:
                return 'fall'
            elif month in [6, 7, 8]:
                return 'winter'
            else:
                return 'spring'
    
    def _simulate_weather_condition(self, temp: float, humidity: float, rain_chance: float, hour: int) -> WeatherCondition:
        """Simulate realistic weather condition based on parameters."""
        # Use location and time to add some deterministic "randomness"
        seed = (hour * 7 + int(temp * 3) + int(humidity / 10)) % 100
        
        # Determine precipitation first
        if seed < rain_chance:
            if temp < 2:
                return WeatherCondition.SNOW
            elif seed < rain_chance / 3:
                return WeatherCondition.LIGHT_RAIN
            elif seed < rain_chance * 2 / 3:
                return WeatherCondition.RAIN
            else:
                return WeatherCondition.THUNDERSTORM
        
        # Clear/cloudy conditions based on humidity and time
        cloud_factor = (humidity - 40) / 60 + (seed % 30) / 100  # 0-1 scale
        
        if cloud_factor < 0.2:
            return WeatherCondition.SUNNY if 6 <= hour <= 18 else WeatherCondition.CLEAR
        elif cloud_factor < 0.4:
            return WeatherCondition.PARTLY_CLOUDY
        elif cloud_factor < 0.7:
            return WeatherCondition.CLOUDY
        else:
            return WeatherCondition.OVERCAST
    
    async def get_current_weather(self, lat: float, lon: float) -> Optional[WeatherData]:
        """
        Get simulated current weather data for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            WeatherData object with realistic simulated data
        """
        cache_key = self._get_cache_key(lat, lon)
        
        # Check cache first
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                return cached_data
        
        now = datetime.now()
        weather_data = self._generate_simulated_weather(lat, lon, now)
        
        # Cache the result
        if weather_data:
            self.cache[cache_key] = (weather_data, now)
        
        return weather_data
    
    def _generate_simulated_weather(self, lat: float, lon: float, dt: datetime) -> WeatherData:
        """Generate realistic simulated weather for location and time."""
        # Determine climate zone and season
        climate_zone = self._get_climate_zone(lat)
        season = self._get_season(dt, lat)
        hour = dt.hour
        
        # Get base parameters for this location
        base_params = self.location_patterns[climate_zone]
        seasonal_adj = self.seasonal_adjustments[season]
        hourly_adj = self.hourly_temp_curve[hour]
        
        # Calculate temperature
        base_temp = base_params['temp_base']
        seasonal_temp = seasonal_adj['temp']
        
        # Add some location-based variation (coastal vs inland effect)
        coastal_effect = 0
        if abs(lon) < 10:  # Near prime meridian - more continental
            coastal_effect = -2 if season in ['winter', 'fall'] else 2
        
        final_temp = base_temp + seasonal_temp + hourly_adj + coastal_effect
        
        # Calculate humidity (varies by season and location)
        base_humidity = base_params['humidity']
        if climate_zone == 'tropical':
            humidity = base_humidity + (10 if season in ['summer', 'fall'] else -5)
        else:
            humidity = base_humidity + (5 if season in ['winter', 'spring'] else -10)
        
        humidity = max(30, min(95, humidity))  # Keep in realistic range
        
        # Calculate precipitation chance
        base_rain = base_params['rain_chance']
        seasonal_rain = seasonal_adj['rain']
        rain_chance = max(0, min(80, base_rain + seasonal_rain))
        
        # Generate condition
        condition = self._simulate_weather_condition(final_temp, humidity, rain_chance, hour)
        
        # Generate wind speed (higher in winter, varies by location)
        base_wind = 8  # km/h
        if season == 'winter':
            base_wind += 5
        if abs(lat) > 50:  # Higher latitudes are windier
            base_wind += 3
        
        # Add some variation based on coordinates
        wind_variation = ((int(lat * 10) + int(lon * 10)) % 20) - 10
        wind_speed = max(0, base_wind + wind_variation)
        
        # Generate description
        descriptions = {
            WeatherCondition.SUNNY: "Sunny and clear",
            WeatherCondition.CLEAR: "Clear skies",
            WeatherCondition.PARTLY_CLOUDY: "Partly cloudy",
            WeatherCondition.CLOUDY: "Mostly cloudy", 
            WeatherCondition.OVERCAST: "Overcast skies",
            WeatherCondition.LIGHT_RAIN: "Light rain",
            WeatherCondition.RAIN: "Moderate rain",
            WeatherCondition.HEAVY_RAIN: "Heavy rain",
            WeatherCondition.THUNDERSTORM: "Thunderstorms",
            WeatherCondition.SNOW: "Snow",
            WeatherCondition.FOG: "Foggy conditions"
        }
        
        description = descriptions.get(condition, "Variable conditions")
        
        # Adjust for temperature extremes
        if final_temp > 35:
            description = f"Very hot, {description.lower()}"
        elif final_temp > 25:
            description = f"Warm, {description.lower()}"
        elif final_temp < -10:
            description = f"Very cold, {description.lower()}"
        elif final_temp < 5:
            description = f"Cold, {description.lower()}"
        
        return WeatherData(
            temperature_celsius=final_temp,
            temperature_fahrenheit=final_temp * 9/5 + 32,
            condition=condition,
            description=description,
            humidity=humidity,
            wind_speed_kmh=wind_speed,
            precipitation_chance=rain_chance,
            feels_like_celsius=final_temp - (wind_speed / 10),  # Simple wind chill
            timestamp=dt,
            location=(lat, lon)
        )
    
    def get_weather_business_suggestions(self, weather_data: WeatherData) -> Dict[str, List[str]]:
        """
        Get business category suggestions based on weather conditions.
        
        Returns:
            Dictionary with 'preferred' and 'avoid' business categories
        """
        preferred = []
        avoid = []
        
        if weather_data.is_rainy:
            preferred.extend([
                "shopping mall", "indoor restaurant", "cinema", "cafe with covered seating",
                "bookstore", "library", "gym", "indoor entertainment", "covered parking"
            ])
            avoid.extend([
                "outdoor market", "park", "outdoor sports", "beach", "outdoor dining",
                "golf course", "outdoor events"
            ])
        
        elif weather_data.is_hot:
            preferred.extend([
                "air conditioned restaurant", "shopping mall", "ice cream shop", "pool",
                "beach", "water sports", "indoor cafe", "cold drinks", "frozen yogurt"
            ])
            avoid.extend([
                "outdoor market", "hot food", "outdoor sports", "hiking", "non-AC venues"
            ])
        
        elif weather_data.is_cold:
            preferred.extend([
                "coffee shop", "warm restaurant", "indoor dining", "heating",
                "hot food", "warm clothing store", "indoor activities", "soup kitchen"
            ])
            avoid.extend([
                "ice cream", "cold drinks", "outdoor dining", "swimming", "water activities"
            ])
        
        elif weather_data.is_pleasant:
            preferred.extend([
                "outdoor dining", "park", "outdoor market", "sports venue",
                "outdoor events", "walking trails", "outdoor cafe", "recreational activities"
            ])
        
        # Condition-specific recommendations
        if weather_data.condition == WeatherCondition.SUNNY:
            preferred.extend(["sunglasses shop", "outdoor gear", "beach accessories"])
        elif weather_data.condition == WeatherCondition.FOG:
            preferred.extend(["indoor venues", "coffee shop", "bookstore"])
            avoid.extend(["scenic viewpoints", "outdoor photography"])
        
        return {
            "preferred": list(set(preferred)),  # Remove duplicates
            "avoid": list(set(avoid))
        }

# Global weather service instance
weather_service = WeatherService()
