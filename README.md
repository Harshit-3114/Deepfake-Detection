# Deepfake Detection System

Multimodal deepfake detection platform that accepts media uploads (text, image, audio, video), runs modality-specific detectors, fuses results into a single fake probability score, and provides a web frontend and REST API for ingestion and status checking.

## Architecture

```
                     ┌─────────────────────────────────────┐
                     │        Frontend (React + Vite)       │
                     │   Upload file / Check Job Status     │
                     └──────────────────┬──────────────────┘
                                        │ POST /ingest
                                        │ GET /status/{id}
                     ┌──────────────────▼──────────────────┐
                     │       Orchestrator Service (:8400)   │
                     │  - Accepts uploads, stores to S3     │
                     │  - Fans out to all 4 detectors       │
                     │  - Sends results to Fusion Service   │
                     └──┬───────┬───────┬───────┬───────┬──┘
                        │       │       │       │       │
              ┌─────────┘       │       │       │       └─────────┐
              ▼                 ▼       ▼       ▼                  ▼
      ┌──────────────┐  ┌──────────┐ ┌──────┐ ┌────────┐  ┌──────────────┐
      │ Text Detector│  │  Image   │ │Audio │ │  Video │  │ Fusion       │
      │ RoBERTa-NLI  │  │ Xception │ │Dummy │ │ Dummy  │  │ GradientBoost │
      │   (:8001)    │  │ (:8002)  │ │(:8003)│ │(:8004) │  │   (:8005)    │
      └──────────────┘  └──────────┘ └──────┘ └────────┘  └──────────────┘
                        ┌─────────────┐    ┌──────────────┐
                        │ MinIO (S3)  │    │ PostgreSQL   │
                        │  (:9000)    │    │   (:5432)    │
                        └─────────────┘    └──────────────┘
```

## Services

| Service | Port | Description | Status |
|---------|------|-------------|--------|
| **Frontend** | 5173 | React + Vite + TailwindCSS web UI | Functional |
| **Orchestrator** | 8400 | Central API gateway, job management, S3/DB | Functional |
| **Text Detector** | 8001 | NLI claim verification via RoBERTa-large-MNLI | Real model, tiny evidence corpus |
| **Image Detector** | 8002 | Xception binary classifier (pretrained) | Real architecture, needs fine-tuning |
| **Audio Detector** | 8003 | Audio spoof detection (placeholder) | Placeholder (random scores) |
| **Video Detector** | 8004 | Per-frame + AV-sync analysis (placeholder) | Placeholder (random scores) |
| **Fusion Service** | 8005 | GradientBoosting over 9 features | Trained on synthetic data |
| **MinIO** | 9000 | S3-compatible blob storage | Functional |
| **PostgreSQL** | 5432 | Job metadata & results | Functional |
| **Ingestion Service** | 8000 | Legacy upload endpoint (not used by pipeline) | Legacy |

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Node.js](https://nodejs.org/) 18+ (for frontend dev server)

### Run Everything

```bat
start.bat
```

This will:
1. Build and start all backend services via Docker Compose
2. Install frontend npm dependencies
3. Launch the React dev server
4. Run a self-test and open the browser

### Manual Start

```bash
# 1. Start backend services
docker-compose up --build -d

# 2. Start frontend
cd frontend
npm install
npm run dev
```

### Test the API

```bash
# Upload a text file
curl -X POST -F "file=@sample.txt" http://localhost:8400/ingest

# Upload an image
curl -X POST -F "file=@photo.jpg" http://localhost:8400/ingest

# Check job status
curl http://localhost:8400/status/<job_id>

# Health check
curl http://localhost:8400/health
```

## API Reference

### `POST /ingest`

Upload a file for deepfake analysis.

**Request:** multipart/form-data with `file` field
**Response:**
```json
{
  "job_id": "uuid",
  "filename": "test.txt",
  "detector_results": {
    "text": { "text_score": 0.2, "llm_flag": 0.3, "claims": [...], "reason_codes": [...] },
    "image": { "image_score": 0.5, "mask": [...], "reason_codes": [...] },
    "audio": { "audio_score": 0.5, "suspicious_segments": [] },
    "video": { "video_score": 0.5, "av_sync_score": 0.5, "frame_flags": [] }
  },
  "fusion_result": {
    "fake_probability": 0.35,
    "reason_codes": [...]
  }
}
```

### `GET /status/{job_id}`

Retrieve results for a submitted job.

### `GET /health`

Health check for all downstream services + DB + S3.

## Detectors

### Text Detector
- **Model:** `roberta-large-mnli` from HuggingFace
- **Approach:** Splits text into sentences, retrieves evidence via BM25, verifies claims via NLI
- **Limitation:** Evidence corpus is a 3-document dummy. Replace with a real knowledge base (Wikipedia, news archive).
- **Outputs:** `text_score`, `llm_flag`, `claims[]` (verdicts per sentence)

### Image Detector
- **Model:** Xception via `timm` (pretrained on ImageNet)
- **Approach:** Resize to 299x299, run through binary classifier with sigmoid output
- **Limitation:** No deepfake-specific training. Run `training/train_image_xception.py` with real data.
- **Outputs:** `image_score`, `mask` (placeholder), `reason_codes`

### Audio Detector
- **Model:** Placeholder (random scores)
- **Limitation:** Returns `numpy.random.uniform()`. Replace with RawNet2 or similar.
- **Outputs:** `audio_score`, `suspicious_segments`

### Video Detector
- **Model:** Placeholder (random scores)
- **Limitation:** Returns `numpy.random.uniform()` per frame and for AV-sync. Replace with 3D CNN or temporal transformer.
- **Outputs:** `video_score`, `av_sync_score`, `frame_flags`

## Fusion Service

Combines 9 features from all detectors using a `GradientBoostingClassifier`:

| Index | Feature | Source |
|-------|---------|--------|
| 0 | `text_score` | Text Detector |
| 1 | `llm_flag` | Text Detector |
| 2 | `percent_claims_refuted` | Text Detector |
| 3 | `source_score` | Default 0.5 |
| 4 | `image_score` | Image Detector |
| 5 | `image_localization_confidence` | Default 0.0 |
| 6 | `audio_score` | Audio Detector |
| 7 | `video_score` | Video Detector |
| 8 | `av_sync_score` | Video Detector |

**Limitation:** Currently trained on synthetic random data. Retrain with `training/train_fusion.py` after collecting real detector outputs.

## Training

```bash
# Generate sample datasets
cd data_generators
python make_text_dataset.py    # Creates text_dataset.jsonl
python make_image_dataset.py   # Creates image_dataset/ with dummy JPGs
python make_audio_dataset.py   # Creates audio_dataset/ with dummy WAVs
python make_video_dataset.py   # Creates video_dataset/ with dummy MP4s

# Train models
cd ../training
python train_text_nli.py        # Fine-tune RoBERTa-base on text dataset
python train_image_xception.py  # Train Xception on image dataset
python train_fusion.py          # Train GradientBoosting on synthetic data
```

## Preprocessors

Utility modules in `preprocessors/` for data preparation (not yet integrated into the pipeline):

- **text_preprocessor.py** — HTML extraction via newspaper3k, NER via spaCy
- **image_preprocessor.py** — Face detection via MTCNN, crop/resize
- **audio_preprocessor.py** — Silence trimming, log-mel spectrogram
- **video_preprocessor.py** — Frame extraction at configurable rate, face detection

## LabelStudio

Annotation configuration for human-in-the-loop labeling is in `labelstudio/`:

- Text: claim-level SUPPORTED / REFUTED / NEI
- Image: real / fake classification
- Audio: bona_fide / spoof
- Video: real / fake

```bash
# Import into Label Studio
label-studio start --project-config labelstudio/labelstudio_preset.yml
```

## Project Structure

```
deepfake_detection/
├── start.bat                       # One-click launcher
├── docker-compose.yml              # Multi-service Docker orchestration
├── Deepfake_Detection_README.md    # This file
├── ingestion_service/              # Legacy file upload service
├── orchestrator_service/           # Central API gateway
├── detectors/
│   ├── text_detector/              # NLI-based text analysis
│   ├── image_detector/             # Xception image classifier
│   ├── audio_detector/             # Audio spoof detection (placeholder)
│   └── video_detector/             # Video manipulation (placeholder)
├── fusion_service/                 # Multi-modal score fusion
├── preprocessors/                  # Modality preprocessing utilities
├── data_generators/                # Synthetic dataset creators
├── training/                       # Model training scripts
├── frontend/                       # React + Vite web UI
├── infra/                          # Infrastructure configs
├── labelstudio/                    # Annotation project presets
└── examples/                       # Sample data
```

## Known Limitations (MVP)

1. **Audio & Video detectors return random scores** — placeholders only
2. **Fusion model trained on synthetic data** — needs real detector outputs
3. **Text BM25 corpus is 3 documents** — replace with real knowledge base
4. **Image Xception has no deepfake fine-tuning** — needs real training data
5. **No authentication or rate limiting** — for local/dev use only
6. **No automated tests** — manual testing required for now
7. **File type detection is extension-based** — not content-based

## Stopping

```bash
docker-compose down
```

To also delete volumes (wipes DB and S3 data):
```bash
docker-compose down -v
```
