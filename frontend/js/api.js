const base = new URLSearchParams(location.search).get("api") || window.API_BASE || "";

export class ApiError extends Error {
  constructor(message, status, details, requestId) {
    super(message);
    this.status = status;
    this.details = details;
    this.requestId = requestId;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(base + path, { headers: { "Content-Type": "application/json" }, ...options });
  } catch (e) {
    throw new ApiError("Cannot reach the API. Check that the service is running.", 0);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = body && body.error;
    throw new ApiError(err ? err.message : `Request failed (${res.status})`, res.status, err && err.details, err && err.request_id);
  }
  return body;
}

export const api = {
  health: () => request("/health"),
  model: () => request("/api/v1/model"),
  patient: (id) => request(`/api/v1/patients/${encodeURIComponent(id)}`),
  patients: (params) => request(`/api/v1/patients?${new URLSearchParams(params)}`),
  predict: (features) => request("/api/v1/predict", { method: "POST", body: JSON.stringify(features) }),
};
