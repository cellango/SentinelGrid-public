"""ECS normalization service."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.models.event import RawEvent, ECSField

logger = logging.getLogger(__name__)


class ECSNormalizer:
    """Service for normalizing events to ECS (Elastic Common Schema)."""
    
    def normalize(self, raw_event: RawEvent, tenant_id: str) -> ECSField:
        """
        Normalize raw event to ECS format.
        
        Args:
            raw_event: Raw event from connector
            tenant_id: Tenant ID
        
        Returns:
            Normalized ECS fields
        """
        # Ensure timestamp is datetime object
        timestamp = raw_event.timestamp
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)
        elif isinstance(timestamp, datetime):
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            else:
                timestamp = timestamp.astimezone(timezone.utc)
        else:
            timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        ecs_data = {
            "@timestamp": timestamp,
            "tenant_id": tenant_id,
            "event_type": raw_event.event_type,
            "source": self._normalize_source(raw_event),
        }

        edr_source = self._resolve_edr_source(raw_event)
        if edr_source:
            ecs_data["edr_source"] = edr_source

        sidecar_enabled = self._resolve_sidecar_enabled(raw_event, default_if_edr=bool(edr_source))
        if sidecar_enabled is not None:
            ecs_data["sidecar_enabled"] = sidecar_enabled
        
        # Extract user information
        user_data = self._extract_user(raw_event.raw_data)
        if user_data:
            ecs_data["user"] = user_data
        
        # Extract host information
        host_data = self._extract_host(raw_event.raw_data)
        if host_data:
            ecs_data["host"] = host_data
        
        # Extract device information
        device_data = self._extract_device(raw_event.raw_data)
        if device_data:
            ecs_data["device"] = device_data
        
        # Extract network information
        network_data = self._extract_network(raw_event.raw_data)
        if network_data:
            ecs_data["network"] = network_data

        process_data = self._extract_process(raw_event.raw_data)
        if process_data:
            ecs_data["process"] = process_data

        file_data = self._extract_file(raw_event.raw_data)
        if file_data:
            ecs_data["file"] = file_data

        registry_data = self._extract_registry(raw_event.raw_data)
        if registry_data:
            ecs_data["registry"] = registry_data

        driver_data = self._extract_driver(raw_event.raw_data)
        if driver_data:
            ecs_data["driver"] = driver_data

        module_data = self._extract_module(raw_event.raw_data)
        if module_data:
            ecs_data["module"] = module_data

        sensor_data = self._extract_sensor(raw_event.raw_data)
        if sensor_data:
            ecs_data["sensor"] = sensor_data

        hunt_data = self._extract_hunt(raw_event.raw_data)
        if hunt_data:
            ecs_data["hunt"] = hunt_data

        task_data = self._extract_task(raw_event.raw_data)
        if task_data:
            ecs_data["task"] = task_data

        collection_data = self._extract_collection(raw_event.raw_data)
        if collection_data:
            ecs_data["collection"] = collection_data
        
        # Extract action and outcome
        action = self._extract_action(raw_event.raw_data)
        if action:
            ecs_data["action"] = action
        
        outcome = self._extract_outcome(raw_event.raw_data)
        if outcome:
            ecs_data["outcome"] = outcome
        
        # Store any additional details
        details = self._extract_details(raw_event.raw_data)
        if details:
            ecs_data["details"] = details
        
        return ECSField(**ecs_data)
    
    def _normalize_source(self, raw_event: RawEvent) -> Dict[str, Any]:
        """Normalize source information."""
        source_data = {
            "name": raw_event.source,
            "type": self._map_source_type(raw_event.source)
        }
        
        # Add source-specific fields
        raw_data = raw_event.raw_data
        
        # IP address (if present)
        if "ip" in raw_data or "source_ip" in raw_data or "ipAddress" in raw_data:
            ip = raw_data.get("ip") or raw_data.get("source_ip") or raw_data.get("ipAddress")
            if ip:
                source_data["ip"] = str(ip)
        
        # Port (if present)
        if "port" in raw_data or "source_port" in raw_data:
            port = raw_data.get("port") or raw_data.get("source_port")
            if port:
                source_data["port"] = int(port)
        
        return source_data
    
    def _map_source_type(self, source: str) -> str:
        """Map source name to ECS source type."""
        source_lower = source.lower()
        if "google" in source_lower or "workspace" in source_lower:
            return "identity_provider"
        elif "aws" in source_lower or "cloudtrail" in source_lower:
            return "cloud"
        elif "okta" in source_lower:
            return "identity_provider"
        elif "microsoft" in source_lower or "entra" in source_lower or "azure" in source_lower:
            return "identity_provider"
        else:
            return "unknown"

    def _resolve_edr_source(self, raw_event: RawEvent) -> Optional[str]:
        """Resolve and normalize edr_source (wazuh/openedr/velociraptor)."""
        candidates = []
        if raw_event.edr_source:
            candidates.append(raw_event.edr_source)
        if raw_event.metadata and isinstance(raw_event.metadata, dict):
            candidates.append(raw_event.metadata.get("edr_source"))

        raw_data = raw_event.raw_data or {}
        for key in ("edr_source", "edr.source", "edrSource"):
            if key in raw_data:
                candidates.append(raw_data.get(key))
        # Fallback: infer from source name
        candidates.append(raw_event.source)

        for candidate in candidates:
            normalized = self._canonicalize_edr_source(candidate)
            if normalized:
                return normalized
        return None

    def _canonicalize_edr_source(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        val = str(value).lower()
        if "velociraptor" in val:
            return "sentinelguard-velociraptor"
        if "openedr" in val or "open-edr" in val or "open edr" in val:
            return "sentinelguard-openedr"
        if "wazuh" in val:
            return "sentinelguard-wazuh"
        # Already canonical?
        if val in ("sentinelguard-wazuh", "sentinelguard-openedr", "sentinelguard-velociraptor"):
            return val
        return None

    def _resolve_sidecar_enabled(self, raw_event: RawEvent, default_if_edr: bool = False) -> Optional[bool]:
        """Resolve sidecar_enabled flag with tenant-aware defaults."""
        for candidate in (
            raw_event.sidecar_enabled,
            raw_event.metadata.get("sidecar_enabled") if isinstance(raw_event.metadata, dict) else None,
            raw_event.raw_data.get("sidecar_enabled") if isinstance(raw_event.raw_data, dict) else None,
            raw_event.raw_data.get("edr_sidecar_enabled") if isinstance(raw_event.raw_data, dict) else None,
        ):
            if isinstance(candidate, bool):
                return candidate
            if isinstance(candidate, str):
                lowered = candidate.lower()
                if lowered in ("true", "1", "yes"):
                    return True
                if lowered in ("false", "0", "no"):
                    return False
        return True if default_if_edr else None
    
    def _extract_user(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract user information from raw data."""
        user = {}
        
        # Common user fields
        if "user" in raw_data and isinstance(raw_data["user"], dict):
            user_data = raw_data["user"]
            if "email" in user_data:
                user["email"] = user_data["email"]
            if "id" in user_data:
                user["id"] = str(user_data["id"])
            if "name" in user_data:
                user["name"] = user_data["name"]
        else:
            # Try direct fields
            if "user_email" in raw_data or "email" in raw_data:
                user["email"] = raw_data.get("user_email") or raw_data.get("email")
            if "user_id" in raw_data:
                user["id"] = str(raw_data["user_id"])
            if "username" in raw_data:
                user["name"] = raw_data["username"]
        
        return user if user else None
    
    def _extract_host(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract host information from raw data."""
        host = {}
        
        if "hostname" in raw_data:
            host["hostname"] = raw_data["hostname"]
        if "host" in raw_data and isinstance(raw_data["host"], dict):
            host_data = raw_data["host"]
            if "hostname" in host_data:
                host["hostname"] = host_data["hostname"]
            if "ip" in host_data:
                host["ip"] = host_data["ip"]
        
        return host if host else None
    
    def _extract_device(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract device information from raw data."""
        device = {}
        
        if "device_id" in raw_data:
            device["id"] = str(raw_data["device_id"])
        if "device_type" in raw_data:
            device["type"] = raw_data["device_type"]
        if "user_agent" in raw_data or "userAgent" in raw_data:
            device["user_agent"] = raw_data.get("user_agent") or raw_data.get("userAgent")
        
        return device if device else None
    
    def _extract_network(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract network information from raw data."""
        network = {}
        
        # Source IP
        source_ip = raw_data.get("source_ip") or raw_data.get("sourceIP") or raw_data.get("ip")
        if source_ip:
            network["source"] = {"ip": str(source_ip)}
        
        # Destination IP
        dest_ip = raw_data.get("destination_ip") or raw_data.get("destinationIP")
        if dest_ip:
            network["destination"] = {"ip": str(dest_ip)}
        
        # Protocol
        if "protocol" in raw_data:
            network["protocol"] = raw_data["protocol"]
        
        return network if network else None

    def _extract_process(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract process information relevant to EDR."""
        process = {}
        raw_process = raw_data.get("process")
        if isinstance(raw_process, dict):
            process.update(raw_process)

        mappings = {
            "process_id": "pid",
            "pid": "pid",
            "ppid": "ppid",
            "parent_pid": "ppid",
            "process_name": "name",
            "image": "executable",
            "exe": "executable",
            "process_path": "executable",
            "command_line": "command_line",
            "cmd": "command_line",
        }
        for raw_key, target_key in mappings.items():
            if raw_key in raw_data and raw_data[raw_key] is not None:
                process[target_key] = raw_data[raw_key]

        hash_fields = {}
        for key in ("hash", "sha1", "sha256", "md5"):
            if raw_data.get(key):
                hash_fields[key] = raw_data[key]
        if hash_fields:
            process["hash"] = hash_fields

        return process if process else None

    def _extract_file(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract file operations for EDR telemetry."""
        file_info = {}
        raw_file = raw_data.get("file")
        if isinstance(raw_file, dict):
            file_info.update(raw_file)

        for raw_key, target_key in {
            "file_path": "path",
            "filepath": "path",
            "file": "path",
            "file_name": "name",
            "filename": "name",
            "file_hash": "hash",
            "sha256": "hash.sha256",
            "sha1": "hash.sha1",
            "md5": "hash.md5",
            "action": "action",
        }.items():
            if raw_key in raw_data and raw_data[raw_key] is not None:
                self._assign_nested(file_info, target_key, raw_data[raw_key])

        return file_info if file_info else None

    def _extract_registry(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract registry operation details."""
        registry = {}
        raw_registry = raw_data.get("registry")
        if isinstance(raw_registry, dict):
            registry.update(raw_registry)

        for raw_key, target_key in {
            "registry_key": "key",
            "registry_value": "value",
            "registry_operation": "operation",
            "hive": "hive",
        }.items():
            if raw_key in raw_data and raw_data[raw_key] is not None:
                registry[target_key] = raw_data[raw_key]

        return registry if registry else None

    def _extract_driver(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract driver or kernel module details."""
        driver = {}
        raw_driver = raw_data.get("driver")
        if isinstance(raw_driver, dict):
            driver.update(raw_driver)

        for raw_key, target_key in {
            "driver_name": "name",
            "driver_path": "path",
            "driver_hash": "hash",
            "kernel_module": "module",
        }.items():
            if raw_key in raw_data and raw_data[raw_key] is not None:
                driver[target_key] = raw_data[raw_key]

        return driver if driver else None

    def _extract_module(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract loaded module/dll information."""
        module = {}
        raw_module = raw_data.get("module")
        if isinstance(raw_module, dict):
            module.update(raw_module)

        if "dll" in raw_data and isinstance(raw_data.get("dll"), dict):
            module["dll"] = raw_data.get("dll")

        for raw_key, target_key in {
            "module_name": "name",
            "module_path": "path",
            "module_hash": "hash",
        }.items():
            if raw_key in raw_data and raw_data[raw_key] is not None:
                module[target_key] = raw_data[raw_key]

        return module if module else None

    def _extract_sensor(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract sensor/agent health signals."""
        sensor = {}
        for raw_key, target_key in {
            "sensor_status": "status",
            "sensor_health": "health",
            "sensor_version": "version",
            "last_checkin": "last_checkin",
            "uptime_seconds": "uptime_seconds",
        }.items():
            if raw_key in raw_data and raw_data[raw_key] is not None:
                sensor[target_key] = raw_data[raw_key]
        return sensor if sensor else None

    def _extract_hunt(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract hunt metadata (e.g., Velociraptor jobs)."""
        hunt = {}
        if isinstance(raw_data.get("hunt"), dict):
            hunt.update(raw_data.get("hunt"))
        for raw_key, target_key in {
            "hunt_id": "id",
            "hunt_name": "name",
            "artifact": "artifact",
        }.items():
            if raw_key in raw_data and raw_data[raw_key] is not None:
                hunt[target_key] = raw_data[raw_key]
        return hunt if hunt else None

    def _extract_task(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract task identifiers/results for collection jobs."""
        task = {}
        if isinstance(raw_data.get("task"), dict):
            task.update(raw_data.get("task"))
        for raw_key, target_key in {
            "task_id": "id",
            "task_name": "name",
            "task_status": "status",
        }.items():
            if raw_key in raw_data and raw_data[raw_key] is not None:
                task[target_key] = raw_data[raw_key]
        return task if task else None

    def _extract_collection(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract collection results metadata."""
        collection = {}
        if isinstance(raw_data.get("collection"), dict):
            collection.update(raw_data.get("collection"))
        for raw_key, target_key in {
            "collection_id": "id",
            "collection_status": "status",
            "collection_path": "path",
        }.items():
            if raw_key in raw_data and raw_data[raw_key] is not None:
                collection[target_key] = raw_data[raw_key]
        return collection if collection else None

    @staticmethod
    def _assign_nested(obj: Dict[str, Any], path: str, value: Any) -> None:
        """Assign a value into a nested dict using dot notation keys."""
        parts = path.split(".")
        current = obj
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    
    def _extract_action(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract action from raw data."""
        return (
            raw_data.get("action") or
            raw_data.get("eventAction") or
            raw_data.get("operation") or
            raw_data.get("event_type")
        )
    
    def _extract_outcome(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract outcome from raw data."""
        outcome = raw_data.get("outcome") or raw_data.get("status") or raw_data.get("result")
        if outcome:
            # Normalize to success/failure/unknown
            outcome_lower = str(outcome).lower()
            if "success" in outcome_lower or "ok" in outcome_lower or outcome_lower == "200":
                return "success"
            elif "fail" in outcome_lower or "error" in outcome_lower or outcome_lower in ["401", "403", "404", "500"]:
                return "failure"
        return None
    
    def _extract_details(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract additional details from raw data."""
        # Store important fields that don't fit in standard ECS structure
        details = {}
        
        # Common important fields
        for field in ["message", "description", "error", "reason", "resource", "service"]:
            if field in raw_data:
                details[field] = raw_data[field]
        
        return details if details else None
