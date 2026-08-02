# HealSense Cloud-Native System Topology (v1.2.0)

```mermaid
graph TD
    subgraph Edge Hardware Acquisition Layer
        MAX[MAX30100 - Heart Rate & SpO₂] -->|I2C| ESP[ESP32 IoT Gateway]
        MLX[MLX90614 - Temperature] -->|I2C| ESP
        NVS[(ESP32 NVS Storage Ring Buffer\n- Offline Retry Queue\n- delayed_sync flag)] <--> ESP
    end

    subgraph Direct Cloud Ingestion & Authentication
        ESP -->|HTTPS POST /api/v1/telemetry\nHeader: X-Device-API-Key| API[FastAPI Cloud Gateway]
        APP[Web & Mobile Dashboards] -->|REST / WebSockets| API
    end

    subgraph Centralized Intelligence Pipeline
        API --> AUTH[Header Auth & Device Key Hash Validation]
        AUTH --> SCHEMA[Canonical Schema Layer\n- Pydantic Validation]
        
        SCHEMA --> RULE[Deterministic Rules Engine\n- Safety Bounds Overrides]
        SCHEMA --> LSTM[Temporal LSTM Analysis\n- 60-Window Proxy Model]
        
        RULE --> FUSION[Hybrid Fusion Engine\n- Critical Override Priority\n- Experimental Confidence Scoring]
        LSTM --> FUSION
        
        FUSION --> GEMINI[Gemini Explanation Layer\n- Non-Diagnostic Reasoning Text]
    end

    subgraph Persistence & Client Broadcast
        FUSION --> DB[(PostgreSQL Database)]
        GEMINI --> DB
        DB --> APP
    end
```

> [!NOTE]
> **Raspberry Pi 5 Status**: Completely eliminated from production data path. Telemetry flows directly from ESP32 to FastAPI Cloud Backend over Wi-Fi/HTTPS.
