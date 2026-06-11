# 🧳 Travel Bag Co. — AI Image Studio (Local Prototype)

Make professional-looking travel bag photos on your own Mac.
No cloud accounts. No subscriptions. Everything runs on your computer.

You only need to do **Part A once**. After that, starting the app is two lines.

---

## What you need

- A Mac with Apple Silicon (M1–M5). You have an M5 — perfect.
- About **10 GB of free disk space** (the AI model downloads once and is reused).
- An internet connection **for the first run only** (to download the model).

---

## Part A — One-time setup (about 10–15 minutes)

### Step 1. Open the Terminal app

Press `⌘ Command + Space`, type **Terminal**, press `Return`.
A window with text appears. You will copy-paste commands into it.

> Tip: copy each gray box below with `⌘C`, click the Terminal window,
> paste with `⌘V`, then press `Return`. Wait for it to finish before the next one.

### Step 2. Check that Python is installed

```
python3 --version
```

- If you see `Python 3.10`, `3.11`, `3.12` or similar → good, continue.
- If you see an error or a version below 3.10 → install Python from
  https://www.python.org/downloads/ (big yellow button), then close and
  reopen Terminal and try again.

### Step 3. Go to this project folder

If the folder is in your Downloads:

```
cd ~/Downloads/travel-bag-genai
```

(If you put it somewhere else, drag the folder onto the Terminal window
after typing `cd ` — the path fills in automatically. Then press `Return`.)

### Step 4. Create a private workspace for the app

```
python3 -m venv venv
```

```
source venv/bin/activate
```

After this, the line in Terminal starts with `(venv)`. That's correct.

### Step 5. Install the app's components

```
pip install -r requirements.txt
```

This downloads about 3 GB of software. It can take 5–10 minutes.
When the cursor comes back and there are no red errors, you're done.

---

## Part B — Using the app (every time)

### Step 1. Start it

In Terminal, inside the project folder:

```
source venv/bin/activate
```

```
python app.py
```

Your web browser opens by itself with the **Travel Bag Co. — AI Image Studio**
screen. (If it doesn't, copy the address shown in Terminal —
usually `http://127.0.0.1:7860` — into your browser.)

### Step 2. Make images

1. Pick a **Campaign preset** at the top, or choose your own options 2–7.
2. Press the big orange **✨ Create my images** button.
3. Wait. Images appear on the right.

⚠️ **The very first time you press the button**, the AI model itself downloads
(about 7 GB). This is a **one-time wait of 10–30 minutes** depending on your
internet. Watch the Terminal window — you'll see a progress bar there.
Every run after that skips straight to creating images.

On your M5, each image should take roughly **10–30 seconds** once the model
is loaded.

### Step 3. Find your images

Every image is saved automatically in the **`outputs`** folder inside the
project folder — open it in Finder. File names tell you what's in them, e.g.

```
backpack_mountain-trail_golden-hour_seed42_20260611-141502.png
```

### Step 4. Recreate an image you liked

The Status box shows a **Seed** number after each run. Write it down.
Next time, open **More options**, type that number into the **Seed** box,
keep the same choices, and you'll get the exact same images again.

### Step 5. Stop the app

Click the Terminal window and press `Control + C` (the `control` key, not ⌘).
You can also just close the Terminal window.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `command not found: python3` | Install Python (Part A, Step 2). |
| `command not found: pip` | Run `source venv/bin/activate` first. |
| Red errors during `pip install` | Run the command again — downloads sometimes hiccup. |
| Browser shows "can't connect" | Look in Terminal for `http://127.0.0.1:7860` and paste it into the browser yourself. |
| First image takes forever | Normal — the 7 GB model is downloading. Check Terminal for progress. |
| Mac feels slow / fan spins | Normal while generating. It stops when images are done. |
| Out-of-memory error | Open **More options** → switch Model to **"Small & light — SD 1.5"**. |

---

## What's in this folder

```
travel-bag-genai/
├── app.py                  ← the app (don't need to touch it)
├── requirements.txt        ← list of components pip installs
├── config/campaigns/       ← campaign presets (plain text, editable)
├── outputs/                ← your generated images land here
└── README.md               ← this file
```

### Editing campaign presets (optional)

The files in `config/campaigns/` are plain text. Open one with TextEdit,
change the words after the colons, save, restart the app — your preset
appears in the dropdown. Copy a file to make a new preset.

---

## Notes for the technical follow-up (not needed for the demo)

- Default model: **SDXL-Lightning 4-step** (single-file checkpoint,
  `ByteDance/SDXL-Lightning`, no HuggingFace login needed). Fallback:
  **SD 1.5** for low-memory machines.
- Runs on Apple Silicon via PyTorch **MPS** in float16. The plain
  `pip install torch` wheel already includes MPS — no special index URL on Mac.
- `transformers` is in requirements because diffusers needs it for the CLIP
  text encoders (it is not optional, contrary to the original plan doc).
- `xformers` is CUDA-only and intentionally excluded — it does nothing on Mac.
- Prompts and seeds are embedded in each PNG's metadata for traceability.
- CLI mode, LoRA fine-tuning, ControlNet, and upscaling are deferred per the
  project plan (Tiers 2–4).
