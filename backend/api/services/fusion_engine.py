import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from api.config import get_settings
from api.models.schemas import CanonicalClinicalFeatureSchema, HealthStatus
from api.models.database.models import Patient, VitalSigns
from api.services.prediction_service import prediction_service

import logging
logger = logging.getLogger(__name__)

settings = get_settings()

class FusionEngine:
    """
    Clinical Hybrid Risk Engine
    Combines Deterministic Rules (WHO Guidelines), ML Probability, and User History.
    """
    
    def __init__(self):
        self.deterministic_weight = settings.DETERMINISTIC_WEIGHT
        self.ml_weight = settings.ML_WEIGHT

    def create_canonical_feature_vector(self, patient: Patient, vitals: VitalSigns) -> CanonicalClinicalFeatureSchema:
        """Normalizes inputs into the Canonical Clinical Feature Schema."""
        return CanonicalClinicalFeatureSchema(
            heart_rate=vitals.heart_rate,
            spo2=vitals.spo2,
            temperature=vitals.temperature,
            systolic_bp=vitals.systolic_bp or 120.0,
            diastolic_bp=vitals.diastolic_bp or 80.0,
            
            age=patient.age,
            age_missing=patient.age is None,
            
            diabetes=patient.diabetes or "unknown",
            smoking_status=patient.smoking_status or "unknown",
            
            medications=patient.medications or [],
            past_conditions=patient.past_conditions or [],
            
            timestamp=vitals.timestamp,
            source=vitals.data_source.value if vitals.data_source else "unknown"
        )

    def evaluate_deterministic_rules(self, features: CanonicalClinicalFeatureSchema) -> Dict[str, Any]:
        """Layer 2: Deterministic Engine based on WHO/Clinical guidelines"""
        triggered_rules = []
        risk_class = HealthStatus.NORMAL
        base_confidence = 1.0

        # WHO/Clinical Guidelines for Critical
        if features.spo2 < 92:
            triggered_rules.append("Severe Hypoxemia (SpO2 < 92%)")
            risk_class = HealthStatus.CRITICAL
        elif features.heart_rate > 150 or features.heart_rate < 40:
            triggered_rules.append("Severe Arrhythmia/Tachycardia/Bradycardia")
            risk_class = HealthStatus.CRITICAL
        elif features.systolic_bp >= 180 or features.diastolic_bp >= 120:
            triggered_rules.append("Hypertensive Crisis")
            risk_class = HealthStatus.CRITICAL
            
        # Warning Guidelines
        elif features.spo2 < 95:
            triggered_rules.append("Mild Hypoxemia (SpO2 < 95%)")
            risk_class = HealthStatus.WARNING
        elif features.heart_rate > 120 or features.heart_rate < 50:
            triggered_rules.append("Abnormal Heart Rate")
            risk_class = HealthStatus.WARNING
        elif features.temperature >= 38.0 or features.temperature < 35.0:
            triggered_rules.append("Hyperthermia/Fever or Hypothermia")
            risk_class = HealthStatus.WARNING
            
        # Hard penalties for missing critical history
        penalty = 0.0
        if features.age_missing:
            penalty += 0.05
        if features.diabetes == "unknown":
            penalty += 0.05
        if features.smoking_status == "unknown":
            penalty += 0.05
            
        final_confidence = max(0.0, base_confidence - penalty)
        
        # Convert class to numerical score for fusion
        score_map = {HealthStatus.NORMAL: 0.0, HealthStatus.WARNING: 0.5, HealthStatus.CRITICAL: 1.0}
        
        return {
            "risk_class": risk_class,
            "triggered_rules": triggered_rules,
            "rule_confidence": final_confidence,
            "score": score_map[risk_class]
        }

    def fuse_risk(self, deterministic_output: Dict[str, Any], ml_prediction: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Layer 4: Fusion Engine (Pure Code)"""
        
        # 1. Safety Override: If deterministic rules mandate CRITICAL, it is absolute.
        if deterministic_output["risk_class"] == HealthStatus.CRITICAL:
            return {
                "final_risk_level": "critical",
                "confidence_score": deterministic_output["rule_confidence"],
                "deterministic_flags": deterministic_output["triggered_rules"],
                "ml_risk_probability": ml_prediction["probability"] if ml_prediction else None,
                "fusion_method": "deterministic_override"
            }
            
        # 2. Weighted Fusion
        det_score = deterministic_output["score"]
        ml_score = 0.0
        ml_prob = None
        
        if ml_prediction:
            ml_prob = ml_prediction["probability"]
            if ml_prediction["predicted_class"] == "critical":
                ml_score = 1.0
            elif ml_prediction["predicted_class"] == "warning":
                ml_score = 0.5
                
            final_numeric_score = (self.deterministic_weight * det_score) + (self.ml_weight * ml_score)
            confidence = deterministic_output["rule_confidence"] * ml_prediction.get("probability", 1.0)
        else:
            # If no ML prediction (e.g. < 60 readings), rely 100% on deterministic
            final_numeric_score = det_score
            confidence = deterministic_output["rule_confidence"]
            
        if final_numeric_score >= 0.7:
            final_risk = "critical"
        elif final_numeric_score >= 0.4:
            final_risk = "warning"
        else:
            final_risk = "normal"
            
        return {
            "final_risk_level": final_risk,
            "confidence_score": round(confidence, 2),
            "deterministic_flags": deterministic_output["triggered_rules"],
            "ml_risk_probability": round(ml_prob, 2) if ml_prob else None,
            "fusion_method": "weighted_fusion" if ml_prediction else "deterministic_only"
        }

    async def generate_explanation(self, patient: Patient, fusion_result: Dict[str, Any]) -> str:
        """Layer 5: LLM Explanation Layer (Gemini)"""
        if not settings.GEMINI_API_KEY:
            return "AI Explanation unavailable. (GEMINI_API_KEY not configured)"
            
        system_prompt = """SYSTEM PROMPT: Clinical Hybrid Risk Engine

You are a clinical decision-support reasoning engine that evaluates patient risk using a hybrid architecture consisting of:
- Deterministic Rules Engine (priority layer)
- Machine Learning Risk Model (probabilistic layer)
- Patient Self-Reported Medical History (context augmentation layer)

SAFETY CONSTRAINTS:
1. You DO NOT decide the final risk. The final risk has already been decided by the backend.
2. Your ONLY job is to output a concise clinical explanation based on the provided inputs.
3. Never fabricate missing medical values.
4. Always prioritize safety over model prediction.
5. Treat system as decision support, not diagnosis.
6. Do NOT upgrade or alter the certainty tone of the final decision.
7. Do NOT introduce non-existent clinical reasoning language that is not explicitly supported by the triggered rules.
8. Maintain a neutral, objective, and purely explanatory tone."""

        user_prompt = f"""
Please explain the following clinical decision.

INPUT STRUCTURE:
A) Patient Medical History
- Age: {patient.age if patient.age else 'Unknown'}
- Diabetes: {patient.diabetes}
- Smoking Status: {patient.smoking_status}
- Medications: {', '.join(patient.medications) if patient.medications else 'None reported'}
- Past Conditions: {', '.join(patient.past_conditions) if patient.past_conditions else 'None reported'}

B) Computed Outputs
- Triggered Deterministic Rules: {', '.join(fusion_result['deterministic_flags']) if fusion_result['deterministic_flags'] else 'None'}
- ML Risk Probability: {fusion_result['ml_risk_probability']}

C) Final Backend Decision (ALREADY DETERMINED)
- Final Risk Level: {fusion_result['final_risk_level'].upper()}
- Confidence Score: {fusion_result['confidence_score']}
- Fusion Method: {fusion_result['fusion_method']}

OUTPUT FORMAT:
Return ONLY a concise, human-readable clinical reasoning paragraph explaining why this decision was reached. Do not include any JSON or markdown headers.
"""
        try:
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
            
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser: {user_prompt}"}]}]
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(gemini_url, json=payload)
                
            if response.status_code >= 400:
                logger.error(f"Gemini error: {response.text}")
                return "Failed to generate AI reasoning due to API error."
                
            data = response.json()
            explanation = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return explanation.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate LLM explanation: {str(e)}")
            return "Failed to generate clinical reasoning."

fusion_engine = FusionEngine()
