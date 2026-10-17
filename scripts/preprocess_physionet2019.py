#!/usr/bin/env python3
"""
HealSense — PhysioNet/CinC 2019 Preprocessing Pipeline
=======================================================
Converts raw per-patient .psv files into canonical windowed sequences for the
HealSense temporal risk model.

Key design decisions (see docs/ml/PhysioNet_Pipeline.md):
  1. Only 5 features are used — HR, O2Sat, Temp, SBP, DBP — matching the
     canonical feature vector in backend/api/services/fusion_engine.py.
  2. Labels are FUTURE-WINDOW labels: the worst rules-derived severity observed
     in the K hours AFTER the window ends. This removes the circularity of the
     original pipeline, which labelled each window with its own current state.
  3. Sequence length defaults to 24, not 60. Mean ICU stay in this dataset is
     ~38.8 h and only 4% of patients have >= 60 hourly rows; a 60-step window
     would silently discard ~96% of the cohort and bias the model toward
     long-stay (sicker) patients.
  4. NaN is preserved in the output. Imputation is deliberately deferred to the
     training split so medians are computed without leakage.

Usage:
    python scripts/preprocess_physionet2019.py \
        --data-dir data/raw \
        --seq-len 24 --horizon 6 \
        --out data/processed/physionet2019_seq24_h6.npz

Input layout:
    data/raw/training_setA/*.psv
    data/raw/training_setB/*.psv
"""

import argparse
import glob
import json
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

FEATURES: List[str] = ["HR", "O2Sat", "Temp", "SBP", "DBP"]

# Verbatim copy of the production rules in
# backend/api/services/fusion_engine.py::evaluate_deterministic_rules (Layer 2).
# Any change here MUST be mirrored there, and vice versa.
CRITICAL_SPO2 = 92.0
CRITICAL_HR_HIGH = 150.0
CRITICAL_HR_LOW = 40.0
CRITICAL_SBP = 180.0
CRITICAL_DBP = 120.0

WARNING_SPO2 = 95.0
WARNING_HR_HIGH = 120.0
WARNING_HR_LOW = 50.0
WARNING_TEMP_HIGH = 38.0
WARNING_TEMP_LOW = 35.0

NORMAL, WARNING, CRITICAL = 0, 1, 2
CLASS_NAMES = ["normal", "warning", "critical"]


def _val(x) -> Optional[float]:
    """Return a float, or None for NaN/absent values."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if np.isnan(v):
        return None
    return v


def severity_of_row(row: pd.Series) -> Optional[int]:
    """
    Apply the production deterministic rules to a single hourly row.

    Returns 0/1/2, or None when no assessable feature is present.
    Mirrors fusion_engine.evaluate_deterministic_rules closely enough that the
    labels describe the same clinical thresholds the backend enforces.
    """
    spo2 = _val(row.get("O2Sat"))
    hr = _val(row.get("HR"))
    temp = _val(row.get("Temp"))
    sbp = _val(row.get("SBP"))
    dbp = _val(row.get("DBP"))

    if all(v is None for v in (spo2, hr, temp, sbp, dbp)):
        return None

    # ── CRITICAL ──
    if spo2 is not None and spo2 < CRITICAL_SPO2:
        return CRITICAL
    if hr is not None and (hr > CRITICAL_HR_HIGH or hr < CRITICAL_HR_LOW):
        return CRITICAL
    if (sbp is not None and sbp >= CRITICAL_SBP) or (dbp is not None and dbp >= CRITICAL_DBP):
        return CRITICAL

    # ── WARNING ──
    if spo2 is not None and spo2 < WARNING_SPO2:
        return WARNING
    if hr is not None and (hr > WARNING_HR_HIGH or hr < WARNING_HR_LOW):
        return WARNING
    if temp is not None and (temp >= WARNING_TEMP_HIGH or temp < WARNING_TEMP_LOW):
        return WARNING

    return NORMAL


def build_patient_windows(
    df: pd.DataFrame,
    seq_len: int,
    horizon: int,
    min_valid_fraction: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Slice one patient's stay into (X, y, end_index) arrays.

    X shape: (n_windows, seq_len, 5) float32, NaN preserved
    y:      (n_windows,) int8, FUTURE-WINDOW label
    """
    if len(df) < seq_len + 1:
        return (np.empty((0, seq_len, len(FEATURES)), dtype=np.float32),
                np.empty((0,), dtype=np.int8),
                np.empty((0,), dtype=np.int32))

    values = df[FEATURES].to_numpy(dtype=np.float32)

    # Severity of every hour, computed once per patient.
    severities = np.full(len(df), -1, dtype=np.int8)
    for i in range(len(df)):
        s = severity_of_row(df.iloc[i])
        if s is not None:
            severities[i] = s

    X_list, y_list, idx_list = [], [], []

    for end in range(seq_len - 1, len(df)):
        future = severities[end + 1: end + 1 + horizon]
        future = future[future >= 0]
        if future.size == 0:
            continue  # no observable future -> this window has no label

        window = values[end - seq_len + 1: end + 1]
        valid_fraction = float(np.mean(~np.isnan(window)))
        if valid_fraction < min_valid_fraction:
            continue  # almost entirely empty history

        X_list.append(window)
        y_list.append(int(future.max()))
        idx_list.append(end)

    if not X_list:
        return (np.empty((0, seq_len, len(FEATURES)), dtype=np.float32),
                np.empty((0,), dtype=np.int8),
                np.empty((0,), dtype=np.int32))

    return (np.stack(X_list).astype(np.float32),
            np.asarray(y_list, dtype=np.int8),
            np.asarray(idx_list, dtype=np.int32))


def preprocess(
    data_dir: str,
    seq_len: int,
    horizon: int,
    min_valid_fraction: float,
    sets: List[str],
    verbose: bool = True,
) -> Dict[str, np.ndarray]:

    X_parts, y_parts, pid_parts, seplabel_parts = [], [], [], []
    patients_read = patients_used = patients_skipped_short = 0
    t0 = time.time()

    for set_name in sets:
        pattern = os.path.join(data_dir, set_name, "*.psv")
        files = sorted(glob.glob(pattern))
        if verbose:
            print(f"[{set_name}] found {len(files)} patient files")

        for fp in files:
            patients_read += 1
            try:
                df = pd.read_csv(fp, sep="|")
            except Exception as e:  # corrupt / truncated download
                if verbose and patients_read % 5000 == 0:
                    print(f"  skipped unreadable {os.path.basename(fp)}: {e}")
                continue

            missing_cols = [c for c in FEATURES if c not in df.columns]
            if missing_cols:
                continue

            pid = os.path.splitext(os.path.basename(fp))[0]

            X, y, end_idx = build_patient_windows(
                df, seq_len, horizon, min_valid_fraction
            )
            if X.shape[0] == 0:
                patients_skipped_short += 1
                continue

            patients_used += 1
            X_parts.append(X)
            y_parts.append(y)
            pid_parts.append(np.full(X.shape[0], pid, dtype=object))

            # Keep the dataset's genuine clinical outcome for optional
            # external validation (reported separately; not used as the
            # training label).
            if "SepsisLabel" in df.columns:
                seplabel_parts.append(df["SepsisLabel"].to_numpy()[end_idx])
            else:
                seplabel_parts.append(np.zeros(X.shape[0], dtype=np.int8))

            if verbose and patients_read % 5000 == 0:
                el = time.time() - t0
                print(f"  {patients_read:>6} patients | {el:5.1f}s | "
                      f"{sum(p.shape[0] for p in X_parts):>8} windows")

    if not X_parts:
        raise RuntimeError(
            f"No windows produced. Check --data-dir ('{data_dir}') and that "
            f"training_setA/ or training_setB/ contain .psv files."
        )

    X = np.concatenate(X_parts, axis=0)
    y = np.concatenate(y_parts, axis=0)
    pids = np.concatenate(pid_parts, axis=0)
    sepsis = np.concatenate(seplabel_parts, axis=0).astype(np.int8)

    if verbose:
        print(f"\nDone in {time.time() - t0:.1f}s")
        print(f"  patients read      : {patients_read}")
        print(f"  patients used      : {patients_used}")
        print(f"  patients skipped   : {patients_skipped_short} "
              f"(stays too short for seq_len={seq_len})")
        print(f"  windows            : {X.shape[0]}")
        print(f"  X shape            : {X.shape}")
        counts = np.bincount(y, minlength=3)
        for i, name in enumerate(CLASS_NAMES):
            pct = counts[i] / len(y) * 100 if len(y) else 0.0
            print(f"    {name:9s}: {counts[i]:>8} ({pct:5.2f}%)")
        print(f"  feature missingness: " + ", ".join(
            f"{f} {np.isnan(X[:, :, i]).mean() * 100:.1f}%"
            for i, f in enumerate(FEATURES)
        ))

    return {
        "X": X,
        "y": y,
        "patient_ids": pids,
        "sepsis_label": sepsis,
        "features": np.array(FEATURES),
        "class_names": np.array(CLASS_NAMES),
        "seq_len": np.array(seq_len),
        "horizon": np.array(horizon),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="data/raw",
                    help="directory containing training_setA/ and training_setB/")
    ap.add_argument("--seq-len", type=int, default=24,
                    help="history window length in hours (default 24)")
    ap.add_argument("--horizon", type=int, default=6,
                    help="K: hours ahead for the future-window label (default 6)")
    ap.add_argument("--min-valid-fraction", type=float, default=0.20,
                    help="drop windows with fewer than this fraction of non-NaN values")
    ap.add_argument("--sets", default="A,B",
                    help="which training sets to include, comma separated (A,B)")
    ap.add_argument("--out", default=None,
                    help="output .npz path")
    args = ap.parse_args()

    sets = [f"training_set{s.strip().upper()}" for s in args.sets.split(",") if s.strip()]
    out_path = args.out or f"data/processed/physionet2019_seq{args.seq_len}_h{args.horizon}.npz"

    result = preprocess(
        data_dir=args.data_dir,
        seq_len=args.seq_len,
        horizon=args.horizon,
        min_valid_fraction=args.min_valid_fraction,
        sets=sets,
    )

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    np.savez_compressed(out_path, **result)

    meta = {
        "source": "PhysioNet/CinC Challenge 2019 v1.0.0",
        "license": "CC BY 4.0",
        "feature_order": FEATURES,
        "class_names": CLASS_NAMES,
        "sequence_length": args.seq_len,
        "horizon_hours": args.horizon,
        "label_scheme": "future_window_max_severity",
        "min_valid_fraction": args.min_valid_fraction,
        "n_windows": int(result["X"].shape[0]),
        "n_patients": int(len(np.unique(result["patient_ids"]))),
    }
    meta_path = os.path.splitext(out_path)[0] + "_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved: {out_path}  ({os.path.getsize(out_path) / 1e6:.1f} MB)")
    print(f"Saved: {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
