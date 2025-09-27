"""
Contextual recommendation engine that combines time of day, weather, and user history
to provide smart, situational business recommendations.
"""
import os
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict, Counter
from dataclasses import dataclass
from enum import Enum
import json

from weather_service import weather_service, WeatherData, WeatherCondition

logger = logging.getLogger("contextual_recommendations")

class TimeOfDay(Enum):
    """Time periods for contextual recommendations."""
    EARLY_MORNING = "early_morning"  # 5-8 AM
    MORNING = "morning"              # 8-11 AM  
    LATE_MORNING = "late_morning"    # 11 AM-12 PM
    LUNCH = "lunch"                  # 12-2 PM
    AFTERNOON = "afternoon"          # 2-5 PM
    EARLY_EVENING = "early_evening"  # 5-7 PM
    EVENING = "evening"              # 7-9 PM
    NIGHT = "night"                  # 9 PM-12 AM
    LATE_NIGHT = "late_night"        # 12-5 AM

@dataclass
class ContextualFactor:
    """Individual contextual factor with weight."""
    factor_type: str  # 'time', 'weather', 'history', 'location'
    category_boost: Dict[str, float]  # business category -> boost multiplier
    category_penalty: Dict[str, float]  # business category -> penalty multiplier
    weight: float = 1.0  # Overall weight of this factor
    reason: str = ""  # Human-readable explanation

@dataclass
class RecommendationContext:
    """Complete context for generating recommendations."""
    user_id: str
    user_location: Tuple[float, float]  # (lat, lon)
    current_time: datetime
    time_of_day: TimeOfDay
    weather_data: Optional[WeatherData]
    user_history: Dict[str, Any]
    search_query: Optional[str] = None
    session_id: Optional[str] = None

class ContextualRecommendationEngine:
    """Engine for generating contextual business recommendations."""
    
    def __init__(self, cf_engine=None):
        self.cf_engine = cf_engine  # Collaborative filtering engine
        
        # Time-based business preferences
        self.time_preferences = {
            TimeOfDay.EARLY_MORNING: {
                "preferred": ["coffee shop", "bakery", "gym", "pharmacy", "gas station", "breakfast restaurant"],
                "boosted": {"coffee shop": 2.0, "bakery": 1.8, "gym": 1.5, "breakfast restaurant": 1.7},
                "avoid": ["bar", "nightclub", "late night food"]
            },
            TimeOfDay.MORNING: {
                "preferred": ["coffee shop", "office supply", "bank", "business services", "breakfast restaurant"],
                "boosted": {"coffee shop": 1.8, "business services": 1.5, "breakfast restaurant": 1.5},
                "avoid": ["bar", "nightclub", "dinner restaurant"]
            },
            TimeOfDay.LATE_MORNING: {
                "preferred": ["shopping mall", "retail", "services", "coffee shop", "brunch restaurant"],
                "boosted": {"shopping mall": 1.3, "brunch restaurant": 1.6},
                "avoid": ["bar", "nightclub"]
            },
            TimeOfDay.LUNCH: {
                "preferred": ["restaurant", "fast food", "cafe", "food court", "takeaway"],
                "boosted": {"restaurant": 1.8, "fast food": 1.6, "cafe": 1.4, "lunch specials": 2.0},
                "avoid": ["breakfast restaurant", "late night food"]
            },
            TimeOfDay.AFTERNOON: {
                "preferred": ["shopping mall", "retail", "services", "coffee shop", "office supply"],
                "boosted": {"shopping mall": 1.4, "retail": 1.3, "coffee shop": 1.2},
                "avoid": ["bar", "nightclub", "breakfast restaurant"]
            },
            TimeOfDay.EARLY_EVENING: {
                "preferred": ["restaurant", "grocery store", "retail", "services", "happy hour"],
                "boosted": {"restaurant": 1.6, "grocery store": 1.4, "happy hour": 1.8},
                "avoid": ["breakfast restaurant", "late night food"]
            },
            TimeOfDay.EVENING: {
                "preferred": ["restaurant", "entertainment", "cinema", "bar", "shopping"],
                "boosted": {"restaurant": 1.7, "entertainment": 1.5, "bar": 1.4, "cinema": 1.6},
                "avoid": ["breakfast restaurant", "business services"]
            },
            TimeOfDay.NIGHT: {
                "preferred": ["restaurant", "bar", "entertainment", "cinema", "late night food"],
                "boosted": {"bar": 1.8, "entertainment": 1.6, "late night food": 1.7},
                "avoid": ["breakfast restaurant", "business services", "office supply"]
            },
            TimeOfDay.LATE_NIGHT: {
                "preferred": ["24hr service", "late night food", "convenience store", "gas station", "pharmacy"],
                "boosted": {"24hr service": 2.0, "late night food": 1.8, "convenience store": 1.6},
                "avoid": ["business services", "retail", "shopping mall"]
            }
        }
        
        # Day of week preferences
        self.day_preferences = {
            "monday": {"boosted": {"coffee shop": 1.3, "business services": 1.2}},
            "tuesday": {"boosted": {"restaurant": 1.1, "services": 1.1}},
            "wednesday": {"boosted": {"coffee shop": 1.2, "lunch specials": 1.3}},
            "thursday": {"boosted": {"restaurant": 1.2, "happy hour": 1.4}},
            "friday": {"boosted": {"restaurant": 1.4, "bar": 1.5, "entertainment": 1.3}},
            "saturday": {"boosted": {"restaurant": 1.3, "entertainment": 1.4, "shopping mall": 1.2, "recreational": 1.3}},
            "sunday": {"boosted": {"brunch restaurant": 1.6, "recreational": 1.2, "family entertainment": 1.3}}
        }
    
    def get_time_of_day(self, dt: datetime) -> TimeOfDay:
        """Determine time of day category from datetime."""
        hour = dt.hour
        
        if 5 <= hour < 8:
            return TimeOfDay.EARLY_MORNING
        elif 8 <= hour < 11:
            return TimeOfDay.MORNING
        elif 11 <= hour < 12:
            return TimeOfDay.LATE_MORNING
        elif 12 <= hour < 14:
            return TimeOfDay.LUNCH
        elif 14 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 19:
            return TimeOfDay.EARLY_EVENING
        elif 19 <= hour < 21:
            return TimeOfDay.EVENING
        elif 21 <= hour < 24:
            return TimeOfDay.NIGHT
        else:  # 0-5
            return TimeOfDay.LATE_NIGHT
    
    async def get_user_context(
        self, 
        user_id: str, 
        user_lat: float, 
        user_lng: float,
        search_query: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> RecommendationContext:
        """Build complete recommendation context for a user."""
        current_time = datetime.now()
        time_of_day = self.get_time_of_day(current_time)
        
        # Get weather data
        weather_data = None
        try:
            weather_data = await weather_service.get_current_weather(user_lat, user_lng)
        except Exception as e:
            logger.warning(f"Failed to get weather data: {e}")
        
        # Get user history from collaborative filtering
        user_history = {}
        if self.cf_engine:
            try:
                # Get user interactions
                interactions = await self.cf_engine.get_user_interactions(user_id, days=30)
                user_history['recent_interactions'] = interactions
                
                # Get user preferences
                preferences = await self.cf_engine.get_user_preferences(user_id)
                if preferences:
                    user_history['preferences'] = {
                        'categories': preferences.preferred_categories,
                        'tags': preferences.preferred_tags,
                        'search_patterns': preferences.search_patterns
                    }
                
                # Analyze patterns
                user_history.update(self._analyze_user_patterns(interactions))
                
            except Exception as e:
                logger.warning(f"Failed to get user history: {e}")
        
        return RecommendationContext(
            user_id=user_id,
            user_location=(user_lat, user_lng),
            current_time=current_time,
            time_of_day=time_of_day,
            weather_data=weather_data,
            user_history=user_history,
            search_query=search_query,
            session_id=session_id
        )
    
    def _analyze_user_patterns(self, interactions: List[Dict]) -> Dict[str, Any]:
        """Analyze user interaction patterns for contextual insights."""
        if not interactions:
            return {}
        
        patterns = {}
        
        # Time-based patterns
        hour_activity = defaultdict(int)
        day_activity = defaultdict(int)
        category_time = defaultdict(lambda: defaultdict(int))
        
        for interaction in interactions:
            try:
                timestamp = datetime.fromisoformat(interaction.get('timestamp', ''))
                hour = timestamp.hour
                day = timestamp.strftime('%A').lower()
                category = interaction.get('category', 'unknown')
                
                hour_activity[hour] += 1
                day_activity[day] += 1
                category_time[category][hour] += 1
                
            except Exception:
                continue
        
        patterns['peak_hours'] = sorted(hour_activity.items(), key=lambda x: x[1], reverse=True)[:3]
        patterns['peak_days'] = sorted(day_activity.items(), key=lambda x: x[1], reverse=True)[:3]
        patterns['category_timing'] = dict(category_time)
        
        # Location patterns (simplified - would need more sophisticated clustering)
        locations = []
        for interaction in interactions:
            if 'location' in interaction and interaction['location']:
                try:
                    lat, lng = interaction['location']
                    locations.append((lat, lng))
                except Exception:
                    continue
        
        patterns['frequent_locations'] = locations[-10:]  # Last 10 locations
        
        return patterns
    
    def generate_contextual_factors(self, context: RecommendationContext) -> List[ContextualFactor]:
        """Generate all contextual factors for recommendations."""
        factors = []
        
        # Time of day factor
        time_factor = self._generate_time_factor(context)
        if time_factor:
            factors.append(time_factor)
        
        # Day of week factor
        day_factor = self._generate_day_factor(context)
        if day_factor:
            factors.append(day_factor)
        
        # Weather factor
        if context.weather_data:
            weather_factor = self._generate_weather_factor(context)
            if weather_factor:
                factors.append(weather_factor)
        
        # User history factors
        history_factors = self._generate_history_factors(context)
        factors.extend(history_factors)
        
        return factors
    
    def _generate_time_factor(self, context: RecommendationContext) -> Optional[ContextualFactor]:
        """Generate time-of-day contextual factor."""
        time_prefs = self.time_preferences.get(context.time_of_day, {})
        if not time_prefs:
            return None
        
        return ContextualFactor(
            factor_type='time',
            category_boost=time_prefs.get('boosted', {}),
            category_penalty={cat: 0.3 for cat in time_prefs.get('avoid', [])},
            weight=1.2,  # Time is important
            reason=f"Time of day: {context.time_of_day.value} ({context.current_time.strftime('%H:%M')})"
        )
    
    def _generate_day_factor(self, context: RecommendationContext) -> Optional[ContextualFactor]:
        """Generate day-of-week contextual factor."""
        day_name = context.current_time.strftime('%A').lower()
        day_prefs = self.day_preferences.get(day_name, {})
        
        if not day_prefs:
            return None
        
        return ContextualFactor(
            factor_type='day',
            category_boost=day_prefs.get('boosted', {}),
            category_penalty={},
            weight=0.8,  # Day is moderately important
            reason=f"Day of week: {day_name.title()}"
        )
    
    def _generate_weather_factor(self, context: RecommendationContext) -> Optional[ContextualFactor]:
        """Generate weather-based contextual factor."""
        if not context.weather_data:
            return None
        
        weather = context.weather_data
        suggestions = weather_service.get_weather_business_suggestions(weather)
        
        # Convert suggestions to boost/penalty format
        category_boost = {}
        category_penalty = {}
        
        for category in suggestions.get('preferred', []):
            category_boost[category] = 1.5
        
        for category in suggestions.get('avoid', []):
            category_penalty[category] = 0.4
        
        # Special weather condition boosts
        if weather.is_rainy:
            category_boost.update({
                "indoor": 1.8,
                "covered": 1.6,
                "mall": 1.4
            })
            weight = 1.3
        elif weather.is_hot:
            category_boost.update({
                "air conditioning": 1.6,
                "cold drinks": 1.5,
                "ice cream": 1.8
            })
            weight = 1.2
        elif weather.is_cold:
            category_boost.update({
                "coffee": 1.6,
                "warm food": 1.5,
                "heated": 1.4
            })
            weight = 1.2
        else:
            weight = 1.0
        
        return ContextualFactor(
            factor_type='weather',
            category_boost=category_boost,
            category_penalty=category_penalty,
            weight=weight,
            reason=f"Weather: {weather.description} ({weather.temperature_celsius:.0f}°C)"
        )
    
    def _generate_history_factors(self, context: RecommendationContext) -> List[ContextualFactor]:
        """Generate user history-based contextual factors."""
        factors = []
        history = context.user_history
        
        if not history:
            return factors
        
        # Category preference factor
        if 'preferences' in history and 'categories' in history['preferences']:
            category_prefs = history['preferences']['categories']
            if category_prefs:
                # Normalize scores to boost multipliers
                max_score = max(category_prefs.values()) if category_prefs else 1
                category_boost = {
                    cat: min(1.0 + score / max_score, 2.0) 
                    for cat, score in category_prefs.items() 
                    if score > 0
                }
                
                factors.append(ContextualFactor(
                    factor_type='user_preferences',
                    category_boost=category_boost,
                    category_penalty={},
                    weight=1.1,
                    reason="Based on your previous preferences"
                ))
        
        # Time-based usage patterns
        if 'peak_hours' in history and history['peak_hours']:
            current_hour = context.current_time.hour
            user_peak_hours = [hour for hour, _ in history['peak_hours']]
            
            if current_hour in user_peak_hours:
                # User is active at this time - boost familiar categories
                recent_categories = {}
                for interaction in history.get('recent_interactions', [])[-20:]:  # Last 20
                    category = interaction.get('category', '')
                    if category:
                        recent_categories[category] = recent_categories.get(category, 0) + 1
                
                if recent_categories:
                    max_count = max(recent_categories.values())
                    category_boost = {
                        cat: 1.0 + (count / max_count) * 0.3
                        for cat, count in recent_categories.items()
                    }
                    
                    factors.append(ContextualFactor(
                        factor_type='usage_patterns',
                        category_boost=category_boost,
                        category_penalty={},
                        weight=0.9,
                        reason=f"Active time pattern (you're usually active at {current_hour}:00)"
                    ))
        
        return factors
    
    def apply_contextual_factors(
        self, 
        businesses: List[Dict[str, Any]], 
        factors: List[ContextualFactor]
    ) -> List[Dict[str, Any]]:
        """Apply contextual factors to business results."""
        if not factors or not businesses:
            return businesses
        
        scored_businesses = []
        
        for business in businesses:
            business_copy = business.copy()
            contextual_score = 1.0
            applied_factors = []
            
            category = business.get('business_category', '').lower()
            tags = business.get('business_tags', '').lower()
            combined_text = f"{category} {tags}".lower()
            
            for factor in factors:
                factor_applied = False
                
                # Check category boosts
                for boost_category, multiplier in factor.category_boost.items():
                    if boost_category.lower() in combined_text:
                        contextual_score *= multiplier * factor.weight
                        factor_applied = True
                        break
                
                # Check category penalties
                for penalty_category, multiplier in factor.category_penalty.items():
                    if penalty_category.lower() in combined_text:
                        contextual_score *= multiplier / factor.weight  # Inverse weight for penalties
                        factor_applied = True
                        break
                
                if factor_applied:
                    applied_factors.append(factor.reason)
            
            business_copy['contextual_score'] = contextual_score
            business_copy['applied_factors'] = applied_factors
            business_copy['original_score'] = business.get('vector_score', business.get('distance_km', 0))
            
            # Combine with original scoring
            if 'distance_km' in business:
                # For distance-based, lower is better, so we boost by reducing effective distance
                business_copy['final_score'] = business['distance_km'] / contextual_score
            elif 'vector_score' in business:
                # For vector score, lower is better, so we boost by reducing effective score
                business_copy['final_score'] = business['vector_score'] / contextual_score
            else:
                business_copy['final_score'] = 1.0 / contextual_score
            
            scored_businesses.append(business_copy)
        
        # Sort by final score (lower is better)
        scored_businesses.sort(key=lambda x: x['final_score'])
        
        return scored_businesses
    
    async def get_contextual_recommendations(
        self,
        user_id: str,
        user_lat: float,
        user_lng: float,
        search_query: Optional[str] = None,
        base_results: Optional[List[Dict[str, Any]]] = None,
        limit: int = 20,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate contextual recommendations for a user.
        
        Args:
            user_id: User identifier
            user_lat: User latitude
            user_lng: User longitude  
            search_query: Optional search query
            base_results: Optional base search results to enhance
            limit: Maximum recommendations to return
            session_id: Optional session ID
            
        Returns:
            Dictionary containing recommendations and context information
        """
        # Build user context
        context = await self.get_user_context(
            user_id, user_lat, user_lng, search_query, session_id
        )
        
        # Generate contextual factors
        factors = self.generate_contextual_factors(context)
        
        # If no base results provided, get collaborative filtering recommendations
        if not base_results and self.cf_engine:
            try:
                base_results = await self.cf_engine.get_collaborative_recommendations(
                    user_id=user_id,
                    limit=limit * 2  # Get more to have options after contextual filtering
                )
            except Exception as e:
                logger.warning(f"Failed to get CF recommendations: {e}")
                base_results = []
        
        if not base_results:
            base_results = []
        
        # Apply contextual factors
        contextual_results = self.apply_contextual_factors(base_results, factors)
        
        # Generate context summary
        context_summary = self._generate_context_summary(context, factors)
        
        return {
            "recommendations": contextual_results[:limit],
            "context": {
                "time_of_day": context.time_of_day.value,
                "weather": {
                    "condition": context.weather_data.condition.value if context.weather_data else None,
                    "temperature": context.weather_data.temperature_celsius if context.weather_data else None,
                    "description": context.weather_data.description if context.weather_data else None
                } if context.weather_data else None,
                "factors_applied": [f.reason for f in factors],
                "summary": context_summary
            },
            "user_id": user_id,
            "generated_at": context.current_time.isoformat()
        }
    
    def _generate_context_summary(
        self, 
        context: RecommendationContext, 
        factors: List[ContextualFactor]
    ) -> str:
        """Generate human-readable context summary."""
        parts = []
        
        # Time context
        time_str = context.current_time.strftime('%A, %I:%M %p')
        parts.append(f"It's {time_str}")
        
        # Weather context
        if context.weather_data:
            weather = context.weather_data
            parts.append(f"Weather is {weather.description} at {weather.temperature_celsius:.0f}°C")
        
        # Activity suggestions based on context
        suggestions = []
        for factor in factors:
            if factor.factor_type == 'time' and context.time_of_day == TimeOfDay.LUNCH:
                suggestions.append("perfect for lunch")
            elif factor.factor_type == 'weather' and context.weather_data:
                if context.weather_data.is_rainy:
                    suggestions.append("indoor activities recommended")
                elif context.weather_data.is_pleasant:
                    suggestions.append("great weather for outdoor activities")
        
        if suggestions:
            parts.append(f"({', '.join(suggestions)})")
        
        return ". ".join(parts) + "."

# Global contextual recommendation engine
contextual_engine = ContextualRecommendationEngine()
