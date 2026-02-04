# Demo videos — optional

If you use demo videos (public bucket), keep the workflow boring:

1. Upload a demo video
2. Mark it active (only one active demo at a time)
3. Run pose detection / serve analysis as needed

## Production setup

- Create a **public** bucket in Supabase (e.g. `demo-videos`)
- Set:

```bash
SUPABASE_DEMO_BUCKET=demo-videos
```

- Configure admin user IDs in backend config (comma-separated):

```bash
ADMIN_USER_IDS=00000000-0000-0000-0000-000000000000,...
```

## Admin UI (Recommended)

Admins can manage demo videos through the web UI:

1. **Access Admin Panel**: Navigate to the "Admin" tab (visible only to admins)
2. **Upload Demo Video**: Click "Upload Demo Video" and check "Upload as demo video"
3. **Set Active Demo**: Click "Set as Active" on any demo video
4. **Run Pose Analysis**: Click "Run Pose Analysis" to start pose detection
5. **Create Serve Attempts**: Use the regular video analysis interface to tag serve attempts

The admin UI shows:

- Active demo status
- Pose analysis status (✓ or ⚠)
- Serve attempt count (✓ or ⚠)
- All demo videos with their status

## CLI Scripts (Alternative)

For command-line management:

### List demo videos

```bash
python backend/scripts/set_active_demo.py --list
```

### Set active demo

```bash
python backend/scripts/set_active_demo.py --video-id <video_id>
```

### Run pose analysis

```bash
python backend/scripts/analyze_demo_pose.py --video-id <video_id>
python backend/scripts/analyze_demo_pose.py  # Analyzes active demo
```

## Authorization

Admin access is controlled by the `ADMIN_USER_IDS` environment variable (comma-separated Supabase auth user UUIDs). Only users in this list can:

- Upload demo videos
- Upload videos on behalf of other users
- Set active demo
- Trigger pose analysis for demo videos
- Create/edit serve attempts for demo videos
- Access the admin UI. The admin UI automatically checks admin status and only shows the "Admin" tab to authorized users.

Set `ADMIN_USER_IDS` via environment variables (e.g., Fly.io secrets in production).
