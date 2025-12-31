# User Data Deletion & GDPR Compliance

## Problem

When a user is deleted from Supabase Auth, we need to cascade delete their data. Can't use foreign keys to `auth.users` (Supabase-managed table).

## Solution: Application-Level Service

Create `UserDeletionService` that deletes:

- All user's videos (cascades to ball_detections, pose_detections, ball_contacts, etc. via SQLAlchemy)
- All user's players (cascades to video_players via FK)
- All files from storage (local or Supabase Storage)

```python
# app/services/user_deletion_service.py
class UserDeletionService:
    def delete_user_data(self, db: Session, user_id: str) -> dict:
        # Delete videos + files
        videos = db.query(Video).filter(Video.user_id == user_id).all()
        for video in videos:
            storage_service.delete_video_file(video.file_path)
            db.delete(video)  # Cascades to related data

        # Delete players
        players = db.query(Player).filter(Player.user_id == user_id).all()
        for player in players:
            db.delete(player)  # Cascades to video_players

        db.commit()
```

## Trigger Options

**Option 1**: Database trigger (PostgreSQL only)

- Trigger on `auth.users` deletion → calls function to delete data
- Automatic, but PostgreSQL-only

**Option 2**: Application service (recommended)

- Works with SQLite + PostgreSQL
- Easier to test
- Can include file cleanup

## GDPR Checklist

✅ Delete all user data (videos, players, related records)  
✅ Delete files from storage  
✅ Log deletion for audit trail
