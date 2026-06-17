# 🩺 HealSense Project

**Deep Learning-Based Smart Health Surveillance and Prediction Model**

[![License](https://img.shields.io/badge/license-Academic-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React Native](https://img.shields.io/badge/react--native-0.81.5-blue.svg)](https://reactnative.dev/)
[![TensorFlow](https://img.shields.io/badge/tensorflow-2.x-orange.svg)](https://www.tensorflow.org/)

## 🌟 Overview

HealSense is an AI-powered health monitoring system that uses deep learning to predict health risks from real-time vital signs. The system combines IoT sensors, LSTM neural networks, and mobile/web applications to provide continuous health surveillance with intelligent alerting.

### Key Features

- **🤖 AI-Powered Predictions**: LSTM model with 93%+ accuracy for health risk classification
- **📱 Mobile-First**: React Native app with real-time vital sign monitoring
- **🌐 Web Dashboard**: React + Vite web application with Shadcn UI
- **⚡ Real-Time Alerts**: Instant notifications for critical health events
- **📊 Data-Driven**: Trained on UCI Heart Disease, PhysioNet, and Kaggle datasets
- **🔒 Secure**: Built with authentication, encryption, and HIPAA compliance in mind
- **📦 Production-Ready**: TFLite mobile deployment with <5MB model size

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 24+
- Jupyter Notebook

### Setup & Training

```bash
# Navigate to project
cd healsense

# Install Python dependencies
pip install -r requirements.txt

# Generate synthetic training data
python scripts/generate_synthetic_data.py

# Train the LSTM model
jupyter notebook notebooks/02_lstm_health_prediction.ipynb

# Deploy to mobile (generates TFLite model)
python scripts/deploy_model.py
```

### Run Mobile App

```bash
cd frontend/mobile-app
npm install
npx expo start
```

**Demo Account**: `umair@healsense.com` / `password123`

### Run Web Dashboard

```bash
cd frontend/web-app
npm install
npm run dev
```

## 📁 Project Structure

```
healsense/
├── data/
│   ├── raw/                    # Source datasets
│   │   ├── uci_heart_disease/  # UCI Heart Disease dataset
│   │   ├── physionet_bidmc/    # PhysioNet BIDMC dataset
│   │   ├── kaggle_health_data/ # Kaggle health datasets
│   │   └── synthetic/          # Generated training data
│   └── models/                 # Trained models
│       ├── checkpoints/        # Training checkpoints
│       ├── metadata/           # Model metadata & scalers
│       └── tflite/            # Mobile-optimized models
│
├── notebooks/                  # Jupyter notebooks
│   ├── 01_data_exploration.ipynb
│   └── 02_lstm_health_prediction.ipynb
│
├── scripts/                    # Utility scripts
│   ├── generate_synthetic_data.py  # Data generation
│   ├── deploy_model.py            # Model deployment
│   └── download_datasets.py       # Dataset downloaders
│
├── frontend/
│   ├── mobile-app/            # React Native + Expo app
│   │   ├── src/
│   │   │   ├── components/   # Reusable UI components
│   │   │   ├── screens/      # App screens
│   │   │   ├── contexts/     # State management
│   │   │   ├── hooks/        # Custom React hooks
│   │   │   └── types/        # TypeScript definitions
│   │   └── package.json
│   │
│   └── web-app/               # React + Vite + Shadcn UI
│       ├── src/
│       │   ├── components/   # UI components
│       │   ├── pages/        # Page components
│       │   ├── hooks/        # Custom hooks
│       │   └── lib/          # Utilities
│       └── package.json
│
├── backend/                    # Backend API (in development)
│   └── .env.example
│
└── docs/                       # Documentation
    └── diagrams/              # PlantUML architecture diagrams
```

## 🧠 Machine Learning Model

### Architecture

- **Type**: LSTM (Long Short-Term Memory) Neural Network
- **Input**: 60 timesteps × 5 features (HR, SpO₂, Temp, BP, RR)
- **Layers**: 
  - LSTM(128) + Dropout(0.3)
  - LSTM(64) + Dropout(0.2)
  - Dense(32) + Dropout(0.1)
  - Dense(3, softmax)
- **Output**: 3 classes (Normal, Warning, Critical)

### Performance

- **Accuracy**: 93%+ on test data
- **Critical Recall**: >95% (catches emergencies)
- **Model Size**: <5MB (TFLite with float16 quantization)
- **Inference Time**: <100ms on mobile devices

### Training Features

- StandardScaler normalization
- Class weights for imbalance handling
- Early stopping & learning rate reduction
- Comprehensive evaluation (confusion matrix, ROC curves)

## 📱 Mobile Application

### Features

- **Real-Time Monitoring**: Live vital signs display with color-coded status
- **Smart Alerts**: Automatic notifications for abnormal vitals
- **Profile Management**: Patient info, medical conditions, medications
- **Emergency System**: One-tap emergency contacts with WhatsApp integration
- **Authentication**: Secure login with AsyncStorage persistence
- **Dark Mode**: Full dark mode support

### Tech Stack

- React Native 0.81.5 with Expo 54
- TypeScript 5.3.3
- React Navigation 6.x
- React Query for state management
- Expo components & APIs

## 🌐 Web Dashboard

### Features

- **Modern UI**: Shadcn UI components with Tailwind CSS
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Type-Safe**: Full TypeScript support
- **Fast Development**: Vite for instant HMR

### Tech Stack

- React 19
- Vite
- TypeScript
- Shadcn UI + Radix UI
- Tailwind CSS
- React Query

## 📊 Datasets

- **UCI Heart Disease**: 303 patients with 14 clinical features
- **PhysioNet BIDMC**: Respiratory and vital signs from ICU patients
- **Kaggle Health Data**: Various health prediction datasets
- **Synthetic Data**: 10,000 generated records with realistic distributions

## 📖 Documentation

- **[CONSTRUCTION.md](CONSTRUCTION.md)**: Complete system architecture and implementation guide
- **[healsense/README.md](healsense/README.md)**: Quick start guide for ML pipeline
- **[healsense/TODO.md](healsense/TODO.md)**: 18-week development roadmap
- **[healsense/SETUP.md](healsense/SETUP.md)**: Installation instructions
- **[healsense/MODEL_SUMMARY.md](healsense/MODEL_SUMMARY.md)**: Detailed model documentation
- **[mobile-app/README.md](healsense/frontend/mobile-app/README.md)**: Mobile app documentation

## 🛠️ Development Status

### ✅ Completed

- [x] Project structure and setup
- [x] Data collection and preprocessing pipelines
- [x] LSTM model training and evaluation
- [x] TFLite model conversion and optimization
- [x] Mobile app with full UI/UX
- [x] Web dashboard with Shadcn UI
- [x] Authentication and profile management
- [x] Real-time monitoring and alerts
- [x] Emergency contact system

### 🚧 In Progress

- [ ] Backend API development
- [ ] WebSocket real-time data streaming
- [ ] IoT sensor integration
- [ ] Database setup (PostgreSQL/Firebase)
- [ ] Cloud deployment

### 📅 Planned

- [ ] Hardware integration (Arduino/Raspberry Pi)
- [ ] WhatsApp Business API integration
- [ ] Push notifications (FCM)
- [ ] Historical data charts and analytics
- [ ] Multi-patient support
- [ ] Export health reports (PDF)

## 🧪 Testing

```bash
# Mobile app tests
cd frontend/mobile-app
npm test

# Web app tests
cd frontend/web-app
npm test
```

## 📄 License

This project is part of an academic Final Year Project (FYP).

## 👨‍💻 Author

**Umair Hakeem**

## 🙏 Acknowledgments

- UCI Machine Learning Repository for Heart Disease dataset
- PhysioNet for BIDMC dataset
- Kaggle community for health datasets
- TensorFlow and React Native communities

## 📞 Contact

For questions or collaboration, please open an issue in the repository.

---

**Project Start Date**: November 1, 2025  
**Last Updated**: January 21, 2026  
**Status**: Active Development

---

*Project initialized on: November 1, 2025*
