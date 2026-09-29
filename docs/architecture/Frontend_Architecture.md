# Frontend Architecture Specification

**Framework**: Vite + React 18 + TypeScript + TailwindCSS + ShadcnUI  
**Subsystem**: Web Dashboard Application (`frontend/web-app/`)  
**Version**: v1.4.0-frontend-integration  
**Date**: August 3, 2026  

---

> [!IMPORTANT]
> **Project Identity Anchor**:  
> *HealSense is an explainable IoT-based clinical decision support prototype that combines deterministic physiological safety rules with temporal machine learning analysis.*

---

## 1. Modular Frontend Directory Structure

```
frontend/web-app/
 ├── src/
 │    ├── components/
 │    │    ├── vitals/               # Specialized Vitals Cards & Charts
 │    │    │    ├── HeartRateCard.tsx
 │    │    │    ├── SpO2Card.tsx
 │    │    │    ├── TemperatureCard.tsx
 │    │    │    ├── BloodPressureCard.tsx  # Displays bp_source badge
 │    │    │    └── VitalTrendChart.tsx    # Recharts timeline history
 │    │    ├── risk/                 # Hybrid Fusion & Explainability Cards
 │    │    │    ├── RiskGauge.tsx          # Multi-score & safety rules gauge
 │    │    │    └── GeminiExplanationCard.tsx # "Decision Support Explanation"
 │    ├── hooks/
 │    │    ├── useTelemetrySocket.ts # Real-time telemetry.ingested WebSocket hook
 │    │    └── useVitals.ts          # Vitals polling & state manager
 │    ├── services/
 │    │    ├── apiClient.ts          # HTTP client & auth interceptor
 │    │    └── telemetryService.ts   # Direct POST /api/v1/telemetry service
 │    ├── pages/
 │    │    ├── Dashboard.tsx         # Primary Clinical Dashboard
 │    │    └── Devices.tsx           # Hardware Gateway & Device Monitor page
 │    └── test/
 │         └── Phase4ClinicalComponents.test.tsx # Vitest component suite
```

---

## 2. Real-Time Telemetry Data Flow

```
ESP32 Hardware / Telemetry Source
       │
       ▼
HTTP POST /api/v1/telemetry
       │
       ▼
FastAPI Cloud Ingestion Service
       │
       ├─► Broadcast Event: "telemetry.ingested" (WebSockets)
       │
       ▼
Frontend `useTelemetrySocket` Hook
       │
       ▼
React Dashboard Component Re-render (Live Updates)
```
