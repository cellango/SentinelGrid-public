"""
Active Directory Connector
Implements LDAP-based sync with Active Directory
"""

import logging
from typing import List, Dict, Any, Optional
import ldap3
from ldap3 import Server, Connection, ALL, SUBTREE

from app.services.connector_framework import BaseConnector, SyncDirection, SyncStatus

logger = logging.getLogger(__name__)


class ActiveDirectoryConnector(BaseConnector):
    """Connector for Active Directory via LDAP."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ldap_url = config.get("ldap_url")
        self.bind_dn = config.get("bind_dn")
        self.bind_password = config.get("bind_password")
        self.users_dn = config.get("users_dn")
        self.groups_dn = config.get("groups_dn", config.get("users_dn"))
        self.domain = config.get("domain")
        
        # AD-specific attributes
        self.username_attribute = config.get("username_attribute", "sAMAccountName")
        self.email_attribute = config.get("email_attribute", "mail")
        self.first_name_attribute = config.get("first_name_attribute", "givenName")
        self.last_name_attribute = config.get("last_name_attribute", "sn")
        
        self._connection = None
    
    def _get_connection(self) -> Connection:
        """Get or create LDAP connection."""
        if self._connection is None or not self._connection.bound:
            server = Server(self.ldap_url, get_info=ALL)
            self._connection = Connection(
                server,
                user=self.bind_dn,
                password=self.bind_password,
                auto_bind=True
            )
        return self._connection
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Active Directory."""
        try:
            conn = self._get_connection()
            if conn.bound:
                # Try a simple search to verify access
                conn.search(
                    self.users_dn,
                    '(objectClass=person)',
                    attributes=[self.username_attribute],
                    size_limit=1
                )
                return {
                    "status": "connected",
                    "message": "Successfully connected to Active Directory",
                    "server": self.ldap_url,
                    "domain": self.domain
                }
            else:
                return {
                    "status": "failed",
                    "error": "Could not bind to LDAP server"
                }
        except Exception as e:
            logger.error(f"Error testing AD connection: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def sync_users(
        self,
        direction: SyncDirection = SyncDirection.IMPORT,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sync users from Active Directory."""
        if direction != SyncDirection.IMPORT:
            return {
                "status": "skipped",
                "message": "AD connector currently supports import only"
            }
        
        try:
            conn = self._get_connection()
            
            # Build search filter
            search_filter = '(&(objectClass=user)(objectCategory=person))'
            if filters and filters.get("ou"):
                # Filter by organizational unit
                search_base = filters["ou"]
            else:
                search_base = self.users_dn
            
            # Attributes to retrieve
            attributes = [
                self.username_attribute,
                self.email_attribute,
                self.first_name_attribute,
                self.last_name_attribute,
                "displayName",
                "userPrincipalName",
                "memberOf",
                "userAccountControl",  # For account status
                "whenCreated",
                "whenChanged"
            ]
            
            # Perform search
            conn.search(
                search_base,
                search_filter,
                attributes=attributes,
                search_scope=SUBTREE
            )
            
            users = []
            for entry in conn.entries:
                try:
                    user = {
                        "username": str(entry[self.username_attribute][0]) if entry[self.username_attribute] else None,
                        "email": str(entry[self.email_attribute][0]) if entry[self.email_attribute] else None,
                        "first_name": str(entry[self.first_name_attribute][0]) if entry[self.first_name_attribute] else None,
                        "last_name": str(entry[self.last_name_attribute][0]) if entry[self.last_name_attribute] else None,
                        "display_name": str(entry["displayName"][0]) if entry["displayName"] else None,
                        "user_principal_name": str(entry["userPrincipalName"][0]) if entry["userPrincipalName"] else None,
                        "dn": str(entry.entry_dn),
                        "groups": [str(g) for g in entry["memberOf"]] if entry["memberOf"] else [],
                        "enabled": self._is_account_enabled(entry.get("userAccountControl", [None])[0]),
                        "created_at": str(entry["whenCreated"][0]) if entry["whenCreated"] else None,
                        "updated_at": str(entry["whenChanged"][0]) if entry["whenChanged"] else None
                    }
                    users.append(user)
                except Exception as e:
                    logger.warning(f"Error processing user entry: {e}")
                    continue
            
            return {
                "status": "success",
                "users_synced": len(users),
                "users": users,
                "direction": direction.value
            }
            
        except Exception as e:
            logger.error(f"Error syncing AD users: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "users_synced": 0
            }
    
    def sync_groups(
        self,
        direction: SyncDirection = SyncDirection.IMPORT,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sync groups from Active Directory."""
        if direction != SyncDirection.IMPORT:
            return {
                "status": "skipped",
                "message": "AD connector currently supports import only"
            }
        
        try:
            conn = self._get_connection()
            
            # Build search filter for groups
            search_filter = '(objectClass=group)'
            if filters and filters.get("group_type"):
                if filters["group_type"] == "security":
                    search_filter = f'(&{search_filter}(groupType:1.2.840.113556.1.4.803:=2147483648))'
                elif filters["group_type"] == "distribution":
                    search_filter = f'(&{search_filter}(!(groupType:1.2.840.113556.1.4.803:=2147483648)))'
            
            search_base = self.groups_dn
            
            attributes = [
                "cn",  # Common name
                "name",
                "description",
                "member",
                "memberOf",
                "groupType",
                "whenCreated",
                "whenChanged"
            ]
            
            conn.search(
                search_base,
                search_filter,
                attributes=attributes,
                search_scope=SUBTREE
            )
            
            groups = []
            for entry in conn.entries:
                try:
                    group = {
                        "name": str(entry["cn"][0]) if entry["cn"] else str(entry["name"][0]) if entry["name"] else None,
                        "description": str(entry["description"][0]) if entry["description"] else None,
                        "dn": str(entry.entry_dn),
                        "members": [str(m) for m in entry["member"]] if entry["member"] else [],
                        "parent_groups": [str(g) for g in entry["memberOf"]] if entry["memberOf"] else [],
                        "group_type": self._get_group_type(entry.get("groupType", [None])[0]),
                        "created_at": str(entry["whenCreated"][0]) if entry["whenCreated"] else None,
                        "updated_at": str(entry["whenChanged"][0]) if entry["whenChanged"] else None
                    }
                    groups.append(group)
                except Exception as e:
                    logger.warning(f"Error processing group entry: {e}")
                    continue
            
            return {
                "status": "success",
                "groups_synced": len(groups),
                "groups": groups,
                "direction": direction.value
            }
            
        except Exception as e:
            logger.error(f"Error syncing AD groups: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "groups_synced": 0
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get AD connector capabilities."""
        return {
            "user_sync": True,
            "group_sync": True,
            "attribute_mapping": True,
            "filtering": True,
            "incremental_sync": True,  # Via whenChanged attribute
            "real_time_sync": False,
            "password_sync": False  # AD passwords cannot be exported
        }
    
    def _is_account_enabled(self, user_account_control: Optional[int]) -> bool:
        """Check if AD account is enabled."""
        if user_account_control is None:
            return True
        
        # ACCOUNTDISABLE flag (0x0002)
        return (user_account_control & 2) == 0
    
    def _get_group_type(self, group_type: Optional[int]) -> str:
        """Get group type from AD groupType attribute."""
        if group_type is None:
            return "unknown"
        
        # Security group flag (0x80000000)
        if (group_type & 0x80000000) != 0:
            return "security"
        else:
            return "distribution"

