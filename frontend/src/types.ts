// Types des données renvoyées par le backend (voir backend/app/models.py).

export type Meeting = {
  id: number;
  title: string;
  meeting_date: string;
  start_time: string;
  end_time: string;
  location: string;
  recipients: string[];
  agenda: string[];
  confirmation_date: string;
  contact: string;
};

export type ConvocationDocument = {
  id: string;
  title: string;
  meeting_date: string;
  storage_key: string;
  created_at: string;
};

export type ConvocationResult = {
  clarification: string | null;
  document: ConvocationDocument | null;
  meeting: Meeting | null;
  text: string;
};

/** « 2026-12-18 » ou « 2026-12-18T09:30:00Z » → « 18 décembre 2026 ». */
export function formatDate(value: string) {
  const date = value.length === 10 ? new Date(`${value}T12:00:00`) : new Date(value);
  return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
}

/** « 2026-12-18 » → « décembre ». */
export function formatMonth(value: string) {
  return new Date(`${value}T12:00:00`).toLocaleDateString('fr-FR', { month: 'long' });
}

/** « 14:00:00 » → « 14:00 ». */
export const formatTime = (value: string) => value.slice(0, 5);
