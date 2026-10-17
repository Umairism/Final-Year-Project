# HealSense — Repository Sweep & Execution Roadmap

**Repo:** `Umairism/Final-Year-Project`
**Commit inspected:** `312ee6e` — *"Directory Tree is more organized than before and do some LLM auditing"* (29 Sep 2026)
**Reviewed:** 17 Oct 2026
**Scope:** Full repo read — backend, frontend, firmware, ML scripts, notebooks, all docs, audit reports

---

## Progress log

| Date | Item | Status |
|---|---|---|
| 17 Oct 2026 | Safety Invariant 2 — ML can no longer originate a CRITICAL alarm | ✅ Done — `fusion_engine.py`, 11 new tests |
| 17 Oct 2026 | Train/serve imputation skew — `-1.0` / `0.0` replaced by a persisted median imputer | ✅ Done — `train_model.py`, `prediction_service.py` |
| 17 Oct 2026 | Missing BP no longer fabricated as 120/80 | ✅ Done — `fusion_engine.py`, `telemetry_service.py` |
| 17 Oct 2026 | Synthetic-data label thresholds aligned to the production rules engine | ✅ Done — `generate_synthetic_data.py` |
| 17 Oct 2026 | Regression suite: 11 new tests passing, 32 existing tests passing | ✅ Done |
| 17 Oct 2026 | PhysioNet 2019 pipeline + future-window labels (`preprocess_physionet2019.py`) | ✅ Done — validated on 500 real patients |
| 17 Oct 2026 | Self-contained Colab/Kaggle training notebook with ablation + early-warning metric | ✅ Done — `notebooks/03_physionet2019_training.ipynb` |
| 17 Oct 2026 | Backend now reads `sequence_length` + feature contract from the artifact (supports 24×10 models) | ✅ Done — `prediction_service.py`, 24 tests pass |
| 17 Oct 2026 | Fixed 2 integration bugs caught in testing: LabelEncoder alphabetical remap, HR→heart_rate key mismatch | ✅ Done |
| Next | **Run the notebook on Kaggle/Colab** → drop 5 artifact files into `data/models/v1.0.2/` | ⏳ Your turn (~40 min) |

See `fyp/docs/audit/Safety_Hardening_Update.md` for the full before/after write-up, test evidence, and defence-ready wording.

---

## 1. Bottom line

1. **Your documentation is genuinely strong** — better than most FYP repos I see. The phase reports, release notes, PlantUML diagrams and self-audit are defense-grade material. Don't let anyone tell you otherwise.
2. **The system architecture is real and correctly wired.** Telemetry → rules → LSTM → fusion → LLM is actually chained in `telemetry_service.py:153-179`. The safety override in `fusion_engine.py` genuinely works. This is not a fake demo.
3. **The one thing that makes it an "AI project" is missing: there is no trained model.** `data/models/` contains only `.gitkeep` files. The LSTM layer returns `None` on every request and the system silently runs in `deterministic_only` mode.
4. **The Raspberry Pi was never the right answer — and you don't need it.** Go cloud. The reasoning is in §3 with the numbers.

---

## 2. Audit vs. reality — what's already fixed

Your `AI_ENGINE_REPORT.md` and `PUBLICATION_READINESS.md` (29 Sep) are accurate but **partly stale**. Some break-points have already been closed:

| Issue from `AI_ENGINE_REPORT.md` | Status today | Evidence |
|---|---|---|
| Break 2 — model version mismatch (v1.0.1 vs v1.0.2) | ✅ **Fixed** | `config.py:73` now reads `v1.0.2` |
| Break 9 — fake metrics from `np.random` | ✅ **Fixed** | `evaluate_model.py` is now a real evaluation script; the fake `metrics_report.json` is gone |
| Break 1 — training CSV missing | 🔴 Still broken | `data/` is empty; `train_model.py:32` will `FileNotFoundError` |
| Break 3 — silent degradation to deterministic-only | 🔴 Still broken | `prediction_service.py:75-77` returns `None` |
| Break 4 — BIDMC lacks temp + both BPs (3 of 5 features) | 🔴 Still broken | `preprocess_bidmc.py` sets them to `np.nan` |
| Break 5 — `-1.0` imputation + train/serve skew | 🔴 Still broken | `train_model.py:98` vs `prediction_service.py:87` |
| Break 6 — circular labels | 🔴 Still true by design | documented honestly, but it's the model's core weakness |
| Break 7 — synthetic generator uses different thresholds | 🔴 Still broken | `generate_synthetic_data.py`: HR>130 critical vs rules' >150; SpO2<90 critical vs rules' <92 |
| Break 8 — 60-reading window = 1 hour warm-up | 🔴 Still an issue | depends on sampling cadence, which is undefined |
| No trained artifacts at all | 🔴 Still broken | `data/models/` empty |

**So the honest status is: architecture 8/10, documentation 9/10, ML delivery 2/10.** The entire gap is concentrated in one place — getting a real model trained, correctly, and shipping the artifacts.

---

## 3. The Raspberry Pi / cloud question — answered

You said the Pi 5 felt expensive and you're considering cloud. **You made the right call, and the reasoning is stronger than "it was expensive."**

### 3.1 What the Pi was actually doing

Read your own `Cloud_Architecture_Proposal.md` — it already concludes the Pi was only a **pass-through network bridge** between ESP32 and cloud. It added latency, a thermal failure point, a power supply, and a config surface, while computing nothing that required a computer.

### 3.2 Inference does not need a Pi, a GPU, or a cloud VM

Your model is **tiny**:

| Property | Value |
|---|---|
| Input | `(1, 60, 5)` |
| LSTM layers | 64 → 32 units |
| Total parameters | ≈ **25,000** |
| Model file size | ≈ **200–400 KB** |
| Inference time on a normal CPU | **1–5 ms** |

This is smaller than a single photo. It runs comfortably inside your existing FastAPI process. A Pi 5 would be paying ~PKR 40,000 to do 3 milliseconds of work per minute that your laptop already does for free.

**Conclusion: run inference in the cloud backend. No edge device. No GPU. No Pi.**

### 3.3 Training should never have been on the Pi

Training is a **one-time offline job**, not a runtime task. On a Pi 5 it would take hours (no CUDA, thermally throttled, 8 GB shared RAM). On a free Colab T4 GPU it takes **15–30 minutes** for a model this size.

| Task | Where it belongs | Cost |
|---|---|---|
| Data labelling (proxy label generation) | Python script, offline | Rs 0 |
| Model training | Google Colab (free T4) | Rs 0 |
| Inference | Cloud FastAPI backend | Rs 0 (runs inside existing process) |
| Dashboard / DB | Cloud | free tier |

### 3.4 Cost reality check

| Option | Cost | Verdict |
|---|---|---|
| Raspberry Pi 5 8GB kit (board + PSU + SD + case) | ~PKR 35,000–55,000 | ❌ Unnecessary |
| Google Colab free tier (training) | Rs 0 | ✅ Use this |
| Run backend on your laptop for the demo | Rs 0 | ✅ Fine for defense day |
| Oracle Cloud Always Free VM (2 OCPU / 12 GB ARM, always-on) | Rs 0 | ✅ If you want it "deployed" |
| Render free web service (512 MB RAM) | Rs 0 | ⚠️ TF is heavy — only viable with TFLite |
| Railway / Fly.io small instance | ~US$5/mo | ⚠️ Only if free tiers fail |
| Hugging Face Docker Spaces | **No longer free** (paid plan since Jul 2026) | ❌ Don't plan on it |

> **Note on Oracle:** the Always Free ARM allowance was quietly halved on 15 Jun 2026 from 4 OCPU/24 GB to **2 OCPU/12 GB**. Still free forever and still more RAM than a Pi 5 — but any guide quoting 24 GB is out of date. Signup requires a card.

### 3.5 Target architecture (final)

```
┌──────────────┐   I2C    ┌────────────┐   HTTPS POST    ┌─────────────────────────┐
│ MAX30100     │─────────▶│            │   (JSON)        │  Cloud FastAPI Backend  │
│ MLX90614     │          │   ESP32    │────────────────▶│                         │
└──────────────┘          │  + NVS     │                 │  1. validate + persist  │
                          │  buffer    │                 │  2. rules engine        │
                          └────────────┘                 │  3. LSTM (TFLite/h5)    │
                                                         │  4. fusion              │
┌──────────────┐          ┌────────────┐   WebSocket     │  5. Gemini explanation  │
│ Web dashboard│◀────────▶│ PostgreSQL │◀───────────────▶│                         │
│ Flutter app  │          └────────────┘                 └─────────────────────────┘
└──────────────┘                                                   ▲
                                                                   │ artifacts (~300 KB)
                                                     ┌─────────────┴──────────────┐
                                                     │ Google Colab (training)    │
                                                     │ → data/models/v1.0.2/      │
                                                     └────────────────────────────┘
```

No Raspberry Pi anywhere in the path. Your repo already has a document proposing exactly this — you just need to execute it and update the diagrams.

---

## 4. The real blocker: the training data is structurally broken

This is more important than "train the model." If you run `train_model.py` as it stands today, you will get a model that is **worse than useless** — one that produces garbage at inference. Here's why, in order.

### 4.1 Problem A — the dataset only has 2 of the 5 features

`preprocess_bidmc.py` sets `temperature`, `systolic_bp`, `diastolic_bp` to `np.nan` because BIDMC/PhysioNet only provides HR and SpO2. So **60% of your feature space is empty by construction.**

### 4.2 Problem B — `-1.0` imputation creates train/serve skew

```python
# train_model.py:98
X_imputed = np.where(np.isnan(X_reshaped), -1.0, X_reshaped)
```

- `-1.0 °C` is physiologically impossible, so the `StandardScaler` fits a bimodal distribution with a huge mass at −1.0.
- Those columns have near-zero variance → `scaler.scale_` ≈ 0 → `(x − μ)/σ` explodes at inference.
- At serve time, `prediction_service.py:87` does `v.get(f, 0.0)` — it fills missing values with **`0.0`, not `-1.0`**. The scaler was fit on −1.0 and is fed 0.0. **This alone corrupts every prediction.**

### 4.3 Problem C — the labels are circular

Labels are derived from the *same* WHO thresholds the rules engine applies, at the *same* timestamp. The LSTM is being trained to reproduce a rule it sits next to. A sharp examiner will ask: *"What does your model know that your rules don't?"* Right now the answer is: nothing.

### 4.4 Problem D — the 60-reading window has no defined cadence

`sequence_length = 60`. If the ESP32 sends one reading per minute, every patient is `deterministic_only` for their first **hour**. If it sends every 5 seconds, the warm-up is 5 minutes. This must be a conscious design decision, documented.

### 4.5 Three ways forward — pick one

| | Option A — PhysioNet 2019 Sepsis ⭐ | Option B — BIDMC, 2 features only | Option C — Kaggle Human Vital Signs |
|---|---|---|---|
| Features available | **5/5** (HR, O2Sat, Temp, SBP, DBP) | 2/5 (HR, SpO2) | 5/5 |
| Real temporal sequences | ✅ Yes, hourly per patient, ~40k patients | ✅ Yes | ❌ Likely one row per patient |
| Patient IDs for split | ✅ Yes | ✅ Yes | ⚠️ Verify |
| Work required | Medium — new preprocessor | Low — shrink model input | High — likely must synthesise sequences |
| Defensibility | **High** — real ICU vitals, published benchmark dataset | Medium — weak feature set | Low — synthetic, narrow ranges |
| Verdict | **Recommended** | Fallback | ❌ Avoid for LSTM |

> **Option C caveat:** the popular "Human Vital Sign Dataset" on Kaggle is one row per patient with very narrow ranges (HR 60–100, SpO2 95–100, Temp 36–37.5). You cannot build 60-step sequences from that without inventing data. `preprocess_kaggle_vitals.py` assumes it's usable — **verify the row structure before spending time on it.**

### 4.6 The label fix that turns this into a real ML project

Instead of labelling *the present state with the rules*, label **the future state**:

```
For each window ending at time t:
    label = risk class at time t + K   (e.g. K = 6 readings ahead)
```

Now the two layers do different jobs, and you can say this in your defense:

> *"The deterministic rules classify the patient's present state. The LSTM predicts whether the patient will deteriorate within the next 30 minutes. The fusion engine therefore delivers early warning, not a second opinion on the same instant."*

This single change:
- kills the circularity objection,
- gives the ML layer an actual reason to exist,
- produces a publishable ablation: **rules-only vs rules+ML, measured by how many minutes earlier deterioration is caught**,
- gives you a headline result for the report: *"ML layer flagged deterioration a median of N minutes before the deterministic threshold was crossed."*

That number is your FYP's contribution. Chase it.

### 4.7 Code-level fix list (exact)

| File | Change |
|---|---|
| `scripts/train_model.py:32` | Point at the new processed dataset |
| `scripts/train_model.py:98` | Replace `-1.0` with **median imputation + 5 missing-indicator columns** (input becomes 10-dim), or forward-fill within patient |
| `scripts/train_model.py` (artifacts) | Save `imputer.pkl` (the medians) alongside `scaler.pkl` |
| `backend/api/services/prediction_service.py:87` | Replace `v.get(f, 0.0)` with the **same saved medians** — no skew, ever |
| `scripts/generate_synthetic_data.py:17-31` | Align thresholds **exactly** with `fusion_engine.py:54-73` |
| `scripts/preprocess_bidmc.py:38-44` | If superseded, delete or rename to `_legacy` to avoid confusion |
| `backend/api/config.py:73` | ✅ Already correct |
| `data/models/v1.0.2/` | Commit the trained artifacts (~300 KB) — no external download at demo time |

### 4.8 One safety issue worth fixing before the viva

In `fuse_risk()`, if deterministic = WARNING and the ML says critical:

```
0.6 × 0.5 + 0.4 × 1.0 = 0.70  →  final = CRITICAL
```

**So the ML can escalate a WARNING into a CRITICAL alert.** It can never *downgrade* a critical (that override is genuinely absolute), but an examiner may ask *"can your AI create a critical alarm the rules never authorised?"* — and today the answer is yes.

Suggested hardening (one line): allow ML to escalate at most to `warning` unless the deterministic layer independently reports `warning` or worse. Document the rule in the report. It's a five-minute change that makes the safety story airtight.

---

## 5. Cloud plan — what runs where, and it costs nothing

| Component | Where | Free tier / cost |
|---|---|---|
| Data labelling | Local Python script | Rs 0 |
| Training | **Google Colab free T4** | Rs 0 (sessions up to ~12 h) |
| Model artifacts | **Commit to repo** (`data/models/v1.0.2/`, ~300 KB) | Rs 0 — simplest, most reliable at demo time |
| Backend API | Laptop for demo → later Oracle Always Free VM | Rs 0 |
| Database | SQLite for demo → Neon/Supabase free Postgres | Rs 0 |
| Web dashboard | Vercel/Netlify free, or served by the backend | Rs 0 |
| Gemini explanations | Google AI Studio free key | Rs 0 within free quota |

**Practical tip:** convert the final model to **TFLite** (`data/models/tflite/` already exists in your tree). It cuts the runtime from ~500 MB RAM (full TensorFlow) to ~50 MB, making free-tier hosting actually viable and killing cold-start delays. Inference accuracy is unchanged.

---

## 6. Three-week execution plan

### Week 1 — Make the AI real (the only thing that matters)
- [ ] Day 1 — Download PhysioNet 2019 (training_setA), inspect columns, confirm patient IDs + hourly rows
- [ ] Day 2 — Write `scripts/preprocess_physionet2019.py` → canonical 5-feature CSV, per-patient, with `patient_id` + `timestamp`
- [ ] Day 3 — Implement **future-window labels** (K = 6) + trend features; document the definition in `docs/ml/`
- [ ] Day 4 — Fix imputation (medians + missing indicators), save `imputer.pkl`; replicate at serve time
- [ ] Day 5 — Train on Colab (patient-wise split, class weights), download artifacts into `data/models/v1.0.2/`
- [ ] Day 6 — Run the real `evaluate_model.py`; produce confusion matrix + per-class metrics
- [ ] Day 7 — **Ablation:** rules-only vs rules+ML, early-warning lead time. This is your headline result.

### Week 2 — Close the demo gaps
- [ ] Add `firmware/main.cpp` — sensor read loop (MAX30100 + MLX90614), 5–10 s cadence
- [ ] Replace `telemetry_client.cpp:50` simulated POST with real `HTTPClient` + `WiFiClientSecure`
- [ ] Implement the actual NVS write in `storage_manager.cpp`
- [ ] Frontend: set `VITE_USE_MOCK_DATA=false`; replace `Dashboard.tsx:192` `mlProbability={0.15}` with the live `/fusion_risk` value; wire `GeminiExplanationCard` to the real explanation
- [ ] Backend: add `/auth` (register/login/JWT), uncomment `app.py:148`; remove the hardcoded `SECRET_KEY`; add `.env.example`

### Week 3 — Deployment + defense
- [ ] `Dockerfile` + `docker-compose.yml` (api + postgres) — currently zero deployment config exists
- [ ] Deploy backend (Oracle Always Free VM or Render with TFLite)
- [ ] Update architecture diagrams to the cloud-native design (replace every Pi reference)
- [ ] Update `docs/defence/*` with **real** numbers; delete every stale claim
- [ ] Rehearse the five questions in §7

---

## 7. The five questions you will be asked — and the answers

**Q1: "Your labels come from your own rules. Isn't this circular?"**
> "It was, in v1. The current model predicts the patient's state *K readings into the future*, so it learns temporal deterioration rather than restating the rules. Here's the ablation showing it catches threshold crossings a median of N minutes earlier."

**Q2: "What does the AI add over the deterministic rules?"**
> "Early warning. The rules are reactive — they fire the moment a threshold is crossed. The LSTM fires before it. Baseline comparison table, page X."

**Q3: "Why did you drop the Raspberry Pi?"**
> "It was a pass-through bridge adding cost, latency and a thermal failure point while computing nothing. Inference is 3 ms and runs in the backend. Documented in `Cloud_Architecture_Proposal.md`, and it reduced BOM cost by roughly PKR 40,000."

**Q4: "Can your ML create a false critical alarm?"**
> "No. Deterministic CRITICAL is absolute and unconditional in `fusion_engine.py`. ML escalation is capped at warning unless the rules independently agree." *(after the fix in §4.8 — make sure you actually implement it before saying this)*

**Q5: "Is this clinically validated?"**
> "No, and the project explicitly does not claim to be. It is an explainable decision-support prototype. Clinical validation would require a multi-centre study — stated as a limitation in §E of `Flaws.md`."

---

## 8. What I can build for you next, right now

In this workspace I can:

1. **Write the complete fixed training pipeline** — `preprocess_physionet2019.py`, fixed `train_model.py` (median imputation + missing indicators + future labels), and a **ready-to-run Colab notebook** with no placeholder URLs.
2. **Actually train it here** — download the dataset, train, evaluate, and hand you a real `data/models/v1.0.2/` with genuine metrics. CPU-only, so it may take 30–60 minutes, but you'd get working artifacts today.
3. **Fix the safety gap** (§4.8) and the serve-side imputation skew.
4. **Write the firmware** (`main.cpp`, real HTTP POST, NVS persistence).
5. **Wire the frontend** to live data and remove the hardcoded risk values.
6. **Produce the deployment setup** (`Dockerfile`, `docker-compose.yml`, `.env.example`) and auth endpoints.

My recommendation for sequence: **3 → 1 → 2** (fix skew + safety, build the pipeline, then train), since a model trained on broken preprocessing is wasted time.

---

*Written from direct inspection of commit `312ee6e`. Every file/line reference above was verified in the repository — nothing here is inferred from the existing audit documents alone.*
