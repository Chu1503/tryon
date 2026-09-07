# Digital Wardrobe

Digital Wardrobe is a local-first 2D virtual wardrobe. It keeps body references, garment originals, transparent cleaned garments, and generated try-ons on your computer. Front and back views are processed and generated independently, and successful results are versioned and cached permanently. By default, generation prefers the official FASHN VTON 1.5 Hugging Face Space and falls back to local CatVTON.

This is Part A only. There is no 3D pipeline and no body or garment measurement workflow.

The repository includes one placeholder body reference, two shirts, and two pairs of pants in `assets/seed`. The app uses port `8011` for FastAPI, and Next.js proxies same-origin `/api` requests to it to avoid Windows/WSL CORS and hostname problems.

Conda intentionally lives inside WSL, so `conda` is not expected to work in PowerShell. The launch helper enters WSL and activates it automatically.

## Architecture

```text
required front + optional back garment upload
  → rembg segmentation (BiRefNet by default)
  → alpha checks, safe deskew, crop, padding, 1024×1024 normalization
  → originals + clean PNGs on disk; paths and versions in SQLite
  → independent front/back background jobs
  → FASHN VTON 1.5 hosted service (preferred) or local CatVTON fallback
  → provider-, input-, and version-checked PNG cache
  → instant wardrobe selection and FRONT/BACK switching
```

- `frontend/`: Next.js App Router, React, TypeScript, Tailwind CSS.
- `backend/app/api/`: FastAPI routes.
- `backend/app/services/`: storage, deterministic processing, job management, and ML boundaries.
- `backend/app/models/`: SQLAlchemy models that can later use PostgreSQL.
- `data/`: body images, UUID garment folders, and `wardrobe.db`.
- `assets/seed/`: replaceable demo images.
- `scripts/`: environment checks, demo seeding, model setup, and launch helpers.

Images are not stored in SQLite. The API never accepts arbitrary filesystem paths, and uploaded filenames are ignored.

## Requirements

### Normal application

- Windows 10/11 with WSL2 Ubuntu
- Node.js 20 or newer on Windows (Node 22 LTS recommended)
- Miniconda inside WSL
- Python 3.10 in the Conda environment

### Real CatVTON inference

- An NVIDIA GPU visible in WSL (`nvidia-smi` must work there)
- Current NVIDIA Windows driver with WSL CUDA support
- Several gigabytes of free disk space for PyTorch and Hugging Face checkpoints

The official [CatVTON](https://github.com/Zheng-Chong/CatVTON) project describes under 8 GB VRAM at its full 1024×768 BF16 setting. The included low-memory profile defaults to FP16, 384×512, 12 steps, guidance scale 2.5, one worker, and no safety-checker allocation. Twelve steps favors latency while retaining normal guidance for garment fidelity. Increase `CATVTON_STEPS` to 20–30 or try 512×768 when more GPU memory is available and detail matters more than speed.

CPU CatVTON is disabled because diffusion inference is too slow for the wardrobe experience. Background removal and the rest of the app still work if CatVTON is unavailable, and `/api/health` reports the exact reason.

CatVTON is licensed CC BY-NC-SA 4.0. Review its license before commercial use.

### Hosted high-quality inference

The default `VTON_PROVIDER=hybrid` profile calls the official [FASHN VTON 1.5 Space](https://huggingface.co/spaces/fashn-ai/fashn-vton-1.5). It produces 576×864 images and is normally much faster and more detailed than the reduced local profile required by this laptop's 4 GB GPU. A Hugging Face account is not required, but adding a free read token as `HF_TOKEN` in `.env` raises the ZeroGPU allowance. Free hosted inference is not unlimited: anonymous users have a small daily GPU allowance, signed-in free users have a larger allowance, and a queue may add delay. Those limits are controlled by Hugging Face and can change.

The hybrid setup has no hard application-level generation limit because it automatically switches to local CatVTON when hosted inference is unavailable. The tradeoff is that fallback output is lower resolution and slower. Hosted generation also means the person and garment images are sent to Hugging Face for processing; originals and completed results remain stored locally by this app.

Provider options in `.env`:

```text
VTON_PROVIDER=hybrid   # FASHN first, local CatVTON fallback (recommended)
VTON_PROVIDER=fashn    # FASHN only; fail visibly when quota/service is unavailable
VTON_PROVIDER=catvton  # local only; private and unlimited, but slower/lower quality here
FASHN_STEPS=30         # 20 is faster; 30 is the balanced default; 50 favors detail
HF_TOKEN=              # optional free Hugging Face read token
```

## Fresh installation on Windows

These steps prepare a new Windows development machine.

The WSL examples below assume the repository is cloned to `C:\code\digital-wardrobe`, which appears inside WSL as `/mnt/c/code/digital-wardrobe`. Adjust that path if you clone it elsewhere.

### 1. Install prerequisites

Install [Node.js LTS](https://nodejs.org/) and the latest NVIDIA driver. In an Administrator PowerShell window:

```powershell
wsl --install -d Ubuntu
```

Restart Windows if prompted. Open Ubuntu once and create its Linux username/password.

### 2. Install Miniconda and create the environment

In the Ubuntu/WSL terminal:

```bash
wget -O /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash /tmp/miniconda.sh -b -p "$HOME/miniconda3"
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda init bash
conda create --override-channels -c conda-forge -n digital-wardrobe python=3.10 -y
conda activate digital-wardrobe
export PYTHONNOUSERSITE=1
cd /mnt/c/code/digital-wardrobe
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-catvton-wsl.txt
python -m pip install --no-build-isolation 'git+https://github.com/facebookresearch/detectron2.git@v0.6'
python scripts/setup_models.py
```

The app uses a tested CatVTON dependency set because the upstream repository currently combines an unpinned development `diffusers` dependency with incompatible Hugging Face version bounds.

### 3. Install the frontend

From the repository root in PowerShell:

```powershell
npm --prefix frontend install
```

### 4. Create configuration and demo data

From the repository root in PowerShell, copy the example only if `.env` does not exist:

```powershell
Copy-Item .env.example .env
```

Then in WSL:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate digital-wardrobe
export PYTHONNOUSERSITE=1
cd /mnt/c/code/digital-wardrobe
python scripts/seed_demo.py
python scripts/verify_environment.py
```

`seed_demo.py` is idempotent. It preserves a real body upload by default; use `--replace-body` only when you intentionally want the placeholder back.

## Run the app

The easiest option is one command in PowerShell. It opens the backend and frontend in separate windows, waits for the API health check, and avoids the frontend starting without its API:

```powershell
.\scripts\start-app.ps1
```

Or open two PowerShell windows at the repository root and start the services separately.

Terminal 1 — backend:

```powershell
.\scripts\start-backend.ps1
```

Terminal 2 — frontend:

```powershell
.\scripts\start-frontend.ps1
```

Open:

- Wardrobe: [http://localhost:3000](http://localhost:3000)
- API health: [http://localhost:3000/api/health](http://localhost:3000/api/health)
- FastAPI docs: [http://localhost:8011/docs](http://localhost:8011/docs)

The default hosted path avoids loading CatVTON locally. If hosted inference is out of quota or unavailable, the first fallback generation downloads any missing checkpoints and loads CatVTON and its masking models into GPU memory, so it is slower than later local generations. The backend reuses the loaded model, and valid generated PNGs are served from cache without rerunning inference. Selecting garments or switching FRONT/BACK never starts generation by itself; use **Generate view** explicitly.

While generation runs, the wardrobe shows the real backend percentage and current phase (model loading, mask preparation, diffusion steps, or saving). Body references are fitted onto CatVTON's portrait canvas without cutting off the head or feet, and the final image repaints untouched pixels from the original reference so the face, hands, body, and background remain stable.

Garment preprocessing uses the strong `birefnet-general-lite` segmentation model. Opaque images require segmentation, while correctly transparent PNGs skip that step. For a smaller, faster but less accurate segmentation model, set `REMBG_MODEL=u2netp` in `.env` and restart the backend.

If PowerShell blocks the helper scripts, allow them only for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## Replace the placeholder images

Use the setup page to upload real front and back full-body images. Replacing either reference increments the body version and invalidates existing try-on caches. Add Garment requires only a front JPG, JPEG, PNG, or WEBP image. The back garment image is optional and can be added later. Supplied images automatically run through background removal and normalization; already-transparent PNGs skip segmentation for near-instant processing.

The current seed intentionally uses its one body image for both views and each placeholder garment for both garment views. They are only there to make the UI immediately populated.

## Tests

Backend tests in WSL:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate digital-wardrobe
export PYTHONNOUSERSITE=1
cd /mnt/c/code/digital-wardrobe/backend
pytest
```

Frontend production build in PowerShell:

```powershell
npm --prefix frontend run build
```

One person + garment pipeline test in WSL:

```bash
cd /mnt/c/code/digital-wardrobe
python scripts/test_pipeline.py \
  --person data/user/me_front.png \
  --garment assets/seed/black_tee.png \
  --category T-Shirt \
  --output data/pipeline_test.png
```

Add `--mock` only when testing without CatVTON.

## Cache behavior

A try-on is reused only when its file exists and its inference profile, recorded body-reference version, and view-specific garment-image version all match current values. Changing the provider or quality settings invalidates old outputs. A body change invalidates all generated views. Replacing only a front garment image invalidates only its front result. Front and back failures are recorded separately, so one successful view remains available if the other fails.

`ENABLE_WRINKLE_CLEANING=false` intentionally uses the no-op cleaner. Generative wrinkle removal can alter logos, text, stitching, prints, or garment shape, so identity preservation takes priority in V1.
