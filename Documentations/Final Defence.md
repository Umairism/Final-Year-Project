# HealSense Final Defence

## 1. Project State Overview

HealSense is currently a full-stack smart health monitoring platform with four integrated domains:

- Backend services (FastAPI + PostgreSQL + Alembic)
- Frontend clients (Web + Mobile)
- AI inference pipeline (LSTM/CNN oriented training and deployment flow)
- Realtime workflow (REST + WebSocket + fallback polling)

The system already supports patient/device management, vitals ingestion, alert generation, realtime streaming, and AI provider gateway endpoints for assistant-style responses.

## 2. Backend Current State

### 2.1 Technology Stack

- FastAPI application core in api/app.py
- Route modules for patients, devices, alerts, realtime, and AI
- SQLAlchemy ORM + Alembic migrations
- pydantic and pydantic-settings for runtime validation
- Environment-driven configuration via .env and api/config.py

### 2.2 Implemented Backend Capabilities

- CRUD and domain APIs for patient and device lifecycle
- Vitals submission paths including mobile/phone source
- Realtime websocket endpoints:
  - /ws/live
  - /ws/patients/{patient_id}
  - /ws/devices/{device_id}
- Event broadcasting from vitals/alerts/device events
- AI gateway endpoints for provider-backed chat flow

### 2.3 Runtime and Deployment Status

- Development server start and import validation are operational
- Dependency compatibility adjusted for modern Python and Windows execution
- Startup scripts available for dev/prod execution

## 3. Frontend Current State

### 3.1 Web App

- React + TypeScript + Vite architecture
- Dashboard for vital cards, trends, history, alerts, and emergency actions
- Realtime status parity added:
  - websocket live state
  - polling fallback state
  - active IoT source visibility
- API client supports both wrapped and raw backend JSON response formats

### 3.2 Mobile App

- Flutter app integrated with backend REST and realtime streams
- Provider-based vitals orchestration with fallback logic
- Phone/device registration and periodic vitals push
- Dashboard actions wired for emergency and history interactions

## 4. AI Engine (LSTM/CNN) State

### 4.1 Data + Training Pipeline Assets

- Data assets and scripts available under data/ and scripts/
- Notebooks present for data exploration and LSTM health prediction
- Model artifact directories present:
  - checkpoints
  - metadata
  - tflite export area

### 4.2 Modeling Direction

- LSTM branch: temporal sequence modeling for vitals trend-based prediction
- CNN branch: local pattern extraction over transformed/segmented signal windows
- Hybrid capability can be structured as feature fusion from both branches

### 4.3 Mathematical Objective (LaTeX)

Sequence input can be expressed as:

$$
X_t = [HR_t, SpO2_t, Temp_t, SBP_t, DBP_t, RR_t]
$$

For a prediction horizon $h$, model objective:

$$
\hat{y}_{t+h} = f_\theta(X_{t-k+1:t})
$$

Composite loss example:

$$
\mathcal{L} = \lambda_1 \cdot \text{MSE}(y, \hat{y}) + \lambda_2 \cdot \text{BCE}(a, \hat{a})
$$

where $y$ is continuous risk score (or future vital target) and $a$ is binary alert event.

## 5. End-to-End Workflow

### 5.1 Operational Workflow

1. IoT/phone devices capture vitals periodically.
2. Mobile/Web clients submit or fetch vitals via REST APIs.
3. Backend persists data and evaluates alert thresholds.
4. Realtime manager broadcasts event updates over WebSocket.
5. Clients render live status and fallback to polling when needed.
6. AI services consume historical windows to produce risk or recommendation outputs.

### 5.2 Pipeline Stages

- Data ingestion pipeline: sensors -> API validation -> storage
- Monitoring pipeline: storage -> threshold rules -> alert generation
- Streaming pipeline: domain event -> websocket channel -> UI refresh
- AI pipeline: data extraction -> preprocessing -> model inference -> response/API exposure

## 6. Complete Architecture (Current)

### 6.1 Layered Architecture Summary

- Edge Layer: phone sensors and connected devices
- Client Layer: Flutter mobile app and React web app
- Service Layer: FastAPI routes, realtime manager, AI gateway
- Data Layer: PostgreSQL + migration/version control via Alembic
- Intelligence Layer: LSTM/CNN model training, checkpointing, inference outputs

### 6.2 LaTeX Architecture Block (for Defence Slides/Report)

```latex
\[
\begin{array}{c}
\textbf{Edge Layer} \\
\text{Phone/IoT Sensors}
\end{array}
\xrightarrow{\text{REST/WebSocket}}
\begin{array}{c}
\textbf{Client Layer} \\
\text{Flutter Mobile} \\
\text{React Web}
\end{array}
\xrightarrow{\text{API Calls}}
\begin{array}{c}
\textbf{Service Layer} \\
\text{FastAPI Core} \\
\text{Realtime Manager} \\
\text{AI Gateway}
\end{array}
\xrightarrow{\text{ORM/Queries}}
\begin{array}{c}
\textbf{Data Layer} \\
\text{PostgreSQL + Alembic}
\end{array}
\]
```

### 6.3 TikZ Architecture Diagram (LaTeX)

```latex
\begin{tikzpicture}[node distance=1.8cm, >=latex, rounded corners]
  \node[draw, fill=blue!10] (edge) {Edge: Phone + IoT Sensors};
  \node[draw, fill=green!10, right=3.2cm of edge] (clients) {Clients: Flutter + React};
  \node[draw, fill=orange!10, right=3.2cm of clients] (service) {FastAPI + Realtime + AI Gateway};
  \node[draw, fill=purple!10, below=1.8cm of service] (data) {PostgreSQL + Alembic};
  \node[draw, fill=red!10, above=1.8cm of service] (ai) {LSTM/CNN Models + Inference};

  \draw[->] (edge) -- node[above]{REST/WS} (clients);
  \draw[->] (clients) -- node[above]{API Requests} (service);
  \draw[->] (service) -- node[right]{Persist/Fetch} (data);
  \draw[->] (service) -- node[right]{Inference Call} (ai);
  \draw[->] (ai) -- node[left]{Risk/Insight} (service);
  \draw[->] (service) -- node[below]{Realtime Events} (clients);
\end{tikzpicture}
```

## 7. Realtime and Reliability Design

- Primary live channel: WebSocket streams from backend realtime routes
- Fallback strategy: client-side polling if websocket drops
- Connection health shown in both mobile and web dashboard layers
- Device source visibility allows operator-level traceability for active stream origin

## 8. Defence Talking Points

- The project is no longer a prototype-only UI; it is an integrated distributed health system.
- Backend is modular, event-driven, and environment-configurable.
- Frontend is cross-platform and now synchronized for realtime health status semantics.
- AI path is prepared with data pipeline and model lifecycle components suitable for iterative improvement.
- Architecture supports extension toward production hardening (auth tightening, observability, model monitoring, CI/CD).

## 9. Immediate Next Technical Milestones

- Formalize model evaluation report (AUC/F1/MAE depending on target type)
- Add model version registry and drift checks
- Add E2E test suite for realtime failover scenarios
- Add deployment manifests and observability dashboards

---

This Final Defence file reflects the current integrated state of HealSense across backend, frontend, AI engine, workflows, and architecture.
