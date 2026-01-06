export type TransportType = 'daily' | 'websocket' | 'smallwebrtc';

export const VOICE_BACKEND_URL = import.meta.env.VITE_VOICE_BACKEND_URL || '';

export const DEFAULT_TRANSPORT: TransportType =
  (import.meta.env.VITE_DEFAULT_TRANSPORT as TransportType) || 'smallwebrtc';

export const ICE_SERVERS: RTCIceServer[] = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
  // Free public TURN servers (OpenRelay Project) for NAT traversal
  {
    urls: 'turn:openrelay.metered.ca:80',
    username: 'openrelayproject',
    credential: 'openrelayproject',
  },
  {
    urls: 'turn:openrelay.metered.ca:443',
    username: 'openrelayproject',
    credential: 'openrelayproject',
  },
  {
    urls: 'turn:openrelay.metered.ca:443?transport=tcp',
    username: 'openrelayproject',
    credential: 'openrelayproject',
  },
];
