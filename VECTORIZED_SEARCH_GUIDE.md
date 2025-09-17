# 🧠 Vectorized Search System Guide

## How Vectorized Search Works

### 1. **Data Flow**
```
Business Registration → CSV File → Pathway Indexing → Vector Embeddings → Search
```

1. **Registration**: Business data is added to `data/data.csv`
2. **Auto-Indexing**: Pathway automatically detects file changes and processes the CSV
3. **Vectorization**: Each row is converted to embeddings using OpenAI's text-embedding model
4. **Storage**: Embeddings stored in Pathway's vector index with metadata
5. **Search**: User queries are vectorized and matched against business embeddings

### 2. **Search Process**

#### **Vectorized Search (Primary Method)**
```python
# Step 1: User query "coffee shops near me"
query = "coffee shops near me"

# Step 2: Query enhancement with location context
enhanced_query = f"{query} cafe coffee espresso"

# Step 3: Vector similarity search via Pathway
pathway_response = requests.post("/v1/retrieve", {
    "query": enhanced_query,
    "k": 50  # Get many results for location filtering
})

# Step 4: Parse business data from vectorized chunks
businesses = parse_business_from_text(chunk["text"])

# Step 5: Apply location filtering (distance calculation)
nearby_businesses = filter_by_distance(businesses, user_lat, user_lng, radius)

# Step 6: Hybrid ranking: 70% relevance + 30% distance
sorted_results = sort_by_relevance_and_distance(nearby_businesses)
```

#### **Fallback CSV Search (Backup Method)**
If Pathway is unavailable, the system automatically falls back to direct CSV file processing with basic text matching.

### 3. **Advantages of Vectorized Search**

#### **Semantic Understanding**
- **Query**: "coffee shops" 
- **Finds**: "cafe", "espresso bar", "coffee house", "coffee shop"
- **Why**: Vector embeddings capture semantic meaning, not just exact text

#### **Fuzzy Matching**
- **Query**: "italian food"
- **Finds**: "Italian Restaurant", "Pizza Place", "Pasta Bar"
- **Why**: AI understands food categories and cuisine types

#### **Multi-language Support**
- **Query**: "restaurant"
- **Finds**: "restaurante", "ristorante" (if in data)
- **Why**: Embeddings can capture cross-language similarities

#### **Context Awareness**
- **Query**: "car service"
- **Finds**: "Auto Repair", "Gas Station", "Car Wash"
- **Why**: AI understands related business types

### 4. **Ranking Algorithm**

Results are ranked using a hybrid approach:

```python
def calculate_score(business):
    vector_score = business["vector_score"]  # Lower = more relevant
    distance_km = business["distance_km"]    # Lower = closer
    max_distance = user_max_distance
    
    # Normalize scores (0-1 scale, lower is better)
    relevance_score = vector_score
    distance_score = distance_km / max_distance
    
    # Weighted combination: 70% relevance, 30% distance
    final_score = 0.7 * relevance_score + 0.3 * distance_score
    return final_score
```

### 5. **Search Performance**

#### **Vectorized Search Benefits**
- ✅ **Semantic matching**: Understands meaning beyond keywords
- ✅ **Better recall**: Finds relevant businesses even with different terminology
- ✅ **AI ranking**: Uses machine learning to rank relevance
- ✅ **Real-time**: Updates automatically as new businesses are added

#### **Performance Characteristics**
- **Latency**: ~1-3 seconds (includes Pathway API call + processing)
- **Accuracy**: High semantic relevance + precise distance calculations
- **Scalability**: Pathway handles thousands of businesses efficiently
- **Reliability**: Automatic fallback to CSV search if needed

### 6. **Configuration Options**

#### **In `app.yaml`**
```yaml
# Embedding model (affects search quality)
$embedder: !pw.xpacks.llm.embedders.OpenAIEmbedder
  model: "text-embedding-3-small"  # Recommended upgrade

# Search results count
question_answerer: !pw.xpacks.llm.question_answering.SummaryQuestionAnswerer
  search_topk: 8  # More results = better location filtering
```

#### **In Search Request**
```json
{
  "query": "coffee shops",
  "user_lat": 37.7749,
  "user_lng": -122.4194,
  "max_distance_km": 10.0,
  "limit": 20
}
```

### 7. **API Endpoints**

#### **Primary: Vectorized Search**
```bash
POST /search-businesses
{
  "query": "italian restaurants",
  "user_lat": 37.7749,
  "user_lng": -122.4194,
  "max_distance_km": 5.0
}
```

#### **Fallback: CSV-Only Search**
```bash
POST /search-businesses-csv
# Same parameters, but uses only CSV file processing
```

### 8. **Troubleshooting**

#### **No Results from Vectorized Search**
1. **Check Pathway status**: `/health` endpoint shows Pathway connectivity
2. **Verify indexing**: Use `/v2/list_documents` to confirm CSV is indexed
3. **Try broader queries**: "business" instead of specific terms
4. **Check distance**: Increase `max_distance_km`

#### **Poor Search Quality**
1. **Improve data quality**: Add more descriptive business tags
2. **Use better categories**: Standardize business categories
3. **Upgrade embedding model**: Use `text-embedding-3-small` or `text-embedding-3-large`
4. **Adjust ranking weights**: Modify the 70/30 relevance/distance ratio

#### **System Falls Back to CSV**
- **Pathway offline**: Check if Pathway API is running on port 8000
- **Indexing delayed**: Wait 1-2 minutes after adding new businesses
- **API connectivity**: Verify network connection between services

### 9. **Example Search Scenarios**

#### **Scenario 1: Coffee Search**
```json
// Query: "coffee near me"
// Location: San Francisco (37.7749, -122.4194)
// Radius: 5km

// Vectorized Results:
[
  {
    "business_name": "Blue Bottle Coffee",
    "category": "Cafe", 
    "distance_km": 1.2,
    "relevance": 95%,
    "vector_score": 0.05
  },
  {
    "business_name": "The Coffee Bar",
    "category": "Coffee Shop",
    "distance_km": 2.1,
    "relevance": 92%,
    "vector_score": 0.08
  }
]
```

#### **Scenario 2: Food Search**
```json
// Query: "italian food"
// Results include: "Italian Restaurant", "Pizza Place", "Pasta Bar"
// Why: AI understands cuisine relationships
```

#### **Scenario 3: Service Search**
```json
// Query: "car repair"
// Results include: "Auto Service", "Garage", "Mechanic Shop"
// Why: Vector embeddings capture service type semantics
```

### 10. **Best Practices**

#### **For Business Registration**
- Use **descriptive categories**: "Italian Restaurant" vs "Restaurant"
- Add **comprehensive tags**: "wifi,parking,outdoor-seating,takeout"
- Ensure **accurate coordinates**: Use GPS or geocoding services

#### **For Search Queries**
- Use **natural language**: "coffee shops with wifi" vs "cafe wifi"
- Be **specific when needed**: "mexican restaurant" vs "food"
- Try **variations**: "car service" and "auto repair" may yield different results

#### **For System Optimization**
- **Monitor performance**: Check `/health` endpoint regularly
- **Update embeddings**: Restart Pathway after significant data changes
- **Tune parameters**: Adjust search radius and result limits based on usage

### 11. **Future Enhancements**

#### **Planned Improvements**
- **Reranking**: Add cross-encoder models for final result ordering
- **Query expansion**: Automatically add synonyms and related terms
- **User feedback**: Learn from click-through rates to improve ranking
- **Caching**: Cache frequent searches for faster response times
- **Personalization**: Adapt results based on user preferences

#### **Advanced Features**
- **Multi-modal search**: Include images of businesses in embeddings
- **Temporal awareness**: Consider business hours and seasonal availability
- **Social signals**: Incorporate reviews and ratings into ranking
- **Route optimization**: Order results by travel time, not just distance
