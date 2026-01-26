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

## Rotate active demo

```bash
python backend/scripts/set_active_demo.py --list
python backend/scripts/set_active_demo.py --video-id <video_id>
```

