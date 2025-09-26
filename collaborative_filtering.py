import json
import logging
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

# Handle optional imports gracefully
try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available - some CF features will be limited")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis not available - CF will not work")

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except (ImportError, TypeError) as e:
    AIOREDIS_AVAILABLE = False
    logger.warning(f"aioredis not available or incompatible: {e}")

try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback BaseModel
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

logger = logging.getLogger("collaborative_filtering")

# Redis key patterns
USER_INTERACTIONS_KEY = "user_interactions:{user_id}"
BUSINESS_INTERACTIONS_KEY = "business_interactions:{business_id}" 
SEARCH_QUERIES_KEY = "search_queries:{user_id}"
SIMILAR_USERS_KEY = "similar_users:{user_id}"
BUSINESS_SIMILARITY_KEY = "business_similarity:{business_id}"
POPULAR_SEARCHES_KEY = "popular_searches"
USER_PREFERENCES_KEY = "user_preferences:{user_id}"

class UserInteraction(BaseModel):
    """Model for user interactions with businesses."""
    user_id: str
    business_id: str
    business_name: str
    interaction_type: str  # "view", "click", "search", "bookmark"
    timestamp: datetime
    query: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    location: Optional[Tuple[float, float]] = None  # (lat, lng)
    session_id: str
    implicit_rating: float = 1.0  # 1-5 scale based on interaction type

class UserPreferences(BaseModel):
    """Model for user preferences derived from interactions."""
    user_id: str
    preferred_categories: Dict[str, float]  # category -> preference score
    preferred_tags: Dict[str, float]  # tag -> preference score
    preferred_locations: List[Tuple[float, float, float]]  # (lat, lng, preference)
    search_patterns: List[str]
    last_updated: datetime

class CollaborativeFilteringEngine:
    """Main collaborative filtering engine."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.min_interactions_for_cf = 3  # Minimum interactions to enable CF
        self.similarity_threshold = 0.1  # Minimum similarity score
        self.max_recommendations = 20
        
    async def connect(self):
        """Initialize Redis connection."""
        if not self.redis_client:
            self.redis_client = aioredis.from_url(self.redis_url, decode_responses=True)
            
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def generate_user_id(self, user_agent: str, ip_address: str) -> str:
        """Generate anonymous user ID from user agent and IP."""
        identifier = f"{user_agent}:{ip_address}"
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]
    
    def calculate_implicit_rating(self, interaction_type: str, dwell_time: Optional[int] = None) -> float:
        """Calculate implicit rating based on interaction type and dwell time."""
        base_ratings = {
            "search": 1.0,
            "view": 2.0,
            "click": 3.0,
            "bookmark": 5.0,
            "share": 4.0
        }
        
        rating = base_ratings.get(interaction_type, 1.0)
        
        # Boost rating based on dwell time
        if dwell_time and interaction_type in ["view", "click"]:
            if dwell_time > 30:  # More than 30 seconds
                rating += 0.5
            if dwell_time > 120:  # More than 2 minutes
                rating += 1.0
        
        return min(rating, 5.0)
    
    async def record_interaction(self, interaction: UserInteraction):
        """Record a user interaction."""
        await self.connect()
        
        # Store user interaction
        user_key = USER_INTERACTIONS_KEY.format(user_id=interaction.user_id)
        interaction_data = {
            "business_id": interaction.business_id,
            "business_name": interaction.business_name,
            "type": interaction.interaction_type,
            "timestamp": interaction.timestamp.isoformat(),
            "query": interaction.query or "",
            "category": interaction.category or "",
            "tags": json.dumps(interaction.tags or []),
            "rating": interaction.implicit_rating
        }
        
        # Use sorted set to maintain chronological order
        score = interaction.timestamp.timestamp()
        await self.redis_client.zadd(user_key, {json.dumps(interaction_data): score})
        
        # Store business interaction
        business_key = BUSINESS_INTERACTIONS_KEY.format(business_id=interaction.business_id)
        business_data = {
            "user_id": interaction.user_id,
            "type": interaction.interaction_type,
            "timestamp": interaction.timestamp.isoformat(),
            "rating": interaction.implicit_rating
        }
        await self.redis_client.zadd(business_key, {json.dumps(business_data): score})
        
        # Store search query if present
        if interaction.query:
            search_key = SEARCH_QUERIES_KEY.format(user_id=interaction.user_id)
            await self.redis_client.zadd(search_key, {interaction.query: score})
            
            # Track popular searches
            await self.redis_client.zincrby(POPULAR_SEARCHES_KEY, 1, interaction.query)
        
        # Set expiry for data (30 days)
        expire_time = 30 * 24 * 3600
        await self.redis_client.expire(user_key, expire_time)
        await self.redis_client.expire(business_key, expire_time)
        
        # Update user preferences asynchronously
        await self._update_user_preferences(interaction)
    
    async def _update_user_preferences(self, interaction: UserInteraction):
        """Update user preferences based on interaction."""
        prefs_key = USER_PREFERENCES_KEY.format(user_id=interaction.user_id)
        
        # Get existing preferences
        prefs_data = await self.redis_client.get(prefs_key)
        if prefs_data:
            prefs = UserPreferences.model_validate(json.loads(prefs_data))
        else:
            prefs = UserPreferences(
                user_id=interaction.user_id,
                preferred_categories={},
                preferred_tags={},
                preferred_locations=[],
                search_patterns=[],
                last_updated=datetime.now()
            )
        
        # Update category preferences
        if interaction.category:
            current_score = prefs.preferred_categories.get(interaction.category, 0.0)
            prefs.preferred_categories[interaction.category] = current_score + interaction.implicit_rating
        
        # Update tag preferences
        if interaction.tags:
            for tag in interaction.tags:
                current_score = prefs.preferred_tags.get(tag, 0.0)
                prefs.preferred_tags[tag] = current_score + interaction.implicit_rating
        
        # Update search patterns
        if interaction.query and interaction.query not in prefs.search_patterns:
            prefs.search_patterns.append(interaction.query)
            if len(prefs.search_patterns) > 20:  # Keep only recent 20 patterns
                prefs.search_patterns = prefs.search_patterns[-20:]
        
        prefs.last_updated = datetime.now()
        
        # Store updated preferences
        await self.redis_client.setex(
            prefs_key, 
            30 * 24 * 3600,  # 30 days expiry
            json.dumps(prefs.model_dump(), default=str)
        )
    
    async def get_user_interactions(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user interactions for collaborative filtering."""
        await self.connect()
        
        user_key = USER_INTERACTIONS_KEY.format(user_id=user_id)
        cutoff_timestamp = (datetime.now() - timedelta(days=days)).timestamp()
        
        # Get recent interactions
        interactions = await self.redis_client.zrangebyscore(
            user_key, cutoff_timestamp, "+inf", withscores=True
        )
        
        return [json.loads(interaction[0]) for interaction in interactions]
    
    async def calculate_user_similarity(self, user1_id: str, user2_id: str) -> float:
        """Calculate similarity between two users based on their interactions."""
        user1_interactions = await self.get_user_interactions(user1_id)
        user2_interactions = await self.get_user_interactions(user2_id)
        
        if not user1_interactions or not user2_interactions:
            return 0.0
        
        # Create business rating matrices
        user1_ratings = {inter["business_id"]: inter["rating"] for inter in user1_interactions}
        user2_ratings = {inter["business_id"]: inter["rating"] for inter in user2_interactions}
        
        # Find common businesses
        common_businesses = set(user1_ratings.keys()) & set(user2_ratings.keys())
        
        if len(common_businesses) < 2:
            return 0.0
        
        # Calculate cosine similarity
        ratings1 = [user1_ratings[biz] for biz in common_businesses]
        ratings2 = [user2_ratings[biz] for biz in common_businesses]
        
        return cosine_similarity([ratings1], [ratings2])[0][0]
    
    async def find_similar_users(self, user_id: str, limit: int = 10) -> List[Tuple[str, float]]:
        """Find users similar to the given user."""
        await self.connect()
        
        # Check cache first
        cache_key = SIMILAR_USERS_KEY.format(user_id=user_id)
        cached_result = await self.redis_client.get(cache_key)
        
        if cached_result:
            return json.loads(cached_result)
        
        user_interactions = await self.get_user_interactions(user_id)
        if len(user_interactions) < self.min_interactions_for_cf:
            return []
        
        # Get all users who interacted with businesses this user likes
        business_ids = {inter["business_id"] for inter in user_interactions}
        similar_users = set()
        
        for business_id in business_ids:
            business_key = BUSINESS_INTERACTIONS_KEY.format(business_id=business_id)
            business_interactions = await self.redis_client.zrange(business_key, 0, -1)
            
            for interaction_str in business_interactions:
                interaction = json.loads(interaction_str)
                if interaction["user_id"] != user_id:
                    similar_users.add(interaction["user_id"])
        
        # Calculate similarities
        similarities = []
        for similar_user_id in similar_users:
            similarity = await self.calculate_user_similarity(user_id, similar_user_id)
            if similarity > self.similarity_threshold:
                similarities.append((similar_user_id, similarity))
        
        # Sort by similarity and limit
        similarities.sort(key=lambda x: x[1], reverse=True)
        result = similarities[:limit]
        
        # Cache result for 1 hour
        await self.redis_client.setex(cache_key, 3600, json.dumps(result))
        
        return result
    
    async def get_collaborative_recommendations(
        self, 
        user_id: str, 
        exclude_businesses: Optional[Set[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get collaborative filtering recommendations for a user."""
        await self.connect()
        
        similar_users = await self.find_similar_users(user_id, limit=20)
        if not similar_users:
            return []
        
        user_interactions = await self.get_user_interactions(user_id)
        user_businesses = {inter["business_id"] for inter in user_interactions}
        
        # Collect recommendations from similar users
        recommendations = defaultdict(float)
        business_details = {}
        
        for similar_user_id, similarity_score in similar_users:
            similar_interactions = await self.get_user_interactions(similar_user_id)
            
            for interaction in similar_interactions:
                business_id = interaction["business_id"]
                
                # Skip if user already interacted with this business
                if business_id in user_businesses:
                    continue
                
                # Skip if business is in exclude list
                if exclude_businesses and business_id in exclude_businesses:
                    continue
                
                # Weight recommendation by similarity and interaction rating
                weight = similarity_score * interaction["rating"]
                recommendations[business_id] += weight
                
                # Store business details
                business_details[business_id] = {
                    "business_name": interaction["business_name"],
                    "category": interaction["category"],
                    "tags": json.loads(interaction.get("tags", "[]"))
                }
        
        # Sort recommendations by score
        sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
        
        # Format results
        results = []
        for business_id, score in sorted_recs[:limit]:
            if business_id in business_details:
                result = business_details[business_id].copy()
                result.update({
                    "business_id": business_id,
                    "recommendation_score": round(score, 3),
                    "recommendation_type": "collaborative_filtering"
                })
                results.append(result)
        
        return results
    
    async def get_popular_in_category(
        self, 
        category: str, 
        limit: int = 10,
        days: int = 7
    ) -> List[Dict]:
        """Get popular businesses in a specific category."""
        await self.connect()
        
        # This would require scanning all business interactions
        # For now, return empty list - would need more sophisticated indexing
        return []
    
    async def get_trending_searches(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get trending search queries."""
        await self.connect()
        
        trending = await self.redis_client.zrevrange(POPULAR_SEARCHES_KEY, 0, limit-1, withscores=True)
        return [(query, int(score)) for query, score in trending]
    
    async def get_people_also_searched(self, query: str, limit: int = 5) -> List[str]:
        """Get 'People also searched for' suggestions."""
        await self.connect()
        
        # Find users who searched for this query
        users_with_query = set()
        
        # This is a simplified version - in production you'd want better indexing
        # For now, return popular searches as fallback
        trending = await self.get_trending_searches(limit * 2)
        
        # Filter out the original query and return suggestions
        suggestions = [q for q, _ in trending if q.lower() != query.lower()][:limit]
        
        return suggestions
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences."""
        await self.connect()
        
        prefs_key = USER_PREFERENCES_KEY.format(user_id=user_id)
        prefs_data = await self.redis_client.get(prefs_key)
        
        if prefs_data:
            return UserPreferences.model_validate(json.loads(prefs_data))
        
        return None
    
    async def get_analytics_data(self) -> Dict:
        """Get analytics data for monitoring CF performance."""
        await self.connect()
        
        # Count total interactions
        total_interactions = 0
        unique_users = set()
        unique_businesses = set()
        
        # This is simplified - in production you'd want better analytics tracking
        trending = await self.get_trending_searches(20)
        
        return {
            "total_search_queries": sum(count for _, count in trending),
            "unique_search_terms": len(trending),
            "trending_searches": trending[:10],
            "cache_status": "active"
        }

# Global instance
cf_engine = CollaborativeFilteringEngine()
