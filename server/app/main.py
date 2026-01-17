import asyncio
import datetime as dt
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .auth import require_device_auth, require_ui_auth
from .config import AppConfig, load_config
from .db import dumps_json, get_db, init_db, loads_json
from .events import EventBroadcaster
from .models import ItemCreate, ItemUpdate, ReadingsBatchIn, ThresholdsIn


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _parse_ts(value: str) -> dt.datetime:
    if not value:
        raise ValueError("Missing timestamp")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _normalize_ts(value: str) -> str:
    return _parse_ts(value).isoformat()


def _model_to_dict(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=True)
    return model.dict(exclude_unset=True)


def _parse_range(range_str: Optional[str]) -> dt.timedelta:
    if not range_str:
        return dt.timedelta(days=7)
    if len(range_str) < 2:
        raise HTTPException(status_code=400, detail="Invalid range format")
    unit = range_str[-1]
    try:
        value = int(range_str[:-1])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid range format") from exc
    if unit == "d":
        return dt.timedelta(days=value)
    if unit == "h":
        return dt.timedelta(hours=value)
    raise HTTPException(status_code=400, detail="Invalid range unit")


def _is_newer(new_ts: str, last_ts: Optional[str]) -> bool:
    if not last_ts:
        return True
    try:
        return _parse_ts(new_ts) >= _parse_ts(last_ts)
    except ValueError:
        return new_ts >= last_ts


def _upsert_device(conn, device_id: str, firmware: Optional[str], last_seen: str) -> None:
    conn.execute(
        """
        INSERT INTO devices (id, firmware, last_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET firmware = excluded.firmware, last_seen = excluded.last_seen;
        """,
        (device_id, firmware, last_seen),
    )


def _ensure_sensor(conn, sensor_id: str, device_id: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO sensors (id, device_id)
        VALUES (?, ?);
        """,
        (sensor_id, device_id),
    )


def _get_sensor_state(conn, sensor_id: str) -> Tuple[Optional[str], Optional[str]]:
    row = conn.execute(
        "SELECT last_state, last_update FROM sensors WHERE id = ?;", (sensor_id,)
    ).fetchone()
    if not row:
        return None, None
    return row["last_state"], row["last_update"]


def _update_sensor_state(
    conn,
    sensor_id: str,
    state: str,
    last_value: Optional[float],
    ts: str,
) -> None:
    conn.execute(
        """
        UPDATE sensors
        SET last_state = ?, last_value = ?, last_update = ?
        WHERE id = ?;
        """,
        (state, last_value, ts, sensor_id),
    )


def _get_item_for_sensor(conn, sensor_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT id, name, thresholds, unit, image_url
        FROM items
        WHERE sensor_id = ?;
        """,
        (sensor_id,),
    ).fetchone()
    if not row:
        return None
    return dict(row)


def _create_alert(
    conn,
    sensor_id: str,
    item_id: Optional[str],
    alert_type: str,
    message: str,
    created_at: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO alerts (item_id, sensor_id, type, status, message, created_at)
        VALUES (?, ?, ?, 'active', ?, ?);
        """,
        (item_id, sensor_id, alert_type, message, created_at),
    )
    return int(cursor.lastrowid)


def _resolve_alerts(conn, sensor_id: str, resolved_at: str) -> None:
    conn.execute(
        """
        UPDATE alerts
        SET status = 'resolved', resolved_at = ?
        WHERE sensor_id = ? AND status = 'active';
        """,
        (resolved_at, sensor_id),
    )


config_snapshot = load_config()

app = FastAPI(title="Smart Inventory Server", version="0.1.0")
app.state.config = config_snapshot
app.state.events = EventBroadcaster(config_snapshot.event_queue_size)
app.state.loop = None

if config_snapshot.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config_snapshot.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
async def _startup() -> None:
    config = load_config()
    app.state.config = config
    app.state.events = EventBroadcaster(config.event_queue_size)
    app.state.loop = asyncio.get_running_loop()
    init_db(config)
    if not config.device_tokens and not config.allow_unauth:
        logging.warning("Device auth disabled with INVENTORY_ALLOW_UNAUTH=false")
    if not config.ui_token and not config.allow_unauth:
        logging.warning("UI auth disabled with INVENTORY_ALLOW_UNAUTH=false")


def _broadcast(request: Request, event: Dict[str, Any]) -> None:
    loop = request.app.state.loop
    if loop is None:
        return
    asyncio.run_coroutine_threadsafe(request.app.state.events.publish(event), loop)


@app.get("/api/v1/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "time": _utc_now()}


@app.post("/api/v1/readings/batch")
def ingest_readings(batch: ReadingsBatchIn, request: Request) -> Dict[str, Any]:
    require_device_auth(request)
    config: AppConfig = request.app.state.config
    now = _utc_now()
    ack_seq: Optional[int] = None
    events: List[Dict[str, Any]] = []

    with get_db(config) as conn:
        _upsert_device(conn, batch.device_id, batch.firmware, now)

        for reading in batch.readings:
            try:
                reading_ts = _normalize_ts(reading.ts)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid reading timestamp") from exc
            _ensure_sensor(conn, reading.sensor_id, batch.device_id)
            prev_state, prev_ts = _get_sensor_state(conn, reading.sensor_id)
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO readings
                (device_id, seq_id, sensor_id, ts, raw_value, normalized_value, state, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    batch.device_id,
                    reading.seq_id,
                    reading.sensor_id,
                    reading_ts,
                    reading.raw_value,
                    reading.normalized_value,
                    reading.state,
                    now,
                ),
            )
            ack_seq = reading.seq_id
            if cursor.rowcount == 0:
                continue

            if _is_newer(reading_ts, prev_ts):
                _update_sensor_state(
                    conn,
                    reading.sensor_id,
                    reading.state,
                    reading.normalized_value,
                    reading_ts,
                )

            item = _get_item_for_sensor(conn, reading.sensor_id)
            events.append(
                {
                    "type": "item_status_update",
                    "sensor_id": reading.sensor_id,
                    "item_id": item["id"] if item else None,
                    "state": reading.state,
                    "normalized_value": reading.normalized_value,
                    "ts": reading_ts,
                }
            )

            if prev_state != reading.state:
                if reading.state in {"low", "out"}:
                    item_name = item["name"] if item else None
                    message = (
                        f"{item_name} is {reading.state}"
                        if item_name
                        else f"Sensor {reading.sensor_id} is {reading.state}"
                    )
                    alert_id = _create_alert(
                        conn,
                        reading.sensor_id,
                        item["id"] if item else None,
                        reading.state,
                        message,
                        now,
                    )
                    events.append(
                        {
                            "type": "alert_created",
                            "alert_id": alert_id,
                            "sensor_id": reading.sensor_id,
                            "item_id": item["id"] if item else None,
                            "state": reading.state,
                            "created_at": now,
                            "message": message,
                        }
                    )
                if reading.state == "ok":
                    _resolve_alerts(conn, reading.sensor_id, now)
                    events.append(
                        {
                            "type": "alert_resolved",
                            "sensor_id": reading.sensor_id,
                            "item_id": item["id"] if item else None,
                            "resolved_at": now,
                        }
                    )

    for event in events:
        _broadcast(request, event)

    return {"ack_seq_id": ack_seq, "server_time": now}


@app.get("/api/v1/items")
def list_items(request: Request) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    with get_db(config) as conn:
        rows = conn.execute(
            """
            SELECT items.id, items.name, items.sensor_id, items.thresholds,
                   items.unit, items.image_url, items.created_at, items.updated_at,
                   sensors.last_state, sensors.last_update, sensors.last_value
            FROM items
            LEFT JOIN sensors ON items.sensor_id = sensors.id
            ORDER BY items.name ASC;
            """
        ).fetchall()
    items = []
    for row in rows:
        thresholds = loads_json(row["thresholds"])
        items.append(
            {
                "id": row["id"],
                "name": row["name"],
                "sensor_id": row["sensor_id"],
                "thresholds": thresholds,
                "unit": row["unit"],
                "image_url": row["image_url"],
                "status": row["last_state"] or "unknown",
                "last_update": row["last_update"],
                "last_value": row["last_value"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    return {"items": items}


@app.get("/api/v1/items/{item_id}")
def get_item(item_id: str, request: Request) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    with get_db(config) as conn:
        item_row = conn.execute(
            """
            SELECT id, name, sensor_id, thresholds, unit, image_url, created_at, updated_at
            FROM items
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()
        if not item_row:
            raise HTTPException(status_code=404, detail="Item not found")
        latest = None
        if item_row["sensor_id"]:
            latest_row = conn.execute(
                """
                SELECT seq_id, ts, raw_value, normalized_value, state
                FROM readings
                WHERE sensor_id = ?
                ORDER BY ts DESC
                LIMIT 1;
                """,
                (item_row["sensor_id"],),
            ).fetchone()
            if latest_row:
                latest = dict(latest_row)
    return {
        "id": item_row["id"],
        "name": item_row["name"],
        "sensor_id": item_row["sensor_id"],
        "thresholds": loads_json(item_row["thresholds"]),
        "unit": item_row["unit"],
        "image_url": item_row["image_url"],
        "created_at": item_row["created_at"],
        "updated_at": item_row["updated_at"],
        "latest_reading": latest,
    }


@app.get("/api/v1/items/{item_id}/history")
def item_history(
    item_id: str,
    request: Request,
    range: Optional[str] = Query(default="7d"),
    limit: int = Query(default=500, ge=1),
) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    delta = _parse_range(range)
    since = (dt.datetime.now(dt.timezone.utc) - delta).isoformat()
    if limit > config.history_limit:
        limit = config.history_limit

    with get_db(config) as conn:
        item_row = conn.execute(
            "SELECT sensor_id FROM items WHERE id = ?;", (item_id,)
        ).fetchone()
        if not item_row:
            raise HTTPException(status_code=404, detail="Item not found")
        sensor_id = item_row["sensor_id"]
        if not sensor_id:
            return {"item_id": item_id, "readings": []}
        rows = conn.execute(
            """
            SELECT seq_id, ts, raw_value, normalized_value, state
            FROM readings
            WHERE sensor_id = ? AND ts >= ?
            ORDER BY ts ASC
            LIMIT ?;
            """,
            (sensor_id, since, limit),
        ).fetchall()
    return {"item_id": item_id, "readings": [dict(row) for row in rows]}


@app.post("/api/v1/items")
def create_item(payload: ItemCreate, request: Request) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    item_id = str(uuid.uuid4())
    now = _utc_now()
    with get_db(config) as conn:
        conn.execute(
            """
            INSERT INTO items (id, sensor_id, name, thresholds, unit, image_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                item_id,
                payload.sensor_id,
                payload.name,
                dumps_json(payload.thresholds),
                payload.unit,
                payload.image_url,
                now,
                now,
            ),
        )
    return {"id": item_id, "created_at": now}


@app.put("/api/v1/items/{item_id}")
def update_item(item_id: str, payload: ItemUpdate, request: Request) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    now = _utc_now()
    fields = []
    values: List[Any] = []

    for key, value in _model_to_dict(payload).items():
        if key == "thresholds":
            fields.append("thresholds = ?")
            values.append(dumps_json(value))
        else:
            fields.append(f"{key} = ?")
            values.append(value)
    if not fields:
        return {"id": item_id, "updated_at": now}

    fields.append("updated_at = ?")
    values.append(now)
    values.append(item_id)

    with get_db(config) as conn:
        cursor = conn.execute(
            f"UPDATE items SET {', '.join(fields)} WHERE id = ?;",
            values,
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    return {"id": item_id, "updated_at": now}


@app.post("/api/v1/items/{item_id}/thresholds")
def update_thresholds(
    item_id: str, payload: ThresholdsIn, request: Request
) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    now = _utc_now()
    with get_db(config) as conn:
        cursor = conn.execute(
            """
            UPDATE items
            SET thresholds = ?, updated_at = ?
            WHERE id = ?;
            """,
            (dumps_json(_model_to_dict(payload)), now, item_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item_id, "updated_at": now}


@app.get("/api/v1/alerts")
def list_alerts(
    request: Request, status: str = Query(default="active")
) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    with get_db(config) as conn:
        rows = conn.execute(
            """
            SELECT alerts.id, alerts.item_id, alerts.sensor_id, alerts.type, alerts.status,
                   alerts.message, alerts.created_at, alerts.resolved_at, items.name
            FROM alerts
            LEFT JOIN items ON alerts.item_id = items.id
            WHERE alerts.status = ?
            ORDER BY alerts.created_at DESC;
            """,
            (status,),
        ).fetchall()
    return {"alerts": [dict(row) for row in rows]}


@app.post("/api/v1/alerts/{alert_id}/ack")
def ack_alert(alert_id: int, request: Request) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    now = _utc_now()
    with get_db(config) as conn:
        cursor = conn.execute(
            """
            UPDATE alerts
            SET status = 'acknowledged', resolved_at = ?
            WHERE id = ? AND status = 'active';
            """,
            (now, alert_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
    _broadcast(
        request,
        {"type": "alert_acknowledged", "alert_id": alert_id, "acknowledged_at": now},
    )
    return {"id": alert_id, "status": "acknowledged", "acknowledged_at": now}


@app.get("/api/v1/devices")
def list_devices(request: Request) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    with get_db(config) as conn:
        rows = conn.execute(
            "SELECT id, name, location, firmware, last_seen FROM devices ORDER BY id;"
        ).fetchall()
    return {"devices": [dict(row) for row in rows]}


@app.get("/api/v1/sensors")
def list_sensors(request: Request) -> Dict[str, Any]:
    require_ui_auth(request)
    config: AppConfig = request.app.state.config
    with get_db(config) as conn:
        rows = conn.execute(
            """
            SELECT id, device_id, type, thresholds, state_map, last_state, last_value, last_update
            FROM sensors
            ORDER BY id;
            """
        ).fetchall()
    sensors = []
    for row in rows:
        sensors.append(
            {
                "id": row["id"],
                "device_id": row["device_id"],
                "type": row["type"],
                "thresholds": loads_json(row["thresholds"]),
                "state_map": loads_json(row["state_map"]),
                "last_state": row["last_state"],
                "last_value": row["last_value"],
                "last_update": row["last_update"],
            }
        )
    return {"sensors": sensors}


@app.get("/api/v1/stream")
async def stream(request: Request) -> StreamingResponse:
    require_ui_auth(request)
    queue = await request.app.state.events.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                payload = json.dumps(event, ensure_ascii=True)
                yield f"data: {payload}\n\n"
        finally:
            await request.app.state.events.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
