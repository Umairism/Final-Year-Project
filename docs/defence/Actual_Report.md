# Clinical Hybrid Risk Engine: Technical Documentation

## 1. System Overview
**Problem Statement:** Modern clinical settings generate vast streams of physiological telemetry, but pure black-box Machine Learning models lack the transparency and deterministic safety guarantees required for medical decision support.
**System Goal:** To build an explainable, reliable, and reproducible clinical decision support system that accurately tracks physiological degradation while maintaining rigid safety boundaries.
**Hybrid Architecture Definition:** The Clinical Hybrid Risk Engine integrates deterministic clinical safety rules with a probabilistic Machine Learning (ML) layer, culminating in an explicitly constrained Large Language Model (LLM) explanation layer. It functions as a **self-consistency validation architecture** where the ML model acts as a temporal mimic layer for safety-constrained decision boundaries.

## 2. System Architecture (DETAILED)

### A. Frontend Layer
* **Web Dashboard:** (React / Next.js architecture) Provides clinicians with a real-time visualization of risk outputs.
* **Mobile UI Input System:** (React Native / Expo architecture) Designed for continuous monitoring and data ingress.
* **Patient Data Entry Flow:** Captures physiological telemetry and structured medical history dynamically.
* **Visualization of Risk Output:** Displays current risk level (Normal, Warning, Critical) along with deterministic rule triggers and the LLM-generated rationale.
* **API Communication Flow:** Uses RESTful APIs over HTTP to transmit JSON payloads representing continuous patient streams to the FastAPI backend.

*(Note: Extended deployment integration of web and mobile UI modules is marked as limited in the current prototype implementation).*

### B. Backend Layer (FastAPI)
* **API Routes Structure:** Utilizes FastAPI for asynchronous, high-throughput routing.
* **Patient Endpoints:** Routes handling CRUD operations for patient records and physiological ingestion.
* **Fusion Endpoint (`/fusion_risk`):** The primary endpoint orchestrating the hybrid decision logic.
* **Data Flow Orchestration:** 
  1. Validates incoming JSON via Pydantic.
  2. Routes structured data to the Deterministic Engine.
  3. Prepares continuous arrays for the LSTM Model.
  4. Triggers the Fusion Engine for the final state.
  5. Asynchronously queries the Gemini API for natural language explanation.

### C. Database Layer
* **Patient Schema:** Manages core demographic metadata.
* **Medical History Schema:** Stores structured binary flags (e.g., `diabetes`, `smoking_status`).
* **Storage of Vitals, History, Predictions:** Time-series telemetry linked to patient IDs.
* **Relational Structure:** Currently implemented as a lightweight persistence layer tying a `Patient` ID to a temporal series of `Readings` and historic `Predictions`.

*(Note: Advanced distributed database capabilities are not included in the current implementation).*

## 3. Canonical Clinical Schema

Schema standardization is critical because it guarantees structural consistency across deterministic boundaries, preventing missing or malformed data from triggering unhandled exceptions or artificial biases.

**Vitals:**
* `heart_rate`: (bpm)
* `spo2`: (%)
* `temperature`: (°C)
* `systolic_bp`: (mmHg)
* `diastolic_bp`: (mmHg)

**Medical History:**
* `diabetes`: boolean flag (`unknown` if unrecorded)
* `smoking_status`: boolean flag (`unknown` if unrecorded)
* `age`: integer (or flagged `age_missing`)

**Missingness Encoding:** 
Absent sensor modalities (e.g., Temperature, BP) are explicitly encoded as `NaN`. Prior to ML ingestion, an explicit missing mask replaces `NaN` with a constant `-1.0` imputation, rigorously preserving structural width without creating physiological hallucinations.

**Validation Rules:** Hard boundaries enforced via Pydantic to ensure input bounds (e.g., SpO$_2$ cannot exceed 100).

## 4. Machine Learning Pipeline

* **LSTM Architecture Description:** A Long Short-Term Memory network utilizing `Masking` layers to handle `-1.0` imputed sequences, followed by dense output layers with softmax activation.
* **Sequence Length:** Evaluates exactly `60` timesteps (representing 60 seconds of 1 Hz data).
* **Input Features:** 5 continuous physiological signals normalized via `StandardScaler`.
* **Training Pipeline:** Supervised learning using categorical cross-entropy.
* **Output Probability:** Returns a probabilistic confidence array for classes $S \in \{\text{normal, warning, critical}\}$.

**Limitation - Rule-Derived Proxy Labels:** The model does not predict true clinical outcomes (e.g., mortality). It is strictly trained on **rule-derived proxy labels**, meaning it learns to mimic the outputs of the deterministic engine rather than discovering independent medical truth.

## 5. Deterministic Rule Engine
* **Safety Thresholds:** Immediate categorization based on hard physiological bounds.
* **WHO-based Constraints:** Utilizes established proxy thresholds (e.g., SpO$_2 < 92\%$ triggers severe hypoxia classification).
* **Override Logic:** Operates as an absolute safety net. If a threshold is breached, the patient state is instantly bound to the mandated severity, ignoring ML probability.

## 6. Fusion Engine
The Fusion Engine mathematically reconciles the predictions.

\[ \text{FinalScore} = (w_d \cdot D) + (w_m \cdot M) \]

* **Deterministic vs ML Weights:** The system utilizes a priority-weighted combination where $w_d = 0.6$ (Deterministic priority) and $w_m = 0.4$ (ML contribution).
* **Override Rules for CRITICAL cases:** If the deterministic output $D$ equals `CRITICAL`, the fusion calculation is entirely bypassed, forcing the `FinalScore` to the critical threshold.

## 7. LLM Explanation Layer
* **Role of Gemini:** The Gemini API is utilized exclusively as an Explanation Layer to translate complex mathematical fusion into human-readable clinical rationale.
* **Strict Non-Decision Role:** The LLM is structurally isolated from the decision-making process.
* **Explanation-Only Constraint:** Governed by an explicit system prompt demanding neutral, objective language that cannot alter the backend severity tone.

## 8. Data Pipeline
* **PhysioNet BIDMC Dataset:** The pipeline utilizes real-world continuous telemetry from the PhysioNet BIDMC PPG and Respiration Dataset.
* **Preprocessing Steps:** Extracts raw `wfdb` 1 Hz logs and aligns them to the `CanonicalClinicalFeatureSchema`.
* **NaN Handling:** Missing continuous parameters are explicitly tracked using `NaN`.
* **Sequence Generation:** Independent patient-level splitting guarantees no data leakage across 60-timestep sliding windows.

## 9. System Workflow (END-TO-END)
1. **UI:** Client transmits payload of continuous 1 Hz telemetry and structured history.
2. **API:** FastAPI receives and validates payload.
3. **Preprocessing:** Maps to Canonical Schema and applies `-1.0` mask to missing inputs.
4. **ML + Rules:** The LSTM evaluates the 60-second window while the Deterministic Engine assesses the instantaneous state.
5. **Fusion:** Weighted scores aggregate the predictions (respecting safety overrides).
6. **Explanation:** Gemini API constructs the clinical reasoning paragraph.
7. **Response:** Unified JSON is returned to the UI for clinician review.

## 10. Evaluation Methodology

* **Confusion Matrix:** Tracks alignment across Normal, Warning, and Critical classes.
* **Cohen’s Kappa:** Measures system agreement between the probabilistic ML layer and the deterministic rule layer.
* **Ablation Study:** The holdout set is evaluated individually across Rules-Only, ML-Only, and Hybrid System outputs to verify architectural stability.
* **Limitation - Proxy Labels:** The methodology does not claim external clinical validation. Evaluation metrics strictly assess the system's ability to maintain consistency with internal safety constraints.

**CONSTRAINTS ENFORCED:** 
* No fake clinical claims.
* No inflated accuracy claims.
* Internal consistency strictly maintained.
