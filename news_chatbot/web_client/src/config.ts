export type TransportType = 'daily' | 'websocket';

export const VOICE_BACKEND_URL = import.meta.env.VITE_VOICE_BACKEND_URL || '';

export const DEFAULT_TRANSPORT: TransportType =
  (import.meta.env.VITE_DEFAULT_TRANSPORT as TransportType) || 'daily';
