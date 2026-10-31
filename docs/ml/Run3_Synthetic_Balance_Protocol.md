# HealSense Run 3 Synthetic Class-Balancing Protocol & Evaluation Gate

## 1. Executive Summary & Protocol Principles
This document defines the evaluation gate and protocol for **Run 3 (Synthetic Class-Balancing Experiment)** for the HealSense LSTM vital sign classification pipeline.

### Data Split & Leakage Prevention Rules
1. **Patient-Level Splitting First**: Patients are partitioned into train, validation, and test splits strictly before any balancing or augmentation takes place. No patient records span across splits.
2. **Training-Only Augmentation**: Synthetic and augmented samples are derived exclusively from the training set patients.
3. **Imputation & Normalization Hygiene**: Imputation medians and feature scalers (`StandardScaler`/`RobustScaler`) are fitted strictly on real training windows only, then transformed across validation/test.
4. **Natural Prevalence for Evaluation**: Validation and test sets remain 100% real PhysioNet windows reflecting real-world clinical prevalence. No synthetic samples enter validation or test sets.

---

## 2. Historical Baselines & Established Facts

| Metric / Fact | Run 1 Baseline | Run 2 Current Deployed (v1.0.2) |
|---|---|---|
| **Model Version** | v1.0.1 | v1.0.2 |
| **Artifact Directory** | `data/models/v1.0.1` | `data/models/v1.0.2` |
| **Validation Accuracy** | — | 0.5958 |
| **Validation Macro-F1** | — | — |
| **Test Accuracy** | 0.6130 | Not retained |
| **Test Macro-F1** | 0.5490 | 0.5675 (retained) |
| **Normal F1** | 0.7330 | Not retained |
| **Warning F1** | 0.4890 | Not retained |
| **Critical F1** | 0.4260 | Not retained |
| **Derived Class Dist.** | Normal: 54.98%, Warning: 32.73%, Critical: 12.29% | Same derived distribution |

> **IMPORTANT FACT:** The historical 93.66% binary figure in legacy documentation was an uncalibrated synthetic/binary artefact and is **superseded**. It must not be cited or quoted as the final PhysioNet three-class result.

---

## 3. Run 3 Experiment Configuration & Completed Run Results

Umair executed `HealSense_Training_v6_SyntheticBalance_2026-10-28.ipynb` (SHA-256: `230835c456ec614572908be7e3ce91d9b2ec164f98f611b89bc6e4513e4b69a1`).
Build signature: `BUILD v6-synthetic-balance-2026-10-28`.

### Patient & Window Counts
- **Usable Patients:** 29,244
- **Full Derived Windows:** 628,091
- **Real Natural Class Distribution:** Normal 52.73%, Warning 31.93%, Critical 15.34%
- **Synthetic Training Windows Generated:** 163,961 (for `synthetic_augmentation`)
- **Final Training Set Distribution (Synthetic):** Normal 38.46%, Warning 30.77%, Critical 30.77%
- **Final Training Set Distribution (None):** Normal 52.81%, Warning 31.74%, Critical 15.45% (231,641 / 139,248 / 67,757)

### Metrics Matrix

| Metric | v6 None (`v1.0.3-none`) | v6 Oversample (`oversample`) | v6 Synthetic (`v1.0.3-synthetic`) |
|---|---|---|---|
| **Training Epochs** | Best: 5, Early stop: 10 | *(Not authorized)* | Best: 7, Early stop: 12 |
| **Validation Accuracy** | **0.6110** | — | **0.6099** |
| **Validation Balanced Acc**| **0.5827** | — | **0.5738** |
| **Validation Macro-F1** | **0.5676** | — | **0.5639** |
| **Validation Weighted-F1** | **0.6177** | — | **0.6163** |
| **Validation Normal F1** | **0.718** | — | 0.707 |
| **Validation Warning F1** | 0.532 | — | **0.542** |
| **Validation Critical F1**| **0.453** | — | 0.443 |
| **Validation Crit. Precision**| 0.392 | — | **0.409** |
| **Validation Crit. Recall**| **0.536** | — | 0.516 |
| **Test Accuracy** | **0.6113** (raw JSON: 0.6190) | — | **0.6088** |
| **Test Balanced Accuracy** | **0.5871** (raw JSON: 0.5850) | — | **0.5805** |
| **Test Macro-F1** | **0.5714** (raw JSON: 0.5727) | — | **0.5685** |
| **Test Weighted-F1** | **0.6178** (raw JSON: 0.6238) | — | **0.6156** |
| **Test Normal F1** | **0.716** (raw JSON: 0.729) | — | 0.707 |
| **Test Warning F1** | 0.528 (raw JSON: 0.523) | — | **0.542** |
| **Test Critical F1** | **0.471** (raw JSON: 0.466) | — | 0.456 |
| **Test Critical Precision**| 0.408 (raw JSON: 0.412) | — | 0.409 |
| **Test Critical Recall** | **0.556** (raw JSON: 0.535) | — | 0.516 |
| **Early-Warning Capture** | **67.6%** | — | 66.8% |

### Test Confusion Matrix (v1.0.3-none)
```
[[33875, 10335,  5613],
 [ 8277, 15952,  6138],
 [ 2701,  3769,  8102]]
```

---

## 4. Formal Run 3 Decision & Gate Verdict

### Formal Decision:
1. **`synthetic_augmentation` is REJECTED for deployment.**
   - Versus the `none` baseline, synthetic augmentation was demonstrably inferior across virtually all clinical and statistical dimensions: lower validation/test accuracy, lower balanced accuracy, lower macro-F1, lower weighted-F1, lower normal F1, lower critical F1, lower critical recall (0.516 vs 0.556), and lower early-warning capture (66.8% vs 67.6%).
   - Synthetic augmentation improved warning-class F1 marginally, but at the direct cost of severe regressions in critical event capture and overall calibration.
2. **`v1.0.3-none` Candidate Status:**
   - **`v1.0.3-none` candidate smoke passed, but artifact-to-Kaggle-log identity is UNRESOLVED; not accepted for swap.**
   - **Audit Finding (Outcome A)**: The console log pasted by Umair for `none` was evaluated on the exact same 94,762 test set (normal 49,823; warning 30,367; critical 14,572) as `synthetic_augmentation`. That log confirms that balancing degrades performance on a controlled split. However, the files in `<RUN3_ARTIFACTS_DIR>/none/` originate from a different run/cohort (timestamp 2026-10-30T20:48:25 UTC; 96,060 test windows; 4,386 validation patients; distinct scaler `67A134BB...`). Until the matching artifacts for the 94,762-window log are identified and provided, the candidate cannot be swapped into production.
3. **Current Deployed Model Retained:**
   - Run 2 (`v1.0.2`) remains active as the deployed and rollback baseline. No model swap or pointer update is approved at this time.
4. **No Further Balancing Runs Authorized:**
   - No pure-random PhysioNet regeneration and no `oversample` run is authorized from this result.
5. **Fusion Weights Remain Unchanged:**
   - The notebook sweep is test-set descriptive and its `det=0.0 / ml=1.0` result is still safety-capped; it does NOT represent an LSTM-only architecture. Any future fusion tuning requires validation-based optimization and explicit separate approval.

---

## 5. Automated Compare Tool Output (`compare_model_metrics.py`)

> **Path Placeholder**: `<RUN3_ARTIFACTS_DIR>` represents the local directory where Run 3 candidate evaluation artifacts are stored.

Execution command:
```bash
python scripts/compare_model_metrics.py \
  --base <RUN3_ARTIFACTS_DIR>/synthetic_augmentation/evaluation_metrics.json \
  --candidate <RUN3_ARTIFACTS_DIR>/none/evaluation_metrics.json \
  --base-label v1.0.3-synthetic \
  --candidate-label v1.0.3-none
```

```text
======================================================================
HealSense Model Metrics Comparison: [v1.0.3-synthetic] vs [v1.0.3-none]
======================================================================

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
 WARNING: DATASET SPLIT / COHORT MISMATCH DETECTED
 The compared runs were evaluated on DIFFERENT dataset cohorts or splits:
   • Validation total support mismatch: [v1.0.3-synthetic: 94470] vs [v1.0.3-none: 93371]
   • Validation 'normal' support mismatch: [v1.0.3-synthetic: 49528] vs [v1.0.3-none: 48577]
   • Validation 'critical' support mismatch: [v1.0.3-synthetic: 13995] vs [v1.0.3-none: 14024]
   • Validation 'warning' support mismatch: [v1.0.3-synthetic: 30947] vs [v1.0.3-none: 30770]
   • Test total support mismatch: [v1.0.3-synthetic: 94762] vs [v1.0.3-none: 96060]
   • Test 'normal' support mismatch: [v1.0.3-synthetic: 49823] vs [v1.0.3-none: 50973]
   • ... and 2 more mismatch(es)
 DELTAS DO NOT REFLECT A STRICT CONTROLLED SAME-SPLIT A/B TEST.
 Deltas compound model architecture shifts with patient cohort variance.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

--- Validation Set Metrics ---
Metric                    | v1.0.3-synthetic | v1.0.3-none    | Delta       
----------------------------------------------------------------------------
Accuracy                  | 0.6099         | 0.6166         | +0.0067     
Balanced Accuracy         | 0.5738         | 0.5849         | +0.0111     
Macro-F1                  | 0.5639         | 0.5732         | +0.0093     
Weighted-F1               | 0.6163         | 0.6211         | +0.0048     
AUROC                     | 0.7680         | 0.7756         | +0.0076     

--- Test Set Metrics ---
Metric                    | v1.0.3-synthetic | v1.0.3-none    | Delta       
----------------------------------------------------------------------------
Accuracy                  | 0.6088         | 0.6190         | +0.0102     
Balanced Accuracy         | 0.5805         | 0.5850         | +0.0045     
Macro-F1                  | 0.5685         | 0.5727         | +0.0043     
Weighted-F1               | 0.6156         | 0.6238         | +0.0083     
AUROC                     | 0.7706         | 0.7762         | +0.0056     

--- Per-Class Test Metrics ---
Class        | Metric     | v1.0.3-synthetic | v1.0.3-none  | Delta     
------------------------------------------------------------------------
critical     | precision  | 0.4094       | 0.4121       | +0.0028   
critical     | recall     | 0.5156       | 0.5348       | +0.0192   
critical     | f1         | 0.4564       | 0.4655       | +0.0091   
critical     | support    | 14572        | 14543        | -29.00    
normal       | precision  | 0.7535       | 0.7546       | +0.0011   
normal       | recall     | 0.6658       | 0.7054       | +0.0397   
normal       | f1         | 0.7069       | 0.7292       | +0.0223   
normal       | support    | 49823        | 50973        | +1150.00  
warning      | precision  | 0.5252       | 0.5324       | +0.0073   
warning      | recall     | 0.5600       | 0.5148       | -0.0452   
warning      | f1         | 0.5420       | 0.5235       | -0.0186   
warning      | support    | 30367        | 30544        | +177.00   

--- Confusion Matrices (Test) ---
[v1.0.3-synthetic]:
   [33170, 11087, 5566]
   [8086, 17007, 5274]
   [2767, 4291, 7514]
[v1.0.3-none]:
   [35957, 9910, 5106]
   [8831, 15725, 5988]
   [2865, 3900, 7778]
```
