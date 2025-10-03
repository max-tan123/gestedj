/**
 * @fileoverview Connection Status Component
 *
 * This component displays the connection status to the GesteDJ backend
 * and provides controls for connection management.
 *
 * @author GesteDJ Team
 * @version 1.0.0
 */

import React from 'react';
import { useBackendConnection, useLatencyTest } from '../hooks/useWebSocket';

interface ConnectionStatusProps {
  /** Additional CSS classes */
  className?: string;
  /** Show detailed capabilities */
  showDetails?: boolean;
}

/**
 * Component displaying backend connection status and capabilities
 */
export function ConnectionStatus({ className = '', showDetails = true }: ConnectionStatusProps) {
  const { status, capabilities, testConnection } = useBackendConnection();
  const { results, isesting, runLatencyTest } = useLatencyTest();

  const getStatusColor = (status: string): string => {
    if (status.includes('✅')) return '#4CAF50';
    if (status.includes('❌')) return '#f44336';
    if (status.includes('Testing')) return '#FF9800';
    return '#2196F3';
  };

  return (
    <div className={`connection-status ${className}`} style={{
      border: '2px solid #333',
      borderRadius: '8px',
      padding: '15px',
      margin: '10px 0'
    }}>
      <h3>🔗 Backend Connection</h3>

      <div style={{
        display: 'flex',
        gap: '10px',
        marginBottom: '15px',
        flexWrap: 'wrap'
      }}>
        <button
          onClick={testConnection}
          style={{
            padding: '8px 16px',
            backgroundColor: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Test Connection
        </button>

        <button
          onClick={() => runLatencyTest(10)}
          disabled={isesting}
          style={{
            padding: '8px 16px',
            backgroundColor: isesting ? '#666' : '#FF9800',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isesting ? 'not-allowed' : 'pointer'
          }}
        >
          {isesting ? 'Testing Latency...' : 'Test Latency'}
        </button>
      </div>

      <div style={{
        padding: '10px',
        backgroundColor: getStatusColor(status),
        borderRadius: '4px',
        marginBottom: '10px'
      }}>
        <strong>Status:</strong> {status}
      </div>

      {showDetails && (
        <div style={{
          backgroundColor: '#1a1a1a',
          padding: '10px',
          borderRadius: '4px',
          fontSize: '12px',
          fontFamily: 'monospace'
        }}>
          <div><strong>Backend Capabilities:</strong></div>
          <div>MediaPipe: {capabilities.mediapipe ? '✅' : '❌'}</div>
          <div>MIDI Device: {capabilities.midi ? '✅' : '❌'}</div>
          <div>RTMIDI: {capabilities.rtmidi ? '✅' : '❌'}</div>
          <div>Original MIDI: {capabilities.originalMidi ? '✅' : '❌'}</div>
        </div>
      )}

      {results.count > 0 && (
        <LatencyResults results={results} />
      )}
    </div>
  );
}

interface LatencyResultsProps {
  results: {
    min: number;
    max: number;
    avg: number;
    count: number;
  };
}

/**
 * Component to display latency test results
 */
function LatencyResults({ results }: LatencyResultsProps) {
  const getLatencyColor = (avg: number): string => {
    if (avg < 20) return '#4CAF50'; // Green - Excellent
    if (avg < 30) return '#FF9800'; // Orange - Good
    return '#f44336'; // Red - Needs optimization
  };

  const getLatencyEmoji = (avg: number): string => {
    if (avg < 20) return '🟢';
    if (avg < 30) return '🟡';
    return '🔴';
  };

  return (
    <div style={{
      marginTop: '10px',
      padding: '10px',
      backgroundColor: '#f5f5f5',
      borderRadius: '8px',
      color: '#333'
    }}>
      <h4 style={{ margin: '0 0 8px 0' }}>Latency Test Results:</h4>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
        <div>
          <strong>Average:</strong>{' '}
          <span style={{ color: getLatencyColor(results.avg) }}>
            {results.avg}ms {getLatencyEmoji(results.avg)}
          </span>
        </div>

        <div>
          <strong>Count:</strong> {results.count} tests
        </div>

        <div>
          <strong>Min:</strong> {results.min}ms
        </div>

        <div>
          <strong>Max:</strong> {results.max}ms
        </div>
      </div>

      <div style={{
        marginTop: '8px',
        fontSize: '11px',
        color: '#666'
      }}>
        🟢 &lt;20ms: Excellent | 🟡 20-30ms: Good | 🔴 &gt;30ms: Needs optimization
      </div>
    </div>
  );
}

/**
 * Simplified connection indicator for minimal UI
 */
export function ConnectionIndicator() {
  const { status } = useBackendConnection();

  const isConnected = status.includes('✅');
  const isError = status.includes('❌');

  const color = isConnected ? '#4CAF50' : isError ? '#f44336' : '#FF9800';
  const text = isConnected ? 'Connected' : isError ? 'Disconnected' : 'Connecting';

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px',
      padding: '4px 8px',
      backgroundColor: color,
      color: 'white',
      borderRadius: '12px',
      fontSize: '12px',
      fontWeight: 'bold'
    }}>
      <div style={{
        width: '8px',
        height: '8px',
        backgroundColor: 'white',
        borderRadius: '50%'
      }} />
      {text}
    </div>
  );
}