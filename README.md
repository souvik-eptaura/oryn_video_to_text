# oryn_video_to_text

Private Sources API for downloading Instagram reels, extracting audio, transcribing via an internal Whisper load balancer, and writing results to Firestore.

## Requirements

- Docker + Docker Compose
- Firebase project + service account (or ADC)
- Whisper load balancer reachable on the docker network

## Setup

1) Copy environment file

```bash
cp .env.example .env
```

2) Provide Firebase credentials

Option A: Mount a service account JSON file and set `GOOGLE_APPLICATION_CREDENTIALS` in `.env`.

Option B: Set `FIREBASE_SERVICE_ACCOUNT_JSON` with the raw JSON string.

3) Ensure the Whisper network exists (or update `docker-compose.yml`)

```bash
docker network create whisper_net
```

## Run Locally

```bash
docker compose up -d --build
```

Check health:

```bash
curl http://localhost/health
```

Expected:

```json
{"ok":true,"service":"sources-api"}
```

## Auth Usage

All API endpoints (except `/health`) require Firebase JWTs.

Example request:

```bash
curl -X POST http://localhost/v1/transcribe \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "workspaceId": "WORKSPACE123",
    "source": "instagram",
    "reelUrl": "https://www.instagram.com/reel/XXXX/",
    "postedAt": null,
    "metadata": {"handle": "@somehandle"}
  }'
```

Check job status (workspaceId is required for lookup):

```bash
curl "http://localhost/v1/jobs/JOB_ID?workspaceId=WORKSPACE123" \
  -H "Authorization: Bearer YOUR_JWT"
```

## VPS Deployment (Contabo)

1) Clone repo
2) Create `.env` from `.env.example`
3) Ensure `whisper_net` network exists or rename in `docker-compose.yml`
4) Start services

```bash
docker compose up -d --build
```

## Scaling Workers

```bash
docker compose up -d --scale worker=3
```

## Logs

```bash
docker logs -f oryn_video_to_text-api-1
docker logs -f oryn_video_to_text-worker-1
```

## Notes

- Whisper load balancer URL is configured via `WHISPER_URL`.
- Firestore is the system of record.
- Videos/audio are stored only in `/tmp` and removed after processing.
- If a reel already has `transcriptText`, the job is marked `completed` immediately.
- Nginx serves a self-signed certificate by default. Replace with a real cert for production.
