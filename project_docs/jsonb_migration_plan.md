# JSONB Migration Plan

## Overview

This document outlines why and when to migrate JSON text columns to PostgreSQL JSONB for video analysis data.

## Current State

**JSON Data Storage:**

- `pose_detections.pose_data` - Text column storing JSON string
- `pose_detections.confidence_scores` - Text column storing JSON string
- `pose_detections.visibility_scores` - Text column storing JSON string
- `ball_detections.detection_data` - Text column storing JSON string
- `ball_detections.confidence_scores` - Text column storing JSON string

**Current Approach:**

- Store JSON as `Text` (SQLite/PostgreSQL compatible)
- Serialize with `json.dumps()` before saving
- Deserialize with `json.loads()` after loading
- Load entire JSON string into Python for processing

## Why Migrate to JSONB?

### 1. **Query Within JSON Data**

**Current Limitation:**

```python
# Must load entire JSON, parse in Python, then filter
pose_detection = db.query(PoseDetection).filter(PoseDetection.video_id == video_id).first()
pose_data = json.loads(pose_detection.pose_data)  # Load entire dataset
filtered = [frame for frame in pose_data if frame['confidence'] > 0.8]  # Filter in Python
```

**With JSONB:**

```python
# Query directly in database
frames = db.query(PoseDetection).filter(
    PoseDetection.pose_data['frames'].op('@>')({'confidence': {'$gt': 0.8}})
).all()
```

**Benefits:**

- Filter large datasets in database (faster)
- Reduce memory usage (don't load unnecessary data)
- Complex queries possible (aggregations, joins on JSON fields)

### 2. **Index JSON Fields**

**Current Limitation:**

- Cannot index JSON content
- Full table scans for JSON queries
- Slow performance on large datasets

**With JSONB:**

```sql
-- Create GIN index on JSONB column
CREATE INDEX idx_pose_data_confidence ON pose_detections
USING GIN (pose_data jsonb_path_ops);

-- Fast queries on indexed JSON
SELECT * FROM pose_detections
WHERE pose_data @> '{"average_confidence": {"$gt": 0.8}}';
```

**Benefits:**

- 10-100x faster queries on JSON fields
- Index specific JSON paths
- Support for complex JSON queries

### 3. **Partial Updates**

**Current Limitation:**

```python
# Must load, modify, serialize, save entire JSON
pose_data = json.loads(pose_detection.pose_data)
pose_data['frames'][100]['confidence'] = 0.95
pose_detection.pose_data = json.dumps(pose_data)
db.commit()
```

**With JSONB:**

```sql
-- Update single JSON field without loading entire document
UPDATE pose_detections
SET pose_data = jsonb_set(pose_data, '{frames,100,confidence}', '0.95')
WHERE id = 123;
```

**Benefits:**

- Update single fields without loading entire JSON
- Atomic updates
- Better concurrency (less locking)

### 4. **JSON Aggregations**

**Current Limitation:**

- Must load all records, parse JSON, aggregate in Python
- Memory intensive for large datasets

**With JSONB:**

```sql
-- Aggregate JSON data directly in database
SELECT
  video_id,
  jsonb_agg(pose_data->'keypoints') as all_keypoints,
  avg((pose_data->>'confidence')::float) as avg_confidence
FROM pose_detections
GROUP BY video_id;
```

**Benefits:**

- Database-level aggregations (faster)
- Less memory usage
- Complex analytics possible

## When to Migrate

### Immediate Need (Next 2-3 Weeks)

**Trigger**: Deep video analysis implementation

**Requirements:**

- Query pose data by confidence thresholds
- Filter frames by keypoint visibility
- Aggregate statistics across multiple videos
- Search for specific pose patterns in JSON data

**Example Use Cases:**

- "Find all videos where player's elbow angle > 90 degrees"
- "Get average confidence scores for all forehand strokes"
- "Find frames with specific pose keypoint patterns"

### Migration Checklist

- [ ] Identify all JSON text columns to migrate
- [ ] Create migration script to convert Text → JSONB
- [ ] Update SQLAlchemy models (Text → JSONB type)
- [ ] Update service layer (remove json.loads/dumps where possible)
- [ ] Add JSONB indexes for common queries
- [ ] Test queries on sample data
- [ ] Update API endpoints if needed
- [ ] Document new query patterns

## Migration Strategy

### Step 1: Add JSONB Column (Non-Breaking)

```python
# Migration: Add new JSONB column alongside Text column
def upgrade():
    op.add_column('pose_detections',
        sa.Column('pose_data_jsonb', postgresql.JSONB, nullable=True))

    # Copy data from Text to JSONB
    op.execute("""
        UPDATE pose_detections
        SET pose_data_jsonb = pose_data::jsonb
        WHERE pose_data IS NOT NULL
    """)
```

### Step 2: Update Application Code

```python
# Update model
class PoseDetection(Base):
    pose_data = Column(Text, nullable=True)  # Keep for compatibility
    pose_data_jsonb = Column(postgresql.JSONB, nullable=True)  # New column

    # Add property for backward compatibility
    @property
    def pose_data_dict(self):
        if self.pose_data_jsonb:
            return self.pose_data_jsonb
        return json.loads(self.pose_data) if self.pose_data else None
```

### Step 3: Migrate Data Gradually

- Write to both columns during transition
- Read from JSONB when available, fallback to Text
- Monitor for issues

### Step 4: Remove Text Column (Breaking)

```python
# Migration: Remove Text column after full migration
def upgrade():
    op.drop_column('pose_detections', 'pose_data')
    op.rename_column('pose_detections', 'pose_data_jsonb', 'pose_data')
```

## Caveats & Considerations

### 1. **SQLite Compatibility**

**Problem**: JSONB is PostgreSQL-only, SQLite doesn't support it

**Solution**:

- Use SQLAlchemy's `JSON` type (works on both)
- Or use conditional column types based on database
- For local dev, keep Text or use SQLite's JSON1 extension

**Code Example:**

```python
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB

# Conditional type based on database
if settings.database_url.startswith('postgresql'):
    pose_data = Column(JSONB, nullable=True)
else:
    pose_data = Column(Text, nullable=True)  # SQLite fallback
```

### 2. **Data Migration Complexity**

**Challenge**: Converting existing Text JSON to JSONB

**Considerations:**

- Validate all JSON strings are valid before migration
- Handle malformed JSON gracefully
- Test migration on copy of production data first
- Plan for downtime if large dataset

### 3. **Query Syntax Differences**

**Learning Curve**: JSONB query syntax is different

**Resources:**

- PostgreSQL JSONB documentation
- SQLAlchemy JSONB query examples
- Test queries thoroughly before production

### 4. **Index Maintenance**

**Overhead**: GIN indexes on JSONB can be large

**Considerations:**

- Index only frequently queried paths
- Monitor index size
- Rebuild indexes periodically if needed

### 5. **Backward Compatibility**

**Challenge**: Supporting both Text and JSONB during transition

**Solution:**

- Dual-write during migration period
- Read from JSONB with Text fallback
- Gradual migration approach

## Recommended Approach

### Phase 1: Preparation (Before Deep Analysis)

1. **Research JSONB query patterns** for your use cases
2. **Design indexes** based on expected queries
3. **Create test migration** on sample data
4. **Update models** to support both Text and JSONB

### Phase 2: Implementation (During Deep Analysis Development)

1. **Add JSONB columns** alongside Text (non-breaking)
2. **Update write paths** to write to both columns
3. **Update read paths** to prefer JSONB, fallback to Text
4. **Add JSONB indexes** for new queries

### Phase 3: Migration (After Deep Analysis Stable)

1. **Migrate existing data** from Text to JSONB
2. **Verify data integrity**
3. **Update all queries** to use JSONB
4. **Remove Text columns** (breaking change, version bump)

## Example: Query Patterns After Migration

### Before (Text Column):

```python
# Load all, filter in Python
pose_detections = db.query(PoseDetection).filter(
    PoseDetection.video_id == video_id
).all()

high_confidence_frames = []
for pd in pose_detections:
    data = json.loads(pd.pose_data)
    for frame in data.get('frames', []):
        if frame.get('confidence', 0) > 0.8:
            high_confidence_frames.append(frame)
```

### After (JSONB Column):

```python
# Query directly in database
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

high_confidence_frames = db.query(
    func.jsonb_array_elements(
        PoseDetection.pose_data_jsonb['frames']
    ).alias('frame')
).filter(
    func.cast(
        func.jsonb_extract_path_text('frame', 'confidence'),
        sa.Float
    ) > 0.8
).all()
```

## Conclusion

**Migrate to JSONB when:**

- ✅ You need to query within JSON data
- ✅ You need to index JSON fields for performance
- ✅ You're doing deep analysis with complex queries
- ✅ You have large JSON datasets (>1000 records)

**Don't migrate if:**

- ❌ You only store/retrieve entire JSON documents
- ❌ You're using SQLite for local development
- ❌ Your JSON data is small and simple
- ❌ You don't need JSON-specific queries

**For this project**: Migrate when implementing deep video analysis (next 2-3 weeks) to enable efficient querying of pose and detection data.

---

**Last Updated**: 2024-12-29  
**Status**: Planning Document - Implementation Pending
