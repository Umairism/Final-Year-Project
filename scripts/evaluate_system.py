import numpy as np
import pandas as pd
import joblib
import os
import json
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import sys

# Ensure backend modules can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend/api'))

MODEL_VERSION = "v1.0.2"
MODEL_DIR = f'../data/models/{MODEL_VERSION}'
DATA_PATH = '../data/raw/bidmc_vitals.csv'
TEST_PATIENTS_PATH = '../data/processed/test_patients.csv'

print("--- System-Level Ablation Study & Evaluation ---")

# 1. Load Data
df = pd.read_csv(DATA_PATH)
test_patients = pd.read_csv(TEST_PATIENTS_PATH)['patient_id'].tolist()
test_df = df[df['patient_id'].isin(test_patients)]
print(f"Loaded {len(test_df)} test readings from {len(test_patients)} patients.")

# 2. Reconstruct Sequences
SEQ_LENGTH = 60
FEATURES = ['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp']
X_test, y_test_raw = [], []
for patient_id in test_patients:
    patient_data = test_df[test_df['patient_id'] == patient_id]
    features = patient_data[FEATURES].values
    labels = patient_data['health_status'].values
    for i in range(len(features) - SEQ_LENGTH + 1):
        X_test.append(features[i:i + SEQ_LENGTH])
        y_test_raw.append(labels[i + SEQ_LENGTH - 1])

X_test = np.array(X_test)
y_test_raw = np.array(y_test_raw)

if len(X_test) == 0:
    print("No test sequences could be formed. Sequences must be >= 60 length.")
    sys.exit(1)

# 3. Load Model and Preprocessors
model = tf.keras.models.load_model(f"{MODEL_DIR}/lstm_best.h5")
scaler = joblib.load(f"{MODEL_DIR}/scaler.pkl")
encoder = joblib.load(f"{MODEL_DIR}/label_encoder.pkl")

# Scale features
n_samples, n_timesteps, n_features = X_test.shape
X_reshaped = X_test.reshape(-1, n_features)
X_imputed = np.where(np.isnan(X_reshaped), -1.0, X_reshaped)
X_scaled = scaler.transform(X_imputed)
X_test_scaled = X_scaled.reshape(n_samples, n_timesteps, n_features)

# ML Predictions
ml_probs = model.predict(X_test_scaled, verbose=0)
ml_pred_idx = np.argmax(ml_probs, axis=1)
ml_pred_labels = encoder.inverse_transform(ml_pred_idx)

# 4. Deterministic Engine Logic (Simulation of backend fusion_engine.py)
# The deterministic logic is based on the LAST reading in the sequence (the current timestep)
def run_deterministic_rules(features_array):
    last_reading = features_array[-1] # [hr, spo2, temp, sbp, dbp]
    hr, spo2, _, _, _ = last_reading
    # Simplified simulation of the clinical rules engine
    if spo2 < 92 and spo2 > 0:
        return 'critical', 1.0
    elif hr > 120 or hr < 50:
        return 'warning', 0.5
    elif spo2 < 95 and spo2 >= 92:
        return 'warning', 0.5
    else:
        return 'normal', 0.0

det_pred_labels = []
det_scores = []
for seq in X_test:
    lbl, score = run_deterministic_rules(seq)
    det_pred_labels.append(lbl)
    det_scores.append(score)

# 5. Hybrid System Fusion Logic
DETERMINISTIC_WEIGHT = 0.6
ML_WEIGHT = 0.4

hybrid_pred_labels = []
for i in range(len(X_test)):
    det_lbl = det_pred_labels[i]
    det_score = det_scores[i]
    ml_lbl = ml_pred_labels[i]
    
    if det_lbl == 'critical':
        hybrid_pred_labels.append('critical')
        continue
    
    ml_score = 1.0 if ml_lbl == 'critical' else (0.5 if ml_lbl == 'warning' else 0.0)
    final_numeric_score = (DETERMINISTIC_WEIGHT * det_score) + (ML_WEIGHT * ml_score)
    
    if final_numeric_score >= 0.7:
        hybrid_pred_labels.append('critical')
    elif final_numeric_score >= 0.4:
        hybrid_pred_labels.append('warning')
    else:
        hybrid_pred_labels.append('normal')

from sklearn.metrics import cohen_kappa_score

# 6. Evaluation Metrics
print("\n--- ABLATION STUDY RESULTS ---")
print("NOTE: The system is evaluated on internally derived proxy labels, not external clinical outcomes.")

def print_metrics(name, y_true, y_pred):
    print(f"\n[{name} SYSTEM]")
    print("Confusion Matrix:")
    print(confusion_matrix(y_true, y_pred, labels=['critical', 'warning', 'normal']))

print_metrics("1. DETERMINISTIC RULES ONLY", y_test_raw, det_pred_labels)
print_metrics("2. ML MODEL ONLY", y_test_raw, ml_pred_labels)
print_metrics("3. HYBRID FUSION ENGINE", y_test_raw, hybrid_pred_labels)

# 7. Rule Alignment Evaluation
kappa = cohen_kappa_score(det_pred_labels, ml_pred_labels)
print(f"\nRule-Alignment Score (ML vs Deterministic Cohen's Kappa): {kappa:.4f}")
print("NOTE: High agreement is expected as ML learns from rule-derived proxy labels.")


print("\nEvaluation Complete.")
