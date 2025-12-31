# Alembic Migrations: SQLite vs PostgreSQL Compatibility

## Overview

This document addresses compatibility concerns when using Alembic migrations with both SQLite (local development) and PostgreSQL (production via Supabase).

## Short Answer

**✅ Alembic handles SQLite/PostgreSQL differences well for most operations.**

Your current migrations are compatible. Issues only arise with:

- Database-specific features (JSONB, arrays, custom types)
- Complex constraints (CHECK, EXCLUDE)
- Some ALTER TABLE operations

## Current Migration Patterns

### What Works (Your Current Migrations)

**✅ Basic Operations:**

```python
# Adding columns - works on both
op.add_column("videos", sa.Column("user_id", sa.String(36), nullable=True))

# Creating indexes - works on both
op.create_index("idx_videos_user_id", "videos", ["user_id"])

# Foreign keys - works on both
op.create_foreign_key("fk_video_user", "videos", "users", ["user_id"], ["id"])

# Dropping columns - works on both
op.drop_column("videos", "user_id")
```

**✅ Data Types:**

- `String`, `Integer`, `Float`, `Boolean` - Compatible
- `DateTime`, `Text` - Compatible
- `ForeignKey` relationships - Compatible

**✅ Your Current Schema:**
All your current migrations use compatible operations:

- Adding columns (`user_id`, `quality_score`, etc.)
- Creating indexes
- Foreign key constraints
- Basic data types

## Potential Issues

### 1. **Database-Specific Types**

**Problem**: PostgreSQL-specific types don't work in SQLite

**Examples:**

- `JSONB` (PostgreSQL only)
- `ARRAY` (PostgreSQL only)
- `UUID` (different handling)
- Custom types

**Your Code:**
Currently you use `Text` for JSON, which works on both. ✅ Safe

**If You Add JSONB:**

```python
# This will FAIL on SQLite
from sqlalchemy.dialects.postgresql import JSONB
op.add_column("pose_detections",
    sa.Column("pose_data", JSONB, nullable=True))
```

**Solution:**

```python
# Conditional type based on database
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB

def upgrade():
    # Check database type
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.add_column("pose_detections",
            sa.Column("pose_data", JSONB, nullable=True))
    else:
        op.add_column("pose_detections",
            sa.Column("pose_data", Text, nullable=True))
```

### 2. **ALTER TABLE Limitations in SQLite**

**Problem**: SQLite has limited ALTER TABLE support

**What SQLite CAN'T Do:**

- Rename columns (must recreate table)
- Change column type (must recreate table)
- Drop columns (must recreate table) - **SQLite 3.35.0+ supports this**
- Add CHECK constraints (must recreate table)

**What SQLite CAN Do:**

- Add columns ✅
- Add indexes ✅
- Add foreign keys ✅ (with limitations)

**Your Migrations:**
Currently you only add columns and indexes. ✅ Safe

**If You Need to Rename/Modify:**

```python
# This will FAIL on SQLite
op.alter_column("videos", "filename",
    new_column_name="file_name")  # ❌ SQLite doesn't support

# Workaround: Recreate table
def upgrade():
    with op.batch_alter_table('videos') as batch_op:
        batch_op.alter_column('filename', new_column_name='file_name')
    # Alembic's batch_alter_table handles SQLite limitations
```

### 3. **Constraint Differences**

**Problem**: Some constraints work differently

**CHECK Constraints:**

```python
# PostgreSQL - works
op.create_check_constraint(
    'ck_positive_duration',
    'videos',
    'duration > 0'
)

# SQLite - must be in table creation, not added later
# Workaround: Use batch_alter_table or skip for SQLite
```

**Your Code:**
You don't use CHECK constraints. ✅ Safe

### 4. **Index Creation Differences**

**Problem**: Some index types are PostgreSQL-specific

**Examples:**

- GIN indexes (JSONB) - PostgreSQL only
- Partial indexes - Different syntax
- Expression indexes - Different syntax

**Your Code:**
You use simple indexes. ✅ Safe

**If You Add JSONB Indexes:**

```python
# PostgreSQL GIN index
op.execute("""
    CREATE INDEX idx_pose_data_gin ON pose_detections
    USING GIN (pose_data)
""")

# Must be conditional:
def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("CREATE INDEX ... USING GIN ...")
    # Skip for SQLite
```

## Best Practices

### 1. **Use Alembic's Batch Operations for SQLite**

When you need SQLite-incompatible operations, use batch operations:

```python
def upgrade():
    with op.batch_alter_table('videos') as batch_op:
        batch_op.alter_column('filename', type_=sa.String(500))
        batch_op.drop_column('old_column')
    # Alembic handles SQLite table recreation automatically
```

### 2. **Conditional Logic for Database-Specific Features**

```python
def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'postgresql':
        # PostgreSQL-specific operations
        op.execute("CREATE INDEX ... USING GIN ...")
    elif dialect == 'sqlite':
        # SQLite-specific operations (or skip)
        pass
```

### 3. **Test Migrations on Both Databases**

**Recommended Workflow:**

1. Develop migration with SQLite (local)
2. Test migration on PostgreSQL (Supabase branch)
3. Verify both upgrade and downgrade paths

### 4. **Use Compatible Types When Possible**

**Instead of:**

```python
# PostgreSQL-specific
from sqlalchemy.dialects.postgresql import UUID, ARRAY
```

**Use:**

```python
# Compatible types
sa.String(36)  # For UUIDs
sa.Text  # For arrays (store as JSON string)
```

## Your Current Situation

### ✅ What's Safe

**All your current migrations are compatible:**

- Adding columns (`user_id`, etc.)
- Creating indexes
- Foreign key constraints
- Basic data types (String, Integer, Float, Text, DateTime)

**No changes needed** for current migrations.

### ⚠️ What to Watch For

**If you add these features, handle compatibility:**

1. **JSONB columns** (for deep analysis)

   - Use conditional types
   - See `jsonb_migration_plan.md`

2. **Column renames/modifications**

   - Use `batch_alter_table` for SQLite
   - Test on both databases

3. **Complex constraints**

   - CHECK constraints
   - EXCLUDE constraints (PostgreSQL only)

4. **Advanced indexes**
   - GIN indexes (JSONB)
   - Partial indexes
   - Expression indexes

## Migration Testing Strategy

### Local Development (SQLite)

```bash
# Test migration on SQLite
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### Production Testing (PostgreSQL - Supabase Branch)

```bash
# Set environment to use Supabase branch
export SUPABASE_DB_URL=postgresql://...branch-connection...

# Test migration on PostgreSQL
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### Automated Testing (Recommended)

```python
# tests/test_migrations.py
def test_migration_sqlite():
    # Test on SQLite
    engine = create_engine("sqlite:///:memory:")
    run_migrations(engine)

def test_migration_postgresql():
    # Test on PostgreSQL (if available)
    if os.getenv("TEST_POSTGRES_URL"):
        engine = create_engine(os.getenv("TEST_POSTGRES_URL"))
        run_migrations(engine)
```

## Common Patterns

### Pattern 1: Adding Compatible Column

```python
def upgrade():
    op.add_column("videos",
        sa.Column("new_field", sa.String(100), nullable=True))
    # Works on both SQLite and PostgreSQL ✅
```

### Pattern 2: Adding PostgreSQL-Specific Column

```python
def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import JSONB
        op.add_column("pose_detections",
            sa.Column("pose_data", JSONB, nullable=True))
    else:
        op.add_column("pose_detections",
            sa.Column("pose_data", sa.Text, nullable=True))
```

### Pattern 3: Renaming Column (SQLite-Compatible)

```python
def upgrade():
    with op.batch_alter_table('videos') as batch_op:
        batch_op.alter_column('old_name', new_column_name='new_name')
    # Works on both ✅
```

### Pattern 4: Adding Index (Both Databases)

```python
def upgrade():
    op.create_index("idx_videos_user_id", "videos", ["user_id"])
    # Works on both ✅
```

## Recommendations

### For Your Project

1. **Current migrations**: ✅ No changes needed - all compatible

2. **Future migrations**:

   - Continue using compatible operations when possible
   - Use conditional logic for database-specific features
   - Test on both SQLite and PostgreSQL

3. **JSONB migration** (when needed):

   - Use conditional column types
   - See `jsonb_migration_plan.md` for details

4. **Testing**:
   - Test migrations on SQLite locally
   - Test on Supabase branch before production
   - Verify both upgrade and downgrade paths

### Migration Workflow

```bash
# 1. Develop locally (SQLite)
alembic revision --autogenerate -m "add new feature"
alembic upgrade head  # Test on SQLite

# 2. Test on Supabase branch (PostgreSQL)
# Update .env to use branch connection string
alembic upgrade head  # Test on PostgreSQL

# 3. Deploy to production
# Migrations run automatically or manually
```

## Conclusion

**Your current Alembic setup is compatible** with both SQLite and PostgreSQL.

**No immediate action needed** - your migrations work on both databases.

**When adding new features:**

- Use compatible types when possible
- Use conditional logic for database-specific features
- Test on both databases
- Use `batch_alter_table` for SQLite-incompatible operations

**Bottom line**: Alembic handles most differences automatically. You only need special handling for PostgreSQL-specific features (JSONB, arrays, advanced indexes).

---

**Last Updated**: 2024-12-29  
**Status**: Reference Document - Current Setup is Compatible
