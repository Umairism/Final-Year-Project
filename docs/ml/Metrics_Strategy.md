# Why 90% Accuracy Is the Wrong Target — and What to Report Instead

**Question:** can HealSense reach 90% accuracy, possibly by combining PhysioNet, Kaggle,
BIDMC and other datasets?

**Short answer:** No — not honestly, on this task. And pursuing it would make your system
*less* useful. But you **can** legitimately report a 90% figure. Section 5 shows how.

---

## 1. Where your model actually stands

| | Accuracy |
|---|---|
| Trivial baseline (always predict "normal") | **54.98 %** |
| Your Run 1 model | **61.3 %** |

Your model beats the trivial baseline by only 6.3 points on accuracy. That looks bad.
It isn't — accuracy is the wrong lens for a 55/33/12 problem.

---

## 2. What the literature reports on this exact dataset

PhysioNet/CinC 2019 is one of the most heavily contested clinical ML benchmarks in
existence — 104 teams, 853 entries.

| Source | Reported accuracy |
|---|---|
| Team ranked 31/79 (CinC2019-034) | 0.761 (hospital A) · 0.863 (hospital B) · **0.694 (hospital C)** |
| Ensemble entry (CinC2019-317) | AUROC 0.744–0.792 |
| Top-5 utility scores | 0.426 · 0.410 · 0.408 |
| Typical AUROC across entrants | 0.75 – 0.82 |

**No competitive entrant reports 90% accuracy.** The published range for this task is
**0.69 – 0.86**, and that is for predicting *actual Sepsis-3 labels*, which correlate
directly with the features.

Your task — predicting **rules-derived future-window severity** — carries additional
irreducible noise (see §3), so the ceiling is similar or lower.

---

## 3. Why 90% is mathematically unreachable here

### 3.1 Temperature is missing 65.8% of the time — and the label depends on it

Your warning label triggers on `Temp ≥ 38.0 °C`. But temperature is absent for
**two thirds of all hourly readings**.

The model is asked to predict a label frequently determined by a variable it **cannot
observe** for 65.8% of the record. This is an information-theoretic ceiling, not a
modelling failure. No architecture fixes it.

### 3.2 Genuine unpredictability of acute events

A patient can spike a fever, bleed, or throw an arrhythmia between hour *t* and
*t+6* for reasons no prior trajectory encodes. Published AUPRC on this dataset is
**0.05–0.10** — meaning even the best systems have very low precision at realistic
alert rates. That is the field's honest state, not your shortfall.

### 3.3 Class overlap between "warning" and "critical"

Once SpO₂ drops below 95%, the distinction between warning and critical often hinges on
one noisy value crossing a threshold. Adjacent windows are near-identical yet carry
different labels. That caps achievable accuracy well below 90%.

### 3.4 Your label is a **maximum over a future window**

`label = max(severity(t+1 … t+6))`. A single aberrant reading anywhere in those six hours
sets the label. This is deliberately a hard target — and it is why the model is useful.

---

## 4. Four ways to "hit 90%" — and why each would fail your viva

### ❌ Leak 1: random split instead of patient-wise

The most common inflation in student projects. With ~11 windows per patient, a random
split puts the *same patient's adjacent hours* in both train and test. The model
recognises the patient, not the physiology.

**Effect:** typically +10 to +20 accuracy points. Would plausibly push you past 90%.
**Cost:** the entire result is invalid. Any examiner who asks "how did you split?" ends it.

You already do patient-wise splitting. **Do not change it.**

### ❌ Leak 2: predict *current* state instead of future

The label becomes a deterministic function of the same 5 features the model sees. It
learns the thresholds almost perfectly → 95%+ accuracy.

**Cost:** this is exactly the circularity we removed from v1. The model would know
nothing the rules don't. Your `AI_ENGINE_REPORT.md` already identifies this as Break 6 —
an examiner can read it.

### ❌ Leak 3: partial-window validation

Evaluate only on windows near sepsis onset and skip the rest of the stay. This hides
false-positive alarms and inflates every metric (documented practice in the literature:
*"risks inflating performance estimates by reducing exposure to false-positive alarms"*).

**Cost:** it is a recognised methodological flaw. Your full-window evaluation is correct.

### ❌ Leak 4: collapse to binary "stable vs unwell"

Higher accuracy, but it destroys the three-tier information your rules engine and
dashboard are built around.

**Cost:** contradicts your own architecture.

### The cautionary example

> A hospital's sepsis prediction system reported **92% accuracy** but **failed to identify
> 40% of critical cases** due to dataset imbalance.

A system that misses 40% of deteriorating patients while displaying "92% accuracy" is
*worse* than one reporting 61% honestly. In a clinical decision-support context,
accuracy conceals exactly the failure mode that kills people.

---

## 5. What you *can* legitimately report as "90%"

**Report 90% as sensitivity at a defined operating point.** This is standard clinical ML
practice — models are quoted as *"at 90% sensitivity, specificity was X."*

You are already close. Critical recall is **0.538** at the default argmax threshold.
By lowering the critical decision threshold you can trade precision for recall and
operate at ≥90% sensitivity for the critical class.

```python
from sklearn.metrics import roc_curve, roc_auc_score

# one-vs-rest for the critical class
y_crit = (y_te == 2).astype(int)
p_crit = probs[:, 2]

print("AUROC (critical vs rest):", round(roc_auc_score(y_crit, p_crit), 3))

for target_sens in [0.80, 0.85, 0.90, 0.95]:
    fpr, tpr, thr = roc_curve(y_crit, p_crit)
    idx = np.searchsorted(tpr, target_sens)
    if idx < len(thr):
        print(f"  sensitivity {target_sens:.2f} -> threshold {thr[idx]:.3f}, "
              f"specificity {1-fpr[idx]:.3f}")
```

If critical-vs-rest **AUROC lands around 0.85–0.92**, you can honestly write:

> "For binary critical-state detection the model achieves an AUROC of 0.XX, and at a
> 90% sensitivity operating point a specificity of 0.YY, with an early-warning capture
> of 61.4% — against 0% for the deterministic rules."

That is a **far stronger claim** than 90% accuracy, and it is true.

---

## 6. On combining PhysioNet + Kaggle + BIDMC + others

**This would make your model worse, not better.** Four concrete reasons.

### 6.1 BIDMC cannot supply your features

BIDMC provides **HR and SpO₂ only**. Temperature, systolic and diastolic BP are absent.
Adding it means ~60% of your feature space is imputed for those patients — while your
label depends on temperature. You would be training on fabricated inputs.

### 6.2 The Kaggle "Human Vital Signs" set has no temporal structure

One row per patient, narrow ranges (HR 60–100, SpO₂ 95–100, Temp 36–37.5). Almost no
warnings, no criticals, no sequence. You cannot build 24-step windows from it.
This is the same conclusion as `preprocess_kaggle_vitals.py` — verify before trusting it.

### 6.3 Different datasets use different label definitions

BIDMC's preprocessor labelled `HR > 120 → warning`; your production rules use
`HR > 150 → critical`. Merging datasets with **inconsistent thresholds** injects label
noise that the model cannot resolve — it sees identical vitals mapped to different labels.

### 6.4 Cross-site transfer is a known hard problem, not a free win

From the Challenge organisers directly:

> *"Algorithms generally performed worse on test data from hospital system C than
> hospital systems A and B."*

Team 31/79 fell from 0.863 accuracy on hospital B to **0.694 on hospital C** — a
hospital it never trained on. Adding more heterogeneous sites usually *degrades*
in-distribution performance rather than improving it.

### What *is* legitimate and valuable

**Train on set A, test on set B.** Different hospital system, same schema, same label
definitions. That is genuine **external validation** — a real contribution to your
thesis, and far more impressive than an inflated accuracy number.

---

## 7. If you genuinely want better performance — ranked by value

| # | Change | Effort | Expected gain | Legitimacy |
|---|---|---|---|---|
| 1 | **Threshold tuning** for the critical class | 10 min | Large on recall | ✅ Standard practice |
| 2 | **Report AUROC / AUPRC** per class | 15 min | None (reveals true quality) | ✅ Standard practice |
| 3 | **Add trend features** (Δ over 6h, rolling std/min/max) | 1 h | Moderate | ✅ Sound |
| 4 | **Use more of the 40 PhysioNet columns** — lactate, WBC, creatinine, BUN | 3–4 h | **Largest single gain** | ✅ Strong |
| 5 | **External validation on set B** | 1 h | None (credibility) | ✅ Excellent for the thesis |
| 6 | Ensemble / attention layer | 2–3 h | Small | ✅ Sound |
| 7 | Combine unrelated datasets | Days | **Negative** | ❌ Do not |

### Why #4 is the real answer

Your model currently uses **5 of 40** available columns. Lactate and creatinine are among
the strongest known sepsis predictors — and critically, **the deterministic rules cannot
see them**.

That directly strengthens your central argument:

> "The rules engine is restricted to five bedside vitals. The temporal model additionally
> consumes laboratory values — lactate, WBC, creatinine — that the rules have no access
> to. This is a structural, not merely statistical, reason the ML layer can outperform
> the rule baseline."

The 5-vital canonical vector stays intact for the **fusion** path, so your architecture is
unchanged. Only the ML input widens.

**Caveat:** with a deadline near, this is a real change. Only attempt it if you have a
clean week. Otherwise #1 and #2 give you most of the credibility for an hour's work.

---

## 8. What actually wins marks in a clinical CDSS defence

Not accuracy. Examiners in this domain look for:

| Criterion | Your current status |
|---|---|
| Sensitivity for the critical class | 0.538 — report it, and tune it up |
| Early-warning capability vs baseline | **61.4% vs 0%** — your strongest result |
| Honest baseline comparison | ✅ rules-only ablation |
| Safety invariants enforced | ✅ two invariants, unit-tested |
| Split methodology | ✅ patient-wise |
| Disclosure of limitations | ✅ thorough |
| Accuracy alone | ❌ the wrong yardstick |

The line that should anchor your defence:

> "Accuracy is not an appropriate primary metric for a three-class, imbalanced clinical
> warning system: a trivial majority classifier already achieves 55%, and a model can
> report 92% accuracy while missing 40% of critical cases. We therefore report per-class
> precision/recall, macro-F1, AUROC, and early-warning capture against a rules-only
> baseline. On that basis the temporal model nearly doubles critical-class F1 over the
> deployed rule engine (0.426 vs 0.276) and flags 61.4% of pre-critical windows the rules
> report as normal."
