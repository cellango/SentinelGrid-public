"""TheHive service for observables and analyzers."""

import logging
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class TheHiveService:
    """Service for interacting with TheHive API."""

    def __init__(self):
        self.base_url = settings.THEHIVE_URL
        self.api_key = settings.THEHIVE_API_KEY
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def create_observable(
        self,
        data_type: str,
        data: str,
        tags: Optional[List[str]] = None,
        ioc: bool = False,
        sighted: bool = False,
        message: Optional[str] = None,
        case_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an observable in TheHive.
        
        Args:
            data_type: Type of observable (ip, domain, url, hash, etc.)
            data: The actual data (IP address, domain, etc.)
            tags: Optional tags
            ioc: Whether this is an IOC
            sighted: Whether this has been sighted
            message: Optional message
            case_id: Optional case ID to attach to
        
        Returns:
            Observable object from TheHive
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, returning mock observable")
            return {
                "id": "mock-observable-1",
                "dataType": data_type,
                "data": data,
                "tags": tags or [],
                "ioc": ioc,
                "sighted": sighted,
            }

        try:
            observable_data = {
                "dataType": data_type,
                "data": data,
                "tags": tags or [],
                "ioc": ioc,
                "sighted": sighted,
            }
            if message:
                observable_data["message"] = message

            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/observable"
                if case_id:
                    url = f"{self.base_url}/api/v1/case/{case_id}/observable"

                response = await client.post(url, json=observable_data, headers=self.headers)
                response.raise_for_status()
                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Failed to create observable in TheHive: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"TheHive API error: {e.response.status_code} - {e.response.text}")
            raise

    async def list_analyzers(self, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available analyzers in TheHive.
        
        Args:
            data_type: Optional filter by observable data type
        
        Returns:
            List of analyzer definitions
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, returning mock analyzers")
            return [
                {"id": "VirusTotal_V3_Get_Observable", "name": "VirusTotal", "dataTypes": ["hash", "ip", "domain"]},
                {"id": "AbuseIPDB_GetReputation", "name": "AbuseIPDB", "dataTypes": ["ip"]},
                {"id": "PassiveDNS", "name": "PassiveDNS", "dataTypes": ["domain", "ip"]},
                {"id": "Whois", "name": "Whois", "dataTypes": ["domain", "ip"]},
            ]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/analyzer"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                analyzers = response.json()

                # Filter by data type if specified
                if data_type:
                    analyzers = [
                        a for a in analyzers
                        if data_type in a.get("dataTypes", [])
                    ]

                return analyzers

        except httpx.RequestError as e:
            logger.error(f"Failed to list analyzers from TheHive: {e}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"TheHive API error: {e.response.status_code} - {e.response.text}")
            return []

    async def run_analyzer(
        self,
        analyzer_id: str,
        observable_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run an analyzer on an observable.
        
        Args:
            analyzer_id: TheHive analyzer ID
            observable_id: TheHive observable ID
            parameters: Optional analyzer parameters
        
        Returns:
            Analyzer job response with job_id
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, returning mock analyzer job")
            return {
                "id": "mock-job-1",
                "analyzerId": analyzer_id,
                "observableId": observable_id,
                "status": "Success",
                "report": {
                    "full": {"verdict": "malicious", "summary": "Mock analyzer result"}
                }
            }

        try:
            job_data = {
                "analyzerId": analyzer_id,
                "observableId": observable_id,
            }
            if parameters:
                job_data["parameters"] = parameters

            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/analyzer/{analyzer_id}/run"
                response = await client.post(url, json=job_data, headers=self.headers)
                response.raise_for_status()
                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Failed to run analyzer in TheHive: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"TheHive API error: {e.response.status_code} - {e.response.text}")
            raise

    async def get_analyzer_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get analyzer job status and results.
        
        Args:
            job_id: Analyzer job ID
        
        Returns:
            Job status and report
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, returning mock job status")
            return {
                "id": job_id,
                "status": "Success",
                "report": {
                    "full": {"verdict": "malicious", "summary": "Mock analyzer result"}
                }
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/job/{job_id}"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Failed to get analyzer job from TheHive: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"TheHive API error: {e.response.status_code} - {e.response.text}")
            raise

    async def get_observable(self, observable_id: str) -> Dict[str, Any]:
        """
        Get an observable by ID.
        
        Args:
            observable_id: TheHive observable ID
        
        Returns:
            Observable object
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, returning mock observable")
            return {
                "id": observable_id,
                "dataType": "ip",
                "data": "192.168.1.1",
                "tags": [],
                "ioc": False,
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/observable/{observable_id}"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Failed to get observable from TheHive: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"TheHive API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def create_case(
        self,
        title: str,
        description: Optional[str] = None,
        severity: Optional[int] = None,
        status: str = "Open",
        tags: Optional[List[str]] = None,
        tlp: Optional[int] = None,
        pap: Optional[int] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a case in TheHive.
        
        Args:
            title: Case title
            description: Case description
            severity: Severity level (1-4, where 4 is critical)
            status: Case status (Open, InProgress, Resolved, etc.)
            tags: Optional tags
            tlp: TLP level (0-3)
            pap: PAP level (0-3)
            custom_fields: Optional custom fields
        
        Returns:
            Created case object
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, returning mock case")
            return {
                "id": "mock-case-1",
                "title": title,
                "description": description,
                "severity": severity or 2,
                "status": status,
                "tags": tags or [],
            }

        try:
            case_data = {
                "title": title,
                "status": status,
            }
            
            if description:
                case_data["description"] = description
            
            if severity is not None:
                case_data["severity"] = severity
            
            if tags:
                case_data["tags"] = tags
            
            if tlp is not None:
                case_data["tlp"] = tlp
            
            if pap is not None:
                case_data["pap"] = pap
            
            if custom_fields:
                case_data["customFields"] = custom_fields

            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/case"
                response = await client.post(url, json=case_data, headers=self.headers)
                response.raise_for_status()
                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Failed to create case in TheHive: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"TheHive API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def get_case(self, case_id: str) -> Dict[str, Any]:
        """
        Get a case by ID.
        
        Args:
            case_id: TheHive case ID
        
        Returns:
            Case object
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, returning mock case")
            return {
                "id": case_id,
                "title": "Mock Case",
                "status": "Open",
                "severity": 2,
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/case/{case_id}"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Failed to get case from TheHive: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"TheHive API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def update_case(
        self,
        case_id: str,
        status: Optional[str] = None,
        severity: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a case in TheHive.
        
        Args:
            case_id: TheHive case ID
            status: New status
            severity: New severity
            title: New title
            description: New description
        
        Returns:
            Updated case object
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, returning mock case")
            return {"id": case_id, "status": status or "Open"}

        try:
            case_data = {}
            
            if status:
                case_data["status"] = status
            if severity is not None:
                case_data["severity"] = severity
            if title:
                case_data["title"] = title
            if description:
                case_data["description"] = description

            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/case/{case_id}"
                response = await client.patch(url, json=case_data, headers=self.headers)
                response.raise_for_status()
                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Failed to update case in TheHive: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"TheHive API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def create_task(
        self,
        case_id: str,
        title: str,
        description: Optional[str] = None,
        status: str = "Waiting",
        order: Optional[int] = None,
        group: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a task in a TheHive case.
        
        Args:
            case_id: TheHive case ID
            title: Task title
            description: Task description
            status: Task status (Waiting, InProgress, Completed, Cancel)
            order: Task order
            group: Task group
        
        Returns:
            Created task object
        """
        if not self.base_url:
            logger.warning("TheHive URL not configured, returning mock task")
            return {
                "id": "mock-task-1",
                "title": title,
                "status": status,
                "caseId": case_id,
            }

        try:
            task_data = {
                "title": title,
                "status": status,
            }
            
            if description:
                task_data["description"] = description
            if order is not None:
                task_data["order"] = order
            if group:
                task_data["group"] = group

            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/case/{case_id}/task"
                response = await client.post(url, json=task_data, headers=self.headers)
                response.raise_for_status()
                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Failed to create task in TheHive: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"TheHive API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def create_case_from_ticket(
        self,
        ticket_data: Dict[str, Any],
        observables: Optional[List[Dict[str, Any]]] = None,
        tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a TheHive case from a SentinelGrid ticket.
        
        Args:
            ticket_data: Ticket data dictionary
            observables: Optional list of observables to add
            tasks: Optional list of tasks to add
        
        Returns:
            Created case object
        """
        # Map ticket severity to TheHive severity (1-4)
        severity_map = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }
        severity = severity_map.get(ticket_data.get("severity", "medium"), 2)
        
        # Map ticket status to TheHive status
        status_map = {
            "open": "Open",
            "in_progress": "InProgress",
            "resolved": "Resolved",
            "closed": "Resolved",
        }
        status = status_map.get(ticket_data.get("status", "open"), "Open")
        
        # Build tags
        tags = []
        if ticket_data.get("category"):
            tags.append(ticket_data["category"])
        if ticket_data.get("tenant_id"):
            tags.append(f"tenant:{ticket_data['tenant_id']}")
        if ticket_data.get("cve_ids"):
            tags.extend([f"cve:{cve}" for cve in ticket_data["cve_ids"][:5]])  # Limit tags
        
        # Create case
        case = await self.create_case(
            title=ticket_data.get("title", "Security Incident"),
            description=ticket_data.get("description"),
            severity=severity,
            status=status,
            tags=tags,
        )
        
        case_id = case.get("id")
        
        # Add observables if provided
        if observables and case_id:
            for observable in observables:
                try:
                    await self.create_observable(
                        data_type=observable.get("data_type"),
                        data=observable.get("data"),
                        tags=observable.get("tags", []),
                        ioc=observable.get("ioc", False),
                        sighted=observable.get("sighted", False),
                        message=observable.get("message"),
                        case_id=case_id,
                    )
                except Exception as e:
                    logger.error(f"Failed to create observable: {e}")
        
        # Add tasks if provided
        if tasks and case_id:
            for task in tasks:
                try:
                    await self.create_task(
                        case_id=case_id,
                        title=task.get("title"),
                        description=task.get("description"),
                        status=task.get("status", "Waiting"),
                        order=task.get("order"),
                        group=task.get("group"),
                    )
                except Exception as e:
                    logger.error(f"Failed to create task: {e}")
        
        return case

