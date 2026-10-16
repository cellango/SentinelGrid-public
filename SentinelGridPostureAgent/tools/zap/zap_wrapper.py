"""OWASP ZAP API wrapper for web application security scanning."""

import asyncio
import httpx
import time
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


# ZAP Configuration
DEFAULT_ZAP_API_URL = "http://localhost:8080"
DEFAULT_ZAP_API_KEY = "changeme"


async def scan(
    url: str,
    scan_type: str = "full",
    auth_config: Optional[Dict[str, Any]] = None,
    scope_config: Optional[Dict[str, Any]] = None,
    zap_api_url: Optional[str] = None,
    zap_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run OWASP ZAP scan on a web application.
    
    Args:
        url: Target URL to scan
        scan_type: "quick" | "full" | "api"
        auth_config: Authentication configuration
        scope_config: Scope configuration (include/exclude patterns)
        zap_api_url: ZAP API URL
        zap_api_key: ZAP API key
    
    Returns:
        Dictionary with scan results
    """
    zap_api_url = zap_api_url or DEFAULT_ZAP_API_URL
    zap_api_key = zap_api_key or DEFAULT_ZAP_API_KEY
    
    logger.info(f"Running ZAP {scan_type} scan on {url}")
    
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=3600.0) as client:
            # 1. Spider the target
            logger.info("Starting ZAP spider...")
            spider_response = await client.get(
                f"{zap_api_url}/JSON/spider/action/scan",
                params={"url": url, "apikey": zap_api_key}
            )
            spider_data = spider_response.json()
            scan_id = spider_data.get("scan")
            
            # Wait for spider to complete
            if scan_id:
                await _wait_for_scan(client, zap_api_url, zap_api_key, "spider", scan_id)
            
            # 2. Active scan (if not quick scan)
            if scan_type in ["full", "api"]:
                logger.info("Starting ZAP active scan...")
                scan_response = await client.get(
                    f"{zap_api_url}/JSON/ascan/action/scan",
                    params={"url": url, "apikey": zap_api_key}
                )
                scan_data = scan_response.json()
                ascan_id = scan_data.get("scan")
                
                # Wait for active scan to complete
                if ascan_id:
                    await _wait_for_scan(client, zap_api_url, zap_api_key, "ascan", ascan_id)
            
            # 3. Get alerts
            logger.info("Retrieving ZAP alerts...")
            alerts_response = await client.get(
                f"{zap_api_url}/JSON/core/view/alerts",
                params={"baseurl": url, "apikey": zap_api_key}
            )
            alerts_data = alerts_response.json()
            alerts = alerts_data.get("alerts", [])
            
            # 4. Get URLs tested
            urls_response = await client.get(
                f"{zap_api_url}/JSON/core/view/urls",
                params={"baseurl": url, "apikey": zap_api_key}
            )
            urls_data = urls_response.json()
            urls_tested = len(urls_data.get("urls", []))
            
            duration = int(time.time() - start_time)
            
            return {
                "alerts": alerts,
                "urls_tested": urls_tested,
                "duration": duration,
                "zap_version": "2.14.0",  # TODO: Get actual version
                "scan_type": scan_type
            }
    
    except httpx.ConnectError:
        logger.error(f"Cannot connect to ZAP at {zap_api_url}")
        return {
            "alerts": [],
            "urls_tested": 0,
            "duration": 0,
            "zap_version": "unavailable",
            "scan_type": scan_type,
            "error": f"ZAP not available at {zap_api_url}"
        }
    
    except Exception as e:
        logger.error(f"ZAP scan failed: {str(e)}", exc_info=True)
        return {
            "alerts": [],
            "urls_tested": 0,
            "duration": int(time.time() - start_time),
            "zap_version": "error",
            "scan_type": scan_type,
            "error": str(e)
        }


async def _wait_for_scan(
    client: httpx.AsyncClient,
    zap_api_url: str,
    zap_api_key: str,
    scan_type: str,
    scan_id: str,
    max_wait: int = 3600
) -> None:
    """
    Wait for ZAP scan to complete.
    
    Args:
        client: HTTP client
        zap_api_url: ZAP API URL
        zap_api_key: ZAP API key
        scan_type: "spider" or "ascan"
        scan_id: Scan ID
        max_wait: Maximum wait time in seconds
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = await client.get(
                f"{zap_api_url}/JSON/{scan_type}/view/status",
                params={"scanId": scan_id, "apikey": zap_api_key}
            )
            data = response.json()
            progress = int(data.get("status", 0))
            
            if progress >= 100:
                logger.info(f"ZAP {scan_type} scan completed")
                return
            
            logger.debug(f"ZAP {scan_type} progress: {progress}%")
            await asyncio.sleep(5)
        
        except Exception as e:
            logger.warning(f"Error checking scan status: {str(e)}")
            await asyncio.sleep(5)
    
    logger.warning(f"ZAP {scan_type} scan timed out after {max_wait} seconds")


async def is_zap_available(
    zap_api_url: Optional[str] = None,
    zap_api_key: Optional[str] = None
) -> bool:
    """
    Check if ZAP is available and responsive.
    
    Args:
        zap_api_url: ZAP API URL
        zap_api_key: ZAP API key
    
    Returns:
        True if ZAP is available, False otherwise
    """
    zap_api_url = zap_api_url or DEFAULT_ZAP_API_URL
    zap_api_key = zap_api_key or DEFAULT_ZAP_API_KEY
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{zap_api_url}/JSON/core/view/version",
                params={"apikey": zap_api_key}
            )
            return response.status_code == 200
    except Exception:
        return False

