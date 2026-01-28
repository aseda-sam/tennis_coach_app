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

- Configure demo editor user IDs in backend config:

```bash
DEMO_EDITOR_USER_IDS=ca4a6fcc-4cdf-435c-a22f-1c8c02ce4c5f,...
```

## Admin UI (Recommended)

Demo editors can manage demo videos through the web UI:

1. **Access Admin Panel**: Navigate to the "Admin" tab (visible only to demo editors)
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

Demo editor access is controlled by the `DEMO_EDITOR_USER_IDS` allowlist in backend config. Only users in this list can:

- Upload demo videos
- Set active demo
- Trigger pose analysis for demo videos
- Create/edit serve attempts for demo videos
- Access the admin UI

The admin UI automatically checks demo editor status and only shows the "Admin" tab to authorized users.
