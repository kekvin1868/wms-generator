# 🧳 Travel Bag Co. — AI Image Studio (Local Prototype)

Make professional-looking travel bag photos on your own Mac.
No cloud accounts. No subscriptions. Everything runs on your computer.

The app is now split in two pieces that talk to each other on your laptop:

- **Backend** — a Python service (FastAPI) that runs the AI model.
- **Frontend** — a modern web app (Next.js 15 + React 19 + Tailwind + shadcn/ui-style components) that you click around in.

You only need to do **Part A once**. After that, starting the app is one command.

---

## What you need

- A Mac with Apple Silicon (M1–M5). You have an M5 — perfect.
- About **10 GB of free disk space** (the AI model downloads once and is reused).
- **Python 3.10+**.
- **Node.js 20+** (Node 22 or 24 also fine). Check with `node --version`.
  If missing: install from <https://nodejs.org> or run `brew install node`.
- **pnpm** (recommended) or npm. Install pnpm once with `npm install -g pnpm`.
- An internet connection **for the first run only** (to download the model and frontend deps).

---

## Part A — One-time setup (about 10–15 minutes)

### Step 1. Open Terminal and go to the project folder

```
cd ~/Documents/GitHub/wms-generator
```

(Adjust the path if you put the folder somewhere else. Tip: drag the folder onto the Terminal window after typing `cd ` — the path fills in automatically.)

### Step 2. Set up the Python backend

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

This downloads about 3 GB of software (torch, diffusers, fastapi, …). 5–10 minutes is normal. When the cursor returns with no red errors, you're done.

### Step 3. Set up the Next.js frontend

```
cd frontend
pnpm install
cd ..
```

(If you don't have pnpm, use `npm install` instead.)

This downloads the React/Next.js/Tailwind packages into `frontend/node_modules`. 1–2 minutes.

---

## Part B — Using the app (every time)

### Step 1. Start everything with one command

From the project root:

```
./scripts/dev.sh
```

This script:

1. Activates your Python `venv`.
2. Starts the backend on **<http://127.0.0.1:8000>** (FastAPI + SSE).
3. Starts the frontend on **<http://localhost:3000>** (Next.js dev server).

Open <http://localhost:3000> in your browser. You'll see the **Travel Bag Co. — AI Image Studio** screen.

> Prefer two terminals? Equivalent manual steps:
> ```
> # terminal 1
> source venv/bin/activate
> uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
>
> # terminal 2
> cd frontend && pnpm dev
> ```

### Step 2. Make images

1. Pick a **Campaign preset** at the top, or choose your own options 2–7.
2. (Optional) Open **More options** to change image shape, count, seed, or model.
3. Press the orange **✨ Create my images** button.
4. Watch the **live progress bar** on the right. Images appear in the gallery as soon as they're done. Click any image for a larger lightbox view (prompt + seed shown).

> ⚠️ **The very first time you press the button**, the AI model itself downloads
> (about 7 GB). This is a **one-time wait of 10–30 minutes** depending on your
> internet. Watch the Terminal window — you'll see a progress bar there.
> Every run after that skips straight to creating images.
>
> On your M5, each image should take roughly **10–30 seconds** once the model is loaded.

### Step 3. Find your images

Every image is saved automatically in the **`outputs`** folder. File names tell you what's in them, e.g.

```
backpack_mountain-trail_golden-hour_seed42_20260611-141502.png
```

The PNGs embed `prompt`, `seed`, and `model` as metadata — readable with `Pillow` or `exiftool`.

### Step 4. Browse past runs

Click **History** in the top-right. A side panel slides in showing every PNG in `outputs/` with thumbnail, filename, model, and a **copy seed** button. Paste a seed into the Seed box to reproduce a result exactly.

### Step 5. Recreate an image you liked

After each run, the status line shows the **Seed** used. Open **More options** in the form, paste the same seed, keep the rest of the options the same, and re-run — you'll get the identical images back.

### Step 6. Stop the app

Press `Ctrl + C` in the terminal that's running `./scripts/dev.sh`. Both servers shut down together. (Or just close the terminal.)

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `command not found: python3` | Install Python from <https://www.python.org/downloads/>. |
| `command not found: node` | Install Node 20+ from <https://nodejs.org> or `brew install node`. |
| `command not found: pnpm` | `npm install -g pnpm`, or just use `npm install` / `npm run dev`. |
| `command not found: pip` | Run `source venv/bin/activate` first. |
| Red errors during `pip install` | Run it again — downloads sometimes hiccup. |
| Frontend loads but says "Backend not reachable" | Open <http://127.0.0.1:8000/api/options> in a tab. If it doesn't return JSON, the backend isn't running — check the terminal for the `uvicorn` log. |
| Browser shows "can't connect" on port 3000 | Make sure `pnpm dev` is running; check the terminal output. |
| Port 3000 or 8000 already in use | Kill the stale process: `lsof -ti:3000 | xargs kill` (replace with `8000` as needed). |
| First image takes forever | Normal — the 7 GB model is downloading. Watch the backend terminal for progress. |
| Mac feels slow / fan spins | Normal while generating. It stops when images are done. |
| Out-of-memory error | Open **More options** → switch Model to **"Small & light — SD 1.5"**. |

---

## What's in this folder

```
wms-generator/
├── backend/                 ← FastAPI service
│   ├── main.py              ← routes + SSE
│   ├── pipeline.py          ← model loading + generation (async generator)
│   ├── presets.py           ← YAML preset loader
│   ├── history.py           ← reads outputs/ + PNG metadata
│   ├── constants.py         ← dropdown sources, prompt fragments
│   └── schemas.py           ← Pydantic request/response models
├── frontend/                ← Next.js 15 + React 19 + Tailwind v4
│   ├── app/                 ← layout, page, providers (TanStack Query)
│   ├── components/          ← StudioForm, Gallery, ProgressBar, HistoryDrawer + ui/ primitives
│   ├── hooks/               ← useGenerationStream (SSE client)
│   ├── lib/                 ← api, schemas (Zod), utils
│   └── package.json
├── config/campaigns/        ← campaign presets (plain YAML, editable)
├── outputs/                 ← generated PNGs land here
├── scripts/dev.sh           ← runs backend + frontend together
├── requirements.txt         ← Python deps
└── README.md                ← this file
```

### Editing campaign presets (optional)

The files in `config/campaigns/` are plain YAML. Open one with TextEdit, change the values, save, refresh the browser tab — your preset appears in the dropdown. Copy a file to make a new preset.

---

## API surface (for the curious)

The frontend talks to FastAPI via these endpoints on `http://127.0.0.1:8000`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/options` | All dropdown sources (models, aspects, locations, …) |
| GET | `/api/presets` | Parsed `config/campaigns/*.yaml` |
| POST | `/api/generate` | Submit a job — returns `{ job_id }` |
| GET | `/api/generate/{job_id}/stream` | **Server-Sent Events**: `progress` updates then a final `done` |
| GET | `/api/history` | Files in `outputs/` with PNG metadata |
| GET | `/outputs/{filename}` | Static PNG serving |
| GET | `/api/health` | Reports device (`mps`/`cuda`/`cpu`) |

OpenAPI docs live at <http://127.0.0.1:8000/docs> while the backend is running.

---

## Notes for the technical follow-up (not needed for the demo)

- Default model: **SDXL-Lightning 4-step** (single-file checkpoint, `ByteDance/SDXL-Lightning`, no HuggingFace login needed). Fallback: **SD 1.5** for low-memory machines.
- Runs on Apple Silicon via PyTorch **MPS** in float16. The plain `pip install torch` wheel already includes MPS — no special index URL on Mac.
- `transformers` is in requirements because diffusers needs it for the CLIP text encoders.
- `xformers` is CUDA-only and intentionally excluded — it does nothing on Mac.
- Prompts and seeds are embedded in each PNG's metadata for traceability.
- Generation is serialized via an `asyncio.Lock` in `backend/pipeline.py` — only one job at a time (the MPS model loads once and stays resident).
- Progress is streamed to the browser as Server-Sent Events; the React side consumes them with a native `EventSource` wrapped in `useGenerationStream`.
- CLI mode, LoRA fine-tuning, ControlNet, and upscaling are deferred per the original project plan (Tiers 2–4).
