# HealSense Web Dashboard

## Real-Time Health Monitoring Web Application

The web dashboard is a modern, responsive web application built with React, TypeScript, and Vite for healthcare providers to monitor patient health, manage alerts, and track wellness trends. It provides a comprehensive interface for monitoring multiple patients and accessing detailed health analytics.

## Purpose

The web dashboard serves healthcare providers with a complete platform for:
- Monitoring vital signs of multiple patients in real time
- Viewing detailed patient health history and trends
- Managing and responding to health alerts
- Accessing patient profiles and medical information
- Generating health reports and analytics

## Key Features

### Authentication and Security

**Secure Login**: Email and password authentication with encrypted credential storage

**Session Management**: Automatic session persistence across browser restarts

**Protected Routes**: Dashboard and patient data accessible only to authenticated users

**Demo Account**: Pre-configured test account for exploring functionality

Email: umair@healsense.com  
Password: password123

### Patient Profile Management

**Personal Information**: View and edit patient demographics

**Medical History**: Track medical conditions and medications

**Emergency Contacts**: Store and manage emergency contact information

**Real-Time Updates**: Changes saved instantly to backend storage

### Health Monitoring Dashboard

**Real-Time Vital Signs**: Live monitoring of five critical health metrics (heart rate, blood oxygen, temperature, blood pressure, respiratory rate)

**Visual Status Indicators**: Color-coded health status (green for normal, yellow for warning, red for critical)

**Device Connection Status**: Visual indicator showing if monitoring devices are connected

**Health Alerts**: Automatic notifications when vital signs fall outside safe ranges

**Historical Charts**: Visual graphs showing vital sign trends over time

### Alert Management

**Alert List**: View all active and historical alerts

**Severity Classification**: Alerts categorized by severity level (low, medium, high, critical)

**Alert Actions**: Mark alerts as acknowledged or dismissed

**Filter Options**: Filter alerts by patient, severity, or status

## Tech Stack

### Frontend Framework
- React 18.3.1 - Modern user interface library
- TypeScript 5.x - Static type checking for reliability

### Build Tool
- Vite 5.x - Lightning-fast development and production builds

### UI Components
- Shadcn/ui - Professional pre-built components
- Radix UI - Accessible component primitives
- Lucide React - Icon library

### Styling
- Tailwind CSS 3.x - Utility-first CSS framework
- Class Variance Authority - Dynamic class management

### State Management and Data
- React Hook Form 7.61.1 - Form state management
- React Query 5.83.0 - Server data fetching and caching

### Data Validation
- Zod 3.25.76 - Runtime data validation

### Utilities
- date-fns 3.6.0 - Date manipulation
- next-themes 0.3.0 - Dark/light mode toggling
- sonner 1.7.4 - Toast notifications
- Recharts 2.15.4 - Data visualizations

## Getting Started

### Prerequisites

Before setting up, ensure you have:
- Node.js 16 or higher
- npm or yarn package manager
- Backend server running (see backend README)

### Installation

Navigate to the web app directory:

```bash
cd healsense/frontend/web-app
```

Install all dependencies:

```bash
npm install
```

### Configuration

Create an environment configuration file:

```bash
cp .env.example .env.local
```

Edit .env.local with your backend server details:

VITE_API_BASE_URL=http://localhost:5000  
VITE_WS_BASE_URL=ws://localhost:5000

### Development

Start the development server with hot module reloading:

```bash
npm run dev
```

The application will typically open at http://localhost:8080 with automatic page reloading on code changes.

### Production Build

Create an optimized production build:

```bash
npm run build
```

The compiled files are output to the dist/ directory, ready for deployment.

Preview the production build locally:

```bash
npm run preview
```

## Project Structure

```
web-app/
├── src/                                  # React source code
│   ├── main.tsx                         # Application entry point
│   ├── App.tsx                          # Main app component with routing
│   ├── index.css                        # Global styles
│   │
│   ├── pages/                           # Application pages/screens
│   │   ├── Index.tsx                    # Landing/home page
│   │   ├── Login.tsx                    # User login screen
│   │   ├── Signup.tsx                   # User registration screen
│   │   ├── Profile.tsx                  # Patient profile editor
│   │   ├── Dashboard.tsx                # Main health monitoring dashboard
│   │   └── NotFound.tsx                 # 404 error page
│   │
│   ├── components/                      # Reusable UI components
│   │   ├── ui/                          # Shadcn UI component library
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── [other shadcn components]
│   │   │
│   │   ├── Header.tsx                   # App header with navigation
│   │   ├── Navigation.tsx               # Sidebar navigation menu
│   │   ├── VitalCard.tsx                # Individual vital sign display
│   │   ├── AlertList.tsx                # Alert history list
│   │   ├── AlertBanner.tsx              # Alert notification banner
│   │   │
│   │   └── Charts/                      # Data visualization components
│   │       ├── VitalTrendChart.tsx     # Time-series vital trends
│   │       └── RiskScoreChart.tsx      # Health risk visualization
│   │
│   ├── contexts/                        # React context providers
│   │   ├── AuthContext.tsx              # Authentication state
│   │   ├── ThemeContext.tsx             # Dark/light theme mode
│   │   └── PatientContext.tsx           # Patient data state
│   │
│   ├── hooks/                           # Custom React hooks
│   │   ├── useAuth.ts                   # Authentication logic
│   │   ├── usePatient.ts                # Patient data operations
│   │   ├── useVitals.ts                 # Vital signs data fetching
│   │   ├── useAlerts.ts                 # Alert management
│   │   └── useWebSocket.ts              # Real-time data subscription
│   │
│   ├── lib/                             # Utility functions
│   │   ├── api-client.ts                # HTTP client configuration
│   │   ├── validators.ts                # Data validation schemas
│   │   ├── constants.ts                 # Application constants
│   │   └── utils.ts                     # Helper functions
│   │
│   ├── types/                           # TypeScript type definitions
│   │   ├── patient.ts                   # Patient type definitions
│   │   ├── vital.ts                     # Vital sign types
│   │   ├── alert.ts                     # Alert types
│   │   └── api.ts                       # API response types
│   │
│   └── assets/                          # Static assets
│       ├── images/
│       ├── fonts/
│       └── icons/
│
├── public/                              # Public static files
│   └── vite.svg                        # Vite logo
│
├── Configuration files
│   ├── vite.config.ts                  # Vite build configuration
│   ├── tailwind.config.ts              # Tailwind CSS theme configuration
│   ├── tsconfig.json                   # TypeScript compiler options
│   ├── tsconfig.app.json               # App-specific TypeScript config
│   ├── tsconfig.node.json              # Node-specific TypeScript config
│   ├── vitest.config.ts                # Unit test configuration
│   ├── postcss.config.js               # PostCSS processing
│   └── eslint.config.js                # Code linting rules
│
├── package.json                         # Node.js dependencies
├── .env.example                         # Environment template
└── README.md                            # This file
```

## Build and Development Commands

**Development Server**: npm run dev

Starts the development server with hot module replacement and opens in your browser.

**Production Build**: npm run build

Creates an optimized production-ready bundle in the dist/ directory.

**Development Build**: npm run build:dev

Builds for development environment without minification.

**Preview Build**: npm run preview

Runs the production build locally to verify before deployment.

**Code Linting**: npm run lint

Checks code for style and formatting issues.

**Unit Tests**: npm run test

Runs unit tests using Vitest.

**Test Watch Mode**: npm run test:watch

Continuously watches and reruns tests on code changes.

## API Integration

The web dashboard communicates with the backend API for all data:

**API Base URL**: Configured via VITE_API_BASE_URL environment variable

**Authentication**: JWT Bearer token stored in localStorage after login

**Request Format**: JSON REST API with standard HTTP methods

**Response Handling**: Automatic error handling and validation

### Example API Calls

Fetch patient profile data:

```typescript
GET /api/v1/patients/{patient_id}
```

Submit new vital signs:

```typescript
POST /api/v1/patients/{patient_id}/vitals
```

Get vital sign history:

```typescript
GET /api/v1/patients/{patient_id}/vitals/history?minutes=60
```

Manage alerts:

```typescript
POST /api/v1/alerts/{alert_id}/acknowledge
POST /api/v1/alerts/{alert_id}/dismiss
```

## Real-Time Updates

The dashboard uses WebSocket connections for live vital sign updates:

**Connection**: Established automatically on dashboard load

**Patient Stream**: Receives vital updates and alerts specific to viewing patient

**Auto-Reconnect**: Automatic reconnection if WebSocket drops

**Data Sync**: UI updates in real-time as new measurements arrive

## State Management

**React Context**: Used for global state (authentication, theme, patient data)

**Local State**: Component-level state for UI interactions

**Server Cache**: React Query manages server data and caching

**Form State**: React Hook Form manages form inputs and validation

## Styling Approach

**Tailwind CSS**: Utility-first CSS for rapid component styling

**Shadcn Components**: Pre-styled component collection

**Dark Mode**: Theme-aware styling via next-themes

**Responsive Design**: Mobile-first responsive layout

**Custom Theming**: Tailwind configuration for brand colors

## Authentication Flow

1. User navigates to login page
2. Enters email and password credentials
3. Backend validates and returns JWT token
4. Token stored in secure localStorage
5. Token included in all subsequent API requests
6. Dashboard automatically redirects to login if token expires
7. Logout clears token and returns to login page

## Deployment

### Static Hosting Options

**Vercel** (Recommended):
```bash
npm install -g vercel
vercel
```

**Netlify**:
- Connect GitHub repository
- Set build command: npm run build
- Set publish directory: dist

**AWS S3 + CloudFront**:
```bash
npm run build
aws s3 sync dist/ s3://bucket-name/
```

**Traditional Web Server**:
```bash
npm run build
scp -r dist/* user@server:/var/www/healsense/
```

## Troubleshooting

**Blank Dashboard After Login**: Verify backend is running and API_BASE_URL is correct

**WebSocket Connection Fails**: Check backend is accessible at WS_BASE_URL, verify firewall allows WebSocket connections

**Charts Not Showing**: Ensure vital data is being received from backend, check browser console for errors

**Styling Issues**: Clear browser cache and rebuild: npm run build

**Authentication Loop**: Clear localStorage and try logging in again

**Slow Development Build**: Ensure Node.js version matches requirements, try npm install --legacy-peer-deps

## Browser Support

Modern browsers with ES2020+ support:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance Optimization

- Code splitting for faster initial load
- Image optimization and lazy loading
- CSS purging removes unused styles
- API response caching via React Query
- WebSocket for efficient real-time updates
- Production build minification

## Testing

Unit tests verify component functionality and UI behavior:

```bash
npm run test
npm run test:watch      # Continuous testing during development
```

Test files follow the .test.tsx naming convention.

## Development Guidelines

**Component Structure**: Keep components focused with single responsibility

**Props**: Use TypeScript for strict prop typing

**State**: Prefer React Context over prop drilling for global state

**Naming**: Use descriptive names for components and functions

**Comments**: Include comments for complex logic

**Formatting**: Code is automatically formatted on save via Prettier

## Contributing

1. Create a feature branch from main
2. Make changes with clear commit messages
3. Test changes locally
4. Submit pull request with description

## Environment Variables

Create .env.local file with:

**VITE_API_BASE_URL**: Backend REST API endpoint (e.g., http://localhost:5000)

**VITE_WS_BASE_URL**: Backend WebSocket endpoint (e.g., ws://localhost:5000)

**VITE_APP_TITLE**: Application title displayed in browser

**VITE_APP_VERSION**: Application version number

## Support and Documentation

For complete API reference, see PROJECT_COMPREHENSIVE_DOCUMENTATION.md at project root.

Interactive API documentation available at backend /api/docs endpoint.

## Version

Version: 1.0  
Last Updated: April 2026  
Status: Production-Ready
- ✅ Manage medical conditions
- ✅ Manage current medications
- ✅ Emergency contacts (doctor & family)
- ✅ Real-time save to localStorage

### Dashboard
- ✅ Live vital signs monitoring
- ✅ Color-coded health status
- ✅ Alert notifications
- ✅ Connection indicator
- ✅ Navigation bar with user info
- ✅ Quick access to profile

## 🔧 Mock Data

The app uses the same mock data structure as the mobile app:

### Mock Patient
```typescript
{
  id: '1',
  name: 'Umair Hakeem',
  age: 24,
  gender: 'Male',
  bloodType: 'O+',
  medicalConditions: [],
  currentMedications: [],
  emergencyContacts: [
    {
      name: 'Dr. Ahmed Khan',
      phone: '+92 300 1234567',
      relation: 'Primary Care Physician',
      type: 'doctor',
    },
    {
      name: 'Awais',
      phone: '03145647685',
      relation: 'Brother',
      type: 'family',
    },
  ],
}
```

### Mock Vitals
- Auto-generated realistic values
- Updates every 5 seconds
- Slight variations for realism
- Matches mobile app behavior

## 🛠️ Tech Stack

### Core
- **React**: 19
- **Vite**: Fast build tool
- **TypeScript**: 5.6+
- **React Router**: v6 (routing)

### UI Framework
- **Shadcn UI**: Component library
- **Radix UI**: Headless UI primitives
- **Tailwind CSS**: Utility-first CSS
- **Lucide React**: Icons

### State Management
- **React Query**: Server state
- **React Context**: Auth state
- **localStorage**: Persistence

## 🔐 Authentication Flow

```
Landing Page (/)
      ↓
   Not authenticated? → Login (/login)
      ↓
   Authenticate → Save to localStorage
      ↓
   Redirect to Dashboard (/dashboard)
      ↓
   Already authenticated? → Dashboard
```

## 📝 Environment Variables

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:5000/api/v1
VITE_WS_URL=ws://localhost:5000/ws

# Feature Flags
VITE_USE_MOCK_DATA=true           # Enable mock data
VITE_POLLING_INTERVAL=5000        # Polling interval (ms)

# Development
VITE_DEBUG_MODE=true
```

## 🧪 Development

### Build
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

### Lint
```bash
npm run lint
```

### Type Check
```bash
npm run type-check  # If available
```

## 🚢 Deployment

### Build for Production
```bash
npm run build
# Output: dist/
```

### Deploy to Vercel
```bash
vercel
```

### Deploy to Netlify
```bash
netlify deploy --prod
```

## 🔮 Future Enhancements

- [ ] Backend API integration
- [ ] Real-time WebSocket data streaming
- [ ] Push notifications
- [ ] Multi-user support
- [ ] Dark mode toggle in UI
- [ ] Historical charts
- [ ] Export reports (PDF)
- [ ] Biometric authentication
- [ ] PWA capabilities
- [ ] Mobile responsive improvements

## 🤝 Contributing

This is a Final Year Project. See main project README for contribution guidelines.

## 📄 License

Academic Final Year Project

## 👨‍💻 Author

**Umair Hakeem**

---

**Version**: 0.1.0  
**Last Updated**: January 21, 2026  
**Status**: Active Development
