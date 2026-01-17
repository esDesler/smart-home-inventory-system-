const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const uiToken = import.meta.env.VITE_UI_TOKEN || "";

const defaultHeaders = () => {
  const headers = {
    "Content-Type": "application/json",
  };
  if (uiToken) {
    headers.Authorization = `Bearer ${uiToken}`;
  }
  return headers;
};

const checkResponse = async (response) => {
  if (response.ok) {
    if (response.status === 204) {
      return null;
    }
    return response.json();
  }
  const text = await response.text();
  throw new Error(`${response.status} ${response.statusText}: ${text}`);
};

export const apiGet = async (path) => {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "GET",
    headers: defaultHeaders(),
  });
  return checkResponse(response);
};

export const apiPost = async (path, body = {}) => {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: defaultHeaders(),
    body: JSON.stringify(body),
  });
  return checkResponse(response);
};

export const apiPut = async (path, body = {}) => {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "PUT",
    headers: defaultHeaders(),
    body: JSON.stringify(body),
  });
  return checkResponse(response);
};

export const fetchItems = async () => apiGet("/api/v1/items");
export const fetchItem = async (itemId) => apiGet(`/api/v1/items/${itemId}`);
export const fetchHistory = async (itemId, range = "7d") =>
  apiGet(`/api/v1/items/${itemId}/history?range=${encodeURIComponent(range)}`);
export const fetchAlerts = async () => apiGet("/api/v1/alerts?status=active");
export const ackAlert = async (alertId) =>
  apiPost(`/api/v1/alerts/${alertId}/ack`);
export const fetchDevices = async () => apiGet("/api/v1/devices");
export const fetchSensors = async () => apiGet("/api/v1/sensors");

export const getBaseUrl = () => baseUrl;
export const hasUiToken = () => Boolean(uiToken);
export const getStreamUrl = (lastEventId) => {
  const url = new URL(`${baseUrl}/api/v1/stream`);
  if (uiToken) {
    url.searchParams.set("token", uiToken);
  }
  if (lastEventId) {
    url.searchParams.set("last_event_id", lastEventId);
  }
  return url.toString();
};
