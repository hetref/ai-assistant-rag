"""
Weather service for contextual recommendations - Simulated weather data.
No API keys required - uses realistic weather simulation based on location and time.
"""
import os
import logging
import hashlib
import math
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
    is_simulated: bool = True  # Mark as simulated data
    
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
    """Weather service with simulated realistic data - no API keys required."""
    
    def __init__(self):
        self.cache = {}  # Simple in-memory cache
        self.cache_duration = timedelta(minutes=15)  # Cache for 15 minutes
        
        # Climate zone base patterns
        self.climate_patterns = {
            'tropical': {'temp_base': 28, 'humidity': 80, 'rain_chance': 40, 'temp_variation': 6},
            'subtropical': {'temp_base': 22, 'humidity': 70, 'rain_chance': 35, 'temp_variation': 10},
            'temperate': {'temp_base': 16, 'humidity': 65, 'rain_chance': 30, 'temp_variation': 15},
            'continental': {'temp_base': 12, 'humidity': 60, 'rain_chance': 25, 'temp_variation': 20},
            'cold': {'temp_base': 4, 'humidity': 70, 'rain_chance': 25, 'temp_variation': 18},
            'arctic': {'temp_base': -8, 'humidity': 75, 'rain_chance': 20, 'temp_variation': 12}
        }
        
        # Seasonal adjustments (Northern hemisphere bias)
        self.seasonal_adjustments = {
            'winter': {'temp': -8, 'rain': 10, 'conditions': [WeatherCondition.SNOW, WeatherCondition.CLOUDY, WeatherCondition.OVERCAST]},
            'spring': {'temp': 2, 'rain': 5, 'conditions': [WeatherCondition.PARTLY_CLOUDY, WeatherCondition.LIGHT_RAIN, WeatherCondition.SUNNY]},
            'summer': {'temp': 8, 'rain': -10, 'conditions': [WeatherCondition.SUNNY, WeatherCondition.CLEAR, WeatherCondition.PARTLY_CLOUDY]},
            'fall': {'temp': -2, 'rain': 5, 'conditions': [WeatherCondition.CLOUDY, WeatherCondition.RAIN, WeatherCondition.OVERCAST]}
        }
        
        # Daily temperature curves (0-24 hours)
        self.hourly_temp_factors = {
            0: -0.3, 1: -0.4, 2: -0.4, 3: -0.4, 4: -0.3, 5: -0.2,  # Night
            6: 0.0, 7: 0.2, 8: 0.4, 9: 0.6, 10: 0.8, 11: 0.9,      # Morning  
            12: 1.0, 13: 1.0, 14: 0.9, 15: 0.8, 16: 0.6, 17: 0.4,   # Afternoon
            18: 0.2, 19: 0.0, 20: -0.1, 21: -0.2, 22: -0.2, 23: -0.3 # Evening
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
        
        if abs_lat < 10:
            return 'tropical'
        elif abs_lat < 23:
            return 'subtropical'
        elif abs_lat < 35:
            return 'temperate'
        elif abs_lat < 50:
            return 'continental'
        elif abs_lat < 65:
            return 'cold'
        else:
            return 'arctic'
    
    def _get_season(self, lat: float, month: int) -> str:
        """Get season based on latitude and month."""
        # Northern hemisphere seasons (reverse for Southern hemisphere)
        if lat >= 0:  # Northern hemisphere
            if month in [12, 1, 2]:
                return 'winter'
            elif month in [3, 4, 5]:
                return 'spring'
            elif month in [6, 7, 8]:
                return 'summer'
            else:  # 9, 10, 11
                return 'fall'
        else:  # Southern hemisphere - reverse seasons
            if month in [12, 1, 2]:
                return 'summer'
            elif month in [3, 4, 5]:
                return 'fall'
            elif month in [6, 7, 8]:
                return 'winter'
            else:  # 9, 10, 11
                return 'spring'
    
    def _generate_pseudo_random(self, lat: float, lon: float, hour: int, day: int) -> float:
        """Generate pseudo-random number based on location and time for consistency."""
        # Create a deterministic but varied seed based on location and time
        seed_str = f"{lat:.2f},{lon:.2f},{hour},{day}"
        seed_hash = hashlib.md5(seed_str.encode()).hexdigest()
        # Convert hex to float between 0 and 1
        return int(seed_hash[:8], 16) / (16**8)
    
    async def get_current_weather(self, lat: float, lon: float) -> Optional[WeatherData]:
        """
        Get simulated current weather data for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            WeatherData object with simulated realistic data
        """
        cache_key = self._get_cache_key(lat, lon)
        
        # Check cache first
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                return cached_data
        
        # Generate realistic simulated weather
        weather_data = self._generate_realistic_weather(lat, lon)
        
        # Cache the result
        if weather_data:
            self.cache[cache_key] = (weather_data, datetime.now())
            logger.info(f"Generated realistic weather simulation for {lat:.4f}, {lon:.4f}")
        
        return weather_data
    
    def _generate_realistic_weather(self, lat: float, lon: float) -> WeatherData:
        """Generate realistic weather simulation based on location, time, and seasonal patterns."""
        now = datetime.now()
        hour = now.hour
        day_of_year = now.timetuple().tm_yday
        
        # Get climate zone and season
        climate_zone = self._get_climate_zone(lat)
        season = self._get_season(lat, now.month)
        
        # Get base climate pattern
        climate = self.climate_patterns[climate_zone]
        base_temp = climate['temp_base']
        base_humidity = climate['humidity']
        base_rain_chance = climate['rain_chance']
        temp_variation = climate['temp_variation']
        
        # Apply seasonal adjustments
        seasonal = self.seasonal_adjustments[season]
        adjusted_temp = base_temp + seasonal['temp']
        adjusted_rain_chance = max(0, min(100, base_rain_chance + seasonal['rain']))
        
        # Apply daily temperature curve
        hourly_factor = self.hourly_temp_factors.get(hour, 0)
        daily_temp = adjusted_temp + (hourly_factor * temp_variation)
        
        # Add some pseudo-random variation for realism
        random_factor = self._generate_pseudo_random(lat, lon, hour, day_of_year)
        temp_variation = (random_factor - 0.5) * 6  # ±3°C variation
        final_temp = daily_temp + temp_variation
        
        # Determine weather condition
        condition_random = self._generate_pseudo_random(lat, lon, hour + 100, day_of_year)
        seasonal_conditions = seasonal['conditions']
        
        if condition_random * 100 < adjusted_rain_chance:
            # Rainy conditions
            if final_temp < 0:
                condition = WeatherCondition.SNOW
                description = "Light snow"
            elif condition_random < 0.3:
                condition = WeatherCondition.LIGHT_RAIN
                description = "Light rain"
            elif condition_random < 0.7:
                condition = WeatherCondition.RAIN
                description = "Rain"
            else:
                condition = WeatherCondition.HEAVY_RAIN
                description = "Heavy rain"
        else:
            # Dry conditions - use seasonal preferences
            condition_index = int(condition_random * len(seasonal_conditions))
            condition = seasonal_conditions[condition_index]
            
            condition_descriptions = {
                WeatherCondition.CLEAR: "Clear sky",
                WeatherCondition.SUNNY: "Sunny",
                WeatherCondition.PARTLY_CLOUDY: "Partly cloudy",
                WeatherCondition.CLOUDY: "Cloudy",
                WeatherCondition.OVERCAST: "Overcast",
                WeatherCondition.FOG: "Fog",
                WeatherCondition.WINDY: "Windy"
            }
            description = condition_descriptions.get(condition, condition.value.replace("_", " ").title())
        
        # Calculate other parameters
        humidity_variation = (self._generate_pseudo_random(lat, lon, hour + 200, day_of_year) - 0.5) * 20
        final_humidity = max(20, min(100, base_humidity + humidity_variation))
        
        wind_speed = max(0, 5 + (self._generate_pseudo_random(lat, lon, hour + 300, day_of_year) - 0.5) * 20)
        
        # Feels like temperature (simplified heat index/wind chill)
        feels_like = final_temp
        if final_temp > 20 and final_humidity > 60:
            feels_like = final_temp + ((final_humidity - 60) / 40) * 3  # Heat index effect
        elif final_temp < 10 and wind_speed > 15:
            feels_like = final_temp - (wind_speed / 10)  # Wind chill effect
        
        # Precipitation chance
        precip_chance = adjusted_rain_chance if condition in [
            WeatherCondition.LIGHT_RAIN, WeatherCondition.RAIN, 
            WeatherCondition.HEAVY_RAIN, WeatherCondition.THUNDERSTORM
        ] else max(0, adjusted_rain_chance - 20)
        
        return WeatherData(
            temperature_celsius=round(final_temp, 1),
            temperature_fahrenheit=round(final_temp * 9/5 + 32, 1),
            condition=condition,
            description=description,
            humidity=round(final_humidity, 1),
            wind_speed_kmh=round(wind_speed, 1),
            precipitation_chance=round(precip_chance, 1),
            feels_like_celsius=round(feels_like, 1),
            timestamp=now,
            location=(lat, lon),
            is_simulated=True
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
                "bookstore", "library", "gym", "indoor entertainment", "covered parking",
                "museum", "arcade", "indoor sports"
            ])
            avoid.extend([
                "outdoor market", "park", "outdoor sports", "beach", "outdoor dining",
                "golf course", "outdoor events", "hiking trails", "outdoor festivals"
            ])
        
        elif weather_data.is_hot:
            preferred.extend([
                "air conditioned restaurant", "shopping mall", "ice cream shop", "pool",
                "beach", "water sports", "indoor cafe", "cold drinks", "frozen yogurt",
                "movie theater", "aquarium", "water park"
            ])
            avoid.extend([
                "outdoor market", "hot food", "sauna", "outdoor sports during midday",
                "hiking", "non-AC venues", "heavy meals"
            ])
        
        elif weather_data.is_cold:
            preferred.extend([
                "coffee shop", "warm restaurant", "indoor dining", "heated venues",
                "hot food", "warm clothing store", "indoor activities", "soup restaurant",
                "spa", "indoor markets", "cozy cafes"
            ])
            avoid.extend([
                "ice cream", "cold drinks", "outdoor dining", "swimming", "water activities",
                "outdoor seating", "cold food"
            ])
        
        elif weather_data.is_pleasant:
            preferred.extend([
                "outdoor dining", "park", "outdoor market", "sports venue",
                "outdoor events", "walking trails", "outdoor cafe", "recreational activities",
                "farmers market", "outdoor concerts", "picnic areas"
            ])
        
        # Condition-specific recommendations
        if weather_data.condition == WeatherCondition.SUNNY:
            preferred.extend(["sunglasses shop", "outdoor gear", "beach accessories", "sunscreen"])
        elif weather_data.condition == WeatherCondition.FOG:
            preferred.extend(["indoor venues", "coffee shop", "bookstore"])
            avoid.extend(["scenic viewpoints", "outdoor photography", "driving tours"])
        elif weather_data.condition == WeatherCondition.SNOW:
            preferred.extend(["winter sports", "ski shop", "warm clothing", "hot chocolate"])
            avoid.extend(["outdoor markets", "beach activities", "cold drinks"])
        
        return {
            "preferred": list(set(preferred)),  # Remove duplicates
            "avoid": list(set(avoid))
        }

# Global weather service instance
weather_service = WeatherService()