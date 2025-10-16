import React, { useState, useEffect } from 'react';
import './styles/App.css';
import CameraFeed from './components/CameraFeed';

function App() {
  const [pythonStatus, setPythonStatus] = useState<'running' | 'stopped' | 'unknown'>('unknown');
  const [isLoading, setIsLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    // Check if we're in Electron environment
    if (!window.electronAPI) {
      console.warn('ElectronAPI not available - running in browser mode');
      return;
    }

    // Get initial Python status
    checkPythonStatus();

    // Set up event listeners
    window.electronAPI.onPythonLog((_, data) => {
      setLogs(prev => [...prev.slice(-20), `[LOG] ${data}`]); // Keep last 20 logs
    });

    window.electronAPI.onPythonError((_, data) => {
      setLogs(prev => [...prev.slice(-20), `[ERROR] ${data}`]);
    });

    window.electronAPI.onPythonStatus((_, status) => {
      setPythonStatus(status as 'running' | 'stopped');
    });

    // Cleanup listeners on unmount
    return () => {
      if (window.electronAPI) {
        window.electronAPI.removeAllListeners('python-log');
        window.electronAPI.removeAllListeners('python-error');
        window.electronAPI.removeAllListeners('python-status');
      }
    };
  }, []);

  const checkPythonStatus = async () => {
    if (!window.electronAPI) return;

    try {
      const result = await window.electronAPI.getPythonStatus();
      setPythonStatus(result.status);
    } catch (error) {
      console.error('Failed to get Python status:', error);
    }
  };

  const startPythonBackend = async () => {
    if (!window.electronAPI) return;

    setIsLoading(true);
    try {
      const result = await window.electronAPI.startPythonBackend();
      if (result.success) {
        setPythonStatus('running');
        setLogs(prev => [...prev, `[SUCCESS] ${result.message}`]);
      } else {
        setLogs(prev => [...prev, `[ERROR] ${result.error}`]);
      }
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] ${error}`]);
    }
    setIsLoading(false);
  };

  const stopPythonBackend = async () => {
    if (!window.electronAPI) return;

    setIsLoading(true);
    try {
      const result = await window.electronAPI.stopPythonBackend();
      if (result.success) {
        setPythonStatus('stopped');
        setLogs(prev => [...prev, `[SUCCESS] ${result.message}`]);
      } else {
        setLogs(prev => [...prev, `[ERROR] ${result.error}`]);
      }
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] ${error}`]);
    }
    setIsLoading(false);
  };

  const testWebSocket = async () => {
    if (!window.electronAPI) return;

    try {
      const result = await window.electronAPI.testWebSocketConnection();
      if (result.success) {
        setLogs(prev => [...prev, `[SUCCESS] ${result.message}`]);
      } else {
        setLogs(prev => [...prev, `[ERROR] ${result.error}`]);
      }
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] ${error}`]);
    }
  };

  const getStatusColor = () => {
    switch (pythonStatus) {
      case 'running': return '#4CAF50';
      case 'stopped': return '#f44336';
      default: return '#FF9800';
    }
  };

  const isElectron = !!window.electronAPI;

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎧 GesteDJ Electron</h1>
        <p>Gesture-Controlled Virtual DJ Interface</p>

        {!isElectron && (
          <div className="warning">
            ⚠️ Running in browser mode - Electron features not available
          </div>
        )}
      </header>

      <main className="app-main">
        <section className="camera-section">
          <h2>📷 Camera Feed</h2>
          <CameraFeed onLandmarks={(results) => {
            // Convert MediaPipe results to our landmark format
            const landmarkData: any = {
              type: 'landmarks',
              timestamp: performance.now(),
              hands: {}
            };

            // Map each detected hand to Left/Right
            for (let i = 0; i < results.landmarks.length; i++) {
              const handedness = results.handedness[i][0].categoryName;
              landmarkData.hands[handedness] = results.landmarks[i];
            }

            // Send to main process
            if (window.electronAPI) {
              window.electronAPI.sendLandmarks(landmarkData);
            }
          }} />
        </section>

        <section className="backend-control">
          <h2>🐍 Python Backend Control</h2>

          <div className="status-display">
            <span
              className="status-indicator"
              style={{ backgroundColor: getStatusColor() }}
            />
            <span className="status-text">
              Status: {pythonStatus.toUpperCase()}
            </span>
          </div>

          <div className="control-buttons">
            <button
              onClick={startPythonBackend}
              disabled={isLoading || pythonStatus === 'running' || !isElectron}
              className="btn btn-start"
            >
              {isLoading ? 'Starting...' : 'Start Backend'}
            </button>

            <button
              onClick={stopPythonBackend}
              disabled={isLoading || pythonStatus === 'stopped' || !isElectron}
              className="btn btn-stop"
            >
              {isLoading ? 'Stopping...' : 'Stop Backend'}
            </button>

            <button
              onClick={checkPythonStatus}
              disabled={!isElectron}
              className="btn btn-check"
            >
              Check Status
            </button>

            <button
              onClick={testWebSocket}
              disabled={!isElectron}
              className="btn btn-test"
            >
              Test WebSocket
            </button>
          </div>
        </section>

        <section className="logs-section">
          <h3>📋 Logs</h3>
          <div className="logs-container">
            {logs.length === 0 ? (
              <p className="no-logs">No logs yet...</p>
            ) : (
              logs.map((log, index) => (
                <div
                  key={index}
                  className={`log-entry ${log.includes('[ERROR]') ? 'error' : log.includes('[SUCCESS]') ? 'success' : 'info'}`}
                >
                  {log}
                </div>
              ))
            )}
          </div>
        </section>

        <section className="next-steps">
          <h3>🎯 Next Steps</h3>
          <ul>
            <li>✅ Electron app setup complete</li>
            <li>✅ Python backend integration</li>
            <li>🔄 Testing basic functionality</li>
            <li>⏳ Add video streaming interface</li>
            <li>⏳ Add gesture recognition display</li>
            <li>⏳ Add DJ control interface</li>
          </ul>
        </section>
      </main>
    </div>
  );
}

export default App;