# HealSense — Experiment Log

All runs use: `SEQ_LEN=24`, `HORIZON=6`, patient-wise 70/15/15 split, PhysioNet/CinC 2019,
future-window labels, median imputation + 5 missing-indicators, frozen test set.

---

## Run 1 — BASELINE (completed)

**Date:** 17 Oct 2026
**Notebook:** v4 (`HealSense_Training_v4.ipynb` / BUILD `v3-2026-10-17`, pre weight-sweep)
**Platform:** Kaggle · GPU P100

### Configuration

| Parameter | Value | Note |
|---|---|---|
| `PRESET` | `medium` | 124,931 params |
| `SEQ_LEN` / `HORIZON` | 24 / 6 | |
| `EPOCHS` | 25 (early-stopped at 9) | **best epoch = 4** |
| `BATCH` | 256 | |

### Data

| | Value |
|---|---|
| Files downloaded | 40,000 of 40,336 → **20,029 usable** ⚠️ |
| Patients used | 14,961 (5,068 skipped, stay < 24 h) |
| Windows | 317,749 |
| Train / Val / Test | 222,287 / 48,785 / 46,677 |
| Train patients | 10,472 |
| Class balance | normal 54.98 % · warning 32.73 % · critical 12.29 % |
| Missingness | HR 5.4 % · O2Sat 9.3 % · Temp 65.8 % · SBP 12.7 % · DBP 42.6 % |

> ⚠️ **Known defect:** `training_setB` was never downloaded. Set B files are named
> `p100001–p120000`; the loader requested `p000001–p020000`, so all 20,000 requests
> 404'd silently. **Run 1 used training set A only — half the cohort.** Fixed in v5.

### Training

| Metric | Value |
|---|---|
| Final train acc | 0.6397 |
| Final val acc | 0.5848 |
| **Train/val gap** | **+0.0550 → overfitting flagged** ⚠️ |
| Best epoch | 4 |
| Epoch of early stop | 9 |

### Test results — LSTM vs future-window ground truth

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| normal | 0.748 | 0.719 | 0.733 | 26,035 |
| warning | 0.528 | 0.456 | 0.489 | 14,912 |
| critical | 0.352 | 0.538 | 0.426 | 5,730 |
| **accuracy** | | | **0.613** | 46,677 |
| **macro avg** | 0.543 | 0.571 | **0.549** | |

Confusion matrix:

```
              pred normal  pred warning  pred critical
true normal        18723          4700           2612
true warning        5050          6800           3062
true critical       1261          1386           3083
```

### Ablation

| Method | macro-F1 | normal | warning | critical |
|---|---|---|---|---|
| Rules only (current state) | 0.471 | 0.761 | 0.375 | 0.276 |
| **LSTM only** | **0.549** | 0.733 | 0.489 | **0.426** |
| Fusion A — weighted 0.6/0.4 (deployed) | 0.477 | 0.752 | 0.404 | 0.276 |
| Fusion B — safety-first OR | 0.518 | 0.731 | 0.547 | 0.276 |

### Headline metrics

| Metric | Value |
|---|---|
| **Early-warning capture** | **61.4 %** (3,180 pre-critical windows flagged) |
| Rules-engine capture on same windows | 0.0 % (reactive by definition) |
| LSTM vs rules, macro-F1 lift | +0.078 |
| LSTM vs rules, critical-F1 lift | +0.150 (**+54 % relative**) |

### Artifacts

`/kaggle/working/healsense/v1.0.2/` → `lstm_best.h5` (1,544.6 KB), `scaler.pkl`,
`label_encoder.pkl`, `imputer.pkl`, `model_meta.json`

### Findings (for the report)

1. **The LSTM substantially outperforms the reactive rules.** macro-F1 0.549 vs 0.471;
   critical F1 0.426 vs 0.276. This is the core result.
2. **61.4 % of pre-critical windows are flagged while the rules report normal.** The
   rules are reactive by construction and capture 0 % of these.
3. **The deployed 0.6/0.4 fusion weight is sub-optimal.** Fusion A (0.477) barely
   improves on rules-only (0.471) despite the LSTM alone scoring 0.549 — the weighting
   over-emphasises the weaker signal. To be quantified by the sweep in run 2.
4. **The `medium` preset overfits at this scale** (gap +0.055, best epoch 4 of 9).
   Motivates `small` in run 2.

### Threats to validity (state these explicitly)

- Trained on **set A only** (half the intended cohort) due to the loader defect.
- Labels are **rules-derived future-window proxies**, not clinical sepsis outcomes.
- `Temp` is missing in 65.8 % of rows; imputation compresses its variance.
- Overfitting was present and unaddressed in this run.

---

## Run 2 — TUNED (planned)

**Changes from Run 1 — exactly three, everything else frozen:**

| Parameter | Run 1 | **Run 2** | Rationale |
|---|---|---|---|
| `PRESET` | `medium` | **`small`** | Run 1 gap was +0.055; smaller model should fit better |
| `N_PATIENTS_LIMIT` | (defect) 20k | **`None`** | v5 fixes the set B naming → true ~40k cohort |
| Notebook | v4 | **v5** | adds weight sweep + download fix |

**Predictions to check (write these down before running — it makes the report stronger):**

- [ ] Patient count roughly **doubles** (~14.9k → ~30k)
- [ ] Train/val gap **drops below 0.05**
- [ ] Critical F1 **improves** on the larger cohort
- [ ] Weight sweep will show 0.6 is **not** optimal; expect best near det 0.2–0.4

### Results — training (complete)

| | Value |
|---|---|
| Total params | 33,923 |
| Steps per epoch | 1,715 (Run 1: 869 → ~2× data ✅) |
| Best epoch | **9** |
| Early stop epoch | 14 |
| Train acc / Val acc | 0.6303 / 0.5958 |
| **Train/val gap** | **+0.0345 ✅** (Run 1: +0.0550) |
| Overfit flag | cleared — "Generalising well" |

**Predictions vs outcome**

| Prediction | Result |
|---|---|
| Patient count roughly doubles | ✅ 869 → 1,715 steps/epoch |
| Train/val gap drops below 0.05 | ✅ 0.0550 → 0.0345 |
| Weight sweep shows 0.6 not optimal | ⏳ pending |
| Critical F1 improves on larger cohort | ⏳ pending |

**Artifacts (Run 2, confirmed):** `lstm_best.h5` **439.7 KB** — consistent with the
`small` preset (33,923 params). Run 1's `medium` model was 1,544.6 KB, so the smaller
file confirms this is the Run 2 model, not a leftover. Also `scaler.pkl` 0.7 KB,
`label_encoder.pkl` 0.4 KB, `imputer.pkl` 0.4 KB, `model_meta.json` 1.2 KB, packaged
as `healsense_model.zip`.

> **Evaluation PENDING.** The *Evaluate* and *Save artifacts* cells produced no output
> (stuck/queued). The trained model at `/kaggle/working/healsense/v1.0.2/lstm_best.h5`
> is intact — **no retraining needed.** Recovery: `RECOVER_RUN2.md`.
>
> ⚠️ **Artifact integrity:** `scaler.pkl`, `label_encoder.pkl`, `imputer.pkl` are written
> only by the Save cell. If it never completed, those are from Run 1 while the model is
> from Run 2 — a mismatched set. Check timestamps before committing.

**Data (fill in once evaluation runs)**

| | Value |
|---|---|
| Patients used | |
| Windows | |
| Train / Val / Test | |
| Train patients | |


**Ablation**

| Method | macro-F1 | normal | warning | critical |
|---|---|---|---|---|
| Rules only | | | | |
| LSTM only | | | | |
| Fusion A (0.6/0.4) | | | | |
| Fusion B (safety-first OR) | | | | |

**Weight sweep**

| det / ml | macro-F1 |
|---|---|
| 0.0 / 1.0 | |
| 0.2 / 0.8 | |
| 0.4 / 0.6 | |
| 0.6 / 0.4 (default) | |
| 0.8 / 0.2 | |
| **best** | |

**Headline**

| | Value |
|---|---|
| Early-warning capture | |
| vs Run 1 (61.4 %) | |

---

## Run 1 vs Run 2 — comparison table

| Metric | Run 1 (baseline) | Run 2 (tuned) | Δ |
|---|---|---|---|
| Preset | medium (124,931) | small (33,923) | |
| Patients | 14,961 | | |
| Windows | 317,749 | | |
| Train/val gap | +0.0550 ⚠️ | | |
| macro-F1 (LSTM) | 0.549 | | |
| critical F1 (LSTM) | 0.426 | | |
| critical F1 (Fusion A) | 0.276 | | |
| Early-warning capture | 61.4 % | | |
| Best fusion weights | 0.6/0.4 (assumed) | | |

---

## Suggested report framing

Present Run 1 as an **honest baseline with disclosed limitations**, then Run 2 as the
**corrected configuration**. Examiners respond well to a documented iteration:

> "The first implementation achieved a macro-F1 of 0.549 with an early-warning capture
> of 61.4 %, but exhibited a train/validation gap of 0.055 and — due to a data-loading
> defect discovered after the fact — was trained on only half the available cohort.
> Both issues were corrected: the model was reduced to 33,923 parameters and the full
> 40,336-patient cohort was used. This yielded [Run 2 results]."

Disclosing the defect yourself is much stronger than having it found in the viva.

---

## Operational reminders

- **Download artifacts immediately** after each run — `/kaggle/working/` is wiped at
  session end. Zips are also written to the working directory.
- Commit artifacts to `data/models/v1.0.2/` in the repo; the backend reads
  `sequence_length`, feature order and medians from `imputer.pkl`.
- Kaggle sessions cap at 9 h; the checkpoint saves every epoch and the best weights are
  restored automatically.
