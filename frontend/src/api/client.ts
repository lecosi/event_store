import axios, { AxiosError } from "axios";
import { messages } from "../i18n";
import type { EventStatus } from "../types";
import { useAuthStore } from "../store/authStore";

/** Error thrown by every API call, with a message that is safe to show to users. */
export class ApiError extends Error {
  /** HTTP status, or null when the server could not be reached. */
  readonly status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface ValidationItem {
  loc?: (string | number)[];
  type?: string;
  ctx?: Record<string, unknown>;
}

/** Backend `detail` strings that never change, mapped to their Spanish text. */
export const known = messages.errors.known;

const statusLabels = messages.labels.status;
const statusWords = Object.keys(statusLabels).join("|");
const label = (value: string) => statusLabels[value as EventStatus];

/** Backend `detail` strings that embed values (built with f-strings), each with its Spanish builder. */
const patterns: [RegExp, (...groups: string[]) => string][] = [
  [
    /^capacity cannot exceed the event capacity \((\d+)\)$/,
    messages.errors.sessionCapacityExceedsEvent,
  ],
  [
    /^capacity cannot be lower than the largest session capacity \((\d+)\)$/,
    messages.errors.capacityBelowSessions,
  ],
  [
    /^capacity cannot be lower than the current registrations \((\d+)\)$/,
    messages.errors.capacityBelowRegistrations,
  ],
  [
    new RegExp(`^A (${statusWords}) event cannot be edited$`),
    (value) => messages.errors.eventNotEditable(label(value)),
  ],
  [
    new RegExp(
      `^Cannot change status from (${statusWords}) to (${statusWords})$`,
    ),
    (from, to) => messages.errors.statusTransition(label(from), label(to)),
  ],
  [
    /^Password must be at least (\d+) characters long$/,
    messages.errors.passwordTooShort,
  ],
];

function translateDetail(detail: string): string {
  const exact = known[detail];
  if (exact) return exact;
  for (const [pattern, build] of patterns) {
    const match = pattern.exec(detail);
    if (match) return build(...match.slice(1));
  }
  return messages.common.genericError;
}

/** One 422 item: text chosen by its stable `type`, with `{ctx_key}` placeholders filled from `ctx`. */
function translateValidationItem({
  loc = [],
  type = "",
  ctx = {},
}: ValidationItem): string {
  const template = messages.errors.validation[type] ?? "";
  const keys = [...template.matchAll(/\{(\w+)\}/g)].map((match) => match[1]);
  const usable = template !== "" && keys.every((key) => key in ctx);
  const body = usable
    ? keys.reduce(
        (text, key) => text.replace(`{${key}}`, String(ctx[key])),
        template,
      )
    : messages.common.invalidValue;
  // loc looks like ['body', 'email']; the first element is the source, not useful to users.
  const field = messages.fields[loc.slice(1).join(".")];
  return field ? `${field}: ${body}` : body;
}

/** Converts anything thrown by axios into an ApiError with a Spanish message. */
export function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof AxiosError) {
    if (!error.response) return new ApiError(messages.common.networkError);
    const { status, data } = error.response;
    const detail = (data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string")
      return new ApiError(translateDetail(detail), status);
    if (Array.isArray(detail) && detail.length > 0) {
      return new ApiError(
        (detail as ValidationItem[]).map(translateValidationItem).join(". "),
        status,
      );
    }
    return new ApiError(messages.common.genericError, status);
  }
  return new ApiError(messages.common.genericError);
}

/** Single axios instance shared by all API modules. */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1",
});

// Attach the JWT to every request when the user is logged in.
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

// Normalize errors; an expired/invalid token (401) logs the user out.
apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const apiError = normalizeError(error);
    if (apiError.status === 401) useAuthStore.getState().logout();
    return Promise.reject(apiError);
  },
);
