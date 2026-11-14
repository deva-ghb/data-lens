export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type Method = "POST" | "PUT" | "PATCH" | "DELETE";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function textField(source: Record<string, unknown>, key: string): string | undefined {
  const value = source[key];
  return typeof value === "string" && value !== "" ? value : undefined;
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text === "") {
    return undefined;
  }
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

// The server reports errors as { code, message }, as { detail: "text" } or as
// { detail: { code, message } }. Anything else falls back to the HTTP status text.
function toApiError(response: Response, body: unknown): ApiError {
  const fallbackCode = `http_${response.status}`;
  const fallbackMessage = response.statusText || `Request failed with status ${response.status}`;
  if (!isRecord(body)) {
    return new ApiError(response.status, fallbackCode, fallbackMessage);
  }
  const detail = body["detail"];
  const source = isRecord(detail) ? detail : body;
  const code = textField(source, "code") ?? fallbackCode;
  const message =
    textField(source, "message") ??
    (typeof detail === "string" && detail !== "" ? detail : undefined) ??
    fallbackMessage;
  return new ApiError(response.status, code, message);
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, credentials: "include" });
  const body = await readJson(response);
  if (!response.ok) {
    throw toApiError(response, body);
  }
  return body as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export function apiSend<T>(method: Method, path: string, body?: unknown): Promise<T> {
  if (body === undefined) {
    return request<T>(path, { method });
  }
  return request<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
