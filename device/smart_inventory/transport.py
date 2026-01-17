import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class TransportError(RuntimeError):
    pass


def post_readings_batch(
    base_url: str,
    payload: Dict[str, Any],
    api_token: Optional[str] = None,
    ca_cert_path: Optional[str] = None,
    timeout_seconds: int = 10,
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/api/v1/readings/batch"
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "smart-inventory-device/0.1.0",
    }
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    context = ssl.create_default_context(cafile=ca_cert_path) if ca_cert_path else ssl.create_default_context()
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise TransportError(str(exc)) from exc

    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise TransportError("Invalid JSON response") from exc
