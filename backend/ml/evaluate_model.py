"""
HealSense Real Model Evaluation Script

REQUIRES: A trained model to exist at data/models/v1.0.2/
Run scripts/train_model.py first, then run this script.

Usage:
    cd backend
    python ml/evaluate_model.py
"""
import os
import sys
import json
import logging

import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, precision_recall_fscore_support
)

try:
    import tensorflow as tf
except ImportError:
    print("ERROR: TensorFlow is required. Install with: pip install tensorflow")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_VERSION = "v1.0.2"  # Must match config.py and scripts/train_model.py
MODEL_DIR = os.path.join(BASE_DIR, "data", "models", MODEL_VERSION)
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
DATA_PATH = os.path.join(BASE_DIR, "data", "raw", "bidmc_vitals.csv")
TEST_PATIENTS_PATH = os.path.join(BASE_DIR, "data", "processed", "test_patients.csv")

MODEL_PATH = os.path.join(MODEL_DIR, "lstm_best.h5")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

SEQ_LENGTH = 60
FEATURES = ['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp']
CLASSES = ['critical', 'normal', 'warning']  # alphabetical; matches LabelEncoder


def load_artifacts():
    """Load model, scaler, and label encoder. Fails fast if any is missing."""
    missing = []
    for path, name in [(MODEL_PATH, "LSTM model"), (SCALER_PATH, "Scaler"), (ENCODER_PATH, "Label Encoder")]:
        if not os.path.exists(path):
            missing.append(f"  {name}: {path}")
    if missing:
        logger.error(
            "Cannot evaluate — the following artifacts are missing:\n" + "\n".join(missing)
            + "\n\nRun scripts/train_model.py first."
        )
        sys.exit(1)

    model = tf.keras.models.load_model(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    encoder = joblib.load(ENCODER_PATH)
    logger.info("✅ Artifacts loaded from %s", MODEL_DIR)
    return model, scaler, encoder


def load_test_data():
    """Load held-out test patient data (produced by train_model.py)."""
    for path, name in [(DATA_PATH, "bidmc_vitals.csv"), (TEST_PATIENTS_PATH, "test_patients.csv")]:
        if not os.path.exists(path):
            logger.error("Missing required file: %s\nRun scripts/preprocess_bidmc.py and scripts/train_model.py first.", path)
            sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    test_patients = pd.read_csv(TEST_PATIENTS_PATH)['patient_id'].tolist()
    test_df = df[df['patient_id'].isin(test_patients)]
    logger.info("Loaded %d test readings from %d patients.", len(test_df), len(test_patients))
    return test_df, test_patients


def create_test_sequences(test_df, test_patients, seq_length=SEQ_LENGTH):
    """Create sliding-window sequences for test patients."""
    X, y = [], []
    for patient_id in test_patients:
        patient_data = test_df[test_df['patient_id'] == patient_id]
        features = patient_data[FEATURES].values
        labels = patient_data['health_status'].values
        for i in range(len(features) - seq_length + 1):
            X.append(features[i:i + seq_length])
            y.append(labels[i + seq_length - 1])
    return np.array(X), np.array(y)


def save_results(acc, precision, recall, f1, class_report, cm, encoder):
    """Save metrics JSON, confusion matrix PNG, and summary markdown."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Metrics JSON
    metrics = {
        "model_version": MODEL_VERSION,
        "evaluation_note": "Metrics computed from real LSTM predictions on held-out test patients. Labels are proxy labels derived from WHO clinical thresholds (not external clinical outcomes).",
        "accuracy": round(float(acc), 4),
        "weighted_precision": round(float(precision), 4),
        "weighted_recall": round(float(recall), 4),
        "weighted_f1_score": round(float(f1), 4),
        "total_test_samples": int(cm.sum()),
    }
    metrics_path = os.path.join(RESULTS_DIR, "metrics_report.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info("✅ Metrics saved: %s", metrics_path)

    # Confusion matrix PNG
    fig, ax = plt.subplots(figsize=(7, 6))
    class_names = encoder.classes_.tolist()
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    tick_marks = np.arange(len(class_names))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(class_names, rotation=45, ha='right')
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(class_names)
    ax.set_xlabel('Predicted Label')
    ax.set_ylabel('True Label')
    ax.set_title(f'HealSense LSTM Confusion Matrix ({MODEL_VERSION})\nNOTE: Proxy labels derived from clinical thresholds')
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    plt.tight_layout()
    cm_path = os.path.join(RESULTS_DIR, "confusion_matrix.png")
    plt.savefig(cm_path, dpi=120)
    plt.close()
    logger.info("✅ Confusion matrix saved: %s", cm_path)

    # Markdown summary
    summary = f"""# HealSense LSTM Evaluation Summary — {MODEL_VERSION}

> ⚠️ **Important:** Labels in this evaluation are proxy labels derived from the same WHO clinical thresholds used in the deterministic rules engine (SpO2 < 92 → critical, etc.). This evaluation measures consistency with the rules, not validation against external clinical outcomes.

## Metrics (Test Set — Unseen Patients)

| Metric | Value |
|---|---|
| Accuracy | {acc*100:.2f}% |
| Weighted Precision | {precision*100:.2f}% |
| Weighted Recall | {recall*100:.2f}% |
| Weighted F1 Score | {f1*100:.2f}% |
| Test Samples | {int(cm.sum())} |

## Classification Report

```
{class_report}
```

## Artifacts
- `metrics_report.json` — numeric metrics
- `confusion_matrix.png` — visual confusion matrix
"""
    summary_path = os.path.join(RESULTS_DIR, "evaluation_summary.md")
    with open(summary_path, "w") as f:
        f.write(summary)
    logger.info("✅ Summary saved: %s", summary_path)


def main():
    logger.info("=== HealSense LSTM Evaluation (%s) ===", MODEL_VERSION)

    model, scaler, encoder = load_artifacts()
    test_df, test_patients = load_test_data()
    X_test, y_test_raw = create_test_sequences(test_df, test_patients)

    if len(X_test) == 0:
        logger.error("No test sequences formed. Sequences require >= %d consecutive readings per patient.", SEQ_LENGTH)
        sys.exit(1)

    logger.info("Test sequences: %d (shape %s)", len(X_test), X_test.shape)

    # Scale features
    n_samples, n_timesteps, n_features = X_test.shape
    X_reshaped = X_test.reshape(-1, n_features)
    X_imputed = np.where(np.isnan(X_reshaped), -1.0, X_reshaped)
    X_scaled = scaler.transform(X_imputed).reshape(n_samples, n_timesteps, n_features)

    # Encode labels
    y_encoded = encoder.transform(y_test_raw)

    # Predict
    y_pred_probs = model.predict(X_scaled, verbose=0)
    y_pred = np.argmax(y_pred_probs, axis=1)

    # Metrics
    acc = accuracy_score(y_encoded, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_encoded, y_pred, average='weighted')
    class_report = classification_report(y_encoded, y_pred, target_names=encoder.classes_)
    cm = confusion_matrix(y_encoded, y_pred)

    print("\n--- EVALUATION RESULTS ---")
    print(f"Accuracy:  {acc*100:.2f}%")
    print(f"Precision: {precision*100:.2f}%")
    print(f"Recall:    {recall*100:.2f}%")
    print(f"F1 Score:  {f1*100:.2f}%")
    print(f"\n{class_report}")
    print("Confusion Matrix:")
    print(cm)

    save_results(acc, precision, recall, f1, class_report, cm, encoder)
    logger.info("=== Evaluation complete ===")


if __name__ == "__main__":
    main()
