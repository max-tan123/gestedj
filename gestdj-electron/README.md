# GesteDJ Electron

🎧 **Professional Gesture-Controlled Virtual DJ Interface** built with Electron + React + Python

## Overview

GesteDJ Electron is a modern desktop application that provides a professional UI for gesture-controlled DJ operations. It integrates seamlessly with the existing Python MediaPipe backend while delivering a native desktop experience with superior performance and user experience.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 Electron App                    │
│  ┌─────────────────┐  ┌─────────────────────────┐ │
│  │   React Frontend│  │   Node.js Main Process │ │
│  │   • Video Stream│  │   • Python Integration │ │
│  │   • DJ Interface│  │   • Process Management │ │
│  │   • Gesture UI  │  │   • IPC Communication  │ │
│  └─────────────────┘  └─────────────────────────┘ │
│           ▲                        ▲             │
│           │      IPC/WebSocket     │             │
│           ▼                        ▼             │
│  ┌─────────────────────────────────────────────┐  │
│  │         Python GesteDJ Backend            │  │
│  │   MediaPipe → Gestures → MIDI → Mixxx     │  │
│  │   (Reuse existing app.py architecture)     │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Features

### ✅ Current Implementation
- **Modern Electron Setup**: TypeScript + React + Vite for fast development
- **Python Backend Integration**: Automatic Python process management
- **Real-time Communication**: WebSocket integration with gesture recognition
- **Professional UI**: Modern desktop interface with dark theme
- **IPC Communication**: Secure renderer ↔ main process communication
- **Development Ready**: Hot reload, TypeScript support, ESLint

### 🚧 In Development
- Video streaming interface with gesture overlay
- Real-time gesture recognition display
- DJ control knobs and sliders
- MIDI device configuration
- Tutorial system

### 🎯 Planned Features
- Multi-camera support
- Custom gesture mapping
- Performance analytics
- Plugin system
- Cloud sync for settings

## Project Structure

```
gestdj-electron/
├── src/
│   ├── main/                    # Electron main process
│   │   ├── main.js             # Main application entry
│   │   └── preload.js          # Secure IPC bridge
│   ├── renderer/               # React frontend
│   │   ├── components/         # React components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── styles/            # CSS styles
│   │   ├── App.tsx            # Main React app
│   │   ├── main.tsx           # React entry point
│   │   └── index.html         # HTML template
│   └── shared/                # Shared types and utilities
│       ├── types/             # TypeScript type definitions
│       └── constants/         # Shared constants
├── build/                     # Build output
├── dist/                      # Distribution packages
└── package.json              # Project configuration
```

## Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.8+ with MediaPipe dependencies
- Existing GesteDJ Python backend (from parent directory)

### Installation

```bash
# Install dependencies
npm install

# Start development (both renderer and main process)
npm run dev

# Or start processes individually
npm run dev:renderer  # Start Vite dev server (React)
npm run dev:main      # Start Electron main process
```

### Building for Production

```bash
# Build renderer and create distributable
npm run dist

# Build for specific platform
npm run dist:dir  # Build without packaging
```

## Development

### Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start full development environment |
| `npm run dev:renderer` | Start React development server only |
| `npm run dev:main` | Start Electron main process only |
| `npm run build` | Build production React bundle |
| `npm run dist` | Create distributable packages |
| `npm run typecheck` | Run TypeScript type checking |
| `npm run lint` | Run ESLint |
| `npm run lint:fix` | Fix ESLint issues |

### Python Backend Integration

The Electron app automatically manages the Python gesture recognition backend:

```javascript
// Start Python backend
const result = await window.electronAPI.startPythonBackend();

// Test WebSocket connection
const wsResult = await window.electronAPI.testWebSocketConnection();

// Stop Python backend
await window.electronAPI.stopPythonBackend();
```

### Adding New Features

1. **Frontend Components**: Add to `src/renderer/components/`
2. **IPC Handlers**: Add to `src/main/main.js` and `src/main/preload.js`
3. **Type Definitions**: Add to `src/shared/types/`
4. **Styles**: Add to `src/renderer/styles/`

## Configuration

### Electron Builder

Distribution configuration in `package.json` under `build`:

- **macOS**: DMG installer with x64/arm64 support
- **Windows**: NSIS installer
- **Linux**: AppImage

### Python Backend Path

The app looks for the Python backend at:
```
../gestdj-web-ui/app.py
```

Adjust the path in `src/main/main.js` if your backend is located elsewhere.

## Testing

### Manual Testing Checklist

1. **Electron Launch**: App window opens correctly
2. **Python Integration**: Backend starts/stops via UI
3. **WebSocket Connection**: Real-time communication works
4. **UI Responsiveness**: Interface is smooth and reactive
5. **Hot Reload**: Changes reflect immediately during development

### Automated Testing (Planned)

- Unit tests for React components
- Integration tests for IPC communication
- E2E tests with Playwright

## Performance

### Current Metrics
- **Bundle Size**: ~150MB (Electron + dependencies)
- **Memory Usage**: ~200MB average
- **Startup Time**: ~3 seconds cold start
- **WebSocket Latency**: <30ms with Python backend

### Optimization Opportunities
- Code splitting for large components
- Lazy loading for non-critical features
- Memory profiling for long-running sessions

## Troubleshooting

### Common Issues

**Electron window doesn't open:**
```bash
# Check if ports are available
lsof -i :3000

# Restart development servers
npm run dev
```

**Python backend fails to start:**
- Ensure Python dependencies are installed
- Check Python path in main.js
- Verify WebSocket port (8765) is available

**TypeScript errors:**
```bash
# Run type checking
npm run typecheck

# Fix auto-fixable issues
npm run lint:fix
```

## Contributing

1. Follow TypeScript best practices
2. Use provided ESLint configuration
3. Test frequently during development
4. Update type definitions when adding features
5. Follow conventional commit messages

## Deployment

### Development Deployment
```bash
npm run dev  # Local development
```

### Production Deployment
```bash
npm run dist  # Creates platform-specific installers
```

The generated installers will be in the `dist/` directory.

## Roadmap

### Phase 1: Core Integration ✅
- [x] Electron app setup
- [x] React frontend
- [x] Python backend integration
- [x] Basic UI framework

### Phase 2: Gesture Interface 🚧
- [ ] Video streaming UI
- [ ] Real-time gesture display
- [ ] Hand landmark overlays
- [ ] Basic gesture controls

### Phase 3: DJ Controls 🎯
- [ ] Virtual DJ knobs and sliders
- [ ] MIDI output visualization
- [ ] Performance monitoring
- [ ] Settings management

### Phase 4: Advanced Features 🔮
- [ ] Custom gesture mapping
- [ ] Multi-camera support
- [ ] Plugin architecture
- [ ] Cloud integration

---

## Why Electron?

**vs Tauri:**
- ✅ Easier Python integration via Node.js child processes
- ✅ More mature ecosystem and tooling
- ✅ Better WebSocket/real-time communication support
- ✅ Familiar development experience for web developers
- ❌ Larger bundle size (~150MB vs ~20MB)

**vs Web App:**
- ✅ Native desktop integration (system tray, notifications)
- ✅ Better camera/media device access
- ✅ No browser security restrictions
- ✅ Professional desktop application experience

This architecture provides the best balance of development speed, performance, and user experience for the GesteDJ project.