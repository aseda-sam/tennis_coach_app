# Authentication & Authorization Implementation Plan

## Overview

This document outlines the implementation plan for adding authentication and authorization to the Tennis Coach App using **Supabase Auth**.

## Why Supabase Auth?

- ✅ **Already using Supabase**: Storage and database are on Supabase
- ✅ **Built-in**: No custom password hashing, JWT creation, or user management needed
- ✅ **Simple**: Just verify tokens in FastAPI backend
- ✅ **Local dev friendly**: Can disable auth locally or use Supabase CLI
- ✅ **Migratable**: Can export users and migrate to another system if needed
- ✅ **OAuth ready**: Social login (Google, GitHub) built-in when needed

## Architecture Decision

**Use Supabase Auth** - Frontend handles login/registration, backend verifies tokens.

**Local Development**: Conditional auth - skip in dev, require in production.

---

## Phase 1: Core Authentication ✅ COMPLETED

### 1.1 Database Schema ✅

**Supabase handles user storage** - Users are stored in Supabase's `auth.users` table automatically.

**Tables Updated:**

- ✅ `videos.user_id` - UUID, NOT NULL, indexed
- ✅ `players.user_id` - UUID, NOT NULL, indexed

### 1.2 Backend Implementation ✅

- ✅ `app/utils/supabase_auth.py` - Token verification helper
- ✅ `app/dependencies/auth.py` - `get_current_user` dependency
- ✅ Video upload endpoint requires authentication
- ✅ Player creation endpoint requires authentication

### 1.3 Frontend Implementation ✅

- ✅ `frontend/src/services/supabaseClient.ts` - Supabase client
- ✅ `frontend/src/hooks/useAuth.ts` - Auth state management

---

## Phase 2: Authorization (In Progress)

### 2.1 Authorization Rules

**Admin Access:**

- Admin can access everything (bypass all ownership checks)
- Check via Supabase user metadata (`is_admin` flag)

**Video Access:**

- Users can only see their own videos
- Users can only delete their own videos
- Users can only create ball contacts for their own videos
- Users can only start analysis on their own videos

**Player Ownership:**

- Players belong to users (`players.user_id`)
- Users can only see their own players
- Users can only create players for themselves
- Video owner can tag players they created to their videos (for opponent tracking)

**Ball Contacts:**

- Only video owner can create/update/delete
- Can tag any player (for opponent analysis)

### 2.2 Authorization Utilities ✅ COMPLETED

- ✅ `app/utils/authorization.py` - All authorization helper functions:
  - `is_admin()` - Check admin status
  - `can_access_video()` / `require_video_access()` - Video access control
  - `can_manage_player()` / `require_player_access()` - Player management
  - `can_create_ball_contact_for_video()` / `require_ball_contact_permission()` - Ball contact permissions
  - `can_tag_player_to_video()` / `require_player_tag_permission()` - Player tagging permissions

### 2.3 What's Left to Implement

#### Video Endpoints

- [ ] Add `get_current_user` dependency to all video endpoints:
  - `GET /videos/` - List videos (filter by user_id)
  - `GET /videos/{video_id}` - Get video (check access)
  - `GET /videos/{video_id}/stream` - Stream video (check access)
  - `GET /videos/{video_id}/analysis-status` - Check analysis status (check access)
  - `DELETE /videos/{video_id}` - Delete video (check ownership)
  - `POST /videos/{video_id}/quality-check` - Quality check (check access)
- [ ] Add `require_video_access()` checks to all video endpoints
- [ ] Filter `GET /videos/` to only return user's videos

#### Player Endpoints

- [ ] Add `get_current_user` dependency to all player endpoints:
  - `GET /players/` - List players (filter by user_id)
  - `GET /players/{player_id}` - Get player (check access)
  - `PUT /players/{player_id}` - Update player (check ownership)
  - `DELETE /players/{player_id}` - Delete player (check ownership)
- [ ] Add `require_player_access()` checks to player endpoints
- [ ] Filter `GET /players/` to only return user's players

#### Ball Contact Endpoints

- [ ] Add `get_current_user` dependency to all ball contact endpoints
- [ ] Add `require_ball_contact_permission()` checks:
  - `POST /ball-contacts/` - Create (check video ownership)
  - `PUT /ball-contacts/{id}` - Update (check video ownership)
  - `DELETE /ball-contacts/{id}` - Delete (check video ownership)
- [ ] Filter `GET /ball-contacts/video/{video_id}` to check video access
- [ ] Filter `GET /ball-contacts/player/{player_id}` to check player access

#### Video-Player Association Endpoints

- [ ] Add `get_current_user` dependency to video-player endpoints
- [ ] Add `require_video_access()` and `require_player_tag_permission()` checks:
  - `POST /videos/{video_id}/players/` - Tag player to video
  - `GET /videos/{video_id}/players/` - Get players in video (check video access)
  - `DELETE /videos/{video_id}/players/{player_id}/` - Remove player (check video ownership)

#### Analysis Endpoints

- [ ] Add `get_current_user` dependency to analysis endpoints
- [ ] Add `require_video_access()` checks:
  - `POST /analysis/videos/{video_id}` - Start analysis (check video ownership)
  - `GET /analysis/{analysis_id}` - Get analysis (check video access)

---

## Implementation Status

### ✅ Completed

**Phase 1: Core Authentication**

- ✅ Database schema: `user_id` added to `videos` and `players` tables (NOT NULL)
- ✅ Supabase auth verification helper
- ✅ `get_current_user` dependency
- ✅ Video upload requires authentication
- ✅ Player creation requires authentication
- ✅ Frontend auth setup (Supabase client, useAuth hook)

**Phase 2: Authorization Utilities**

- ✅ Authorization helper functions created
- ✅ All permission checking functions implemented

### 🔄 In Progress / TODO

**Phase 2: Add Authorization to Endpoints**

- [ ] Add auth to all video endpoints (6 endpoints: list, get, stream, analysis-status, delete, quality-check)
- [ ] Add auth to all player endpoints (4 endpoints)
- [ ] Add auth to all ball contact endpoints (11 endpoints)
- [ ] Add auth to video-player association endpoints (4 endpoints)
- [ ] Add auth to analysis endpoints (2+ endpoints)
- [ ] Add authorization checks (require_video_access, require_player_access, etc.)
- [ ] Filter list endpoints by user_id

---

## Security Best Practices

**Supabase handles automatically:**

- ✅ Password hashing (bcrypt)
- ✅ JWT token management
- ✅ Rate limiting on auth endpoints
- ✅ Email verification (optional)
- ✅ Password reset flows

**You need to:**

- ✅ Verify tokens on every protected endpoint
- ✅ Use HTTPS in production
- ✅ Validate all inputs
- ⚠️ Log security events (future enhancement)

---

## Environment Variables

```bash
# Supabase (already configured)
SUPABASE_URL=https://your-project.supabase.co/
SUPABASE_SECRET_KEY=your-secret-key

# Frontend (already configured)
REACT_APP_SUPABASE_URL=https://your-project.supabase.co/
REACT_APP_SUPABASE_PUBLISHABLE_KEY=your-publishable-key

# Optional: Disable auth for local development
ENVIRONMENT=development
REQUIRE_AUTH=false  # Set to true to require auth even in dev
```

---

## Testing Strategy

### Unit Tests ✅

- ✅ Password hashing/verification (Supabase handles)
- ✅ JWT token creation/validation (Supabase handles)
- ✅ Authorization checks (tests exist)

### Integration Tests (TODO)

- [ ] Register flow
- [ ] Login flow
- [ ] Protected endpoint access
- [ ] Authorization enforcement

### Manual Testing (TODO)

- [ ] Register new user
- [ ] Login with credentials
- [ ] Access protected endpoints
- [ ] Try accessing other user's videos (should fail)
- [ ] Test token expiration

---

## Migration Strategy ✅ COMPLETED

### Existing Data

- ✅ SQL script created to assign `user_id` to existing records
- ✅ Migration completed: All existing videos/players assigned to user
- ✅ `user_id` columns are now NOT NULL

---

## Future Enhancements (Not in Current Scope)

- Email verification
- Password reset flow
- Two-factor authentication (2FA)
- OAuth providers (Google, GitHub, etc.)
- Rate limiting
- Audit logging
- Row Level Security (RLS) policies
- Default player suggestion on video upload