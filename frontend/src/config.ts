export const config = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, ""),
  authMode: (import.meta.env.VITE_AUTH_MODE ?? "local") as "local" | "cognito",
  cognito: {
    region: import.meta.env.VITE_COGNITO_REGION ?? "",
    clientId: import.meta.env.VITE_COGNITO_CLIENT_ID ?? "",
  },
};
