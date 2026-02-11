## What this is

This folder vendors a **curated subset** of Supabase's `supabase-postgres-best-practices` agent skill reference docs, intended to be immediately useful for day-to-day backend work (indexes, pooling, RLS, locking, EXPLAIN).

## Upstream source

- **Skill repo**: `https://github.com/supabase/agent-skills/tree/main/skills/supabase-postgres-best-practices`
- **Full reference docs**: `https://github.com/supabase/agent-skills/tree/main/skills/supabase-postgres-best-practices/references`

If you want the *entire* upstream `references/` set, you can copy additional `.md` files from upstream into this directory later (we kept the initial vendored set intentionally small to avoid repo bloat).

## Included files (initial set)

- `query-missing-indexes.md`
- `query-composite-indexes.md`
- `schema-foreign-key-indexes.md`
- `conn-pooling.md`
- `conn-limits.md`
- `security-rls-basics.md`
- `lock-short-transactions.md`
- `monitor-explain-analyze.md`
