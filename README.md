# Clinical Hybrid Risk Engine (HealSense)
## Explainable Hybrid Clinical Decision Support System

The **Clinical Hybrid Risk Engine** is an academic prototype for continuous physiological tracking and safety-constrained risk evaluation. Rather than functioning as a black-box predictive diagnostic AI, this system operates as an **explainable rule-constrained decision system with a Machine Learning mimic layer**.

It ensures absolute safety through deterministic bounds while using an LSTM to smooth temporal trajectories, culminating in a natural language explanation layer.

---

## 1. Core Architectural Identity

The system functions as a **self-consistency validation architecture**:
1. **Deterministic Rule Engine:** Enforces hard physiological safety thresholds (e.g., WHO guidelines) and generates "rule-derived proxy labels."
2. **Machine Learning Model (LSTM):** Learns the temporal sequence patterns that precede the rule-derived proxy labels, effectively operating as a probabilistic mimic of the deterministic engine.
3. **Fusion Engine:** Mathematically reconciles the rule outputs and ML probability scores.
4. **LLM Explanation Layer (Gemini):** Translates complex mathematical fusion into human-readable clinical rationale, strictly constrained from making independent clinical decisions.

---

## 2. Dataset and Pipeline
The system utilizes continuous telemetry from the **PhysioNet BIDMC PPG and Respiration Dataset**.
* The pipeline ingests 1 Hz sequences of Heart Rate and SpO2.
* **Missingness Handling:** Absent parameters (Temperature, Blood Pressure) are explicitly encoded using `NaN`. During LSTM ingestion, these are masked using constant imputation (`-1.0`), meticulously preserving the Canonical Schema without hallucinating physiological states.
* **No External Ground Truth:** The system evaluates temporal states against internally derived proxy labels, bypassing unverified clinical diagnostic claims.

---

## 3. Getting Started

### Prerequisites
* Python 3.10+
* Virtual Environment (venv)

### Installation
```bash
# 1. Clone the repository
git clone https://github.com/Umairism/Final-Year-Project.git
cd healsense

# 2. Setup Virtual Environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 3. Install Dependencies
pip install -r requirements.txt
```

### Execution Pipeline
1. **Fetch and Process Data:**
```bash
# Downloads PhysioNet numeric logs and enforces the Canonical Schema
python scripts/download_bidmc.py
python scripts/preprocess_bidmc.py
```

2. **Train the LSTM Mimic Layer:**
```bash
# Trains the model on proxy-labeled temporal sequences
python scripts/train_model.py
```

3. **System Evaluation:**
```bash
# Runs the ablation study and calculates Rule-Alignment (Cohen's Kappa)
python scripts/evaluate_system.py
```

---

## 4. Academic Disclaimers (Limitations)
* **Not a Diagnostic System:** This architecture is an experimental clinical decision-support prototype. It is fundamentally not designed or authorized to issue medical diagnoses.
* **Rule-Derived Proxy Labels:** The system is evaluated on internally derived proxy labels, not external clinical outcomes. 
* **Self-Consistency Validation:** High evaluation metrics (e.g., Cohen's Kappa = 1.0) do not validate clinical accuracy; they validate consistency with deterministic safety constraints.
