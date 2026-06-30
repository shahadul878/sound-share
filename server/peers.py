"""Connected listener registry for owner panel."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from aiortc import RTCPeerConnection


@dataclass
class PeerRecord:
    peer_id: str
    client_id: str
    device_name: str
    ip: str
    user_agent: str
    pc: RTCPeerConnection
    state: str = "connecting"
    connected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "client_id": self.client_id,
            "device_name": self.device_name,
            "ip": self.ip,
            "user_agent": self.user_agent,
            "state": self.state,
            "connected_at": self.connected_at,
            "connected_for_sec": max(0, int(time.time() - self.connected_at)),
        }


class PeerRegistry:
    def __init__(self) -> None:
        self._peers: dict[str, PeerRecord] = {}

    def register(
        self,
        pc: RTCPeerConnection,
        *,
        client_id: str,
        device_name: str,
        ip: str,
        user_agent: str,
    ) -> PeerRecord:
        peer_id = uuid.uuid4().hex[:12]
        record = PeerRecord(
            peer_id=peer_id,
            client_id=client_id or "unknown",
            device_name=device_name or "Unknown device",
            ip=ip or "unknown",
            user_agent=user_agent or "",
            pc=pc,
        )
        self._peers[peer_id] = record
        pc._soundshare_peer_id = peer_id  # type: ignore[attr-defined]
        return record

    def get(self, peer_id: str) -> PeerRecord | None:
        return self._peers.get(peer_id)

    def find_by_pc(self, pc: RTCPeerConnection) -> PeerRecord | None:
        peer_id = getattr(pc, "_soundshare_peer_id", None)
        if peer_id:
            return self._peers.get(peer_id)
        for record in self._peers.values():
            if record.pc is pc:
                return record
        return None

    def remove(self, peer_id: str) -> PeerRecord | None:
        return self._peers.pop(peer_id, None)

    def remove_pc(self, pc: RTCPeerConnection) -> PeerRecord | None:
        record = self.find_by_pc(pc)
        if record:
            return self.remove(record.peer_id)
        return None

    def update_state(self, pc: RTCPeerConnection, state: str) -> None:
        record = self.find_by_pc(pc)
        if record:
            record.state = state

    def list_peers(self) -> list[dict[str, Any]]:
        alive: list[dict[str, Any]] = []
        dead: list[str] = []
        for peer_id, record in self._peers.items():
            pc_state = record.pc.connectionState
            if pc_state in ("failed", "closed"):
                dead.append(peer_id)
                continue
            record.state = pc_state
            alive.append(record.to_dict())
        for peer_id in dead:
            self._peers.pop(peer_id, None)
        alive.sort(key=lambda x: x["connected_at"])
        return alive

    def connected_count(self) -> int:
        return sum(
            1
            for r in self._peers.values()
            if r.pc.connectionState == "connected"
        )

    def all_pcs(self) -> list[RTCPeerConnection]:
        return [r.pc for r in self._peers.values()]


peer_registry = PeerRegistry()
