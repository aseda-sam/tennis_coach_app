# Upstash Redis Setup Guide

This guide walks you through setting up Upstash Redis for use with both Render API and Fly.io Worker.

## Why Upstash?

- ✅ **Free tier**: 10K commands/day, 256MB storage
- ✅ **Public endpoint**: No IP whitelisting needed
- ✅ **Works everywhere**: Render, Fly.io, local dev
- ✅ **Simple setup**: 5 minutes

## Step 1: Create Upstash Account

1. Go to [https://upstash.com](https://upstash.com)
2. Click **"Sign Up"** (free)
3. Sign up with GitHub, Google, or email
4. Verify your email if required

## Step 2: Create Redis Database

1. In Upstash dashboard, click **"Create Database"**
2. **Name**: `tennis-coach-redis` (or your preferred name)
3. **Type**: Redis
4. **Region**: Choose closest to your Fly.io region
   - If Fly.io is in `iad` (Washington, D.C.), choose `us-east-1` or similar
5. **TLS**: Enabled (recommended for production)
6. Click **"Create"**

## Step 3: Get Connection String

1. Click on your newly created database
2. Go to **"Details"** or **"Connect"** tab
3. Look for **"REST API"** or **"Redis URL"**
4. Copy the connection string

**Format examples:**

- With TLS: `rediss://default:password@region.upstash.io:6379`
- Without TLS: `redis://default:password@region.upstash.io:6379`

**Note**: If you see separate fields:

- **Endpoint**: `region.upstash.io:6379`
- **Password**: `your-password`
- **Username**: Usually `default`

Construct URL: `redis://default:password@region.upstash.io:6379`

## Step 4: Update Fly.io Secrets

```bash
fly secrets set REDIS_URL="redis://default:your-password@your-region.upstash.io:6379"
```

**For TLS (recommended):**

```bash
fly secrets set REDIS_URL="rediss://default:your-password@your-region.upstash.io:6379"
```

**Note**: `rediss://` (with double 's') indicates TLS/SSL connection.

## Step 5: Update Render API (Optional but Recommended)

Using the same Redis for both services simplifies setup:

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Select your API service
3. Go to **"Environment"** tab
4. Update `REDIS_URL` to your Upstash connection string
5. Save changes (service will restart)

## Step 6: Verify Connection

### Test from Fly.io Worker

```bash
fly logs -a tennis-coach-worker
```

Look for:

- `Successfully connected to Redis`
- `RQ Worker Startup`
- `Listening on queues: default, analysis`

### Test from Render API

Check Render logs for:

- `Successfully connected to Redis`
- No Redis connection errors

## Troubleshooting

### Connection Refused

- Verify connection string format
- Check if TLS is required (use `rediss://` instead of `redis://`)
- Ensure password is correct

### Authentication Failed

- Verify username is `default` (or correct username)
- Check password is correct
- Ensure no extra spaces in connection string

### Timeout Errors

- Check region is close to your services
- Verify network connectivity
- Check Upstash dashboard for service status

## Free Tier Limits

- **Commands**: 10,000/day
- **Storage**: 256MB
- **Connections**: 30 concurrent

**For your use case**: This should be sufficient for moderate usage. Monitor in Upstash dashboard.

## Cost

- **Free tier**: $0/month (10K commands/day)
- **Pay-as-you-go**: $0.20 per 100K commands after free tier

## Security Notes

- Connection strings contain passwords - never commit to git
- Use TLS (`rediss://`) in production
- Rotate passwords periodically
- Monitor access in Upstash dashboard

## Migration from Render Redis

If you were using Render Redis:

1. **Data migration**: If you have existing jobs in Render Redis, they won't automatically migrate
2. **Queue names**: Should be the same (`default`, `analysis`)
3. **No downtime**: Both can run simultaneously during migration

## Support

- **Upstash Docs**: https://docs.upstash.com/redis
- **Upstash Dashboard**: https://console.upstash.com
- **Project Issues**: GitHub Issues
