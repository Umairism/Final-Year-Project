# HealSense Backend API

## FastAPI REST and Real-time WebSocket Server

The backend is a FastAPI-based HTTP REST API server that handles all business logic for the HealSense health monitoring system. It manages patient data, vital sign ingestion, machine learning model inference, alert generation, and real-time data streaming through WebSocket connections.

## Overview

The backend serves as the central hub connecting mobile and web clients with the PostgreSQL database, machine learning models, and external services. It provides comprehensive endpoints for patient management, device management, alert handling, and real-time vital sign streaming.

## Quick Start

### Prerequisites

You need the following installed on your system:

- Python 3.10 or higher
- git for version control
- PostgreSQL (for database)
- Redis (optional, for caching)

### Installation

Navigate to the backend directory:

```bash
cd healsense/backend
```

The Python virtual environment and dependencies are configured at the project root. Install dependencies with:

```bash
pip install -r requirements.txt
```

Prepare the environment configuration:

```bash
cp .env.example .env
```

Edit the .env file with your configuration, especially:
- DATABASE_URL pointing to your PostgreSQL instance
- API security keys and secrets
- External service credentials if applicable

### Running the Server

The backend can be run in development mode with auto-reload or production mode with Gunicorn.

**Development Mode**

For development with automatic code reloading:

```bash
python run.py
```

The server will start at http://localhost:5000 with auto-reload enabled.

**Production Mode**

For production deployment using Gunicorn with multiple worker processes:

```bash
gunicorn api.app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
```

**Using Uvicorn Directly**

Alternatively, run Uvicorn directly:

```bash
uvicorn api.app:app --host 0.0.0.0 --port 5000 --reload
```

### Database Setup

Initialize the database schema:

```bash
python init_db.py
```

This creates all tables and seeds sample data. For database migrations after schema changes:

```bash
alembic upgrade head
```

### Access the API

Once running, the API is accessible at several endpoints:

**API Root**: Visit http://localhost:5000/ for general information

**Health Check**: Visit http://localhost:5000/health for server health status

**Interactive API Documentation**: Visit http://localhost:5000/api/docs for Swagger UI interactive documentation

**Alternative Documentation**: Visit http://localhost:5000/api/redoc for ReDoc alternative documentation

### Real-time Streaming

The backend supports WebSocket connections for real-time vital sign streaming:

**Global Stream**: Connect to ws://localhost:5000/ws/live for all vital sign updates across the system

**Patient Stream**: Connect to ws://localhost:5000/ws/patients/{patient_id} for updates specific to a patient

**Device Stream**: Connect to ws://localhost:5000/ws/devices/{device_id} for device status updates

## Project Structure

The backend is organized with clear separation of concerns:

```
backend/
├── api/                             # Main FastAPI application
│   ├── __init__.py
│   ├── app.py                       # FastAPI application initialization
│   │   (CORS setup, middleware registration, route mounting, lifespan)
│   ├── config.py                    # Configuration management
│   │   (Environment variables, Pydantic settings)
│   │
│   ├── routes/                      # API endpoint handlers
│   │   ├── __init__.py
│   │   ├── patients.py              # Patient CRUD endpoints
│   │   ├── alerts.py                # Alert management endpoints
│   │   ├── devices.py               # Device registration and management
│   │   ├── ai.py                    # AI assistant endpoints
│   │   └── realtime.py              # WebSocket endpoint handlers
│   │
│   ├── models/                      # Data models and schemas
│   │   ├── __init__.py
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   └── database/                # SQLAlchemy database models
│   │       ├── __init__.py
│   │       ├── base.py              # Base model class
│   │       ├── patient.py
│   │       ├── vital_signs.py
│   │       ├── device.py
│   │       ├── alert.py
│   │       ├── emergency.py
│   │       └── user.py
│   │
│   ├── services/                    # Business logic services
│   │   ├── __init__.py
│   │   ├── patient_service.py       # Patient operations
│   │   ├── alert_service.py         # Alert generation and management
│   │   ├── ml_service.py            # Machine learning inference
│   │   ├── realtime.py              # WebSocket connection management
│   │   └── notification_service.py  # Alert notifications
│   │
│   ├── middleware/                  # Custom middleware
│   │   ├── __init__.py
│   │   ├── auth.py                  # Authentication middleware
│   │   └── logging.py               # Request logging middleware
│   │
│   └── utils/                       # Utility functions
│       ├── __init__.py
│       └── logger.py                # Structured logging setup
│
├── alembic/                         # Database migration system
│   ├── env.py                       # Migration environment configuration
│   ├── script.py.mako               # Migration script template
│   ├── README                       # Migration usage guide
│   └── versions/                    # Migration files
│       └── b52623274ba1_add_phone_sensor_support_devicetype_.py
│
├── tests/                           # Test suite
│   ├── test_db_endpoints.py         # Database endpoint tests
│   └── test-integration.ps1         # Integration testing script
│
├── run.py                           # Development server launcher
├── wsgi.py                          # Production WSGI application entry
├── alembic.ini                      # Alembic configuration
├── init_db.py                       # Database initialization script
├── requirements.txt                 # Python dependencies
├── verify-setup.ps1                 # Setup verification script
├── .env.example                     # Environment variables template
└── README.md                        # This file
```

## Key Endpoints

### Patient Management

**Get Patient**: GET /api/v1/patients/{patient_id}

Retrieves complete patient information including demographics and medical history.

**Create Patient**: POST /api/v1/patients

Creates a new patient record with provided information.

**Get Patient Profile with Vitals**: GET /api/v1/patients/{patient_id}/profile

Returns patient information along with latest vital signs and recent alerts.

**Get Latest Vitals**: GET /api/v1/patients/{patient_id}/vitals/latest

Returns the most recent vital sign measurement for a patient.

**Get Vitals History**: GET /api/v1/patients/{patient_id}/vitals/history

Returns historical vital signs within specified time window (query parameter: minutes).

**Submit Vitals**: POST /api/v1/patients/{patient_id}/vitals

Records a new vital sign measurement from any device source.

### Alert Management

**List Alerts**: GET /api/v1/alerts

Returns all alerts, optionally filtered by patient, severity, or status.

**Get Alert Details**: GET /api/v1/alerts/{alert_id}

Returns detailed information about a specific alert.

**Acknowledge Alert**: POST /api/v1/alerts/{alert_id}/acknowledge

Marks an alert as acknowledged by a healthcare provider.

**Dismiss Alert**: POST /api/v1/alerts/{alert_id}/dismiss

Marks an alert as dismissed with optional reason.

### Device Management

**Get Device Info**: GET /api/v1/devices/{device_id}

Returns detailed information about a device.

**Get Device Status**: GET /api/v1/devices/{device_id}/status

Returns current connection status, battery level, and signal strength.

**Connect Device**: POST /api/v1/devices/{device_id}/connect

Registers and pairs a device with a patient account.

**Disconnect Device**: POST /api/v1/devices/{device_id}/disconnect

Unregisters a device from a patient account.

### AI Assistant

**Get Providers**: GET /api/v1/ai/providers

Lists available AI service providers (OpenAI, Gemini, etc.).

**Chat with AI**: POST /api/v1/ai/chat

Sends a message to the AI assistant for health guidance.

## Configuration

Configuration is managed through environment variables in the .env file. Key settings include:

### Application Settings

**ENV**: Development or production environment

**DEBUG**: Enable debug logging

**PROJECT_NAME**: Application name

**API_V1_PREFIX**: Base path for API endpoints

**HOST** and **PORT**: Server binding address and port

### Security

**SECRET_KEY**: JWT secret key for token signing (must be strong and unique in production)

**ALGORITHM**: Token encryption algorithm (default: HS256)

**ACCESS_TOKEN_EXPIRE_MINUTES**: How long before access tokens expire

**ALLOWED_ORIGINS**: CORS-allowed origins for frontend applications

### Database Connection

**DATABASE_URL**: PostgreSQL connection string in format postgresql://user:password@host:port/database

**ECHO_SQL**: Enable SQL query logging (dev only for debugging)

### Cache and Real-time

**REDIS_HOST** and **REDIS_PORT**: Redis server connection details (optional)

**REDIS_PASSWORD**: Redis authentication if required

### IoT Device Communication

**MQTT_BROKER** and **MQTT_PORT**: MQTT broker for IoT devices

**MQTT_TOPIC_PREFIX**: Topic prefix for MQTT messages

### External Services

**OPENAI_API_KEY**: OpenAI API key for GPT models

**OPENAI_MODEL**: GPT model name to use

**GEMINI_API_KEY**: Google Gemini API key

**GEMINI_MODEL**: Gemini model name to use

### Machine Learning

**LSTM_MODEL_PATH**: Path to trained LSTM model file

**SCALER_PATH**: Path to fitted feature scaler

**MODEL_VERSION**: Current model version in use

### Alert Configuration

**ALERT_THRESHOLDS**: JSON object defining alert thresholds for each vital

## Database

PostgreSQL is required for data persistence. The database schema includes:

**Patients Table**: Patient demographic and profile information

**Vital Signs Table**: Time-series vital measurement records

**Devices Table**: Connected device information

**Alerts Table**: Health alert records

**Users Table**: Provider and administrator accounts

**Emergencies Table**: Emergency event tracking

Database migrations are managed through Alembic. After schema changes, create and apply migrations:

```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

## Testing

Test vital functionality with included scripts:

**Test Database Endpoints**

```bash
python test_db_endpoints.py
```

**Integration Tests**

```bash
.\test-integration.ps1
```

## Deployment

### Development Deployment

For local development, simply run:

```bash
python run.py
```

### Production Deployment

For production, use Gunicorn:

```bash
gunicorn api.app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000 --access-logfile - --error-logfile -
```

### Docker Deployment

Build and run Docker container:

```bash
docker build -t healsense-backend .
docker run -p 5000:5000 -e DATABASE_URL=postgresql://... healsense-backend
```

### Cloud Deployment

The backend can be deployed to:
- AWS EC2 instances
- Heroku platform
- DigitalOcean
- Google Cloud Platform App Engine
- Azure App Service

## Troubleshooting

**Server Fails to Start**

Verify PostgreSQL is running and DATABASE_URL is correct. Check logs for detailed error messages.

**Database Connection Errors**

Ensure PostgreSQL service is running and credentials in .env are correct. Test connection with psql.

**WebSocket Connection Refused**

Check firewall settings allow WebSocket connections. Verify ws:// protocol is enabled in nginx/reverse proxy if applicable.

**ML Model Not Found**

Verify LSTM_MODEL_PATH and SCALER_PATH in .env point to valid files in data/models/ directory.

**External Service Errors**

Verify API keys for OpenAI and Gemini are valid. Check network connectivity to external services.

## API Response Format

All API responses follow a consistent format:

**Success Response**: Returns data object with status and timestamp

**Error Response**: Returns error message with status code and timestamp

**List Responses**: Include pagination information with total count and page details

## Performance Optimization

The backend includes several optimization features:

- Connection pooling for database efficiency
- Redis caching for frequently accessed data
- Indexed database queries for fast lookups
- Async/await for non-blocking operations
- JSON logging for efficient log aggregation

## Security Considerations

- All endpoints require JWT Bearer token authentication (except /health and /)
- Passwords are hashed with bcrypt before storage
- Database connections use SSL/TLS in production
- CORS is configured to restrict cross-origin requests
- Environment variables protect sensitive configuration

## Monitoring

The backend includes logging and monitoring capabilities:

- Structured JSON logging for easy aggregation
- Health check endpoint for service monitoring
- Performance metrics collection
- Error tracking and reporting

Monitor the health endpoint regularly:

```bash
curl http://localhost:5000/health
```

## Support and Documentation

For complete API documentation, see the PROJECT_COMPREHENSIVE_DOCUMENTATION.md file at the project root.

For detailed endpoint documentation, visit the interactive Swagger UI at /api/docs when the server is running.

## Version

Version: 1.0  
Last Updated: April 2026  
Status: Production-Ready
- `FIREBASE_CREDENTIALS_PATH` - Firebase integration

### ML Models
- `LSTM_MODEL_PATH` - LSTM model file
- `RF_MODEL_PATH` - Random Forest model file
- `SCALER_PATH` - Data scaler file

## 📦 Dependencies

Major dependencies:
- **FastAPI** - Modern web framework
- **Uvicorn** - ASGI server
- **SQLAlchemy** - ORM for database
- **Pydantic** - Data validation
- **TensorFlow** - ML model inference
- **Scikit-learn** - Classical ML models
- **Redis** - Caching
- **Paho-MQTT** - IoT communication
- **Firebase Admin** - Cloud services

See [requirements.txt](requirements.txt) for complete list.

## 🛣️ API Endpoints (Planned)

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh token

### Sensor Data
- `POST /api/v1/data/` - Ingest sensor data
- `GET /api/v1/data/latest/{patient_id}` - Get latest vitals
- `GET /api/v1/data/history/{patient_id}` - Get vital history

### Predictions
- `POST /api/v1/predict/` - Get health prediction
- `GET /api/v1/predict/batch/{patient_id}` - Batch predictions

### Patients
- `GET /api/v1/patients/` - List patients
- `POST /api/v1/patients/` - Create patient
- `GET /api/v1/patients/{id}` - Get patient details
- `PUT /api/v1/patients/{id}` - Update patient
- `DELETE /api/v1/patients/{id}` - Delete patient

### Analytics
- `GET /api/v1/analytics/dashboard` - Dashboard stats
- `GET /api/v1/analytics/trends/{patient_id}` - Trend analysis

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api tests/

# Run specific test file
pytest tests/test_api/test_health.py -v
```

## 🔒 Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS middleware configured
- Rate limiting (to be implemented)
- Input validation with Pydantic

## 📝 Development

### Code Quality

```bash
# Format code
black api/

# Sort imports
isort api/

# Type checking
mypy api/

# Linting
flake8 api/
```

### Adding New Endpoints

1. Create route file in `api/routes/`
2. Define Pydantic models for request/response
3. Implement business logic in `api/services/`
4. Add router to `api/app.py`
5. Write tests in `tests/`

## 📊 Monitoring

- Health check endpoint: `/health`
- Prometheus metrics (to be implemented)
- Structured JSON logging

## 🐳 Docker

```bash
# Build image
docker build -t healsense-backend .

# Run container
docker run -d -p 5000:5000 --env-file .env healsense-backend
```

## 🚧 TODO

- [ ] Implement authentication endpoints
- [ ] Add sensor data ingestion endpoints
- [ ] Integrate ML model for predictions
- [ ] Set up PostgreSQL database
- [ ] Implement Redis caching
- [ ] Add MQTT client for IoT devices
- [ ] Implement rate limiting
- [ ] Add comprehensive test suite
- [ ] Set up CI/CD pipeline
- [ ] Add API documentation
- [ ] Implement WebSocket for real-time updates

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Ensure code quality checks pass
5. Submit pull request

---

**Status**: ✅ Environment Setup Complete | 🚧 API Implementation In Progress
