import { notifications } from '@mantine/notifications';

/** Adresse du backend, intégrée à la compilation depuis la variable VITE_API_URL. */
const configuredUrl: string = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_URL = configuredUrl.replace(/\/+$/, ''); // sans slash final

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    // Le navigateur ne donne aucun détail : backend arrêté, mauvaise adresse ou origine refusée (CORS).
    throw new ApiError(
      0,
      `Backend injoignable (${API_URL}). Vérifiez qu'il est démarré, ainsi que VITE_API_URL et CORS_ORIGINS.`,
    );
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }
  return response;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const { detail } = await response.json();
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((item: { msg: string }) => item.msg).join(' • ');
  } catch {
    // Réponse non JSON, par exemple une page d'erreur de la plateforme d'hébergement.
  }
  return `Erreur ${response.status} renvoyée par le backend.`;
}

function sendJson(method: 'POST' | 'PATCH', body?: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export async function get<T>(path: string): Promise<T> {
  return (await request(path)).json();
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  return (await request(path, sendJson('POST', body))).json();
}

export async function patch<T>(path: string, body: unknown): Promise<T> {
  return (await request(path, sendJson('PATCH', body))).json();
}

export async function downloadPdf(documentId: string, filename: string) {
  const blob = await (await request(`/api/documents/${documentId}/download`)).blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000); // laisse au navigateur le temps de lancer le téléchargement
}

export function showError(error: Error) {
  notifications.show({ color: 'red', title: 'Action non terminée', message: error.message });
}

export function showSuccess(message: string) {
  notifications.show({ color: 'green', message });
}
