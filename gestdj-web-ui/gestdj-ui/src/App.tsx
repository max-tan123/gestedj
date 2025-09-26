import React, { useState, useRef, useCallback } from 'react';
import logo from './logo.svg';
import './App.css';

// Tauri v2 API import
declare global {
  interface Window {
    __TAURI_INVOKE__?: (cmd: string, args?: any) => Promise<any>;
  }
}

function App() {
  const [greetMsg, setGreetMsg] = useState('');
  const [pythonStatus, setPythonStatus] = useState('Not tested');
  const [isLoading, setIsLoading] = useState(false);
  const [latencyResults, setLatencyResults] = useState<{
    min: number;
    max: number;
    avg: number;
    count: number;
  }>({ min: 0, max: 0, avg: 0, count: 0 });
  const [isTestingLatency, setIsTestingLatency] = useState(false);

  // Video streaming state
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [videoStats, setVideoStats] = useState({
    framesSent: 0,
    backendResponses: 0,
    currentFPS: 0,
    dataSent: 0
  });
  const [videoLatencyResults, setVideoLatencyResults] = useState<{
    min: number;
    max: number;
    avg: number;
    count: number;
  }>({ min: 0, max: 0, avg: 0, count: 0 });
  const [isTestingVideoLatency, setIsTestingVideoLatency] = useState(false);

  const streamingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const fpsCounterRef = useRef(0);
  const fpsIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const greet = async () => {
    if (window.__TAURI_INVOKE__) {
      try {
        const message = await window.__TAURI_INVOKE__('greet', { name: 'GesteDJ User' });
        setGreetMsg(message);
      } catch (error) {
        console.error('Error calling greet:', error);
        setGreetMsg('Error: Could not connect to Tauri backend');
      }
    } else {
      setGreetMsg('Tauri not available (running in browser)');
    }
  };

  const testPythonConnection = async () => {
    setIsLoading(true);
    setPythonStatus('Testing...');

    try {
      // For now, just test the WebSocket connection attempt
      const ws = new WebSocket('ws://localhost:8765');

      ws.onopen = () => {
        setPythonStatus('✅ Python backend connected');
        ws.close();
        setIsLoading(false);
      };

      ws.onerror = () => {
        setPythonStatus('❌ Python backend not running');
        setIsLoading(false);
      };

      ws.onclose = () => {
        if (pythonStatus === 'Testing...') {
          setPythonStatus('❌ Python backend not running');
          setIsLoading(false);
        }
      };

    } catch (error) {
      setPythonStatus('❌ WebSocket error');
      setIsLoading(false);
    }
  };

  const testLatency = async () => {
    setIsTestingLatency(true);
    setLatencyResults({ min: 0, max: 0, avg: 0, count: 0 });

    try {
      const ws = new WebSocket('ws://localhost:8765');
      const latencies: number[] = [];
      const testCount = 20; // Number of latency tests
      let completedTests = 0;

      ws.onopen = () => {
        // Start latency testing
        const runLatencyTest = () => {
          const startTime = performance.now();
          const testData = `Test packet ${completedTests + 1}`;

          const testMessage = {
            type: 'latency_test',
            timestamp: startTime,
            test_data: testData
          };

          ws.send(JSON.stringify(testMessage));
        };

        ws.onmessage = (event) => {
          const receiveTime = performance.now();
          const data = JSON.parse(event.data);

          if (data.type === 'latency_response') {
            const roundTripTime = receiveTime - data.client_timestamp;
            latencies.push(roundTripTime);
            completedTests++;

            if (completedTests < testCount) {
              // Continue testing after short delay
              setTimeout(runLatencyTest, 50);
            } else {
              // Calculate results
              const min = Math.min(...latencies);
              const max = Math.max(...latencies);
              const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;

              setLatencyResults({
                min: Math.round(min * 100) / 100,
                max: Math.round(max * 100) / 100,
                avg: Math.round(avg * 100) / 100,
                count: testCount
              });

              ws.close();
              setIsTestingLatency(false);
            }
          }
        };

        // Start the first test
        runLatencyTest();
      };

      ws.onerror = () => {
        setIsTestingLatency(false);
        alert('WebSocket connection failed. Make sure Python server is running.');
      };

    } catch (error) {
      setIsTestingLatency(false);
      alert('Error starting latency test');
    }
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, frameRate: 30 },
        audio: false
      });

      setVideoStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (error) {
      console.error('Camera access failed:', error);
      alert('Camera access failed. Please ensure camera permissions are granted.');
    }
  };

  const stopCamera = () => {
    if (videoStream) {
      videoStream.getTracks().forEach(track => track.stop());
      setVideoStream(null);
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  const captureAndSendFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || !videoStream) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Draw current video frame to canvas
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);

    // Convert to base64 JPEG
    const frameData = canvas.toDataURL('image/jpeg', 0.8);
    const base64Data = frameData.split(',')[1];

    // Send frame with timestamp via WebSocket
    const message = {
      type: 'frontend_video_frame',
      frame_data: base64Data,
      client_timestamp: performance.now(),
      frame_number: videoStats.framesSent
    };

    // Create WebSocket connection for video streaming
    const ws = new WebSocket('ws://localhost:8765');
    ws.onopen = () => {
      ws.send(JSON.stringify(message));
      ws.close(); // Close after sending
    };

    // Update stats
    setVideoStats(prev => ({
      ...prev,
      framesSent: prev.framesSent + 1,
      dataSent: prev.dataSent + (base64Data.length / 1024)
    }));

    fpsCounterRef.current++;
  }, [videoStream, videoStats.framesSent]);

  const startVideoStreaming = () => {
    if (!videoStream) {
      alert('Please start camera first');
      return;
    }

    setIsStreaming(true);

    // Start capturing frames at 15 FPS
    streamingIntervalRef.current = setInterval(captureAndSendFrame, 1000/15);

    // Start FPS counter
    fpsCounterRef.current = 0;
    fpsIntervalRef.current = setInterval(() => {
      setVideoStats(prev => ({ ...prev, currentFPS: fpsCounterRef.current }));
      fpsCounterRef.current = 0;
    }, 1000);
  };

  const stopVideoStreaming = () => {
    setIsStreaming(false);

    if (streamingIntervalRef.current) {
      clearInterval(streamingIntervalRef.current);
      streamingIntervalRef.current = null;
    }

    if (fpsIntervalRef.current) {
      clearInterval(fpsIntervalRef.current);
      fpsIntervalRef.current = null;
    }
  };

  const testVideoLatency = async () => {
    if (!isStreaming || !videoRef.current || !canvasRef.current) {
      alert('Please start video streaming first');
      return;
    }

    setIsTestingVideoLatency(true);
    setVideoLatencyResults({ min: 0, max: 0, avg: 0, count: 0 });

    const latencies: number[] = [];
    const testCount = 20;

    try {
      const ws = new WebSocket('ws://localhost:8765');

      ws.onopen = async () => {
        for (let i = 0; i < testCount; i++) {
          const startTime = performance.now();

          // Capture current frame
          const canvas = canvasRef.current!;
          const ctx = canvas.getContext('2d')!;
          ctx.drawImage(videoRef.current!, 0, 0, canvas.width, canvas.height);

          const frameData = canvas.toDataURL('image/jpeg', 0.8);
          const base64Data = frameData.split(',')[1];

          const testMessage = {
            type: 'video_latency_test',
            frame_data: base64Data,
            timestamp: startTime,
            test_id: `test_${i}`
          };

          // Wait for response
          const response = await new Promise<any>((resolve) => {
            const messageHandler = (event: MessageEvent) => {
              const data = JSON.parse(event.data);
              if (data.type === 'video_latency_response' && data.test_id === `test_${i}`) {
                ws.removeEventListener('message', messageHandler);
                resolve(data);
              }
            };
            ws.addEventListener('message', messageHandler);
            ws.send(JSON.stringify(testMessage));
          });

          const receiveTime = performance.now();
          const roundTripTime = receiveTime - startTime;
          latencies.push(roundTripTime);

          // Small delay between tests
          await new Promise(resolve => setTimeout(resolve, 100));
        }

        // Calculate results
        const min = Math.min(...latencies);
        const max = Math.max(...latencies);
        const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;

        setVideoLatencyResults({
          min: Math.round(min * 100) / 100,
          max: Math.round(max * 100) / 100,
          avg: Math.round(avg * 100) / 100,
          count: testCount
        });

        ws.close();
        setIsTestingVideoLatency(false);
      };

      ws.onerror = () => {
        setIsTestingVideoLatency(false);
        alert('WebSocket connection failed. Make sure Python server is running.');
      };

    } catch (error) {
      setIsTestingVideoLatency(false);
      alert('Error starting video latency test');
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <h1>GesteDJ Web UI - Phase 1 Test</h1>

        <div style={{ margin: '20px 0' }}>
          <button onClick={greet} style={{ margin: '5px', padding: '10px 20px' }}>
            Test Tauri Connection
          </button>
          {greetMsg && <p>{greetMsg}</p>}
        </div>

        <div style={{ margin: '20px 0' }}>
          <button
            onClick={testPythonConnection}
            disabled={isLoading}
            style={{ margin: '5px', padding: '10px 20px' }}
          >
            Test Python Backend
          </button>
          <p>Python Status: {pythonStatus}</p>
        </div>

        <div style={{ margin: '20px 0' }}>
          <button
            onClick={testLatency}
            disabled={isTestingLatency || pythonStatus !== '✅ Python backend connected'}
            style={{
              margin: '5px',
              padding: '10px 20px',
              backgroundColor: pythonStatus !== '✅ Python backend connected' ? '#ccc' : '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px'
            }}
          >
            {isTestingLatency ? 'Testing Latency...' : 'Test WebSocket Latency'}
          </button>

          {latencyResults.count > 0 && (
            <div style={{
              marginTop: '10px',
              padding: '15px',
              backgroundColor: '#f5f5f5',
              borderRadius: '8px',
              textAlign: 'left',
              display: 'inline-block'
            }}>
              <h4 style={{ margin: '0 0 10px 0', color: '#333' }}>Latency Results:</h4>
              <p style={{ margin: '5px 0', color: '#333' }}>
                <strong>Average:</strong> {latencyResults.avg}ms
                {latencyResults.avg < 20 ? ' 🟢' : latencyResults.avg < 30 ? ' 🟡' : ' 🔴'}
              </p>
              <p style={{ margin: '5px 0', color: '#333' }}>
                <strong>Min:</strong> {latencyResults.min}ms
              </p>
              <p style={{ margin: '5px 0', color: '#333' }}>
                <strong>Max:</strong> {latencyResults.max}ms
              </p>
              <p style={{ margin: '5px 0', color: '#666' }}>
                ({latencyResults.count} tests)
              </p>
            </div>
          )}
        </div>

        <div style={{ margin: '20px 0', border: '2px solid #444', borderRadius: '8px', padding: '20px' }}>
          <h3>📹 Video Streaming Test</h3>

          <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <div style={{ margin: '10px 0' }}>
                <button
                  onClick={videoStream ? stopCamera : startCamera}
                  style={{
                    margin: '5px',
                    padding: '10px 20px',
                    backgroundColor: videoStream ? '#f44336' : '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px'
                  }}
                >
                  {videoStream ? 'Stop Camera' : 'Start Camera'}
                </button>
                <p>{videoStream ? '✅ Camera active' : '📷 Camera not started'}</p>
              </div>

              <div style={{ margin: '10px 0' }}>
                <button
                  onClick={isStreaming ? stopVideoStreaming : startVideoStreaming}
                  disabled={!videoStream}
                  style={{
                    margin: '5px',
                    padding: '10px 20px',
                    backgroundColor: !videoStream ? '#ccc' : isStreaming ? '#f44336' : '#FF9800',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px'
                  }}
                >
                  {isStreaming ? 'Stop Streaming' : 'Start Video Streaming'}
                </button>
                <p>{isStreaming ? '📹 Streaming to backend...' : 'Not streaming'}</p>
              </div>

              <div style={{ margin: '10px 0' }}>
                <button
                  onClick={testVideoLatency}
                  disabled={!isStreaming || isTestingVideoLatency}
                  style={{
                    margin: '5px',
                    padding: '10px 20px',
                    backgroundColor: !isStreaming ? '#ccc' : '#9C27B0',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px'
                  }}
                >
                  {isTestingVideoLatency ? 'Testing Video Latency...' : 'Test Video Latency'}
                </button>
              </div>

              <div style={{
                backgroundColor: '#1a1a1a',
                padding: '10px',
                borderRadius: '4px',
                fontSize: '12px',
                fontFamily: 'monospace'
              }}>
                <div><strong>Video Stats:</strong></div>
                <div>Frames sent: {videoStats.framesSent}</div>
                <div>Backend responses: {videoStats.backendResponses}</div>
                <div>Current FPS: {videoStats.currentFPS}</div>
                <div>Data sent: {Math.round(videoStats.dataSent)} KB</div>
              </div>

              {videoLatencyResults.count > 0 && (
                <div style={{
                  marginTop: '10px',
                  padding: '15px',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '8px',
                  textAlign: 'left',
                  color: '#333'
                }}>
                  <h4 style={{ margin: '0 0 10px 0' }}>Video Latency Results:</h4>
                  <p style={{ margin: '5px 0' }}>
                    <strong>Average:</strong> {videoLatencyResults.avg}ms
                    {videoLatencyResults.avg < 30 ? ' 🟢' : videoLatencyResults.avg < 50 ? ' 🟡' : ' 🔴'}
                  </p>
                  <p style={{ margin: '5px 0' }}>
                    <strong>Min:</strong> {videoLatencyResults.min}ms
                  </p>
                  <p style={{ margin: '5px 0' }}>
                    <strong>Max:</strong> {videoLatencyResults.max}ms
                  </p>
                  <p style={{ margin: '5px 0', color: '#666' }}>
                    ({videoLatencyResults.count} video frames tested)
                  </p>
                </div>
              )}
            </div>

            <div style={{ flex: 1, textAlign: 'center' }}>
              <h4>Live Camera Feed</h4>
              <video
                ref={videoRef}
                width="320"
                height="240"
                autoPlay
                muted
                style={{
                  border: '2px solid #444',
                  borderRadius: '8px',
                  backgroundColor: '#111'
                }}
              />
              <canvas
                ref={canvasRef}
                width="320"
                height="240"
                style={{ display: 'none' }}
              />
              <p style={{ fontSize: '12px', color: '#666' }}>
                320x240 capture → WebSocket → Python backend
              </p>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '30px', fontSize: '0.8em', color: '#666' }}>
          <p>Phase 1: Tauri + React + Python WebSocket + Video Streaming Test</p>
          <p style={{ fontSize: '0.7em', marginTop: '10px' }}>
            🟢 &lt;30ms: Excellent | 🟡 30-50ms: Good | 🔴 &gt;50ms: Consider optimization
          </p>
        </div>
      </header>
    </div>
  );
}

export default App;
