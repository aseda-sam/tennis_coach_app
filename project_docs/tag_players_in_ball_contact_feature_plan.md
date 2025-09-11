# Tag Players in Ball Contact - Feature Plan

**Issue**: [#90 - Tag Players in Ball Contact](https://github.com/aseda-sam/tennis_coach_app/issues/90)  
**Branch**: `feature/tag-players-in-ball-contact`  
**Status**: ✅ **COMPLETED**  
**Created**: 2025-01-27  
**Completed**: 2025-09-11

## Overview

This feature will enable tagging players in ball contact events, allowing for player-specific analysis across videos. The implementation includes creating a Player model, updating the BallContact model to reference players, and building API endpoints for player management.

## Goals

1. **Player Management**: Create a Player model to store player information including handedness
2. **Ball Contact Tagging**: Associate ball contacts with specific players

## Technical Requirements

### Database Changes

#### 1. Player Model

```python
class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    dominant_hand = Column(String(10), nullable=False)  # 'left', 'right' - the hand typically used for hitting
    backhand_style = Column(String(20), nullable=True)  # 'one_handed', 'two_handed'
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
3. **Add foreign key constraints**
4. **Data migration script for existing ball contacts** (optional player assignment)

### Implementation Tasks

- [x] Create Player model
- [x] Update BallContact model
- [x] Create database migration
- [x] Implement Player API endpoints
- [x] Update BallContact API endpoints
- [x] Write backend tests
- [x] Make backhand_style optional (additional migration)

### API Schema Examples

#### Player Schemas

```python
class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    dominant_hand: Literal["left", "right"] = Field(..., description="The hand typically used for hitting")
    backhand_style: Optional[Literal["one_handed", "two_handed"]] = Field(None, description="Backhand playing style")
    height: Optional[float] = Field(None, ge=95, le=250, description="Height in cm (95-250cm range for children 4+ to adults)")
    notes: Optional[str] = None

class PlayerInfo(BaseModel):
    id: int
    name: str
    dominant_hand: str
    backhand_style: Optional[str]
    height: Optional[float]
    notes: Optional[str]
    ball_contact_count: int
    created_at: datetime
    updated_at: Optional[datetime]
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

## Success Metrics

- Players can be created and managed successfully
- Ball contacts can be tagged with players
- API endpoints work as expected
- Database relationships function correctly

## Implementation Details

### Completed Files

#### Models & Database
- **`app/models/player.py`** - Player SQLAlchemy model with relationships
- **`app/models/ball_contact.py`** - Updated with player_id foreign key 
- **`alembic/versions/4b5bac20565b_*.py`** - Initial migration for Player table and foreign key
- **`alembic/versions/943e05c001f6_*.py`** - Additional migration to make backhand_style nullable

#### API Layer
- **`app/api/schemas/player.py`** - Pydantic schemas for Player operations
- **`app/api/routes/players.py`** - Full CRUD API endpoints for Player management
- **`app/api/routes/ball_contacts.py`** - Updated to support player tagging
- **`app/services/player_service.py`** - Business logic layer for Player operations

#### Testing
- **`tests/test_player_api.py`** - Comprehensive API tests for Player endpoints
- **`tests/test_ball_contact_player_integration.py`** - Integration tests for Player-BallContact relationships
- **`tests/conftest.py`** - Updated for proper test database isolation

### Key Changes Made Post-Implementation

1. **Made `backhand_style` Optional**: 
   - Updated Player model: `backhand_style = Column(String(20), nullable=True)`
   - Updated schemas: `backhand_style: Optional[Literal["one_handed", "two_handed"]]`
   - Created additional migration: `943e05c001f6_make_backhand_style_nullable.py`

2. **Enhanced Height Validation**:
   - Added realistic height range validation: `ge=95, le=250` (95-250cm for children 4+ to adults)
   - Improved field description with range information

3. **Architectural Improvements**:
   - Service layer maintains API-agnostic approach (returns database models only)
   - Error handling follows established patterns (services throw ValueError, routes handle HTTP conversion)
   - DRY principle applied with helper functions for schema conversion

### Database Schema Changes

The implementation required two migrations:
1. **Initial migration** (`4b5bac20565b`): Created Player table and added player_id to ball_contacts
2. **Follow-up migration** (`943e05c001f6`): Made backhand_style nullable for better usability

Both migrations use SQLite batch operations for compatibility.

## Dependencies

- Existing BallContact model and API
- Database migration system (Alembic)

## Risks and Mitigation

1. **Data Migration Complexity**

   - Risk: Existing ball contacts without players
   - Mitigation: Graceful handling with optional player assignment

---

_This document will be updated as the implementation evolves._
