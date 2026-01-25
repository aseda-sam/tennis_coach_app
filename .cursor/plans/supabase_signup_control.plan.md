---
name: Supabase Signup Control
overview: Prevent random users from creating accounts by disabling public signups in Supabase. For hobby projects where manual user validation is preferred. Requires no code changes - just dashboard configuration.
todos:
  - id: disable-email-signups
    content: Disable email signups in Supabase dashboard (Authentication → Settings)
    status: pending
  - id: test-signup-disabled
    content: Test that signup attempts fail with appropriate error message
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
**Context:** Hobby project where manual user validation is preferred

---

## Overview

By default, Supabase allows anyone to sign up via the authentication API. For hobby projects or applications where you want to control who can access the system, you can disable public signups and manually create users through the Supabase dashboard.

---

## How to Disable Signups

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

With signups disabled:

- The signup form in the frontend will still exist (if not hidden)
- Attempting to sign up will return an error like: `"Signups are disabled"` or `"Email signup is disabled"`
- Existing users can still sign in normally
- Password reset functionality still works (if enabled)

### Optional: Hide Signup UI

If you want to hide the signup form entirely, you can:

1. Conditionally render the signup component based on an environment variable
2. Show a message like "Signups are currently disabled. Please contact the administrator."
3. Remove the signup route/page entirely

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

- **Email confirmation:** Can be disabled in Authentication → Settings → Email Auth
- **Password reset:** Can be enabled/disabled separately from signups
- **OAuth providers:** Can be enabled/disabled independently (Google, GitHub, etc.)

---

## Notes

- Disabling signups only affects the signup API. Existing users and sign-in functionality are unaffected.
- You can re-enable signups at any time through the dashboard.
- Manual user creation is immediate - no email confirmation needed if "Auto Confirm User" is checked.
