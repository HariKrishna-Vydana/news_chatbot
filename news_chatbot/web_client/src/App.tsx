import { useState, useCallback, useRef, useEffect } from 'react';
import { PipecatClient, RTVIEvent } from '@pipecat-ai/client-js';
import { DailyTransport } from '@pipecat-ai/daily-transport';
import { WebSocketTransport } from '@pipecat-ai/websocket-transport';
import { TransportType, DEFAULT_TRANSPORT, VOICE_BACKEND_URL, CHAT_BACKEND_URL } from './config';

interface TranscriptMessage {
  role: 'user' | 'bot';
  text: string;
  timestamp: Date;
}

interface Agent {
  id: string;
  name: string;
  prompt: string;
}

function App() {
  const [transportType, setTransportType] = useState<TransportType>(DEFAULT_TRANSPORT);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [status, setStatus] = useState('Disconnected');
  const [error, setError] = useState<string | null>(null);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const clientRef = useRef<PipecatClient | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch(`${CHAT_BACKEND_URL}/api/agents`);
        if (!response.ok) throw new Error('Failed to fetch agents');
        const data = await response.json();
        setAgents(data.agents);
        if (data.agents.length > 0) {
          setSelectedAgent(data.agents[0].id);
          setSystemPrompt(data.agents[0].prompt);
        }
      } catch (err) {
        console.error('Failed to load agents:', err);
        setAgents([{ id: 'default', name: 'Default Agent', prompt: '' }]);
        setSelectedAgent('default');
      } finally {
        setAgentsLoading(false);
      }
    };
    fetchAgents();
  }, []);

  const handleAgentChange = (agentId: string) => {
    setSelectedAgent(agentId);
    const agent = agents.find(a => a.id === agentId);
    if (agent) {
      setSystemPrompt(agent.prompt);
    }
  };

  const getTransport = (type: TransportType) => {
    switch (type) {
      case 'daily':
        return new DailyTransport();
      case 'websocket':
        return new WebSocketTransport();
      default:
        return new DailyTransport();
    }
  };

  const connect = useCallback(async () => {
    setIsConnecting(true);
    setError(null);

    try {
      const transport = getTransport(transportType);

      const client = new PipecatClient({
        transport,
        enableMic: true,
        enableCam: false,
        callbacks: {
          onConnected: () => {
            setIsConnected(true);
            setIsConnecting(false);
            setStatus('Connected');
          },
          onDisconnected: () => {
            setIsConnected(false);
            setStatus('Disconnected');
            clientRef.current = null;
          },
          onBotReady: () => {
            setStatus('Bot Ready - Start Speaking');
          },
          onUserTranscript: (data: { text?: string; final?: boolean }) => {
            if (data.final && data.text) {
              setTranscript(prev => [...prev, {
                role: 'user',
                text: data.text!,
                timestamp: new Date()
              }]);
            }
          },
          onBotTranscript: (data: { text?: string }) => {
            if (data.text) {
              setTranscript(prev => [...prev, {
                role: 'bot',
                text: data.text!,
                timestamp: new Date()
              }]);
            }
          },
          onError: (message: any) => {
            console.error('RTVI Error:', message);
            const errorMsg = message?.message || message?.error || JSON.stringify(message);
            setError(errorMsg);
            setIsConnecting(false);
          },
        },
      });

      clientRef.current = client;

      client.on(RTVIEvent.TrackStarted, (track: MediaStreamTrack, participant?: any) => {
        if (!participant?.local && track.kind === 'audio') {
          const audio = document.createElement('audio');
          audio.autoplay = true;
          audio.srcObject = new MediaStream([track]);
          document.body.appendChild(audio);
        }
      });

      if (transportType === 'websocket') {
        // For WebSocket, first get the ws_url from backend, then connect directly
        const response = await fetch(`${VOICE_BACKEND_URL || 'http://localhost:7860'}/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ system_prompt: systemPrompt || null }),
        });
        const data = await response.json();
        await client.connect({ wsUrl: data.ws_url });
      } else {
        // For Daily, use the standard connect flow with system_prompt
        const response = await fetch(`${VOICE_BACKEND_URL || 'http://localhost:7860'}/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ system_prompt: systemPrompt || null }),
        });
        const data = await response.json();
        await client.connect({ roomUrl: data.room_url, token: data.token });
      }

    } catch (err) {
      console.error('Connection error:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect');
      setIsConnecting(false);
    }
  }, [transportType, systemPrompt]);

  const disconnect = useCallback(async () => {
    if (clientRef.current) {
      await clientRef.current.disconnect();
      clientRef.current = null;
    }
    setIsConnected(false);
    setStatus('Disconnected');
  }, []);

  const clearTranscript = () => {
    setTranscript([]);
  };

  return (
    <div style={styles.appWrapper}>
      {/* Settings Toggle Button */}
      <button
        onClick={() => setSettingsOpen(!settingsOpen)}
        style={styles.settingsToggle}
        title="Settings"
      >
        ☰
      </button>

      {/* Left Side Panel */}
      <div style={{
        ...styles.sidePanel,
        transform: settingsOpen ? 'translateX(0)' : 'translateX(-100%)',
      }}>
        <div style={styles.sidePanelHeader}>
          <h3 style={styles.sidePanelTitle}>Configuration</h3>
          <button
            onClick={() => setSettingsOpen(false)}
            style={styles.closeButton}
          >
            ✕
          </button>
        </div>

        <div style={styles.sidePanelContent}>
          <div style={styles.settingGroup}>
            <label style={styles.label}>Agent:</label>
            <select
              value={selectedAgent}
              onChange={(e) => handleAgentChange(e.target.value)}
              disabled={isConnected || isConnecting || agentsLoading}
              style={styles.select}
            >
              {agentsLoading ? (
                <option>Loading agents...</option>
              ) : (
                agents.map(agent => (
                  <option key={agent.id} value={agent.id}>{agent.name}</option>
                ))
              )}
            </select>
          </div>

          <div style={styles.settingGroup}>
            <label style={styles.label}>System Prompt (optional):</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              disabled={isConnected || isConnecting}
              placeholder="Enter custom instructions for the agent..."
              style={styles.textarea}
              rows={5}
            />
          </div>

          <div style={styles.settingGroup}>
            <label style={styles.label}>Transport:</label>
            <select
              value={transportType}
              onChange={(e) => setTransportType(e.target.value as TransportType)}
              disabled={isConnected || isConnecting}
              style={styles.select}
            >
              <option value="daily">Daily WebRTC</option>
              <option value="websocket">WebSocket</option>
            </select>
          </div>
        </div>
      </div>

      {/* Overlay when panel is open */}
      {settingsOpen && (
        <div
          style={styles.overlay}
          onClick={() => setSettingsOpen(false)}
        />
      )}

      {/* Main Content */}
      <div style={styles.container}>
        <header style={styles.header}>
          <h1 style={styles.title}>News Chatbot</h1>
          <p style={styles.subtitle}>Voice-powered news assistant</p>
        </header>

        <div style={styles.controls}>
          <button
            onClick={isConnected ? disconnect : connect}
            disabled={isConnecting}
            style={{
              ...styles.button,
              backgroundColor: isConnected ? '#e74c3c' : '#2ecc71',
              opacity: isConnecting ? 0.7 : 1,
            }}
          >
            {isConnecting ? 'Connecting...' : isConnected ? 'Disconnect' : 'Connect'}
          </button>

          <div style={styles.status}>
            <span style={{
              ...styles.statusDot,
              backgroundColor: isConnected ? '#2ecc71' : '#e74c3c'
            }} />
            {status}
          </div>
        </div>

        {error && (
          <div style={styles.error}>
            {error}
          </div>
        )}

        <main style={styles.main}>
          <div style={styles.transcriptHeader}>
            <h2 style={styles.transcriptTitle}>Conversation</h2>
            <button onClick={clearTranscript} style={styles.clearButton}>
              Clear
            </button>
          </div>

          <div style={styles.transcript}>
            {transcript.length === 0 ? (
              <p style={styles.emptyState}>
                {isConnected
                  ? 'Start speaking to ask about news...'
                  : 'Connect to start a conversation'}
              </p>
            ) : (
              transcript.map((msg, i) => (
                <div
                  key={i}
                  style={{
                    ...styles.message,
                    ...(msg.role === 'user' ? styles.userMessage : styles.botMessage),
                  }}
                >
                  <span style={styles.messageRole}>
                    {msg.role === 'user' ? 'You' : 'Bot'}:
                  </span>
                  <span style={styles.messageText}>{msg.text}</span>
                </div>
              ))
            )}
          </div>
        </main>

        <footer style={styles.footer}>
          <p>Ask about current news, sports, tech, or any topic!</p>
        </footer>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  appWrapper: {
    position: 'relative',
    minHeight: '100vh',
  },
  settingsToggle: {
    position: 'fixed',
    top: '20px',
    left: '20px',
    width: '44px',
    height: '44px',
    borderRadius: '8px',
    border: '1px solid #444',
    backgroundColor: '#2d2d44',
    color: '#aaa',
    fontSize: '1.4rem',
    cursor: 'pointer',
    zIndex: 100,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s',
  },
  sidePanel: {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '320px',
    height: '100vh',
    backgroundColor: '#1a1a2e',
    borderRight: '1px solid #333',
    zIndex: 200,
    transition: 'transform 0.3s ease-in-out',
    display: 'flex',
    flexDirection: 'column',
  },
  sidePanelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px',
    borderBottom: '1px solid #333',
  },
  sidePanelTitle: {
    margin: 0,
    fontSize: '1.2rem',
    color: '#ddd',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    color: '#888',
    fontSize: '1.2rem',
    cursor: 'pointer',
    padding: '4px 8px',
  },
  sidePanelContent: {
    padding: '20px',
    overflowY: 'auto',
    flex: 1,
  },
  settingGroup: {
    marginBottom: '24px',
  },
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    zIndex: 150,
  },
  container: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    padding: '20px',
    maxWidth: '800px',
    margin: '0 auto',
  },
  header: {
    textAlign: 'center',
    marginBottom: '30px',
  },
  textarea: {
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid #444',
    backgroundColor: '#2d2d44',
    color: '#fff',
    fontSize: '0.95rem',
    resize: 'vertical',
    minHeight: '60px',
    fontFamily: 'inherit',
    width: '100%',
    boxSizing: 'border-box',
  },
  title: {
    fontSize: '2.5rem',
    marginBottom: '10px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  subtitle: {
    color: '#888',
    fontSize: '1.1rem',
  },
  controls: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
    marginBottom: '20px',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  label: {
    color: '#aaa',
    display: 'block',
    marginBottom: '8px',
  },
  select: {
    padding: '10px 15px',
    borderRadius: '8px',
    border: '1px solid #444',
    backgroundColor: '#2d2d44',
    color: '#fff',
    fontSize: '1rem',
    cursor: 'pointer',
    width: '100%',
    boxSizing: 'border-box',
  },
  button: {
    padding: '12px 30px',
    borderRadius: '8px',
    border: 'none',
    color: '#fff',
    fontSize: '1rem',
    fontWeight: 'bold',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  status: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: '#aaa',
  },
  statusDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
  },
  error: {
    backgroundColor: '#e74c3c22',
    border: '1px solid #e74c3c',
    borderRadius: '8px',
    padding: '15px',
    marginBottom: '20px',
    color: '#e74c3c',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
  },
  transcriptHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '15px',
  },
  transcriptTitle: {
    fontSize: '1.3rem',
    color: '#ddd',
  },
  clearButton: {
    padding: '8px 16px',
    borderRadius: '6px',
    border: '1px solid #444',
    backgroundColor: 'transparent',
    color: '#aaa',
    cursor: 'pointer',
  },
  transcript: {
    flex: 1,
    backgroundColor: '#16162a',
    borderRadius: '12px',
    padding: '20px',
    minHeight: '300px',
    maxHeight: '500px',
    overflowY: 'auto',
  },
  emptyState: {
    color: '#666',
    textAlign: 'center',
    marginTop: '100px',
  },
  message: {
    padding: '12px 16px',
    borderRadius: '12px',
    marginBottom: '10px',
    maxWidth: '80%',
  },
  userMessage: {
    backgroundColor: '#3d3d5c',
    marginLeft: 'auto',
  },
  botMessage: {
    backgroundColor: '#2d4a5c',
    marginRight: 'auto',
  },
  messageRole: {
    fontWeight: 'bold',
    marginRight: '8px',
    color: '#aaa',
  },
  messageText: {
    color: '#fff',
  },
  footer: {
    textAlign: 'center',
    marginTop: '30px',
    color: '#666',
    fontSize: '0.9rem',
  },
};

export default App;
