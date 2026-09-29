# Phase 4: Frontend Repository Audit Report

**Project Title**: HealSense Cloud-Native Migration  
**Subsystem**: Web Dashboard Application (`frontend/web-app/`)  
**Phase**: Phase 4 - Objective 1 Audit  
**Status**: AUDIT COMPLETE (NO CODE MODIFIED YET)  
**Date**: August 3, 2026  

---

> [!IMPORTANT]
> **Project Identity Anchor**:  
> *HealSense is an explainable IoT-based clinical decision support prototype that combines deterministic physiological safety rules with temporal machine learning analysis.*

---

## 1. Current Frontend Architecture Snapshot

```
frontend/
 ├── mobile-app/              # Mobile App integration sub-directory
 └── web-app/                 # Primary Web Dashboard (Vite + React 18 + TypeScript + TailwindCSS + ShadcnUI)
      ├── src/
      │    ├── components/    # Reusable UI widgets (VitalCard, TrendChart, AlertBanner, PatientHeader)
      │    ├── contexts/      # AuthContext
      │    ├── hooks/         # Custom hooks (useVitals, usePatient, useWebSocket)
      │    ├── lib/           # API client (`api.ts`), Endpoint config (`config.ts`)
      │    ├── pages/         # Dashboard, Profile, Login, Signup, Index, NotFound
      │    └── types/         # TypeScript type definitions (`vitals.ts`, `api.ts`)
```

### Component Analysis & Stack Inventory
* **Build Framework**: Vite (`^5.4.19`) + React 18 + TypeScript (`^5.8.3`).
* **UI & Styling**: TailwindCSS (`^3.4.17`), Radix UI Primitives, Lucide Icons (`lucide-react`).
* **Charting Library**: Recharts (`^2.15.4`) for vital trend charts.
* **State & Data Fetching**: TanStack React Query (`^5.83.0`), Custom React Contexts, Custom Hooks.

---

## 2. Identified Gaps & Missing Features

1. **Blood Pressure Acquisition Source Visualization (`bp_source`)**: UI cards currently do not display acquisition mechanisms (`manual_entry`, `ble_cuff`, `hardware_uart`, `none`).
2. **Offline Telemetry Sync Badge (`delayed_sync`)**: Visual indicators for historical NVS ring-buffer syncs are missing.
3. **Hybrid Risk Fusion Gauge & Scoring**: The dashboard lacks a dedicated `RiskGauge` and `RiskTimeline` visualizing rule scores, LSTM probability, and final fusion level.
4. **Gemini Clinical Decision Support Explanation Panel**: Lacks a dedicated non-diagnostic explanation card displaying LLM reasoning.
5. **Dedicated Device Status Page (`/devices`)**: No standalone device monitoring page showing heartbeat timestamps, hardware type, and connection status.
6. **Direct Telemetry Testing Service**: Missing `telemetryService.ts` for testing direct ingestion payloads (`POST /api/v1/telemetry`).

---

## 3. Required Modifications & Component Dependency Map

```
┌────────────────────────────────────────────────────────┐
│                      FRONTEND TARGET MAP               │
├────────────────────────────────────────────────────────┤
│ Services (`src/services/`)                             │
│   • apiClient.ts (Base HTTP client & auth interceptor)  │
│   • telemetryService.ts (POST /api/v1/telemetry testing)│
│   • patientService.ts (Profile & Vitals fetching)       │
│   • alertService.ts (Alert retrieval & acknowledgment)  │
│                                                        │
│ Real-Time Hooks (`src/hooks/`)                        │
│   • useTelemetrySocket.ts (Subscribes to websocket)    │
│                                                        │
│ Components (`src/components/`)                         │
│   • vitals/HeartRateCard.tsx                           │
│   • vitals/SpO2Card.tsx                                │
│   • vitals/TemperatureCard.tsx                         │
│   • vitals/BloodPressureCard.tsx (bp_source tag)       │
│   • risk/RiskGauge.tsx & RiskExplanation.tsx           │
│   • GeminiExplanationCard.tsx ("Decision Support")     │
│   • VitalTrendChart.tsx (Recharts history)             │
│                                                        │
│ Pages (`src/pages/`)                                   │
│   • Dashboard.tsx (Clinical Dashboard)                 │
│   • Devices.tsx (/devices hardware view)               │
└────────────────────────────────────────────────────────┘
```

---

## 4. Phase 4 Execution Checklist

- [x] Repository audit complete.
- [ ] Refactor API client services (`src/services/`).
- [ ] Implement `useTelemetrySocket.ts`.
- [ ] Create specialized vital cards with `bp_source` and `delayed_sync` badges.
- [ ] Implement `RiskGauge` and `GeminiExplanationCard`.
- [ ] Implement `VitalTrendChart` and `/devices` monitoring page.
- [ ] Add Vitest component & integration simulation tests in `frontend/web-app/src/test/`.

**Status**: Audit complete. Ready for implementation.
