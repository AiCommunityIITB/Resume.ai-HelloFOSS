// lib/config.ts
export const authConfig = {
  sso: {
    baseUrl: process.env.NEXT_PUBLIC_SSO_BASE_URL || 'https://sso.tech-iitb.org',
    projectId: process.env.NEXT_PUBLIC_SSO_PROJECT_ID || '1f189ac9-679b-4979-865d-49e6291c70e2',
  },
  api: {
    baseUrl: process.env.NEXT_PUBLIC_BACKEND_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  }
};
