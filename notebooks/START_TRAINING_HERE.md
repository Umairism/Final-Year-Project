# Start Training in ~5 Minutes

Everything is built and validated. Follow this exactly.

---

## Step 1 — Pick where to run (2 min)

| | **Kaggle** ⭐ recommended | **Colab** |
|---|---|---|
| GPU | P100 16 GB, ~30 h/week | T4, not guaranteed |
| Dataset | **already hosted — no download** | downloads in ~4 min |
| Session | 9 h | 12 h, disconnects on idle |

**Kaggle path:**
1. <https://www.kaggle.com> → *Create* → *New Notebook*
2. Right panel → *Add Input* → search `salikhussaini49/prediction-of-sepsis` → **Add**
3. *File → Import Notebook* → upload `03_physionet2019_training.ipynb`
4. *Settings → Accelerator → GPU P100*

**Colab path:**
1. <https://colab.research.google.com> → *File → Upload notebook*
2. `03_physionet2019_training.ipynb`
3. *Runtime → Change runtime type → T4 GPU*

---

## Step 2 — Set the config (cell 0, 20 seconds)

```python
SEQ_LEN   = 24        # leave at 24 — see the warning below
HORIZON   = 6         # predict deterioration 6 hours ahead
PRESET    = "medium"  # small | medium | large
EPOCHS    = 25
USE_DRIVE = True      # checkpoints survive disconnects (Colab)
```

**First run?** Set `N_PATIENTS_LIMIT = 3000` and `EPOCHS = 5` to get a result in
**~6 minutes**. Confirm the whole path works, then set it back to `None` and
re-run for the real model.

---

## Step 3 — Run all cells

`Runtime → Run all` (Colab) or `Run → Run All` (Kaggle).

Expect at the end:

```
✅ Generalising well.
ABLATION — predicted vs FUTURE labels
Rules only (now)              0.4xx
LSTM only                     0.4xx
Fusion (rules + LSTM, capped) 0.4xx
EARLY-WARNING CAPTURE: xx.x%   ← put this number in your report
Saved to .../v1.0.2
  imputer.pkl / label_encoder.pkl / lstm_best.h5 / model_meta.json / scaler.pkl
✅ Artifacts are backend-compatible.
```

---

## Step 4 — Bring the artifacts home

Download `lstm_best.h5`, `scaler.pkl`, `label_encoder.pkl`, `imputer.pkl`,
`model_meta.json` and place them in:

```
data/models/v1.0.2/
```

Commit them (~450 KB). The backend already knows how to load them — no code
changes needed.

> ⚠️ **Do not commit the private Kaggle/Colab dataset** — only these 5 small files.

---

## ⚠️ Read this before changing `SEQ_LEN`

Measured on 500 real patient files (PhysioNet training set A):

| `SEQ_LEN` | Patients used | Windows | Critical % |
|---|---|---|---|
| **24** | **367** | **7,899** | **11.3%** |
| 60 (your original) | 19 | 891 | 15.5% |

Mean ICU stay is 38.8 hours. **A 60-hour window discards 95% of patients and
inflates critical prevalence by 37%** — the survivors are the long-stay sickest
patients. `SEQ_LEN = 24` is not a compromise; 60 would produce a biased model.

---

## On "maximum parameters"

`PRESET` gives you:

| Preset | LSTM units | Params | Use when |
|---|---|---|---|
| `small` | 64 → 32 | ~33k | Baseline / if overfitting |
| **`medium`** | **128 → 64** | **~150k** | **Default** |
| `large` | 256 → 128 | ~600k | Only if `medium` shows no overfit |

**Bigger is not better here.** The labels are a deterministic function of 5
numbers. A larger network memorises the rule boundaries faster — it does not
gain clinical insight. The notebook prints a train/val gap after training:

- gap ≤ 0.05 → generalising, safe to try `large`
- gap > 0.05 → **go smaller**, not larger

The thing that earns marks is the **ablation table** and **early-warning
capture**, not parameter count. An examiner will not ask how many parameters you
used; they will ask what the model knows that the rules don't — that's what
`EARLY-WARNING CAPTURE` answers.

---

## What was already validated in this workspace

| Check | Result |
|---|---|
| Preprocessing on 500 real patients | ✅ 367 used, 7,899 windows |
| Full notebook run (TF 2.21, CPU) | ✅ end-to-end, 3 epochs, no errors |
| Class-order bug | 🐛 found & fixed — `LabelEncoder` sorts alphabetically and would have remapped every class |
| Column-name mismatch (`HR` vs `heart_rate`) | 🐛 found & fixed — artifacts now use canonical keys |
| Backend loads 24×10 artifact | ✅ `seq_len=24`, 10 input features, indicators on |
| Backend handles missing BP | ✅ imputed from training medians |
| Existing test suite | ✅ 24 passed |

---

## Troubleshooting

**"No data"** — on Kaggle the dataset must be added as *Input* first.
On Colab, re-run cell 1; it auto-detects an existing Drive copy.

**GPU not detected** — `Runtime → Change runtime type → GPU`. On Kaggle check
the right-hand *Session options* panel.

**Session disconnected mid-training** — set `USE_DRIVE = True` (Colab). The
checkpoint at `MyDrive/healsense/v1.0.2/lstm_best.h5` holds the best epoch.
Re-running from scratch is unnecessary; the best weights are already saved.

**Metrics look weak (< 0.5 macro-F1)** — check `N_PATIENTS_LIMIT`. A 3,000-patient
smoke run is not representative. Use `None` for the real result, and give it the
full 25 epochs.

**All predictions are one class** — class weights are already balanced; this
usually means too few epochs or a very small `N_PATIENTS_LIMIT`.
