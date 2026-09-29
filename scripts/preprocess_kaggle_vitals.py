#!/usr/bin/env python3
"""
HealSense Kaggle Dataset Preprocessing Pipeline
================================================
Converts "Human Vital Signs 2024" (Kaggle) into the canonical 5-feature
format required by the LSTM training pipeline.

Dataset Source:
  https://www.kaggle.com/datasets/yourfavoritekaggledataset (download manually)
  Expected filename: data/raw/kaggle_health_data/human_vital_signs_dataset_2024.csv

Output:
  data/raw/bidmc_vitals.csv   (same filename as BIDMC — train_model.py reads this)

Run from repository root:
  python scripts/preprocess_kaggle_vitals.py
"""

import os
import sys
import pandas as pd
import numpy as np

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(REPO_ROOT, "data", "raw")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "bidmc_vitals.csv")

# Candidate input paths — first one that exists wins
CANDIDATE_INPUTS = [
    os.path.join(RAW_DATA_DIR, "kaggle_health_data", "human_vital_signs_dataset_2024.csv"),
    os.path.join(RAW_DATA_DIR, "human_vital_signs_dataset_2024.csv"),
    os.path.join(RAW_DATA_DIR, "kaggle_health_data", "vital_signs.csv"),
]

# ─── Column Mapping ───────────────────────────────────────────────────────────
# Maps known Kaggle column names → HealSense canonical schema
# If your CSV uses different names, add them here.
COLUMN_CANDIDATES = {
    'heart_rate':   ['Heart Rate', 'heart_rate', 'HeartRate', 'hr', 'pulse'],
    'spo2':         ['Oxygen Saturation', 'spo2', 'SpO2', 'oxygen_saturation', 'SpO2(%)'],
    'temperature':  ['Body Temperature', 'temperature', 'Temperature', 'temp', 'body_temp'],
    'systolic_bp':  ['Systolic Blood Pressure', 'systolic_bp', 'Systolic', 'SBP', 'systolic'],
    'diastolic_bp': ['Diastolic Blood Pressure', 'diastolic_bp', 'Diastolic', 'DBP', 'diastolic'],
}

# ─── Clinical Label Derivation ────────────────────────────────────────────────
# MUST use the EXACT same thresholds as fusion_engine.py to avoid label skew.
def derive_health_status(row: pd.Series) -> str:
    """
    Applies HealSense WHO/clinical thresholds to derive a proxy health label.
    These EXACTLY match fusion_engine.py:47-94 deterministic rules.
    """
    spo2 = row['spo2']
    hr = row['heart_rate']
    temp = row['temperature']
    sbp = row['systolic_bp']
    dbp = row['diastolic_bp']

    # Critical thresholds (fusion_engine.py Layer 2 — CRITICAL rules)
    if 0 < spo2 < 92:
        return 'critical'
    if hr > 150 or (0 < hr < 40):
        return 'critical'
    if sbp >= 180 or dbp >= 120:
        return 'critical'

    # Warning thresholds (fusion_engine.py Layer 2 — WARNING rules)
    if spo2 < 95:
        return 'warning'
    if hr > 120 or hr < 50:
        return 'warning'
    if temp >= 38.0 or temp < 35.0:
        return 'warning'

    return 'normal'


def resolve_column(df: pd.DataFrame, canonical: str, candidates: list) -> str:
    """Find which candidate column name is in the DataFrame."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(
        f"Could not find column for '{canonical}'. "
        f"Available columns: {df.columns.tolist()}\n"
        f"Tried: {candidates}"
    )


def convert_temperature(df: pd.DataFrame, col: str) -> pd.Series:
    """Auto-detect Fahrenheit (max > 50) and convert to Celsius."""
    series = df[col].copy()
    if series.max() > 50:
        print(f"  Temperature appears to be in Fahrenheit (max={series.max():.1f}). Converting to Celsius.")
        series = (series - 32) * 5 / 9
    return series


def main():
    # ── 1. Find input file ──────────────────────────────────────────────────
    input_path = None
    for path in CANDIDATE_INPUTS:
        if os.path.exists(path):
            input_path = path
            break

    if input_path is None:
        print("ERROR: Kaggle dataset not found.")
        print("Please download 'Human Vital Signs 2024' from Kaggle and place it at:")
        print(f"  {CANDIDATE_INPUTS[0]}")
        print("\nAlternatively, you can use any CSV with columns for HR, SpO2, Temp, SBP, DBP.")
        sys.exit(1)

    print(f"Loading: {input_path}")
    df = pd.read_csv(input_path)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns.")
    print(f"  Columns: {df.columns.tolist()[:10]}{'...' if len(df.columns) > 10 else ''}")

    # ── 2. Map columns to canonical names ──────────────────────────────────
    print("\nResolving column names...")
    rename_map = {}
    for canonical, candidates in COLUMN_CANDIDATES.items():
        src = resolve_column(df, canonical, candidates)
        rename_map[src] = canonical
        print(f"  '{src}' → '{canonical}'")

    df = df.rename(columns=rename_map)

    # ── 3. Fix temperature units ────────────────────────────────────────────
    df['temperature'] = convert_temperature(df, 'temperature')

    # ── 4. Select and cast required columns ────────────────────────────────
    required = ['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp']
    df = df[required].copy()
    for col in required:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    print(f"\nBefore cleaning: {len(df):,} rows")
    df = df.dropna(subset=required)
    print(f"After dropping NaN rows: {len(df):,} rows")

    # ── 5. Physiological bounds filtering ──────────────────────────────────
    bounds = {
        'heart_rate':   (20, 250),
        'spo2':         (50, 100),
        'temperature':  (30, 45),
        'systolic_bp':  (50, 300),
        'diastolic_bp': (20, 200),
    }
    for col, (lo, hi) in bounds.items():
        before = len(df)
        df = df[(df[col] >= lo) & (df[col] <= hi)]
        removed = before - len(df)
        if removed:
            print(f"  Removed {removed:,} rows with out-of-bounds {col} (valid: {lo}–{hi})")

    print(f"After bounds filtering: {len(df):,} rows")

    # ── 6. Create virtual patients for LSTM sequence grouping ───────────────
    # The Kaggle dataset is cross-sectional. We create virtual patient groups of
    # GROUP_SIZE rows so that create_sequences_for_patients() can extract 60-step windows.
    GROUP_SIZE = 200   # each group = one "patient"; gives 141 sequences per patient at SEQ=60
    df = df.reset_index(drop=True)
    df['patient_id'] = (df.index // GROUP_SIZE).astype(str).apply(lambda x: f"KAG_{x}")
    n_patients = df['patient_id'].nunique()
    print(f"\nCreated {n_patients:,} virtual patients (each ≈ {GROUP_SIZE} readings)")

    # ── 7. Derive health status labels ──────────────────────────────────────
    print("Deriving health_status labels (using fusion_engine.py thresholds)...")
    df['health_status'] = df.apply(derive_health_status, axis=1)

    dist = df['health_status'].value_counts()
    print("\nClass distribution:")
    for status, count in dist.items():
        pct = count / len(df) * 100
        print(f"  {status:10s}: {count:7,} ({pct:.2f}%)")

    # ── 8. Save ──────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\n✅ Saved {len(df):,} rows to: {OUTPUT_PATH}")
    print("Next step: python scripts/train_model.py")


if __name__ == "__main__":
    main()
