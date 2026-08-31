/** Typed fetch wrapper. Session lives in an httpOnly cookie, so every call sends
 * credentials and no token is ever readable from JavaScript. */

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isUnauthorized() {
    return this.status === 401;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
};

async function errorFrom(response: Response): Promise<ApiError> {
  let detail = response.statusText;
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") detail = payload.detail;
    else if (Array.isArray(payload?.detail) && payload.detail[0]?.msg) {
      detail = payload.detail[0].msg;
    }
  } catch {
    // A body that is not JSON tells us nothing more than the status already does.
  }
  return new ApiError(response.status, detail);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(path, {
    method: options.method ?? "GET",
    credentials: "include",
    headers: options.body === undefined ? undefined : { "Content-Type": "application/json" },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });

  if (!response.ok) throw await errorFrom(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function upload<T>(path: string, file: File): Promise<T> {
  return uploadWithFields<T>(path, file);
}

export async function uploadWithFields<T>(
  path: string,
  file: File,
  fields: Record<string, string> = {},
): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  for (const [key, value] of Object.entries(fields)) form.append(key, value);
  // No Content-Type header: the browser has to set it itself, because only it
  // knows the multipart boundary it is about to generate.
  const response = await fetch(path, { method: "POST", credentials: "include", body: form });
  if (!response.ok) throw await errorFrom(response);
  return (await response.json()) as T;
}

export function query(params: Record<string, string | string[] | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    // A list repeats the key, which is what FastAPI reads back as a list. An
    // empty one contributes nothing, so "no filter" and "filter on nothing"
    // stay the same request.
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else if (value) search.set(key, value);
  }
  const rendered = search.toString();
  return rendered ? `?${rendered}` : "";
}
