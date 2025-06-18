# Drone Survey Management System - Frontend

A modern React TypeScript frontend for the Drone Survey Management System, providing intuitive interfaces for mission planning, fleet management, real-time monitoring, and analytics.

## 🏗️ Architecture

The frontend follows a feature-based architecture with clear separation of concerns:

```
frontend/src/
├── components/          # Reusable UI components
├── features/           # Feature-specific components and logic
│   ├── mission-planning/
│   ├── fleet-management/
│   ├── mission-monitoring/
│   └── analytics/
├── stores/             # Zustand state management
├── hooks/              # Custom React hooks
├── utils/              # Utility functions and API clients
├── types/              # TypeScript type definitions
└── App.tsx            # Main application component
```

## 🚀 Features

### Core Functionality
- **Dashboard**: System overview with key metrics and status
- **Fleet Management**: Drone inventory, status monitoring, and control
- **Mission Planning**: Interactive map-based mission creation with waypoint generation
- **Mission Monitoring**: Real-time mission progress tracking and control
- **Analytics**: Operational metrics, performance reports, and data visualization

### Technical Features
- **Real-time Updates**: WebSocket integration for live data synchronization
- **Responsive Design**: Mobile-first design with adaptive layouts
- **Type Safety**: Full TypeScript implementation with comprehensive type definitions
- **State Management**: Zustand stores with real-time update integration
- **Data Fetching**: React Query for efficient API communication and caching
- **Interactive Maps**: Leaflet integration for geographical data visualization

## 🛠️ Technology Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and optimized builds
- **UI Library**: Mantine for comprehensive component library
- **State Management**: Zustand for simple and effective state management
- **Data Fetching**: TanStack Query (React Query) for server state management
- **Real-time**: Socket.IO client for WebSocket communication
- **Mapping**: React Leaflet for interactive maps
- **Routing**: React Router DOM for navigation
- **Icons**: Tabler Icons for consistent iconography
- **Charts**: Recharts and Mantine Charts for data visualization

## 📦 Installation & Setup

### Prerequisites
- Node.js 18.0.0 or higher
- npm 9.0.0 or higher
- Backend API running on `http://localhost:5000`

### Development Setup

1. **Navigate to frontend directory**
```bash
cd drone-survey-system/frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Set up environment variables** (optional)
```bash
# Create .env.local file
VITE_API_BASE_URL=http://localhost:5000/api/v1
VITE_WS_URL=http://localhost:5000
```

4. **Start development server**
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | `/api/v1` |
| `VITE_WS_URL` | WebSocket server URL | `http://localhost:5000` |

### Vite Configuration

The Vite configuration includes:
- **Path aliases** for clean imports (`@/`, `@components/`, etc.)
- **Proxy setup** for API requests to backend
- **Build optimization** with chunk splitting
- **TypeScript support** with strict type checking

## 🏗️ Component Architecture

### Feature-Based Organization

Each feature is organized as a self-contained module:

```typescript
features/
├── mission-planning/
│   ├── components/
│   │   ├── MissionForm.tsx
│   │   ├── MapDisplay.tsx
│   │   └── WaypointPreview.tsx
│   ├── hooks/
│   │   └── useMissionPlanning.ts
│   └── index.ts
```

### Shared Components

Reusable components are organized by type:

```typescript
components/
├── layout/
├── forms/
├── maps/
├── charts/
└── ui/
```

## 📊 State Management

### Zustand Stores

The application uses multiple Zustand stores for different domains:

#### Drone Store (`useDroneStore`)
```typescript
- drones: Drone[]           // Fleet inventory
- selectedDrone: Drone      // Currently selected drone
- filters: FilterState      // Search and filter options
- fetchDrones()            // Load fleet data
- updateDroneLocation()    // Update drone position
- subscribeToFleetUpdates() // Enable real-time updates
```

#### Mission Store (`useMissionStore`)
```typescript
- missions: Mission[]       // All missions
- activeMissions: Mission[] // Currently running missions
- selectedMission: Mission  // Currently selected mission
- createMission()          // Create new mission
- startMission()           // Begin mission execution
- subscribeMissionUpdates() // Enable real-time mission tracking
```

### Real-time State Synchronization

Stores automatically sync with WebSocket events:
- Drone status and location updates
- Mission progress and status changes
- Fleet-wide operational metrics
- Mission logs and event notifications

## 🗺️ Map Integration

### Leaflet Configuration

Maps are implemented using React Leaflet with:
- **Base layers**: OpenStreetMap tiles
- **Survey areas**: Polygon overlays for mission boundaries
- **Waypoints**: Markers showing flight path
- **Drone positions**: Real-time position markers
- **Flight paths**: Polylines showing planned routes

### Map Components

```typescript
<MapDisplay
  center={[lat, lng]}
  zoom={13}
  mission={selectedMission}
  showWaypoints={true}
  showFleetPositions={true}
  onAreaSelect={(polygon) => setMissionArea(polygon)}
/>
```

## 🔄 Real-time Communication

### WebSocket Integration

The WebSocket client (`webSocketClient`) handles:
- **Connection management** with automatic reconnection
- **Event subscription** for specific missions or fleet-wide updates
- **Error handling** and connection status monitoring

### Event Handling

```typescript
// Subscribe to mission updates
webSocketClient.subscribeMissionUpdates(missionId);

// Handle real-time progress updates
webSocketClient.onMissionProgress((data) => {
  updateMissionProgress(data.mission_id, data.progress_percentage);
});

// Handle drone status changes
webSocketClient.onDroneStatus((data) => {
  updateDroneStatus(data.drone_id, data.status);
});
```

## 📱 Responsive Design

### Breakpoints

The application adapts to different screen sizes:
- **Mobile**: < 768px - Collapsed navigation, simplified layouts
- **Tablet**: 768px - 1024px - Adaptive grid layouts
- **Desktop**: > 1024px - Full feature interface

### Mobile Considerations

- Touch-friendly controls for map interaction
- Simplified mission creation workflow
- Optimized data tables with horizontal scrolling
- Responsive chart scaling

## 🎨 UI/UX Design

### Design Principles

- **Clean and Professional**: Minimal interface focused on operational efficiency
- **Information Hierarchy**: Critical information prominently displayed
- **Consistent Interactions**: Standardized patterns across all features
- **Accessibility**: WCAG 2.1 compliant with keyboard navigation support

### Color Scheme

- **Primary**: Blue (#2196f3) - Action buttons, active states
- **Success**: Green (#4caf50) - Completed missions, healthy status
- **Warning**: Orange (#ff9800) - Low battery, attention needed
- **Error**: Red (#f44336) - Failed missions, critical alerts
- **Neutral**: Gray scale for text and backgrounds

## 📈 Performance Optimization

### Code Splitting

Vite automatically splits the application into optimized chunks:
- **Vendor bundle**: React, React DOM, routing
- **UI bundle**: Mantine components and hooks
- **Maps bundle**: Leaflet and mapping components
- **Charts bundle**: Visualization libraries

### Data Management

- **React Query caching** for API responses
- **Optimistic updates** for immediate UI feedback
- **Background refetching** for data freshness
- **Error boundaries** for graceful error handling

### Bundle Analysis

```bash
# Analyze bundle size
npm run build
npm run preview -- --mode analyze
```

## 🧪 Development Workflow

### Code Quality

```bash
# Type checking
npm run type-check

# Linting
npm run lint
npm run lint:fix
```

### Development Tools

- **React DevTools**: Component inspection and profiling
- **Vite DevTools**: Build analysis and hot reload
- **TypeScript**: Compile-time error detection
- **ESLint**: Code quality and consistency

## 🔍 Debugging

### WebSocket Debugging

Monitor WebSocket connections in browser DevTools:
1. Open Network tab
2. Filter by WS (WebSocket)
3. View real-time message exchange

### State Debugging

Zustand DevTools integration:
```typescript
// Enable in development
const useStore = create(
  devtools(storeImplementation, { name: 'drone-store' })
);
```

## 🚀 Deployment

### Production Build

```bash
npm run build
```

Generates optimized static files in `/dist` directory.

### Environment Setup

Production environment variables:
```bash
VITE_API_BASE_URL=https://api.yourdomain.com/api/v1
VITE_WS_URL=https://api.yourdomain.com
```

### Static Hosting

The built application can be served from any static hosting service:
- **Netlify**: Automatic deployments from Git
- **Vercel**: Optimized for React applications
- **AWS S3 + CloudFront**: Enterprise-grade hosting
- **Nginx**: Self-hosted solution

## 🤝 Contributing

### Component Guidelines

- Use functional components with TypeScript
- Implement proper error boundaries
- Follow Mantine design patterns
- Include comprehensive JSDoc comments

### State Management Guidelines

- Keep store actions focused and pure
- Use selectors for computed values
- Handle async operations with proper error states
- Implement optimistic updates where appropriate

### Testing Strategy

- Unit tests for utility functions
- Component tests for user interactions
- Integration tests for store operations
- E2E tests for critical user workflows

## 📚 Additional Resources

- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)
- [Mantine Components](https://mantine.dev)
- [React Query Guide](https://tanstack.com/query)
- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [React Leaflet Guide](https://react-leaflet.js.org)

## 🐛 Common Issues

### WebSocket Connection Issues

1. **CORS errors**: Ensure backend CORS settings allow frontend origin
2. **Connection timeouts**: Check firewall settings and proxy configuration
3. **Frequent disconnections**: Verify network stability and server capacity

### Map Rendering Issues

1. **Tiles not loading**: Check internet connection and tile server availability
2. **Performance issues**: Reduce number of markers or implement clustering
3. **Mobile touch issues**: Ensure proper touch event handling

### Build Issues

1. **Memory errors**: Increase Node.js memory limit: `NODE_OPTIONS=--max-old-space-size=4096`
2. **TypeScript errors**: Run `npm run type-check` for detailed error information
3. **Import issues**: Verify path aliases in tsconfig.json and vite.config.ts

---

This frontend provides a comprehensive foundation for the Drone Survey Management System with modern architecture, real-time capabilities, and professional UX design.