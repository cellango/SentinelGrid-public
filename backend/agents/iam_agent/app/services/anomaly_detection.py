"""
Anomaly Detection Service for IAM.

Detects suspicious authentication and access patterns with lightweight rules:
- Impossible travel (geo velocity)
- Failed login burst
- New device/IP seen for a user
"""

import ipaddress
import logging
import math
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.services.anomaly_store import AnomalyStore

logger = logging.getLogger(__name__)


class AnomalyDetectionService:
    """Service for detecting and persisting security anomalies."""

    def __init__(self, store: Optional[AnomalyStore] = None):
        self.store = store or AnomalyStore()
        self.thresholds = {
            "failed_burst_count": 5,
            "failed_burst_minutes": 15,
            "new_device_lookback_days": 30,
            "impossible_travel_speed_kmh": 900,  # commercial jet upper bound
            "impossible_travel_min_distance_km": 500,
        }

    async def detect_anomalies(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        time_window_hours: int = 24,
    ) -> List[Dict]:
        """
        Detect security anomalies for a tenant and persist them.

        Returns newly inserted/updated anomalies.
        """
        if not self.store.available:
            logger.warning("DB unavailable, skipping anomaly detection")
            return []

        window_start = datetime.utcnow() - timedelta(hours=time_window_hours)
        baseline_start = datetime.utcnow() - timedelta(days=self.thresholds["new_device_lookback_days"])

        events = self.store.fetch_auth_events(tenant_id=tenant_id, since=baseline_start, user_id=user_id)
        if not events:
            return []

        grouped: Dict[str, List[Dict]] = defaultdict(list)
        for event in events:
            uid = event.get("user_id")
            if not uid:
                continue
            grouped[uid].append(self._normalize_event(event))

        all_anomalies: List[Dict] = []
        for uid, user_events in grouped.items():
            user_anomalies = self._analyze_user_events(
                tenant_id=tenant_id,
                user_id=uid,
                events=user_events,
                window_start=window_start,
            )
            for anomaly in user_anomalies:
                anomaly["tenant_id"] = tenant_id
                anomaly["user_id"] = uid
            all_anomalies.extend(user_anomalies)

        stored = self.store.upsert_anomalies(all_anomalies, window_start=window_start)
        return stored

    # ------------------------------------------------------------------ #
    # Core detection logic (pure functions, easy to unit test)
    # ------------------------------------------------------------------ #

    def _analyze_user_events(
        self,
        tenant_id: str,
        user_id: str,
        events: List[Dict],
        window_start: datetime,
    ) -> List[Dict]:
        """Run detectors on a user's events."""
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: e["timestamp"])
        recent_events = [e for e in sorted_events if e["timestamp"] >= window_start]
        if not recent_events:
            return []

        known_fingerprints = {
            self._fingerprint(e) for e in sorted_events if e["timestamp"] < window_start and e.get("success")
        }

        anomalies: List[Dict] = []
        anomalies.extend(self._detect_impossible_travel(recent_events))
        anomalies.extend(self._detect_failed_auth_spike(recent_events, window_start))
        anomalies.extend(self._detect_new_device_or_ip(recent_events, known_fingerprints))

        for anomaly in anomalies:
            anomaly.setdefault("status", "open")
            anomaly.setdefault("detected_at", anomaly.get("detected_at") or datetime.utcnow())
            anomaly.setdefault("id", uuid.uuid4())

        return anomalies

    def _detect_impossible_travel(self, events: List[Dict]) -> List[Dict]:
        """Detect impossible travel based on geo velocity between successful logins."""
        successes = [e for e in events if e.get("success")]
        if len(successes) < 2:
            return []

        anomalies: List[Dict] = []
        prev = None
        for event in successes:
            if not prev:
                prev = event
                continue
            prev_loc = prev.get("geo")
            curr_loc = event.get("geo")
            if not prev_loc or not curr_loc:
                prev = event
                continue

            distance = self._distance_km(prev_loc, curr_loc)
            if distance is None or distance < self.thresholds["impossible_travel_min_distance_km"]:
                prev = event
                continue

            hours = max((event["timestamp"] - prev["timestamp"]).total_seconds() / 3600, 0.001)
            speed = distance / hours
            if speed > self.thresholds["impossible_travel_speed_kmh"]:
                anomalies.append(
                    {
                        "anomaly_type": "impossible_travel",
                        "severity": "high",
                        "title": "Impossible travel detected",
                        "description": (
                            f"Login jumped from {prev_loc.get('city') or prev_loc.get('country') or 'unknown'} "
                            f"to {curr_loc.get('city') or curr_loc.get('country') or 'unknown'} in "
                            f"{hours:.2f}h (≈{distance:.0f} km)"
                        ),
                        "risk_score": min(100.0, 70.0 + (speed / self.thresholds["impossible_travel_speed_kmh"]) * 20),
                        "metadata": {
                            "from": prev_loc,
                            "to": curr_loc,
                            "distance_km": distance,
                            "speed_kmh": speed,
                            "previous_timestamp": prev["timestamp"].isoformat(),
                            "current_timestamp": event["timestamp"].isoformat(),
                        },
                        "detected_at": event["timestamp"],
                    }
                )
            prev = event

        return anomalies

    def _detect_failed_auth_spike(self, events: List[Dict], window_start: datetime) -> List[Dict]:
        """Detect bursts of failed authentication attempts."""
        failures = [e for e in events if e.get("success") is False]
        if len(failures) < self.thresholds["failed_burst_count"]:
            return []

        failures = sorted(failures, key=lambda e: e["timestamp"])
        window = timedelta(minutes=self.thresholds["failed_burst_minutes"])
        left = 0
        anomalies: List[Dict] = []

        for right, event in enumerate(failures):
            while failures[left]["timestamp"] < event["timestamp"] - window:
                left += 1
            window_count = right - left + 1
            if window_count >= self.thresholds["failed_burst_count"]:
                anomalies.append(
                    {
                        "anomaly_type": "failed_logins",
                        "severity": "high" if window_count >= self.thresholds["failed_burst_count"] + 2 else "medium",
                        "title": "Failed login burst",
                        "description": (
                            f"{window_count} failed auth attempts within "
                            f"{self.thresholds['failed_burst_minutes']} minutes"
                        ),
                        "risk_score": min(100.0, 50.0 + (window_count - self.thresholds["failed_burst_count"]) * 10),
                        "metadata": {
                            "count": window_count,
                            "window_minutes": self.thresholds["failed_burst_minutes"],
                            "first_failure": failures[left]["timestamp"].isoformat(),
                            "last_failure": event["timestamp"].isoformat(),
                            "ip_addresses": list({f.get("ip_address") for f in failures[left:right + 1] if f.get("ip_address")}),
                        },
                        "detected_at": event["timestamp"],
                    }
                )
                break  # one anomaly per burst

        return anomalies

    def _detect_new_device_or_ip(
        self,
        events: List[Dict],
        known_fingerprints: set,
    ) -> List[Dict]:
        """Detect first-time devices/IPs for the user."""
        anomalies: List[Dict] = []
        for event in events:
            if not event.get("success"):
                continue
            fingerprint = self._fingerprint(event)
            if not fingerprint or fingerprint in known_fingerprints:
                continue

            anomalies.append(
                {
                    "anomaly_type": "new_device_or_ip",
                    "severity": "medium",
                    "title": "New device or IP observed",
                    "description": "Login from an unseen device/IP for this user",
                    "risk_score": 55.0,
                    "metadata": {
                        "ip_address": event.get("ip_address"),
                        "user_agent": event.get("user_agent"),
                        "device_id": event.get("device_id"),
                        "timestamp": event["timestamp"].isoformat(),
                    },
                    "detected_at": event["timestamp"],
                }
            )
            known_fingerprints.add(fingerprint)

        return anomalies

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def detect_access_pattern_anomalies(
        self,
        user_id: str,
        access_history: List[Dict],
        tenant_id: Optional[str] = None,
        time_window_hours: int = 24,
    ) -> List[Dict]:
        """
        Backwards-compatible adapter used by AI features endpoints.
        Accepts pre-loaded access history and reuses the standard detectors.
        """
        window_start = datetime.utcnow() - timedelta(hours=time_window_hours)
        events = []
        for record in access_history:
            events.append(
                {
                    "user_id": user_id,
                    "timestamp": record.get("timestamp", datetime.utcnow()),
                    "success": record.get("success", True),
                    "ip_address": record.get("ip") or record.get("ip_address"),
                    "user_agent": record.get("user_agent"),
                    "device_id": record.get("device_id"),
                    "geo": record.get("geo") or record.get("location"),
                    "metadata": record,
                }
            )
        return self._analyze_user_events(
            tenant_id=tenant_id or "",
            user_id=user_id,
            events=events,
            window_start=window_start,
        )

    def _normalize_event(self, raw: Dict) -> Dict:
        """Normalize DB row into a consistent event shape."""
        metadata = raw.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        timestamp = raw.get("occurred_at") or raw.get("created_at") or raw.get("timestamp") or datetime.utcnow()
        success = raw.get("success")
        action = (raw.get("action") or "").lower()
        if success is None:
            success = not ("fail" in action)

        geo = self._extract_geo(metadata)
        device_id = metadata.get("device_id") or metadata.get("deviceId")

        return {
            "user_id": raw.get("user_id"),
            "timestamp": timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(str(timestamp)),
            "ip_address": raw.get("ip_address"),
            "user_agent": raw.get("user_agent"),
            "metadata": metadata,
            "success": bool(success),
            "action": action,
            "geo": geo,
            "device_id": device_id,
        }

    @staticmethod
    def _extract_geo(metadata: Dict) -> Optional[Dict]:
        """Extract geolocation details if present."""
        geo = metadata.get("geo") or metadata.get("location")
        if isinstance(geo, dict):
            lat = geo.get("lat") or geo.get("latitude")
            lon = geo.get("lon") or geo.get("lng") or geo.get("longitude")
            if lat is not None and lon is not None:
                try:
                    return {
                        "lat": float(lat),
                        "lon": float(lon),
                        "country": geo.get("country"),
                        "city": geo.get("city"),
                    }
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _fingerprint(event: Dict) -> Optional[str]:
        """Create a stable fingerprint for a device/IP combo."""
        ip = event.get("ip_address")
        ua = event.get("user_agent")
        device_id = event.get("device_id")

        try:
            ip_norm = str(ipaddress.ip_address(ip)) if ip else None
        except ValueError:
            ip_norm = ip

        if device_id:
            return f"device:{device_id}"
        if ip_norm and ua:
            return f"{ip_norm}:{ua[:120]}"
        if ip_norm:
            return f"{ip_norm}"
        if ua:
            return f"ua:{ua[:120]}"
        return None

    @staticmethod
    def _distance_km(a: Dict, b: Dict) -> Optional[float]:
        """Haversine distance in kilometers."""
        if "lat" not in a or "lon" not in a or "lat" not in b or "lon" not in b:
            return None
        try:
            lat1, lon1 = math.radians(float(a["lat"])), math.radians(float(a["lon"]))
            lat2, lon2 = math.radians(float(b["lat"])), math.radians(float(b["lon"]))
        except (TypeError, ValueError):
            return None

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        r = 6371.0  # Earth radius in km
        h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * r * math.asin(min(1, math.sqrt(h)))
