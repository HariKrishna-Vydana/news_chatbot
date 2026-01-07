export type TransportType = 'daily' | 'websocket';

export const VOICE_BACKEND_URL = import.meta.env.VITE_VOICE_BACKEND_URL || '';

export const CHAT_BACKEND_URL = import.meta.env.VITE_CHAT_BACKEND_URL || 'http://localhost:8000';

export const DEFAULT_TRANSPORT: TransportType =
  (import.meta.env.VITE_DEFAULT_TRANSPORT as TransportType) || 'daily';
