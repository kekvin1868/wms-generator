# Video Generation — Plan

Add **text → video** to the AI Image Studio. Photos stay free and local; videos are made by a paid cloud model (Wan on fal.ai), paid from one prepaid fal account, with a per-user monthly limit so the bill can't run away.

Status: **planned, not started** · Decided: 2026-11-25

---

## 1. Decisions at a glance

| # | Topic | Decision | Why |
|---|---|---|---|
| 1 | Engine | **fal.ai**, prepaid top-ups | One key → many models (Wan, Kling, Seedance, Veo). Switch model = change one name. No subscription. |
| 2 | Video type | **Text → video** | One step from the existing form. |
| 3 | Length / quality | **10 s @ 1080p** | Ad/website quality. |
| 4 | Who holds the fal key | **One shared video server** | Only way to pay for users *and* keep the key secret. |
| 5 | What runs on the server | **Video only** — photos stay on each Mac | No GPU server needed. |
| 6 | Login | **One invite key per user** | Lets us know who made each clip → per-user limits. |
| 7 | Limit | **30 clips / user / calendar month** | Caps the bill (see §7). |
| 8 | Hosting | **Free-tier host** (Render / Koyeb, pick at build) | $0. Server is stateless, so sleeping/wiped disk is fine. |
| 9 | Storage for keys + counts | **Supabase free (Postgres)** | Survives restarts; web table editor to manage keys by hand. |
| 10 | Where videos are kept | **User's Mac, `outputs/`** | Free, same as photos, History keeps working. |
| 11 | Model | **Wan** (cheapest at 1080p) | ~$0.40–0.50 / clip. Try Kling later if quality is short. |
| 12 | Quota counting | **Reserve at send, refund on failure** | Fair to users, can never overshoot the bill. |
| 13 | Prompt | **Existing form + "camera motion" dropdown** | Reuses `build_prompt()`; consistent clips. |
| 14 | Invite key on the Mac | **`VIDEO_INVITE_KEY` in `backend/.env`** | Same place as `HF_TOKEN`, no new UI. |

Rejected along the way: **Gemini/Veo** (no free API tier, pricier), **DeepSeek** (has no video model), **local video models** (too slow on a Mac: minutes to over an hour per clip).

---

## 2. How it fits together

```
 USER'S MAC (existing app)                 FREE HOST (new)                     fal.ai
┌───────────────────────────┐            ┌──────────────────────────┐        ┌───────────┐
│ Next.js frontend          │            │ video-server (FastAPI)   │        │ Wan 2.x   │
│  Photo | Video toggle     │            │                          │  fal   │ text→video│
│  + camera-motion dropdown │            │ 1. check invite key      │  key   │ 10s 1080p │
│            │              │            │ 2. reserve 1 clip slot   │───────▶│  (queue)  │
│            ▼              │ invite key │ 3. send job to fal queue │        │           │
│ local backend (FastAPI)   │───────────▶│ 4. report status         │◀───────│           │
│  POST /api/video          │◀───────────│ 5. refund slot on fail   │        └───────────┘
│  GET  /api/video/{id}     │  status +  └────────────┬─────────────┘
│  downloads .mp4 →         │  video URL              │
│  outputs/ + History       │                ┌────────▼─────────┐
│                           │                │ Supabase (free)  │
│ photos: SDXL local, $0    │                │ invite_keys      │
└───────────────────────────┘                │ video_jobs       │
                                             └──────────────────┘
```

**Golden rule:** the fal key exists **only** on the video server. The Mac only ever holds its own invite key, and a leaked invite key costs at most that user's 30 clips.

### One clip, step by step

```
Mac frontend ──▶ local backend ──▶ video server ──▶ Supabase: reserve slot (or 429 "quota used")
                                        │
                                        └──▶ fal: submit job → ticket (request_id)
        ◀── job_id ─────────────────────┘

every ~5 s:  frontend ──▶ local backend ──▶ video server ──▶ fal: status?
             queued / running ...                                    (1–3 min)
             done  → video server marks job "done", returns video URL
                   → local backend downloads .mp4 into outputs/ + writes .json sidecar
                   → frontend shows the clip, History lists it
             failed → video server marks job "failed" (slot refunded), frontend shows error
```

Waiting is handled by fal's queue + a ticket number, so no server has to stay awake for 1–3 minutes. That's what makes a sleeping free host OK.

---

## 3. Supabase (keys + counts)

Two tables. No "reset" job is needed: the monthly count is just *"jobs this calendar month that aren't failed"*.

```sql
create table invite_keys (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,                 -- who it belongs to, e.g. "Ana"
  key_hash      text not null unique,          -- sha256 of the invite key, never the key itself
  monthly_quota int  not null default 30,      -- raise per person here
  active        boolean not null default true, -- set false to revoke
  created_at    timestamptz not null default now()
);

create table video_jobs (
  id             uuid primary key default gen_random_uuid(),
  key_id         uuid not null references invite_keys(id),
  fal_request_id text,
  status         text not null default 'reserved'
                 check (status in ('reserved', 'done', 'failed')),
  prompt         text not null,
  created_at     timestamptz not null default now(),
  finished_at    timestamptz
);

create index on video_jobs (key_id, created_at);
```

**Reserving must be atomic**: two clicks at the same moment must not both squeeze past the limit. One Postgres function locks the user's row, counts, and inserts in one go:

```sql
create function reserve_clip(p_key_hash text, p_prompt text)
returns uuid language plpgsql as $$
declare k invite_keys; used int; job uuid;
begin
  select * into k from invite_keys
   where key_hash = p_key_hash and active
   for update;                                   -- serialises concurrent requests per user
  if not found then raise exception 'invalid_key'; end if;

  select count(*) into used from video_jobs
   where key_id = k.id and status <> 'failed'
     and created_at >= date_trunc('month', now());
  if used >= k.monthly_quota then raise exception 'quota_exceeded'; end if;

  insert into video_jobs (key_id, prompt) values (k.id, p_prompt) returning id into job;
  return job;
end $$;
```

Refund = `update video_jobs set status = 'failed'` → it stops counting automatically.

**Managing users (by hand, in Supabase's table editor):**
- Add user: generate a random key (`python -c "import secrets; print(secrets.token_urlsafe(24))"`), store its sha256 in `key_hash`, send the plain key to the user.
- Revoke: set `active = false`.
- Give someone more: raise their `monthly_quota`.

---

## 4. Video server (new: `video-server/`)

Small FastAPI app, separate from the local backend. No model, no GPU.

**Env vars (host secrets, never in git):**

| Var | What |
|---|---|
| `FAL_KEY` | Your fal.ai key. Only lives here. |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | DB access (service key stays server-side). |
| `FAL_MODEL` | Wan endpoint id on fal (confirm exact id in Phase 0). |

**Endpoints** (all need header `X-Invite-Key`):

| Method | Path | Does | Returns |
|---|---|---|---|
| `GET` | `/me` | Quota check | `{name, used, quota, left}` |
| `POST` | `/jobs` | Validate fields → build prompt → `reserve_clip` → submit to fal | `{job_id, left}` · `401` bad key · `429` quota used |
| `GET` | `/jobs/{id}` | Ask fal for status; on done/fail update DB | `{status: queued\|running\|done\|failed, video_url?, error?}` |

**Server pins the expensive knobs.** Model, duration (10 s) and resolution (1080p) are set on the server, not taken from the request. The client sends only the form choices (bag, color, location, lighting, style, people, motion); the server checks them against the known lists and builds the prompt itself. That way a modified client can't order pricier clips or send junk prompts.

Other rules:
- A user can only read their own jobs (`/jobs/{id}` checks `key_id`).
- If fal is unreachable when submitting → mark job `failed` (refund) and return `502`.
- A `reserved` job older than ~1 hour that fal reports as gone → mark `failed`.
- Use the `fal-client` Python package (`submit` / `status` / `result`).

---

## 5. Local app changes (existing code)

### Local backend (`backend/`)
- `constants.py`: add `CAMERA_MOTIONS` (e.g. *slow orbit around bag*, *slow push-in*, *side pan*, *handheld walk-along*, *static with subtle motion*) and `VIDEO_SERVER_URL`.
- Move/share `build_prompt()` + option lists so the video server uses the **same** wording (copy the lists into `video-server/` at first; share later only if they drift).
- New routes in `main.py`:
  - `POST /api/video` → forwards form to video server with `VIDEO_INVITE_KEY` from `.env`.
  - `GET /api/video/{id}` → polls video server; on `done`, downloads the `.mp4` into `outputs/` and writes a `.json` sidecar (prompt, model, motion, created). MP4 can't hold PNG-style text metadata, so the sidecar does that job.
  - `GET /api/video/quota` → proxies `/me` for the "clips left" badge.
- `history.py`: list `.mp4` + sidecar alongside PNGs; add `kind: "image" | "video"` to `HistoryItem`.
- `.env`: add `VIDEO_INVITE_KEY=` (document in README).

### Frontend (`frontend/`)
- `studio-form.tsx`: **Photo | Video** toggle. Video mode shows the same dropdowns + **Camera motion**, hides photo-only fields (model, count, seed, reference image, strength), shows **"X of 30 clips left this month"** and the fixed cost note "10 s · 1080p".
- Progress: no step counter for video — show status text + elapsed time ("Queued…", "Rendering… 1:12").
- `gallery.tsx` / `history-drawer.tsx`: render `<video controls>` for `kind: "video"`.
- `lib/schemas.ts` + `lib/api.ts`: video request/status types and calls.

---

## 6. Build phases

Each phase ends with something you can check.

- [ ] **Phase 0 — Verify before building (~$2–5 test spend)**
  - Create fal account; note **minimum top-up** and current **Wan price per second at 1080p**.
  - Confirm the exact Wan endpoint on fal supports **10 s and 1080p** text → video (older Wan versions top out at 5 s / 720p).
  - Run 3 sample bag prompts by hand in fal's playground. If quality is poor, test Kling with the same prompts before locking the model.
  - *Done when:* model id, price per clip, and min top-up are written into this file.
- [ ] **Phase 1 — Supabase**: create project, run §3 SQL, add one test key. *Done when:* calling `reserve_clip` 31 times with quota 30 fails on the 31st.
- [ ] **Phase 2 — Video server**: endpoints from §4, run locally against fal + Supabase. *Done when:* `curl` can create a job, poll it, and get a working video URL; a bad key gets `401`; an exhausted key gets `429`; a forced fal failure refunds the slot.
- [ ] **Phase 3 — Local backend**: `/api/video*` routes, download to `outputs/`, history listing. *Done when:* a clip requested from the local backend lands in `outputs/` with its sidecar.
- [ ] **Phase 4 — Frontend**: toggle, motion dropdown, quota badge, video in gallery/history. *Done when:* full click-through on one Mac.
- [ ] **Phase 5 — Deploy + invite**: deploy video server to free host (secrets in host settings), set `VIDEO_SERVER_URL`, create invite keys, small first fal top-up. *Done when:* a second person makes a clip from their own Mac.

**Tests to leave behind** (small, like `backend/test_pipeline.py`): quota reserve/refund logic, prompt building with motion, server refusing unknown option values.

---

## 7. Money

| | Per clip | Per user / month (30) | 5 users / month |
|---|---|---|---|
| Wan @ 10 s 1080p (est.) | ~$0.40–0.50 | ~$12–15 | **~$60–75 worst case** |
| Hosting (free tier) | — | — | $0 |
| Supabase (free) | — | — | $0 |

- fal credit is **prepaid** → it's also your hard ceiling. fal has **no built-in spend cap**, so top up in small amounts and refill as needed.
- Bought fal credits **expire after 365 days**.
- New fal accounts run **2 jobs at once**; extra jobs wait in the queue (not rejected). The limit rises automatically as you buy more credit.

Prices above come from comparison blogs (Nov 2026), not fal's own page — Phase 0 replaces them with real numbers.

---

## 8. Risks & known trade-offs

| Risk | Impact | Mitigation |
|---|---|---|
| Text → video: bag looks different in each clip | Not exact to the real product | Accepted for now. Photo → video (animate a generated photo) is the upgrade path if this matters. |
| Free host sleeps | First request after idle waits ~30–60 s | Show "Waking video server…" in UI. Upgrade to ~$5/mo host if annoying. |
| Supabase free pauses after ~1 week idle | Video requests fail until un-paused | Un-pause in dashboard; a weekly ping (cron) keeps it awake if needed. |
| fal key leak | Credit drained | Key only on server; small top-ups; rotate key in fal dashboard if suspected. |
| Invite key leak | That user's 30 clips used by someone else | Revoke (`active = false`) and issue a new one. |
| Wan quality not good enough | Clips not ad-ready | Switch `FAL_MODEL` to Kling (expect ~2× cost) — no code change. |
| Prices change | Budget off | Re-check fal pricing page monthly; quota table makes worst case easy to recompute. |

---

## 9. Not in scope (add later if needed)

- Photo → video (animate an existing photo).
- Sound / music on clips.
- Sharing clips between users or a central gallery.
- Self-service sign-up, email login, payments from users.
- Admin web page (Supabase table editor covers it).
- Per-user dollar budgets (clip count is enough while length/res are fixed).
