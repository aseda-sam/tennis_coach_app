# Auth flow

How we check who you are and what you're allowed to do. Solid arrows = request; dashed = reply. Flows differ by environment (local vs prod).

## Local profile

When `PROFILE=local`, we skip real login and use a fixed test user. No token needed.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#e3f2fd', 'primaryBorderColor':'#1976d2'} }%%
sequenceDiagram
  participant Client
  participant API as FastAPI (/v0)
  participant AuthZ as Access checks

  Client->>API: Request (login token optional)
  API->>API: PROFILE=local → use test user
  API->>AuthZ: Can user use this video / player / …?
  alt allowed
    AuthZ-->>API: ok
    API-->>Client: 2xx response
  else not allowed
    AuthZ-->>API: raise 403
    API-->>Client: 403 Forbidden
  end
```

## Prod / authorized profile

When not local (e.g. production), the API needs a valid login token first, then checks what you're allowed to do.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#e3f2fd', 'primaryBorderColor':'#1976d2'} }%%
sequenceDiagram
  participant Client
  participant API as FastAPI (/v0)
  participant Auth as Check login token
  participant AuthZ as Access checks

  Client->>API: Request with login token
  API->>Auth: Verify token
  alt valid token
    Auth-->>API: user (who you are)
    API->>AuthZ: Can user use this video / player / …?
    alt allowed
      AuthZ-->>API: ok
      API-->>Client: 2xx response
    else not allowed
      AuthZ-->>API: raise 403
      API-->>Client: 403 Forbidden
    end
  else invalid or missing token
    Auth-->>API: None
    API-->>Client: 401 Unauthorized
  end
```

## Notes

- **Local** — No token check; we use a fixed test user (e.g. `dev@localhost`). Access checks (e.g. `require_video_access`, `require_player_access`) still run, so you can get 403.
- **Prod** — Token is verified (e.g. Supabase JWT). Missing/invalid → 401. Then we check permissions (video ownership, player, demo upload, etc.); not allowed → 403.
