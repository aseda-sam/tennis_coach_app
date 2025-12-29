# Authentication & Authorization Overview

## Overview

This document provides a high-level overview of the authentication and authorization system for the Tennis Coach App.

## Architecture

The application uses **Supabase Auth** for authentication. The frontend handles user login/registration, and the backend verifies tokens on protected endpoints.

**Local Development**: Authentication can be conditionally disabled for local development.

---

## Phase 1: Core Authentication ✅ COMPLETED

### Database Schema

- Users are stored in Supabase's `auth.users` table automatically
- `videos.user_id` - UUID, NOT NULL, indexed
- `players.user_id` - UUID, NOT NULL, indexed

### Backend Implementation

- Token verification helper
- `get_current_user` dependency for protected routes
- Video upload endpoint requires authentication
- Player creation endpoint requires authentication

### Frontend Implementation

- Supabase client configuration
- Auth state management hook

---

## Phase 2: Authorization (In Progress)

### Authorization Rules

**Admin Access:**
- Admin can access everything (bypass all ownership checks)
- Check via Supabase user metadata

**Video Access:**
- Users can only see their own videos
- Users can only delete their own videos
- Users can only create ball contacts for their own videos
- Users can only start analysis on their own videos

**Player Ownership:**
- Players belong to users
- Users can only see their own players
- Users can only create players for themselves
- Video owner can tag players they created to their videos

**Ball Contacts:**
- Only video owner can create/update/delete
- Can tag any player (for opponent analysis)

### Implementation Status

**✅ Completed:**
- Authorization helper functions created
- All permission checking functions implemented

**🔄 In Progress:**
- Adding auth to all video endpoints
- Adding auth to all player endpoints
- Adding auth to all ball contact endpoints
- Adding auth to video-player association endpoints
- Adding auth to analysis endpoints

---

## Security Best Practices

**Supabase handles automatically:**
- Password hashing (bcrypt)
- JWT token management
- Rate limiting on auth endpoints
- Email verification (optional)
- Password reset flows

**Application responsibilities:**
- Verify tokens on every protected endpoint
- Use HTTPS in production
- Validate all inputs
- Log security events (future enhancement)

---

## Environment Variables

```bash
# Supabase (required)
SUPABASE_URL=https://your-project.supabase.co/
SUPABASE_SECRET_KEY=your-secret-key

# Frontend (required)
REACT_APP_SUPABASE_URL=https://your-project.supabase.co/
REACT_APP_SUPABASE_PUBLISHABLE_KEY=your-publishable-key

# Optional: Disable auth for local development
ENVIRONMENT=development
REQUIRE_AUTH=false  # Set to true to require auth even in dev
```

---

## Testing Strategy

### Unit Tests ✅
- Authorization checks (tests exist)

### Integration Tests (TODO)
- Register flow
- Login flow
- Protected endpoint access
- Authorization enforcement

---

## Future Enhancements (Not in Current Scope)

- Email verification
- Password reset flow
- Two-factor authentication (2FA)
- OAuth providers (Google, GitHub, etc.)
- Rate limiting
- Audit logging
- Row Level Security (RLS) policies

---

**Last Updated:** 2024-12-29  
**Status:** Phase 1 Complete, Phase 2 Authorization Utilities Complete  
**Next Steps:** Add auth and authorization checks to all API endpoints
