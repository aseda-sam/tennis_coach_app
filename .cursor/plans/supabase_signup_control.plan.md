---
name: Supabase Signup Control
overview: Prevent random users from creating accounts by disabling public signups in Supabase. Only relevant for PROFILE=production where authentication is required. For hobby projects where manual user validation is preferred. Requires no code changes - just dashboard configuration.
todos:
  - id: disable-email-signups
    content: Disable email signups in Supabase dashboard (Authentication → Settings)
    status: pending
  - id: test-signup-disabled
    content: Test that signup attempts fail with appropriate error message (PROFILE=production only)
    status: pending
  - id: hide-signup-ui
    content: Optionally hide signup form in frontend or show disabled message
    status: pending
  - id: document-user-creation
    content: Document manual user creation process for administrators
    status: pending
isProject: false
---

# Supabase Signup Control

**Purpose:** Prevent random users from creating accounts on the application
**Context:** Serve-focused MVP hobby project where manual user validation is preferred
**Profile Context:** Only applies when `PROFILE=production` (auth required). When `PROFILE=local`, authentication is disabled and this plan is not applicable.

---

## Overview

By default, Supabase allows anyone to sign up via the authentication API. For hobby projects or applications where you want to control who can access the system, you can disable public signups and manually create users through the Supabase dashboard.

**Important:** This plan only applies when running with `PROFILE=production`. When `PROFILE=local`, authentication is completely disabled (see `backend/app/core/config.py` - `auth_required` property returns `False` for local profile), so signup control is not relevant.

---

## Profile-Based Authentication

The application uses a **profile-based configuration system** (see `backend/app/core/config.py` and `backend/docs/config.md`):

- **`PROFILE=local`**: Authentication is **disabled** - returns mock user automatically. Supabase signup control is **not applicable**.
- **`PROFILE=production`**: Authentication is **required** - uses Supabase JWT tokens. Signup control **applies here**.

This plan is only relevant when deploying or testing with `PROFILE=production`.

## How to Disable Signups

**Prerequisites:** Ensure your backend is configured with `PROFILE=production` and required Supabase environment variables (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`, etc.)

### Step 1: Access Supabase Dashboard

1. Go to your Supabase project dashboard: https://app.supabase.com
2. Select your project

### Step 2: Disable Email Signups

1. Navigate to **Authentication** → **Settings** (or **Authentication** → **Providers** → **Email**)
2. Find the **"Enable email signup"** toggle or **"Disable signups"** setting
3. **Disable email signups** (toggle OFF) or **Enable "Disable signups"** (toggle ON)

This will prevent the `supabase.auth.signUp()` API from working. Any attempts to sign up through the frontend will fail with an error.

---

## Manual User Creation

After disabling signups, you can manually create users:

### Via Supabase Dashboard

1. Navigate to **Authentication** → **Users**
2. Click **"Add user"** → **"Create new user"**
3. Enter:

- **Email:** User's email address
- **Password:** Temporary password (user can change after first login)
- **Auto Confirm User:** Check this to skip email confirmation

4. Click **"Create user"**

### User Management

- **View users:** Authentication → Users
- **Edit user:** Click on a user to modify email, password, or metadata
- **Delete user:** Click on a user → Delete
- **Reset password:** Click on a user → Reset password

---

## Frontend Behavior

With signups disabled (and `PROFILE=production`):

- The signup form in the frontend will still exist (if not hidden)
- Attempting to sign up will return an error like: `"Signups are disabled"` or `"Email signup is disabled"`
- Existing users can still sign in normally
- Password reset functionality still works (if enabled)
- Frontend auth interceptor (`frontend/src/utils/authInterceptor.ts`) only adds Bearer tokens when `REACT_APP_PROFILE !== 'local'`

### Optional: Hide Signup UI

If you want to hide the signup form entirely, you can:

1. Conditionally render the signup component based on `REACT_APP_PROFILE` environment variable
2. Show a message like "Signups are currently disabled. Please contact the administrator."
3. Remove the signup route/page entirely

**Note:** The frontend already respects the profile system - when `REACT_APP_PROFILE=local`, auth headers are not sent to the backend.

---

## Alternative Approaches

### Email Allowlist (More Complex)

If you want selective signups:

1. Keep signups enabled in Supabase
2. Add backend validation to check emails against an allowlist
3. Automatically delete unapproved users

This requires code changes and is more complex than simply disabling signups.

### Invite-Only System

1. Keep signups disabled
2. Create a custom invite system that generates temporary signup tokens
3. Users can only sign up with a valid invite token

This requires significant code changes and is overkill for most hobby projects.

---

## Recommendation

**For hobby projects:** Simply disable signups in the Supabase dashboard. This approach:

- ✅ Requires no code changes
- ✅ Prevents random signups immediately
- ✅ Allows manual user creation when needed
- ✅ Keeps the application secure
- ✅ Simple to manage

---

## Related Configuration

### Backend Profile System

- **Profile-based auth:** See `backend/app/core/config.py` - `auth_required` property
- **Local development:** Set `PROFILE=local` to disable auth entirely (no Supabase needed)
- **Production:** Set `PROFILE=production` and configure Supabase environment variables
- **Auth dependency:** `backend/app/dependencies/auth.py` returns mock user when `PROFILE=local`

### Supabase Settings

- **Email confirmation:** Can be disabled in Authentication → Settings → Email Auth
- **Password reset:** Can be enabled/disabled separately from signups
- **OAuth providers:** Can be enabled/disabled independently (Google, GitHub, etc.)

### User Data Isolation

All data models include `user_id` fields for proper isolation:

- `videos.user_id` - Videos are scoped to users
- `serve_attempts.user_id` - Serve attempts are scoped to users
- `players.user_id` - Players are scoped to users

When manually creating users, ensure they can access their own data via the `user_id` field.

---

## Notes

- **Profile context:** This plan only applies when `PROFILE=production`. When `PROFILE=local`, authentication is disabled and signup control is not relevant.
- Disabling signups only affects the signup API. Existing users and sign-in functionality are unaffected.
- You can re-enable signups at any time through the dashboard.
- Manual user creation is immediate - no email confirmation needed if "Auto Confirm User" is checked.
- The serve MVP focuses on serve analysis - user accounts are needed to track serve attempts and metrics per user.
