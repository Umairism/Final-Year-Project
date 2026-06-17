import numpy as np
import joblib
import logging
import os
import tensorflow as tf
from typing import List, Dict, Any, Tuple

from api.config import get_settings

logger = logging.getLogger(__name__)

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
        self.sequence_length = 60
        self.features = ['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp']
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
            
            logger.info(f"Loading PredictionService artifacts from {os.path.dirname(model_path)}")
            
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False

            self.model = tf.keras.models.load_model(model_path)
            self.scaler = joblib.load(scaler_path)
            self.label_encoder = joblib.load(encoder_path)
            
            logger.info("PredictionService artifacts loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load PredictionService artifacts: {e}", exc_info=True)
            return False

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
            # Extract features in the correct order
            sequence = []
            for v in vitals_history:
                sequence.append([v.get(f, 0.0) for f in self.features])
                
            sequence = np.array(sequence, dtype=np.float32)
            
            # Strict 60-reading limit (no padding)
            if len(sequence) > self.sequence_length:
                sequence = sequence[-self.sequence_length:]
                
            # Scale features
            seq_reshaped = sequence.reshape(-1, len(self.features))
            seq_scaled = self.scaler.transform(seq_reshaped)
            seq_scaled = seq_scaled.reshape(1, self.sequence_length, len(self.features))
            
            # Predict
            pred_probs = self.model.predict(seq_scaled, verbose=0)[0]
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
                "model_version": self.settings.MODEL_VERSION
            }
            
        except Exception as e:
            logger.error(f"Error during risk prediction inference: {e}", exc_info=True)
            return None

prediction_service = PredictionService()
