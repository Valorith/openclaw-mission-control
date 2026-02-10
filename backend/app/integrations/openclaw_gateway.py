"""OpenClaw gateway client helpers for websocket RPC calls."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse
from uuid import uuid4

import websockets
from websockets.exceptions import WebSocketException

from app.integrations.openclaw_gateway_protocol import PROTOCOL_VERSION


class OpenClawGatewayError(RuntimeError):
    """Raised when OpenClaw gateway calls fail."""


@dataclass
class OpenClawResponse:
    """Container for raw OpenClaw payloads."""

    payload: Any


@dataclass(frozen=True)
class GatewayConfig:
    """Connection configuration for the OpenClaw gateway."""

    url: str
    token: str | None = None


def _build_gateway_url(config: GatewayConfig) -> str:
    base_url: str = (config.url or "").strip()
    if not base_url:
        message = "Gateway URL is not configured for this board."
        raise OpenClawGatewayError(message)
    token = config.token
    if not token:
        return base_url
    parsed = urlparse(base_url)
    query = urlencode({"token": token})
    return str(urlunparse(parsed._replace(query=query)))


async def _await_response(
    ws: websockets.ClientConnection,
    request_id: str,
) -> object:
    while True:
        raw = await ws.recv()
        data = json.loads(raw)

        if data.get("type") == "res" and data.get("id") == request_id:
            ok = data.get("ok")
            if ok is not None and not ok:
                error = data.get("error", {}).get("message", "Gateway error")
                raise OpenClawGatewayError(error)
            return data.get("payload")

        if data.get("id") == request_id:
            if data.get("error"):
                message = data["error"].get("message", "Gateway error")
                raise OpenClawGatewayError(message)
            return data.get("result")


async def _send_request(
    ws: websockets.ClientConnection,
    method: str,
    params: dict[str, Any] | None,
) -> object:
    request_id = str(uuid4())
    message = {
        "type": "req",
        "id": request_id,
        "method": method,
        "params": params or {},
    }
    await ws.send(json.dumps(message))
    return await _await_response(ws, request_id)


def _build_connect_params(config: GatewayConfig) -> dict[str, Any]:
    params: dict[str, Any] = {
        "minProtocol": PROTOCOL_VERSION,
        "maxProtocol": PROTOCOL_VERSION,
        "client": {
            "id": "gateway-client",
            "version": "1.0.0",
            "platform": "web",
            "mode": "ui",
        },
    }
    if config.token:
        params["auth"] = {"token": config.token}
    return params


async def _ensure_connected(
    ws: websockets.ClientConnection,
    first_message: str | bytes | None,
    config: GatewayConfig,
) -> None:
    if first_message:
        if isinstance(first_message, bytes):
            first_message = first_message.decode("utf-8")
        data = json.loads(first_message)
        if data.get("type") != "event" or data.get("event") != "connect.challenge":
            pass
    connect_id = str(uuid4())
    response = {
        "type": "req",
        "id": connect_id,
        "method": "connect",
        "params": _build_connect_params(config),
    }
    await ws.send(json.dumps(response))
    await _await_response(ws, connect_id)


async def openclaw_call(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    config: GatewayConfig,
) -> object:
    """Call a gateway RPC method and return the result payload."""
    gateway_url = _build_gateway_url(config)
    try:
        async with websockets.connect(gateway_url, ping_interval=None) as ws:
            first_message = None
            try:
                first_message = await asyncio.wait_for(ws.recv(), timeout=2)
            except TimeoutError:
                first_message = None
            await _ensure_connected(ws, first_message, config)
            return await _send_request(ws, method, params)
    except OpenClawGatewayError:
        raise
    except (
        TimeoutError,
        ConnectionError,
        OSError,
        ValueError,
        WebSocketException,
    ) as exc:  # pragma: no cover - network/protocol errors
        raise OpenClawGatewayError(str(exc)) from exc


async def send_message(
    message: str,
    *,
    session_key: str,
    config: GatewayConfig,
    deliver: bool = False,
) -> object:
    """Send a chat message to a session."""
    params: dict[str, Any] = {
        "sessionKey": session_key,
        "message": message,
        "deliver": deliver,
        "idempotencyKey": str(uuid4()),
    }
    return await openclaw_call("chat.send", params, config=config)


async def get_chat_history(
    session_key: str,
    config: GatewayConfig,
    limit: int | None = None,
) -> object:
    """Fetch chat history for a session."""
    params: dict[str, Any] = {"sessionKey": session_key}
    if limit is not None:
        params["limit"] = limit
    return await openclaw_call("chat.history", params, config=config)


async def delete_session(session_key: str, *, config: GatewayConfig) -> object:
    """Delete a session by key."""
    return await openclaw_call("sessions.delete", {"key": session_key}, config=config)


async def ensure_session(
    session_key: str,
    *,
    config: GatewayConfig,
    label: str | None = None,
) -> object:
    """Ensure a session exists and optionally update its label."""
    params: dict[str, Any] = {"key": session_key}
    if label:
        params["label"] = label
    return await openclaw_call("sessions.patch", params, config=config)
