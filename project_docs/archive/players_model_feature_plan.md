# Players Model - Feature Plan

**Issue**: [#90 - Tag Players in Ball Contact](https://github.com/aseda-sam/tennis_coach_app/issues/90)  
**Branch**: `feature/players-model`  
**Status**: ✅ **COMPLETED**

## Overview

This feature establishes a comprehensive player management system for the tennis coaching application. It enables tracking individual players across multiple videos, associating them with specific video sessions, and building the foundation for player-specific analytics and progression tracking. The implementation includes creating a Player model, establishing video-player associations, and building API endpoints for complete player lifecycle management.

## Goals

1. **Player Management**: Create a comprehensive Player model to store player information including handedness, physical attributes, and playing style
2. **Video-Player Association**: Enable associating players with specific videos and sessions
3. **Cross-Video Tracking**: Support tracking individual players across multiple videos
4. **Analytics Foundation**: Build the foundation for player-specific analytics, progression tracking, and performance analysis
5. **Workflow Integration**: Integrate player management into the broader tennis coaching workflow

## Technical Requirements

### Database Changes

#### 1. Player Model (✅ COMPLETED)

```python
class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, unique=True)
    dominant_hand = Column(String(10), nullable=False)  # 'left', 'right' - the hand typically used for hitting
    backhand_style = Column(String(20), nullable=True)  # 'one_handed', 'two_handed'
    height = Column(Float, nullable=True)  # in cm
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)

    # Relationships
    ball_contacts = relationship("BallContact", back_populates="player")
```

#### 2. BallContact Model Updates (✅ COMPLETED)

```python
# Add to existing BallContact model
player_id = Column(Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True)
player = relationship("Player", back_populates="ball_contacts")
```

#### 3. VideoPlayer Association Model (🔄 PLANNED)

```python
class VideoPlayer(Base):
    """Junction table for players appearing in specific videos."""
    __tablename__ = "video_players"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    pose_detection_id = Column(Integer, ForeignKey("pose_detections.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    video = relationship("Video", back_populates="video_players")
    player = relationship("Player", back_populates="video_appearances")
    pose_detection = relationship("PoseDetection", back_populates="video_player")

    # Prevent duplicate associations
    __table_args__ = (UniqueConstraint('video_id', 'player_id', name='uq_video_player'),)
```

#### 4. Updated Video Model (🔄 PLANNED)

```python
# Add to existing Video model
class Video(Base):
    # ... existing fields ...

    # New relationships
    video_players = relationship("VideoPlayer", back_populates="video", cascade="all, delete-orphan")

    # Convenience property to get just the players
    @property
    def players(self) -> List[Player]:
        return [vp.player for vp in self.video_players]
```

#### 5. Updated Player Model (🔄 PLANNED)

```python
# Add to existing Player model
class Player(Base):
    # ... existing fields ...

    # New relationships
    video_appearances = relationship("VideoPlayer", back_populates="player")

    # Convenience properties
    @property
    def videos(self) -> List[Video]:
        return [vp.video for vp in self.video_appearances]

    @property
    def total_videos(self) -> int:
        return len(self.video_appearances)
```

### API Endpoints

#### Player Management API (✅ COMPLETED)

- `POST /v0/players/` - Create a new player
- `GET /v0/players/` - List all players (with pagination and filtering)
- `GET /v0/players/{player_id}` - Get player details
- `PUT /v0/players/{player_id}` - Update player information
- `DELETE /v0/players/{player_id}` - Delete player (with cascade handling)

#### Video-Player Association API (🔄 PLANNED)

- `POST /v0/videos/{video_id}/players/{player_id}` - Associate player with video (after pose detection)
- `GET /v0/videos/{video_id}/players/` - List players associated with video
- `PUT /v0/videos/{video_id}/players/{player_id}` - Update player association (change pose detection link)
- `DELETE /v0/videos/{video_id}/players/{player_id}` - Remove player from video

#### Enhanced Player Analytics API (🔄 PLANNED)

- `GET /v0/players/{player_id}/videos/` - List all videos where player appears
- `GET /v0/players/{player_id}/ball-contacts/` - Get all ball contacts across all videos

#### Ball Contact API Updates (✅ COMPLETED + 🔄 ENHANCEMENTS PLANNED)

**Completed:**

- `POST /v0/ball-contacts/` - Add player_id to creation ✅
- `PUT /v0/ball-contacts/{ball_contact_id}` - Allow updating player assignment ✅
- `GET /v0/ball-contacts/player/{player_id}` - Get all ball contacts for a specific player ✅

**Planned Enhancements:**

- `GET /v0/ball-contacts/?video_id={id}&player_id={id}` - Filter ball contacts by video and player
- `GET /v0/videos/{video_id}/player-options` - Get auto-assignment logic for ball contact creation
- Smart ball contact assignment: Auto-assign for single player, manual for multiple
- Bulk update ball contacts: Change player assignment for multiple contacts

### Database Migration Strategy

**Phase 1: Basic Player Model (✅ COMPLETED)**

1. Create Player table ✅
2. Add player_id column to ball_contacts table ✅
3. Add foreign key constraints ✅
4. Make backhand_style nullable (enhancement) ✅

**Phase 2: Video-Player Associations (🔄 PLANNED)** 5. Create VideoPlayer junction table 6. Add relationships to Video and Player models 7. Create database migration

### Implementation Tasks

**Phase 1: Basic Player-BallContact Association (✅ COMPLETED)**

- [x] Create Player model
- [x] Update BallContact model
- [x] Create database migration
- [x] Implement Player API endpoints
- [x] Update BallContact API endpoints
- [x] Write backend tests
- [x] Make backhand_style optional (additional migration)

**Phase 2: Video-Player Association Workflow (🔄 PLANNED)**

- [ ] Create VideoPlayer model
- [ ] Update Video and Player models with relationships
- [ ] Create VideoPlayer migration
- [ ] Implement video-player association API endpoints
- [ ] Implement smart ball contact assignment logic
- [ ] Add player auto-assignment to ball contact creation
- [ ] Add bulk update functionality for ball contact player assignments
- [ ] Write tests for video-player associations and auto-assignment

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

#### Video-Player Association Schemas (🔄 PLANNED)

```python
class VideoPlayerInfo(BaseModel):
    id: int = Field(description="VideoPlayer association ID")
    video_id: int = Field(description="Video ID")
    player_id: int = Field(description="Player ID")
    player: PlayerInfo = Field(description="Player details")
    created_at: datetime = Field(description="When association was created")

    class Config:
        from_attributes = True

class VideoWithPlayers(BaseModel):
    id: int = Field(description="Video ID")
    # ... other video fields ...
    players: List[PlayerInfo] = Field(description="Players appearing in this video")
    total_players: int = Field(description="Number of players in video")
```

## Workflow & User Experience

### Current Workflow (✅ IMPLEMENTED)

1. **Player Database Management**: Create and manage a comprehensive player database with names, handedness, physical attributes, and playing style
2. **Player-Video Association**: Associate players with specific videos and sessions
3. **Cross-Video Player Tracking**: Track individual players across multiple videos and sessions
4. **Player-Specific Analytics**: View all activities and data for a specific player across all videos

### Enhanced Workflow (🔄 PLANNED)

1. **Video Upload**: User uploads video for analysis
2. **Pose Detection**: Run pose detection on video (detects players in video)
3. **Player Association**: User associates detected poses with existing players in the database
4. **Smart Player Assignment**:
   - **Single player in video**: Auto-assign all activities to that player
   - **Multiple players in video**: Show player dropdown for manual selection
   - **No players in video**: Show all players dropdown for manual assignment
5. **Player Progression Tracking**: Track individual player development across multiple videos and sessions
6. **Override Capability**: Always allow changing player assignments as context evolves

### Key Benefits

- **Zero Friction**: Auto-assign activities for single-player videos
- **Smart Defaults**: Automatic assignment when context is clear, manual when needed
- **Player-Centric View**: Track individual player development across multiple videos and sessions
- **Flexible Override**: Always allow changing assignments when context evolves
- **Scalable**: Handles simple and complex video scenarios gracefully
- **Comprehensive Tracking**: Build complete player profiles over time

### Smart Assignment Logic

#### Auto-Assignment Rules

```python
def get_ball_contact_player_options(video_id: int):
    """Determine auto-assignment logic for ball contact creation."""
    video_players = get_players_in_video(video_id)

    if len(video_players) == 1:
        return {
            "auto_assign": video_players[0].player_id,
            "player_name": video_players[0].player.name,
            "options": video_players
        }
    elif len(video_players) > 1:
        return {
            "auto_assign": None,
            "options": video_players,
            "message": "Multiple players in video - select one"
        }
    else:
        return {
            "auto_assign": None,
            "options": get_all_players(),
            "message": "No players assigned to video"
        }
```

#### UI/UX Flow

- **Single player**: "Creating contact for [Player Name] ⚙️ Change"
- **Multiple players**: "Select player: [Video Players Dropdown] ▼"
- **No players**: "Select player: [All Players Dropdown] ▼"
- **Override**: Always show "Change player" option on existing ball contacts

### Testing Strategy

#### Backend Tests (Phase 1: ✅ COMPLETED)

- Unit tests for Player model and service functions
- Integration tests for Player API endpoints
- Tests for BallContact updates with player relationships
- Database migration tests

#### Backend Tests (Phase 2: 🔄 PLANNED)

- Unit tests for VideoPlayer model
- Integration tests for video-player association API
- Tests for smart ball contact assignment logic
- Tests for auto-assignment rules (single/multiple/no players)
- Tests for bulk player assignment updates
- Tests for video-player relationships

## Architecture: Multi-Dimensional Relationships

### Core Relationship Model

```
Player ←→ VideoPlayer ←→ Video
   ↓                        ↓
   └──→ BallContact ←───────┘
```

### Relationship Purposes

#### 1. **Player ↔ BallContact** (Direct, Cross-Video)

- **Purpose**: Long-term progression tracking
- **Use Case**: "Show me John's backhand improvement over 6 months"
- **Query**: `player.ball_contacts` (across ALL videos)

#### 2. **Video ↔ VideoPlayer ↔ Player** (Contextual, Video-Specific)

- **Purpose**: Video-specific workflow and tagging
- **Use Case**: "In today's practice video, who are the players and which shots belong to whom?"
- **Query**: `video.players` or `video.video_players`

#### 3. **BallContact → Video** (Contextual Reference)

- **Purpose**: Link individual contacts back to their video context
- **Use Case**: "This ball contact happened in which video/session?"
- **Query**: `ball_contact.video`

### Why Both Dimensions Matter

- **Temporal Analysis**: Player progression across time (Player → BallContact)
- **Contextual Analysis**: Video-specific player identification (Video → Player → BallContact)
- **Workflow Support**: Efficient tagging and validation within video context
- **Data Integrity**: Ensure tagged players actually appear in the video

## Success Metrics

**Phase 1: Basic Player Tagging (✅ COMPLETED)**

- Players can be created and managed successfully ✅
- Ball contacts can be tagged with players ✅
- API endpoints work as expected ✅
- Database relationships function correctly ✅

**Phase 2: Video-Player Workflow (🔄 PLANNED)**

- Players can be associated with specific videos
- Ball contact creation shows only video-relevant players
- Player validation ensures they appear in the video
- Workflow is intuitive and efficient

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

4. **Player Name Uniqueness**:

   - Enforced uniqueness at the service layer and will enforce at the database level via a unique constraint on `players.name` to prevent duplicates and race conditions.

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

## Next Steps

### Immediate Priority (Phase 2)

1. **Create VideoPlayer Model**: Design and implement the junction table
2. **API Design**: Plan the video-player association endpoints
3. **Migration Strategy**: Handle existing data gracefully
4. **UI/UX Flow**: Design the player tagging workflow

### Implementation Decisions

- Ball contact validation: Recommend player-video associations
- Player creation: Users create players separately first
- API scope: Start with basic POST/GET/PUT/DELETE endpoints
- Model fields: Include pose_detection_id for pose-based associations

## Advanced Features (Future)

### Multi-Player Pose Detection

- Support for multiple players detected in single video
- Pose detection ID tracking for each detected player
- UI for mapping multiple detected poses to different players
- Advanced pose analysis across multiple players

### Pre-Tagging Workflow

- Allow users to pre-tag known players before pose detection
- Automatic pose-to-player mapping when players are pre-tagged
- Bulk player association for videos with known participants

---

_Last Updated: 2025-09-11 - Enhanced with pose detection-based player association workflow_
