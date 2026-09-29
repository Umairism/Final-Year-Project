# HealSense — Clinical Hybrid Risk Decision-Support System

> **FYP | IoT + AI Health Monitoring | Rule-Constrained Clinical Risk Engine**

HealSense is an **explainable, rule-constrained clinical decision-support system** for continuous physiological monitoring — not a diagnostic system. It combines deterministic clinical safety rules, an LSTM temporal risk model, and a Gemini LLM explanation layer into a safety-prioritised fusion pipeline.

---

## Repository Structure

```
healsense/
├── backend/                     # FastAPI backend + ML inference
│   ├── api/                     #   Routes, services, models, schemas
│   │   ├── routes/              #   Endpoint handlers
│   │   ├── services/            #   fusion_engine, prediction_service, telemetry
│   │   └── models/              #   SQLAlchemy ORM + Pydantic schemas
│   ├── ml/                      #   Training evaluation scripts
│   │   └── evaluate_model.py    #   Real evaluation (requires trained model)
│   ├── alembic/                 #   Database migrations
│   └── tests/                   #   Integration test suite
│
├── frontend/                    # React + TypeScript web dashboard
│
├── firmware/                    # ESP32 C++ firmware (sensor node)
│
├── notebooks/                   # Jupyter notebooks (EDA, LSTM training)
│   ├── 01_data_exploration.ipynb
│   ├── 02_lstm_health_prediction.ipynb
│   └── Google_Colab_Setup.ipynb
│
├── scripts/                     # Data & model pipeline scripts
│   ├── preprocess_kaggle_vitals.py  # ← START HERE for training data
│   ├── train_model.py               # LSTM training pipeline
│   ├── evaluate_system.py           # System-level evaluation
│   └── generate_synthetic_data.py   # Synthetic data generator
│
├── data/                        # Dataset directory (not committed)
│   ├── raw/                     #   Downloaded datasets
│   ├── models/                  #   Trained model artifacts (v1.0.2/)
│   └── processed/               #   Preprocessed outputs
│
├── docs/                        # All documentation (see docs/README.md)
│   ├── architecture/            #   System & component architecture
│   ├── api/                     #   API reference
│   ├── database/                #   Schema & alignment reports
│   ├── ml/                      #   ML pipeline & explainability
│   ├── firmware/                #   ESP32 design docs
│   ├── frontend/                #   UI documentation
│   ├── phases/                  #   Phase implementation reports
│   ├── audit/                   #   Audit & validation reports
│   ├── defence/                 #   Defence materials (LaTeX, Q&A)
│   ├── assets/                  #   PDFs, proposals
│   ├── diagrams/                #   PlantUML diagram sources
│   └── releases/                #   Release notes per version
│
├── PUBLICATION_READINESS.md     # Full repository audit (21 dimensions)
├── AI_ENGINE_REPORT.md          # Deep-dive: LSTM + LLM break-points
└── README.md                    # This file
```

---

## Core Architecture

```
Telemetry Input (ESP32 / Mobile / Manual)
         │
         ▼
┌─────────────────────────┐
│  Layer 1: Canonical     │  Normalises all inputs into standard schema
│  Feature Vector         │  (heart_rate, spo2, temp, systolic, diastolic)
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│  Layer 2: Deterministic │  WHO/clinical thresholds — ABSOLUTE OVERRIDE
│  Rules Engine           │  SpO2<92 → CRITICAL | HR>150 → CRITICAL
└────────────┬────────────┘  BP≥180/120 → CRITICAL
             │
┌────────────▼────────────┐
│  Layer 3: LSTM Risk     │  Probabilistic temporal pattern recognition
│  Prediction             │  Input: 60-reading sliding window (5 features)
└────────────┬────────────┘  Requires: data/models/v1.0.2/lstm_best.h5
             │
┌────────────▼────────────┐
│  Layer 4: Fusion Engine │  det×0.6 + ml×0.4 | CRITICAL is non-negotiable
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│  Layer 5: Gemini LLM    │  Clinical reasoning explanation ONLY
│  Explanation            │  Cannot modify or escalate the decision
└─────────────────────────┘
```

---

## Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in GEMINI_API_KEY, DATABASE_URL
python run.py
```

### 2. Train the LSTM (first time)
```bash
# Download Human Vital Signs 2024 from Kaggle → data/raw/kaggle_health_data/
python scripts/preprocess_kaggle_vitals.py   # converts to canonical format
python scripts/train_model.py                # trains → data/models/v1.0.2/
cd backend && python ml/evaluate_model.py    # generates real metrics
```

### 3. Frontend Setup
```bash
cd frontend/web-app
npm install
cp .env.example .env          # set VITE_USE_MOCK_DATA=false
npm run dev
```

---

## Safety Principle

> **The ML model and LLM layer can NEVER override a CRITICAL classification made by the deterministic rules engine.**

This is enforced in code at [`backend/api/services/fusion_engine.py`](backend/api/services/fusion_engine.py) lines 99–107. The deterministic override is unconditional.

---

## Documentation

All documentation is in [`docs/`](docs/). See [`docs/README.md`](docs/README.md) for the full index.

Key audit documents at repository root:
- [`PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md) — 21-dimension system audit
- [`AI_ENGINE_REPORT.md`](AI_ENGINE_REPORT.md) — LSTM & LLM deep-dive with all break-points

---

## Academic Disclaimers

- **Not a diagnostic system.** This is an experimental clinical decision-support prototype.
- **Rule-derived proxy labels.** The LSTM is trained and evaluated on labels derived from the same WHO thresholds used in the rules engine. High internal consistency does not validate clinical accuracy.
- **Self-consistency validation.** Evaluation metrics measure agreement with deterministic safety rules, not external clinical outcomes.
