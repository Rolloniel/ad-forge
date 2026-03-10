export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

class ApiClient {
  private getApiKey(): string | null {
    if (typeof document === "undefined") return null;
    const match = document.cookie.match(/(?:^|; )adforge_api_key=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : null;
  }

  async fetch<T>(path: string, init?: RequestInit): Promise<T> {
    const apiKey = this.getApiKey();
    const headers = new Headers(init?.headers);
    headers.set("Content-Type", "application/json");
    if (apiKey) {
      headers.set("Authorization", `Bearer ${apiKey}`);
    }

    const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });

    if (!res.ok) {
      if (res.status === 401) {
        // Clear cookie and redirect to login
        document.cookie = "adforge_api_key=; path=/; max-age=0";
        window.location.href = "/login";
        throw new ApiError(401, "Session expired");
      }
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail ?? res.statusText);
    }

    return res.json() as Promise<T>;
  }

  get<T>(path: string) {
    return this.fetch<T>(path);
  }

  post<T>(path: string, body?: unknown) {
    return this.fetch<T>(path, {
      method: "POST",
      body: body != null ? JSON.stringify(body) : undefined,
    });
  }

  put<T>(path: string, body?: unknown) {
    return this.fetch<T>(path, {
      method: "PUT",
      body: body != null ? JSON.stringify(body) : undefined,
    });
  }
}

export const api = new ApiClient();
