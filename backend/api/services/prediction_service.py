import numpy as np
import joblib
import logging
import os
try:
    import tensorflow as tf
except Exception as e:
    tf = None
    logging.getLogger(__name__).warning(f"TensorFlow native import unavailable: {e}. Falling back to clinical rules/mock prediction.")

from typing import List, Dict, Any, Tuple

from api.config import get_settings

logger = logging.getLogger(__name__)

# Must match scripts/train_model.py CLINICAL_FALLBACKS.
# Only used when imputer.pkl is unavailable (i.e. the model predates the
# imputation artifact); a warning is logged when this path is taken.
CLINICAL_FALLBACKS = {
    'heart_rate': 75.0,
    'spo2': 98.0,
    'temperature': 37.0,
    'systolic_bp': 120.0,
    'diastolic_bp': 80.0,
}

class PredictionService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PredictionService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.settings = get_settings()
        self.model = None
        self.scaler = None
        self.label_encoder = None
        self.medians = dict(CLINICAL_FALLBACKS)
        self.imputation_source = 'clinical_fallback'
        self.sequence_length = 60
        self.features = ['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp']
        self.include_missing_indicators = False
        self.n_input_features = len(self.features)
        self._initialized = True

    def load_artifacts(self) -> bool:
        """Load the ML model, scaler, and label encoder into memory."""
        try:
            # Resolve absolute paths assuming the backend runs from healsense/backend
            # __file__ is backend/api/services/prediction_service.py
            # 4 dirnames up gets us to healsense/
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            model_path = os.path.normpath(os.path.join(base_dir, self.settings.LSTM_MODEL_PATH.replace('../', '')))
            scaler_path = os.path.normpath(os.path.join(base_dir, self.settings.SCALER_PATH.replace('../', '')))
            encoder_path = os.path.normpath(os.path.join(base_dir, self.settings.ENCODER_PATH.replace('../', '')))
            imputer_path = os.path.normpath(os.path.join(base_dir, self.settings.IMPUTER_PATH.replace('../', '')))
            
            logger.info(f"Loading PredictionService artifacts from {os.path.dirname(model_path)}")
            
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False

            self.model = tf.keras.models.load_model(model_path)
            self.scaler = joblib.load(scaler_path)
            self.label_encoder = joblib.load(encoder_path)

            # Imputation artifact keeps inference identical to training.
            # Without it the model still runs, but with clinical fallbacks only.
            if os.path.exists(imputer_path):
                imputer = joblib.load(imputer_path)
                loaded_medians = imputer.get('medians', {}) if isinstance(imputer, dict) else {}
                self.medians = {**CLINICAL_FALLBACKS, **loaded_medians}
                self.imputation_source = 'training_median_artifact'

                # The artifact declares the model's expected input contract.
                # This lets the service run either the legacy 60x5 model or the
                # PhysioNet-trained 24x10 model (5 vitals + 5 missing indicators)
                # without code changes.
                if isinstance(imputer, dict):
                    declared_len = imputer.get('sequence_length')
                    if declared_len:
                        self.sequence_length = int(declared_len)
                    self.include_missing_indicators = bool(
                        imputer.get('include_missing_indicators', False)
                    )
                    declared_features = imputer.get('feature_order')
                    if declared_features:
                        self.features = list(declared_features)
                    self.n_input_features = int(
                        imputer.get('n_features',
                                    len(self.features) * (2 if self.include_missing_indicators else 1))
                    )
                logger.info(
                    f"Imputation artifact loaded ({imputer_path}) — "
                    f"seq_len={self.sequence_length}, features={len(self.features)}, "
                    f"missing_indicators={self.include_missing_indicators}"
                )
            else:
                self.medians = dict(CLINICAL_FALLBACKS)
                self.imputation_source = 'clinical_fallback'
                logger.warning(
                    f"Imputation artifact not found: {imputer_path}. Falling back to clinical "
                    f"defaults — this may cause train/serve skew. Re-run scripts/train_model.py."
                )
            
            logger.info("PredictionService artifacts loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load PredictionService artifacts: {e}", exc_info=True)
            return False

    def _resolve_feature(self, record: Dict[str, Any], feature: str) -> float:
        """
        Return a usable numeric value for a feature, applying the imputer loaded
        from training. Missing / None / NaN values fall back to the training
        median (NOT 0.0, which previous versions used and which corrupted every
        prediction through train/serve skew).
        """
        default = float(self.medians.get(feature, CLINICAL_FALLBACKS.get(feature, 0.0)))
        value = record.get(feature, None)
        if value is None:
            return default
        try:
            value = float(value)
        except (TypeError, ValueError):
            return default
        if np.isnan(value):
            return default
        return value

    def _resolve_feature_with_flag(self, record: Dict[str, Any], feature: str) -> Tuple[float, bool]:
        """
        Return (value, was_missing). Used both to impute and to populate the
        missing-indicator channel that the PhysioNet-trained model consumes.
        """
        default = float(self.medians.get(feature, CLINICAL_FALLBACKS.get(feature, 0.0)))
        value = record.get(feature, None)
        if value is None:
            return default, True
        try:
            value = float(value)
        except (TypeError, ValueError):
            return default, True
        if np.isnan(value):
            return default, True
        return value, False

    def predict_risk(self, vitals_history: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Predict health risk from a sequence of vital signs.
        
        Args:
            vitals_history: List of dicts, each containing ['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp']
            
        Returns:
            Dict containing predicted_class, probability, full_probability_distribution, model_version
        """
        if not self.model or not self.scaler or not self.label_encoder:
            logger.warning("PredictionService is not fully loaded. Skipping prediction.")
            return None
            
        if len(vitals_history) < self.sequence_length:
            logger.info(f"Not enough vitals for prediction: {len(vitals_history)} < {self.sequence_length}")
            return None
            
        try:
            # Build the raw feature matrix plus a missing-indicator matrix.
            # Imputation uses the SAME training medians loaded from imputer.pkl.
            n_steps = min(len(vitals_history), self.sequence_length)
            recent = vitals_history[-n_steps:]

            raw = np.zeros((n_steps, len(self.features)), dtype=np.float32)
            ind = np.zeros((n_steps, len(self.features)), dtype=np.float32)

            for i, rec in enumerate(recent):
                for j, f in enumerate(self.features):
                    filled, was_missing = self._resolve_feature_with_flag(rec, f)
                    raw[i, j] = filled
                    ind[i, j] = 1.0 if was_missing else 0.0

            # Scale only the raw channels — indicators stay binary.
            scaled = self.scaler.transform(raw)
            seq = np.concatenate([scaled, ind], axis=1) if self.include_missing_indicators else scaled
            seq = seq.reshape(1, n_steps, seq.shape[1])

            # Predict
            pred_probs = self.model.predict(seq, verbose=0)[0]
            pred_class_idx = np.argmax(pred_probs)
            pred_class_label = self.label_encoder.inverse_transform([pred_class_idx])[0]
            
            # Format distribution
            distribution = {
                self.label_encoder.inverse_transform([i])[0]: float(prob)
                for i, prob in enumerate(pred_probs)
            }
            
            return {
                "predicted_class": pred_class_label,
                "probability": float(pred_probs[pred_class_idx]),
                "full_probability_distribution": distribution,
                "model_version": self.settings.MODEL_VERSION,
                "imputation_source": self.imputation_source
            }
            
        except Exception as e:
            logger.error(f"Error during risk prediction inference: {e}", exc_info=True)
            return None

prediction_service = PredictionService()
