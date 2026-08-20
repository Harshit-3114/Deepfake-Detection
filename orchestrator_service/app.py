# orchestrator_service/app.py
import os
import asyncio
import aiohttp
import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import psycopg2
import json

# CONFIG (reads same env you already use)
S3_BUCKET = os.getenv("S3_BUCKET", "deepfake-blobs")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL", "http://minio:9000")
S3_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
S3_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "deepfake")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "pass")

DETECTOR_URLS = {
    "text": os.getenv("TEXT_DETECTOR_URL","http://text_detector:8000/api/text/detect"),
    "image": os.getenv("IMAGE_DETECTOR_URL","http://image_detector:8000/api/image/detect"),
    "audio": os.getenv("AUDIO_DETECTOR_URL","http://audio_detector:8000/api/audio/detect"),
    "video": os.getenv("VIDEO_DETECTOR_URL","http://video_detector:8000/api/video/detect")
}
FUSION_URL = os.getenv("FUSION_URL","http://fusion_service:8000/api/fuse")

app = FastAPI(title="Orchestrator Service")

# Ensure DB table exists on startup
def init_db():
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                s3_path TEXT,
                metadata TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB init warning (will retry at runtime): {e}")

init_db()

# Allow Cross Origin from your frontend (you can restrict to your frontend URL later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://deepfake-detection-nuhl.onrender.com"],  # change to ["https://your-frontend-url"] in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# S3 / MinIO client - use endpoint_url for MinIO compatibility
s3_client = boto3.client(
    "s3",
    aws_access_key_id=S3_KEY,
    aws_secret_access_key=S3_SECRET,
    region_name=S3_REGION,
    endpoint_url=S3_ENDPOINT
)

# DB helper (uses explicit host/user/password to match your env format)
def insert_job(job_id, s3_path, metadata, final_result=None):
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO jobs (job_id, s3_path, metadata, result)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (job_id) DO UPDATE SET result=%s
    """, (job_id, s3_path, json.dumps(metadata), json.dumps(final_result),
          json.dumps(final_result)))
    conn.commit()
    cur.close()
    conn.close()

# HTTP helpers
async def post_json(url, payload, timeout=30):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

async def post_file(url, file_bytes, filename, timeout=30):
    async with aiohttp.ClientSession() as session:
        try:
            data = aiohttp.FormData()
            data.add_field("file", file_bytes, filename=filename, content_type="application/octet-stream")
            async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

async def call_detectors(file_bytes, filename):
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    text_exts = {"txt", "json", "csv", "md", "html", "xml", "log", "py", "js", "ts"}
    is_text = ext in text_exts

    text_content = file_bytes.decode("utf-8", errors="ignore") if is_text else ""
    results = {}

    text_payload = {"text_content": text_content, "max_evidence": 5}
    if is_text:
        results["text"] = await post_json(DETECTOR_URLS["text"], text_payload)
    else:
        results["text"] = {"text_score": 0.5, "llm_flag": 0.5, "claims": [], "reason_codes": ["non_text_input"]}

    img_exts = {"jpg", "jpeg", "png", "gif", "bmp", "webp"}
    audio_exts = {"wav", "mp3", "flac", "ogg", "aac", "m4a"}
    video_exts = {"mp4", "avi", "mov", "mkv", "webm", "flv"}

    if ext in img_exts:
        results["image"] = await post_file(DETECTOR_URLS["image"], file_bytes, filename)
    else:
        results["image"] = {"image_score": 0.5, "mask": [], "reason_codes": ["non_image_input"]}

    if ext in audio_exts:
        results["audio"] = await post_file(DETECTOR_URLS["audio"], file_bytes, filename)
    else:
        results["audio"] = {"audio_score": 0.5, "suspicious_segments": []}

    if ext in video_exts:
        results["video"] = await post_file(DETECTOR_URLS["video"], file_bytes, filename)
    else:
        results["video"] = {"video_score": 0.5, "av_sync_score": 0.5, "frame_flags": []}

    return results

# API
@app.post("/ingest")
async def ingest(file: UploadFile = File(...), uploader_id: str = "unknown"):
    job_id = str(uuid4())
    filename = file.filename or "unknown"
    s3_path = f"{job_id}_{filename}"
    try:
        contents = await file.read()
        s3_client.put_object(Bucket=S3_BUCKET, Key=s3_path, Body=contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {e}")

    metadata = {"uploader_id": uploader_id}
    insert_job(job_id, s3_path, metadata, final_result=None)

    detector_results = await call_detectors(contents, filename)

    text = detector_results.get("text", {})
    image = detector_results.get("image", {})
    audio = detector_results.get("audio", {})
    video = detector_results.get("video", {})

    claims = text.get("claims", [])
    num_refuted = sum(1 for c in claims if c.get("verdict") == "REFUTED")
    percent_refuted = num_refuted / max(len(claims), 1)

    fusion_payload = {
        "text_score": text.get("text_score", 0.5),
        "llm_flag": text.get("llm_flag", 0.5),
        "percent_claims_refuted": percent_refuted,
        "source_score": 0.5,
        "image_score": image.get("image_score", 0.5),
        "image_localization_confidence": 0.0,
        "audio_score": audio.get("audio_score", 0.5),
        "video_score": video.get("video_score", 0.5),
        "av_sync_score": video.get("av_sync_score", 0.5),
    }
    fusion_result = await post_json(FUSION_URL, fusion_payload)
    insert_job(job_id, s3_path, metadata, final_result=fusion_result)

    return {
        "job_id": job_id,
        "filename": filename,
        "detector_results": detector_results,
        "fusion_result": fusion_result,
    }

@app.get("/status/{job_id}")
def status(job_id: str):
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("SELECT s3_path, metadata, result FROM jobs WHERE job_id=%s", (job_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    s3_path, metadata, result = row
    return {"job_id": job_id, "s3_path": s3_path, "metadata": metadata, "result": result}

@app.get("/")
def root():
    return {"status": "ok", "message": "Deepfake Orchestrator Service is running"}

@app.get("/health")
def health_check():
    checks = {}
    # DB
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
    # S3
    try:
        s3_client.list_buckets()
        checks["s3"] = "ok"
    except Exception as e:
        checks["s3"] = f"error: {e}"
    checks["detectors"] = DETECTOR_URLS
    checks["fusion_service"] = FUSION_URL
    return {
        "status": "ok" if all(v == "ok" or isinstance(v, dict) for v in checks.values()) else "degraded",
        "checks": checks
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8400")))
