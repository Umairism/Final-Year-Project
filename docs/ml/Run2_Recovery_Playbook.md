# Recover Run 2 Without Retraining

**Your trained model is safe.** Training finished and `lstm_best.h5` was written by the
checkpoint callback every time val_loss improved. Best weights are restored and on disk
at `/kaggle/working/healsense/v1.0.2/lstm_best.h5`.

You do **not** need to retrain. You need cells 7 and 8 (Evaluate, Save artifacts) to
run once.

---

## ⚠️ First: are the artifacts stale?

`scaler.pkl`, `label_encoder.pkl` and `imputer.pkl` are written **only** by the
"Save artifacts" cell. If that cell never completed, those three files are **from Run 1**
while `lstm_best.h5` is from Run 2 — a mismatched set. The smoke test can still "pass"
with stale files because it loads whatever is on disk.

Run this **before** doing anything else. It has no side effects:

```python
import os, time, joblib, tensorflow as tf
from pathlib import Path

OUT = Path("/kaggle/working/healsense/v1.0.2")
print("file                 size        modified")
for f in sorted(OUT.glob("*")):
    print(f"{f.name:20s} {f.stat().st_size/1024:8.1f} KB   "
          f"{time.strftime('%H:%M:%S', time.localtime(f.stat().st_mtime))}")

m   = tf.keras.models.load_model(OUT / "lstm_best.h5")
imp = joblib.load(OUT / "imputer.pkl")
print("\nmodel input     :", m.input_shape)
print("imputer seq_len :", imp.get("sequence_length"))
print("imputer n_feats :", imp.get("n_features"))
print("indicators      :", imp.get("include_missing_indicators"))
print("medians         :", {k: round(v, 2) for k, v in imp["medians"].items()})

ok = (m.input_shape[1] == imp.get("sequence_length")
      and m.input_shape[2] == imp.get("n_features"))
print("\nCONSISTENT:", ok)
```

**How to read it:**

- All five files share a **recent** timestamp → cell 8 *did* finish, you only lost the
  printed output. Proceed to the evaluation cell below and you are done.
- `lstm_best.h5` is recent but `scaler.pkl` / `imputer.pkl` are **older** → stale
  mismatch. Run the full recovery below.
- `CONSISTENT: False` → stale mismatch, same fix.

---

## Step 1 — Clear the stuck cells

The "already running, no output" state is almost always a **queue**, not a hang. On
Kaggle, clicking Run while another cell is executing queues it, and a queued cell shows
a spinner with no output.

1. **Run → Interrupt** (or the ■ stop button)
2. **Run → Restart Session** if the spinner persists after interrupting
   - This clears the kernel but **does not delete `/kaggle/working`** — your model stays
3. After restart, run cells **one at a time**, in order. Do not use "Run All" again for
   this recovery.

---

## Step 2 — Rebuild the data (skip if `X_te_f` still exists)

After a restart, memory is empty. Re-run cells in this order and **stop before training**:

| Cell | Action |
|---|---|
| 1 — Configuration | run |
| 2 — Get the data | run (skips download if the cache survived; otherwise ~3 min) |
| 3 — Preprocess | run (~2–4 min for the full cohort) |
| 4 — Split / impute / scale | run |
| **5 — Build model** | **SKIP** |
| **6 — Train** | **SKIP** ← this is where the 30 minutes went |

Confirm before continuing:

```python
print("X_te_f:", X_te_f.shape, "| y_te:", y_te.shape)
```

Expect something like `(46677, 24, 10)` — the exact count depends on the split.

---

## Step 3 — Evaluate + save, loading the model from disk

This replaces cells 7 and 8. It loads the **already-trained** model and does the full
report: classification table, ablation, weight sweep, early-warning capture, artifacts.

```python
import joblib, numpy as np, tensorflow as tf, json, time
from pathlib import Path
from sklearn.metrics import classification_report, confusion_matrix, f1_score

OUT = Path("/kaggle/working/healsense/v1.0.2")
NORMAL, WARNING, CRITICAL = 0, 1, 2
CLASS_NAMES = ["normal", "warning", "critical"]

model = tf.keras.models.load_model(OUT / "lstm_best.h5")
probs = model.predict(X_te_f, batch_size=512, verbose=1)
pred  = probs.argmax(1)

print("=" * 62)
print("LSTM vs FUTURE-WINDOW GROUND TRUTH")
print("=" * 62)
print(classification_report(y_te, pred, target_names=CLASS_NAMES,
                            digits=3, zero_division=0))
print(confusion_matrix(y_te, pred))

def current_severity(Xraw):
    out = np.zeros(len(Xraw), np.int8)
    hr, spo2, temp, sbp, dbp = (Xraw[:, -1, i] for i in range(5))
    with np.errstate(invalid="ignore"):
        crit = ((spo2 < 92) | (hr > 150) | (hr < 40) | (sbp >= 180) | (dbp >= 120))
        warn = ((spo2 < 95) | (hr > 120) | (hr < 50) | (temp >= 38) | (temp < 35))
    out[np.nan_to_num(warn, nan=False).astype(bool)] = WARNING
    out[np.nan_to_num(crit, nan=False).astype(bool)] = CRITICAL
    return out

rules_now = current_severity(X_te)
DET_SCORE = np.array([0.0, 0.5, 1.0])
ML_SCORE  = np.array([0.0, 0.5, 1.0])

weighted = 0.6 * DET_SCORE[rules_now] + 0.4 * ML_SCORE[pred]
fuse_w = np.where(weighted >= 0.7, CRITICAL, np.where(weighted >= 0.4, WARNING, NORMAL))
fuse_w = np.where(rules_now == CRITICAL, CRITICAL, fuse_w)
fuse_w = np.where((fuse_w == CRITICAL) & (rules_now != CRITICAL), WARNING, fuse_w)

fuse_or = np.maximum(rules_now, pred)
fuse_or = np.where((fuse_or == CRITICAL) & (rules_now != CRITICAL), WARNING, fuse_or)

print("")
print("=" * 62)
print("ABLATION — predicted vs FUTURE labels")
print("=" * 62)
print(f"{'Method':40s} {'macro-F1':>9s}  " + "  ".join(f"{n[:8]:>9s}" for n in CLASS_NAMES))
rows = [("Rules only (now)", rules_now), ("LSTM only", pred),
        ("Fusion A: weighted 0.6/0.4 (backend)", fuse_w),
        ("Fusion B: safety-first OR", fuse_or)]
for label, p in rows:
    print(f"{label:40s} {f1_score(y_te, p, average='macro', zero_division=0):9.3f}  "
          + "  ".join(f"{v:9.3f}" for v in f1_score(y_te, p, average=None, zero_division=0)))

print("")
print("=" * 62)
print("FUSION WEIGHT SWEEP")
print("=" * 62)
best_w, best_f1 = 0.6, -1.0
for w in np.arange(0.0, 1.01, 0.1):
    sc = w * DET_SCORE[rules_now] + (1 - w) * ML_SCORE[pred]
    fz = np.where(sc >= 0.7, CRITICAL, np.where(sc >= 0.4, WARNING, NORMAL))
    fz = np.where(rules_now == CRITICAL, CRITICAL, fz)
    fz = np.where((fz == CRITICAL) & (rules_now != CRITICAL), WARNING, fz)
    f1w = f1_score(y_te, fz, average="macro", zero_division=0)
    tag = "  <-- backend default" if abs(w - 0.6) < 1e-9 else ""
    mark = " *best*" if f1w > best_f1 else ""
    if f1w > best_f1:
        best_f1, best_w = f1w, w
    print(f"  det {w:.1f} / ml {1-w:.1f}   macro-F1 {f1w:.3f}{mark}{tag}")
print("")
print(f"Best split: det {best_w:.1f} / ml {1-best_w:.1f}  ->  {best_f1:.3f}")

pre_det = (y_te == CRITICAL) & (rules_now == NORMAL)
if pre_det.sum() > 0:
    caught = ((pred == CRITICAL) | (pred == WARNING))[pre_det].mean()
    print("")
    print("EARLY-WARNING CAPTURE")
    print(f"  pre-critical windows where rules say NORMAL: {pre_det.sum():,}")
    print(f"  fraction the LSTM already flags            : {caught*100:.1f}%")
    print(f"  fraction the rules flag                    : 0.0%")

# ── re-save every artifact so the set is internally consistent ──
joblib.dump(scaler, OUT / "scaler.pkl")
joblib.dump(le, OUT / "label_encoder.pkl")
CANON = ["heart_rate", "spo2", "temperature", "systolic_bp", "diastolic_bp"]
CANON_MAP = dict(zip(FEATURES, CANON))
joblib.dump({
    "feature_order": CANON,
    "dataset_columns": FEATURES,
    "medians": {CANON_MAP[k]: v for k, v in medians.items()},
    "clinical_fallbacks": {CANON_MAP[k]: v for k, v in FALLBACKS.items()},
    "strategy": "training_median",
    "include_missing_indicators": True,
    "sequence_length": SEQ_LEN,
    "n_features": len(FEATURES) * 2,
    "model_version": MODEL_VERSION,
}, OUT / "imputer.pkl")

print("")
print("Artifacts re-written to", OUT)
for f in sorted(OUT.glob("*")):
    print(f"  {f.name:20s} {f.stat().st_size/1024:8.1f} KB")
print("DOWNLOAD THESE NOW — /kaggle/working is wiped when the session ends.")
```

> This requires `scaler`, `le`, `medians`, `FEATURES`, `FALLBACKS`, `SEQ_LEN` and
> `MODEL_VERSION` to exist — they come from cells 3 and 4. If you skipped those,
> run them first.

---

## Step 4 — Download immediately

`/kaggle/working` is deleted when the session ends. Download the five files (or the
`.zip`) and commit them to `data/models/v1.0.2/` in the repo.

Then verify locally:

```bash
cd backend
DATABASE_URL="sqlite:///./_check.db" python -c "
from api.services.prediction_service import prediction_service
print('loaded:', prediction_service.load_artifacts())
print('seq_len:', prediction_service.sequence_length)
print('features:', prediction_service.n_input_features)
"
```

You want `loaded: True`, `seq_len: 24`, `features: 10`.

---

## Why the cells stuck

Ranked by likelihood:

1. **Queued, not hung.** A cell clicked while another runs shows a spinner with no
   output. `Run → Interrupt` clears it. Most likely explanation given the last cell ran.
2. **Kernel wedged after the GPU training loop.** Restart Session frees it; `/kaggle/working`
   is unaffected.
3. **Stale output confusion.** The smoke-test output you saw may be from an **earlier
   session** still rendered in the notebook. Timestamps in Step 1 settle this.

None of these affect your trained weights.
