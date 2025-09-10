# Tag Players in Ball Contact - Feature Plan

**Issue**: [#90 - Tag Players in Ball Contact](https://github.com/aseda-sam/tennis_coach_app/issues/90)  
**Branch**: `feature/tag-players-in-ball-contact`  
**Created**: 2025-01-27

## Overview

This feature will enable tagging players in ball contact events, allowing for player-specific analysis and progress tracking over multiple videos. The implementation includes creating a Player model, updating the BallContact model to reference players, and building API endpoints for player management and progress analytics.

## Goals

1. **Player Management**: Create a Player model to store player information including handedness
2. **Ball Contact Tagging**: Associate ball contacts with specific players
3. **Progress Tracking**: Provide API endpoints for player progress analytics over multiple videos

## Technical Requirements

### Database Changes

#### 1. Player Model

```python
class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    dominant_hand = Column(String(10), nullable=False)  # 'left', 'right' - the hand typically used for hitting
    backhand_style = Column(String(20), nullable=False)  # 'one_handed', 'two_handed'
    height = Column(Float, nullable=True)  # in cm
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)

    # Relationships
    ball_contacts = relationship("BallContact", back_populates="player")
```

#### 2. BallContact Model Updates

```python
# Add to existing BallContact model
player_id = Column(Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True)
player = relationship("Player", back_populates="ball_contacts")
```

### API Endpoints

#### Player Management API

- `POST /api/players/` - Create a new player
- `GET /api/players/` - List all players (with pagination and filtering)
- `GET /api/players/{player_id}` - Get player details
- `PUT /api/players/{player_id}` - Update player information
- `DELETE /api/players/{player_id}` - Delete player (with cascade handling)

#### Ball Contact API Updates

- Update existing ball contact endpoints to include player information
- `POST /api/ball-contacts/` - Add player_id to creation
- `PUT /api/ball-contacts/{ball_contact_id}` - Allow updating player assignment
- `GET /api/ball-contacts/player/{player_id}` - Get all ball contacts for a specific player

### Database Migration Strategy

1. **Create Player table**
2. **Add player_id column to ball_contacts table**
3. **Create indexes for performance**
4. **Add foreign key constraints**
5. **Data migration script for existing ball contacts** (optional player assignment)

### Implementation Phases

#### Phase 1: Backend Foundation

- [ ] Create Player model
- [ ] Update BallContact model
- [ ] Create database migration
- [ ] Implement Player API endpoints
- [ ] Update BallContact API endpoints
- [ ] Write backend tests

### API Schema Examples

#### Player Schemas

```python
class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    dominant_hand: Literal["left", "right"] = Field(..., description="The hand typically used for hitting")
    backhand_style: Literal["one_handed", "two_handed"] = Field(..., description="Backhand playing style")
    height: Optional[float] = Field(None, gt=0, description="Height in cm")
    notes: Optional[str] = None

class PlayerInfo(BaseModel):
    id: int
    name: str
    dominant_hand: str
    backhand_style: str
    height: Optional[float]
    notes: Optional[str]
    ball_contact_count: int
    created_at: datetime
    updated_at: Optional[datetime]

class PlayerProgress(BaseModel):
    player_id: int
    metric: str  # 'accuracy', 'consistency', 'power', etc.
    values: List[float]
    timestamps: List[datetime]
    trend: str  # 'improving', 'declining', 'stable'
```

#### Updated BallContact Schemas

```python
class BallContactCreate(BaseModel):
    # ... existing fields ...
    player_id: Optional[int] = None

class BallContactInfo(BaseModel):
    # ... existing fields ...
    player_id: Optional[int] = None
    player: Optional[PlayerInfo] = None
```

### Testing Strategy

#### Backend Tests

- Unit tests for Player model and service functions
- Integration tests for Player API endpoints
- Tests for BallContact updates with player relationships
- Database migration tests
- Performance tests for analytics queries

### Performance Considerations

1. **Database Indexing**

   - Index on player_id in ball_contacts table
   - Composite indexes for common query patterns
   - Consider partitioning for large datasets

2. **Caching Strategy**

   - Cache player information for frequently accessed players
   - Cache progress analytics with TTL
   - Implement cache invalidation on data updates

3. **Query Optimization**
   - Use efficient joins for player-ball contact queries
   - Implement pagination for large result sets
   - Consider materialized views for complex analytics

### Security Considerations

1. **Data Privacy**

   - Ensure player data is properly protected
   - Implement proper access controls
   - Consider data anonymization for analytics

2. **Input Validation**
   - Validate all player input data
   - Sanitize user-provided content
   - Implement rate limiting for API endpoints

### Future Enhancements

1. **Advanced Analytics**

   - Machine learning-based performance predictions
   - Comparative analysis with similar players
   - Automated coaching recommendations

2. **Social Features**

   - Player profiles and sharing
   - Coach-player relationships
   - Team management

3. **Integration Features**
   - Import/export player data
   - Integration with external coaching platforms
   - Mobile app support

## Success Metrics

1. **Functionality**

   - Players can be created and managed successfully
   - Ball contacts can be tagged with players
   - Progress tracking provides meaningful insights

2. **Performance**

   - API response times < 200ms for standard operations
   - Progress analytics load within 2 seconds
   - Database queries optimized for large datasets

3. **User Experience**
   - Intuitive player management interface
   - Seamless ball contact tagging workflow
   - Clear and actionable progress visualizations

## Dependencies

- Existing BallContact model and API
- Database migration system (Alembic)
- Frontend charting library (to be selected)
- Authentication/authorization system (if applicable)

## Risks and Mitigation

1. **Data Migration Complexity**

   - Risk: Existing ball contacts without players
   - Mitigation: Graceful handling with optional player assignment

2. **Performance Impact**

   - Risk: Additional joins affecting query performance
   - Mitigation: Proper indexing and query optimization

## Timeline Estimate

- **Phase 1 (Backend Foundation)**: 2-3 weeks

**Total Estimated Time**: 2-3 weeks

---

_This document will be updated as the implementation progresses and requirements evolve._
