import numpy as np
import pandas as pd
import json
import os
import joblib
from datetime import datetime

import tensorflow as tf
from tensorflow.keras import layers, Sequential
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.utils import to_categorical

from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix

CONFIG = {
    'sequence_length': 60,
    'features': ['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp'],
    'num_features': 5,
    'num_classes': 3,
    'batch_size': 32,
    'epochs': 20, # Reduced for rapid prototype training
    'learning_rate': 0.001,
    'lstm_units': [64, 32], 
    'dropout_rate': [0.3, 0.2, 0.1],
    'dense_units': 32,
    'random_seed': 42
}

DATA_PATH = '../data/raw/bidmc_vitals.csv'
MODEL_VERSION = "v1.0.2"
MODEL_DIR = f'../data/models/{MODEL_VERSION}'
CHECKPOINT_PATH = f"{MODEL_DIR}/lstm_best.h5"
SCALER_PATH = f"{MODEL_DIR}/scaler.pkl"
ENCODER_PATH = f"{MODEL_DIR}/label_encoder.pkl"
IMPUTER_PATH = f"{MODEL_DIR}/imputer.pkl"
METADATA_PATH = f"{MODEL_DIR}/metadata.json"

np.random.seed(CONFIG['random_seed'])
tf.random.set_seed(CONFIG['random_seed'])

os.makedirs(MODEL_DIR, exist_ok=True)

def create_sequences_for_patients(df, patient_ids, sequence_length=60):
    X, y = [], []
    for patient_id in patient_ids:
        patient_data = df[df['patient_id'] == patient_id]
        features = patient_data[CONFIG['features']].values
        labels = patient_data['health_status'].values
        for i in range(len(features) - sequence_length + 1):
            X.append(features[i:i + sequence_length])
            y.append(labels[i + sequence_length - 1])
    return np.array(X), np.array(y)

print("Loading data...")
df = pd.read_csv(DATA_PATH)

print("Splitting patients...")
unique_patients = df['patient_id'].unique()
# Split patients 80/20 train/test
train_patients, test_patients = train_test_split(unique_patients, test_size=0.2, random_state=CONFIG['random_seed'])

# Save test patients to disk for evaluate_system.py
os.makedirs("../data/processed", exist_ok=True)
pd.Series(test_patients).to_csv("../data/processed/test_patients.csv", index=False, header=["patient_id"])

# Further split train patients into train and validation (80/20 of the training set)
train_patients, val_patients = train_test_split(train_patients, test_size=0.2, random_state=CONFIG['random_seed'])

print(f"Train patients: {len(train_patients)}, Val patients: {len(val_patients)}, Test patients: {len(test_patients)}")

print("Creating sequences independently...")
X_train, y_train_raw = create_sequences_for_patients(df, train_patients, CONFIG['sequence_length'])
X_val, y_val_raw = create_sequences_for_patients(df, val_patients, CONFIG['sequence_length'])
X_test, y_test_raw = create_sequences_for_patients(df, test_patients, CONFIG['sequence_length'])

print("Encoding labels...")
label_encoder = LabelEncoder()
# Fit only on training labels
label_encoder.fit(y_train_raw)

y_train_encoded = label_encoder.transform(y_train_raw)
y_val_encoded = label_encoder.transform(y_val_raw)
y_test_encoded = label_encoder.transform(y_test_raw)

y_train_cat = to_categorical(y_train_encoded, num_classes=CONFIG['num_classes'])
y_val_cat = to_categorical(y_val_encoded, num_classes=CONFIG['num_classes'])
y_test_cat = to_categorical(y_test_encoded, num_classes=CONFIG['num_classes'])

print("Normalizing features...")
scaler = StandardScaler()

# ─── Imputation (v1.1 — replaces the physiologically-impossible -1.0 fill) ───
# Missing values are now filled with the TRAINING-SET MEDIAN per feature, and
# those medians are persisted to imputer.pkl. PredictionService loads the same
# artifact at inference, so train-time and serve-time imputation are identical.
# (The previous -1.0 sentinel produced bimodal, near-zero-variance columns that
# corrupted the StandardScaler and caused train/serve skew.)
CLINICAL_FALLBACKS = {
    'heart_rate': 75.0,
    'spo2': 98.0,
    'temperature': 37.0,
    'systolic_bp': 120.0,
    'diastolic_bp': 80.0,
}


def compute_feature_medians(X_train_data):
    """Median per feature, computed on the TRAINING split only (no leakage)."""
    flat = X_train_data.reshape(-1, len(CONFIG['features']))
    medians = {}
    print("\nMissing-data report (training split):")
    for idx, name in enumerate(CONFIG['features']):
        col = flat[:, idx]
        missing_pct = float(np.mean(np.isnan(col))) * 100.0
        if np.all(np.isnan(col)):
            medians[name] = CLINICAL_FALLBACKS[name]
            print(f"  {name:14s} {missing_pct:6.2f}% missing — ENTIRELY ABSENT, using clinical fallback {medians[name]}")
        else:
            medians[name] = float(np.nanmedian(col))
            print(f"  {name:14s} {missing_pct:6.2f}% missing — median {medians[name]:.2f}")
    return medians


def impute_3d(X_data, medians):
    """Fill NaNs with stored training medians. Used identically at train and serve time."""
    X = X_data.astype(np.float32, copy=True)
    for idx, name in enumerate(CONFIG['features']):
        col = X[:, :, idx]
        col[np.isnan(col)] = medians[name]
    return X


def scale_3d(X_data, medians, is_train=False):
    n_samples, n_timesteps, n_features = X_data.shape

    X_imputed = impute_3d(X_data, medians)
    X_reshaped = X_imputed.reshape(-1, n_features)

    if is_train:
        X_scaled = scaler.fit_transform(X_reshaped)
    else:
        X_scaled = scaler.transform(X_reshaped)
    return X_scaled.reshape(n_samples, n_timesteps, n_features)

feature_medians = compute_feature_medians(X_train)
X_train_scaled = scale_3d(X_train, feature_medians, is_train=True)
X_val_scaled = scale_3d(X_val, feature_medians, is_train=False)
X_test_scaled = scale_3d(X_test, feature_medians, is_train=False)

print("Computing class weights...")
class_weights_array = compute_class_weight(
    'balanced', classes=np.unique(y_train_encoded), y=y_train_encoded
)
class_weights = dict(enumerate(class_weights_array))

print("Building model...")
model = Sequential([
    layers.Input(shape=(CONFIG['sequence_length'], CONFIG['num_features'])),
    layers.LSTM(CONFIG['lstm_units'][0], return_sequences=True),
    layers.Dropout(CONFIG['dropout_rate'][0]),
    layers.LSTM(CONFIG['lstm_units'][1]),
    layers.Dropout(CONFIG['dropout_rate'][1]),
    layers.Dense(CONFIG['dense_units'], activation='relu'),
    layers.Dropout(CONFIG['dropout_rate'][2]),
    layers.Dense(CONFIG['num_classes'], activation='softmax')
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=CONFIG['learning_rate']),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

callbacks = [
    ModelCheckpoint(CHECKPOINT_PATH, monitor='val_loss', save_best_only=True, verbose=1),
    EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True)
]

print("Training model...")
model.fit(
    X_train_scaled, y_train_cat,
    validation_data=(X_val_scaled, y_val_cat),
    epochs=CONFIG['epochs'],
    batch_size=CONFIG['batch_size'],
    class_weight=class_weights,
    callbacks=callbacks,
    verbose=1
)

print("\n--- Evaluation on Test Set (Unseen Patients) ---")
print("NOTE: The system is evaluated on internally derived proxy labels, not external clinical outcomes.")
test_loss, test_acc = model.evaluate(X_test_scaled, y_test_cat, verbose=0)
print(f"Test Accuracy: {test_acc:.4f}, Test Loss: {test_loss:.4f}")

y_pred_probs = model.predict(X_test_scaled)
y_pred = np.argmax(y_pred_probs, axis=1)

print("\nClassification Report:")
print(classification_report(y_test_encoded, y_pred, target_names=label_encoder.classes_))

print("Confusion Matrix:")
print(confusion_matrix(y_test_encoded, y_pred))

print("\nSaving artifacts...")
joblib.dump(scaler, SCALER_PATH)
joblib.dump(label_encoder, ENCODER_PATH)
joblib.dump({
    'feature_order': CONFIG['features'],
    'medians': feature_medians,
    'clinical_fallbacks': CLINICAL_FALLBACKS,
    'strategy': 'training_median',
    'model_version': MODEL_VERSION,
}, IMPUTER_PATH)

metadata = {
    'timestamp': datetime.now().isoformat(),
    'model_version': MODEL_VERSION,
    'config': CONFIG,
    'classes': label_encoder.classes_.tolist(),
    'test_accuracy': float(test_acc),
    'imputation': {
        'strategy': 'training_median',
        'medians': feature_medians,
        'artifact': 'imputer.pkl'
    }
}
with open(METADATA_PATH, 'w') as f:
    json.dump(metadata, f, indent=2)

print("Done! Artifacts saved to", MODEL_DIR)
