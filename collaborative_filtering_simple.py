"""
Simple collaborative filtering module with graceful fallbacks.
This version handles import issues gracefully and provides basic functionality.
"""
import json
import logging
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

# Setup logger first
logger = logging.getLogger("collaborative_filtering")

# Handle optional imports gracefully
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("numpy not available - using basic similarity calculations")

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

try:
    # Try different redis clients
    try:
        import aioredis
        REDIS_CLIENT = aioredis
        REDIS_AVAILABLE = True
        logger.info("Using aioredis client")
    except (ImportError, TypeError) as e:
        logger.warning(f"aioredis not compatible: {e}")
        try:
            import redis.asyncio as aioredis
            REDIS_CLIENT = aioredis
            REDIS_AVAILABLE = True
            logger.info("Using redis.asyncio client")
        except ImportError:
            import redis
            REDIS_CLIENT = None
            REDIS_AVAILABLE = False
            logger.warning("No async redis client available")
except Exception as e:
    REDIS_AVAILABLE = False
    REDIS_CLIENT = None
    logger.warning(f"Redis clients not available: {e}")

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
    """Simple collaborative filtering engine with graceful fallbacks."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.min_interactions_for_cf = 3
        self.similarity_threshold = 0.1
        self.max_recommendations = 20
        self.enabled = REDIS_AVAILABLE
        
        if not self.enabled:
            logger.warning("Collaborative filtering disabled - Redis not available")
        
    async def connect(self):
        """Initialize Redis connection."""
        if not self.enabled:
            return
            
        if self.redis_client is None:
            try:
                if REDIS_CLIENT:
                    self.redis_client = REDIS_CLIENT.from_url(self.redis_url, decode_responses=True)
                    # Test connection
                    await self.redis_client.ping()
                    logger.info("Connected to Redis successfully")
                else:
                    self.enabled = False
                    logger.warning("No Redis client available")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.enabled = False
                
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
    
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
        if not self.enabled:
            logger.debug("CF disabled - skipping interaction recording")
            return
            
        try:
            await self.connect()
            if not self.redis_client:
                return
            
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
            
        except Exception as e:
            logger.warning(f"Failed to record interaction: {e}")
    
    async def get_collaborative_recommendations(
        self, 
        user_id: str, 
        exclude_businesses: Optional[Set[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get collaborative filtering recommendations for a user."""
        if not self.enabled:
            logger.debug("CF disabled - returning empty recommendations")
            return []
            
        try:
            await self.connect()
            if not self.redis_client:
                return []
            
            # For now, return empty list - full CF implementation would go here
            # This prevents crashes while maintaining the API
            return []
            
        except Exception as e:
            logger.warning(f"Failed to get CF recommendations: {e}")
            return []
    
    async def get_trending_searches(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get trending search queries."""
        if not self.enabled:
            return []
            
        try:
            await self.connect()
            if not self.redis_client:
                return []
            
            trending = await self.redis_client.zrevrange(POPULAR_SEARCHES_KEY, 0, limit-1, withscores=True)
            return [(query, int(score)) for query, score in trending]
            
        except Exception as e:
            logger.warning(f"Failed to get trending searches: {e}")
            return []
    
    async def get_people_also_searched(self, query: str, limit: int = 5) -> List[str]:
        """Get 'People also searched for' suggestions."""
        if not self.enabled:
            return []
            
        try:
            # Simple implementation - return popular searches as suggestions
            trending = await self.get_trending_searches(limit * 2)
            suggestions = [q for q, _ in trending if q.lower() != query.lower()][:limit]
            return suggestions
            
        except Exception as e:
            logger.warning(f"Failed to get people also searched: {e}")
            return []
    
    async def get_analytics_data(self) -> Dict:
        """Get analytics data for monitoring CF performance."""
        if not self.enabled:
            return {
                "status": "disabled",
                "total_search_queries": 0,
                "unique_search_terms": 0,
                "trending_searches": [],
                "cache_status": "unavailable"
            }
            
        try:
            await self.connect()
            if not self.redis_client:
                return {"status": "error", "message": "Redis connection failed"}
            
            trending = await self.get_trending_searches(20)
            
            return {
                "status": "active",
                "total_search_queries": sum(count for _, count in trending),
                "unique_search_terms": len(trending),
                "trending_searches": trending[:10],
                "cache_status": "active"
            }
            
        except Exception as e:
            logger.warning(f"Failed to get analytics data: {e}")
            return {"status": "error", "message": str(e)}

# Global instance
cf_engine = CollaborativeFilteringEngine()
