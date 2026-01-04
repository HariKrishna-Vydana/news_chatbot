/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_VOICE_BACKEND_URL: string;
  readonly VITE_DEFAULT_TRANSPORT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
