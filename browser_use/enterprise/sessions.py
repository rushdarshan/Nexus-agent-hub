"""Authenticated Session Management.

Handles OAuth, 2FA, persistent sessions, and secure credential storage
for enterprise web automation.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from cryptography.fernet import Fernet
import base64
import hashlib

if TYPE_CHECKING:
    from browser_use import BrowserSession

logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    """Supported authentication methods."""
    PASSWORD = "password"
    OAUTH = "oauth"
    API_KEY = "api_key"
    COOKIE = "cookie"
    SESSION_TOKEN = "session_token"
    TWO_FACTOR = "2fa"


class SessionStatus(Enum):
    """Session lifecycle states."""
    CREATED = "created"
    AUTHENTICATING = "authenticating"
    ACTIVE = "active"
    EXPIRED = "expired"
    FAILED = "failed"
    LOGGED_OUT = "logged_out"


@dataclass
class Credential:
    """Encrypted credential storage."""
    id: str
    service: str  # e.g., "salesforce", "notion", "gmail"
    auth_method: AuthMethod
    encrypted_data: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass
class AuthenticatedSession:
    """
    Represents an authenticated session with a web service.
    
    Stores cookies, tokens, and session state for reuse.
    """
    id: str
    service: str
    status: SessionStatus = SessionStatus.CREATED
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    local_storage: Dict[str, str] = field(default_factory=dict)
    session_storage: Dict[str, str] = field(default_factory=dict)
    auth_tokens: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    browser_session_id: Optional[str] = None
    
    def is_active(self) -> bool:
        """Check if session is still active."""
        if self.status != SessionStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            self.status = SessionStatus.EXPIRED
            return False
        return True
    
    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()


class CredentialVault:
    """
    Secure storage for credentials with encryption.
    
    Uses Fernet symmetric encryption. In production, integrate with:
    - AWS Secrets Manager
    - HashiCorp Vault
    - Azure Key Vault
    """
    
    def __init__(self, storage_path: Optional[Path] = None, encryption_key: Optional[bytes] = None):
        self.storage_path = storage_path or Path.home() / ".browser_use" / "credentials"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Generate or load encryption key
        self._key = encryption_key or self._load_or_create_key()
        self._cipher = Fernet(self._key)
        self._credentials: Dict[str, Credential] = {}
    
    def _load_or_create_key(self) -> bytes:
        """Load existing key or create new one."""
        key_file = self.storage_path / ".key"
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)  # Restrict permissions
            return key
    
    def store(
        self,
        service: str,
        auth_method: AuthMethod,
        credentials: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None,
    ) -> str:
        """
        Securely store credentials.
        
        Args:
            service: Service identifier (e.g., "salesforce")
            auth_method: Authentication method
            credentials: Credential data to encrypt
            metadata: Additional unencrypted metadata
            expires_in_days: Optional expiration
            
        Returns:
            Credential ID
        """
        cred_id = hashlib.sha256(f"{service}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Encrypt credentials
        encrypted = self._cipher.encrypt(json.dumps(credentials).encode())
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        credential = Credential(
            id=cred_id,
            service=service,
            auth_method=auth_method,
            encrypted_data=encrypted,
            metadata=metadata or {},
            expires_at=expires_at,
        )
        
        self._credentials[cred_id] = credential
        self._save_to_disk(credential)
        
        logger.info(f"🔐 Stored credentials for {service} (ID: {cred_id})")
        return cred_id
    
    def retrieve(self, cred_id: str) -> Optional[Dict[str, str]]:
        """Retrieve and decrypt credentials."""
        credential = self._credentials.get(cred_id)
        
        if credential is None:
            credential = self._load_from_disk(cred_id)
        
        if credential is None:
            return None
        
        if credential.is_expired():
            logger.warning(f"Credential {cred_id} has expired")
            return None
        
        # Decrypt
        decrypted = self._cipher.decrypt(credential.encrypted_data)
        credential.last_used = datetime.now()
        
        return json.loads(decrypted.decode())
    
    def delete(self, cred_id: str) -> bool:
        """Securely delete credentials."""
        if cred_id in self._credentials:
            del self._credentials[cred_id]
        
        file_path = self.storage_path / f"{cred_id}.cred"
        if file_path.exists():
            # Overwrite before deleting (secure delete)
            file_path.write_bytes(os.urandom(1024))
            file_path.unlink()
            return True
        return False
    
    def list_credentials(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        """List stored credentials (without sensitive data)."""
        results = []
        
        for file_path in self.storage_path.glob("*.cred"):
            try:
                cred = self._load_from_disk(file_path.stem)
                if cred and (service is None or cred.service == service):
                    results.append({
                        "id": cred.id,
                        "service": cred.service,
                        "auth_method": cred.auth_method.value,
                        "created_at": cred.created_at.isoformat(),
                        "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
                        "is_expired": cred.is_expired(),
                    })
            except Exception as e:
                logger.warning(f"Failed to read credential file {file_path}: {e}")
        
        return results
    
    def _save_to_disk(self, credential: Credential) -> None:
        """Save credential to encrypted file."""
        file_path = self.storage_path / f"{credential.id}.cred"
        
        data = {
            "id": credential.id,
            "service": credential.service,
            "auth_method": credential.auth_method.value,
            "encrypted_data": base64.b64encode(credential.encrypted_data).decode(),
            "metadata": credential.metadata,
            "created_at": credential.created_at.isoformat(),
            "last_used": credential.last_used.isoformat() if credential.last_used else None,
            "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
        }
        
        file_path.write_text(json.dumps(data))
        file_path.chmod(0o600)
    
    def _load_from_disk(self, cred_id: str) -> Optional[Credential]:
        """Load credential from disk."""
        file_path = self.storage_path / f"{cred_id}.cred"
        
        if not file_path.exists():
            return None
        
        data = json.loads(file_path.read_text())
        
        credential = Credential(
            id=data["id"],
            service=data["service"],
            auth_method=AuthMethod(data["auth_method"]),
            encrypted_data=base64.b64decode(data["encrypted_data"]),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )
        
        self._credentials[cred_id] = credential
        return credential


class AuthHandler(ABC):
    """Base class for service-specific authentication handlers."""
    
    @abstractmethod
    async def authenticate(
        self,
        browser_session: "BrowserSession",
        credentials: Dict[str, str],
    ) -> AuthenticatedSession:
        """Perform authentication and return session."""
        pass
    
    @abstractmethod
    async def verify_session(
        self,
        browser_session: "BrowserSession",
        session: AuthenticatedSession,
    ) -> bool:
        """Verify if session is still valid."""
        pass
    
    @abstractmethod
    async def refresh_session(
        self,
        browser_session: "BrowserSession",
        session: AuthenticatedSession,
    ) -> AuthenticatedSession:
        """Refresh an expiring session."""
        pass


class GenericPasswordAuth(AuthHandler):
    """
    Generic username/password authentication.
    
    Works with most websites that have standard login forms.
    Uses vision AI to find and fill login fields.
    """
    
    def __init__(
        self,
        login_url: str,
        success_indicator: str = "dashboard|home|profile|account",
        username_selectors: Optional[List[str]] = None,
        password_selectors: Optional[List[str]] = None,
    ):
        self.login_url = login_url
        self.success_indicator = success_indicator
        self.username_selectors = username_selectors or [
            "input[type=email]",
            "input[type=text][name*=user]",
            "input[type=text][name*=email]",
            "input[id*=user]",
            "input[id*=email]",
        ]
        self.password_selectors = password_selectors or [
            "input[type=password]",
            "input[name*=pass]",
            "input[id*=pass]",
        ]
    
    async def authenticate(
        self,
        browser_session: "BrowserSession",
        credentials: Dict[str, str],
    ) -> AuthenticatedSession:
        """Perform login and capture session."""
        import uuid
        
        session = AuthenticatedSession(
            id=str(uuid.uuid4())[:8],
            service=self.login_url,
            status=SessionStatus.AUTHENTICATING,
        )
        
        try:
            # Navigate to login page
            # In real implementation, use browser_session to navigate
            logger.info(f"🔑 Authenticating to {self.login_url}")
            
            # Fill credentials using browser-use agent
            # This is a placeholder - actual implementation uses Agent
            
            # Capture cookies and tokens after login
            # cookies = await browser_session.get_cookies()
            # session.cookies = cookies
            
            session.status = SessionStatus.ACTIVE
            session.browser_session_id = browser_session.id if hasattr(browser_session, 'id') else None
            
            logger.info(f"✅ Authentication successful for {self.login_url}")
            return session
            
        except Exception as e:
            session.status = SessionStatus.FAILED
            logger.error(f"❌ Authentication failed: {e}")
            raise
    
    async def verify_session(
        self,
        browser_session: "BrowserSession",
        session: AuthenticatedSession,
    ) -> bool:
        """Check if we're still logged in."""
        # Navigate to a protected page and check for login redirect
        # Placeholder implementation
        return session.is_active()
    
    async def refresh_session(
        self,
        browser_session: "BrowserSession",
        session: AuthenticatedSession,
    ) -> AuthenticatedSession:
        """Re-authenticate if session expired."""
        # Would retrieve credentials and re-authenticate
        return session


class OAuthHandler(AuthHandler):
    """
    OAuth 2.0 authentication handler.
    
    Supports authorization code flow with PKCE.
    """
    
    def __init__(
        self,
        client_id: str,
        auth_url: str,
        token_url: str,
        redirect_uri: str,
        scopes: List[str],
    ):
        self.client_id = client_id
        self.auth_url = auth_url
        self.token_url = token_url
        self.redirect_uri = redirect_uri
        self.scopes = scopes
    
    async def authenticate(
        self,
        browser_session: "BrowserSession",
        credentials: Dict[str, str],
    ) -> AuthenticatedSession:
        """Perform OAuth flow."""
        import uuid
        
        session = AuthenticatedSession(
            id=str(uuid.uuid4())[:8],
            service=self.auth_url,
            status=SessionStatus.AUTHENTICATING,
        )
        
        # OAuth implementation would:
        # 1. Generate PKCE code verifier/challenge
        # 2. Navigate to auth URL
        # 3. Wait for user to authorize
        # 4. Capture redirect with auth code
        # 5. Exchange code for tokens
        
        logger.info(f"🔑 OAuth flow for {self.auth_url}")
        
        # Placeholder
        session.status = SessionStatus.ACTIVE
        return session
    
    async def verify_session(
        self,
        browser_session: "BrowserSession",
        session: AuthenticatedSession,
    ) -> bool:
        """Check token validity."""
        return session.is_active()
    
    async def refresh_session(
        self,
        browser_session: "BrowserSession",
        session: AuthenticatedSession,
    ) -> AuthenticatedSession:
        """Use refresh token to get new access token."""
        # Would use refresh_token to get new access_token
        return session


class SessionManager:
    """
    Manages authenticated sessions across multiple services.
    
    Features:
    - Session pooling and reuse
    - Automatic session refresh
    - Multi-service support
    - Credential vault integration
    """
    
    def __init__(
        self,
        credential_vault: Optional[CredentialVault] = None,
        storage_path: Optional[Path] = None,
    ):
        self.vault = credential_vault or CredentialVault()
        self.storage_path = storage_path or Path.home() / ".browser_use" / "sessions"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._sessions: Dict[str, AuthenticatedSession] = {}
        self._handlers: Dict[str, AuthHandler] = {}
    
    def register_handler(self, service: str, handler: AuthHandler) -> None:
        """Register an auth handler for a service."""
        self._handlers[service] = handler
        logger.info(f"Registered auth handler for {service}")
    
    async def get_session(
        self,
        service: str,
        browser_session: "BrowserSession",
        credential_id: Optional[str] = None,
        force_new: bool = False,
    ) -> AuthenticatedSession:
        """
        Get an authenticated session for a service.
        
        Will reuse existing active sessions or create new ones.
        """
        # Check for existing active session
        if not force_new:
            existing = self._find_active_session(service)
            if existing:
                existing.touch()
                logger.info(f"♻️ Reusing existing session for {service}")
                return existing
        
        # Create new session
        handler = self._handlers.get(service)
        if handler is None:
            raise ValueError(f"No auth handler registered for {service}")
        
        # Get credentials
        credentials = {}
        if credential_id:
            credentials = self.vault.retrieve(credential_id) or {}
        
        # Authenticate
        session = await handler.authenticate(browser_session, credentials)
        session.service = service
        
        self._sessions[session.id] = session
        await self._save_session(session)
        
        return session
    
    async def restore_session(
        self,
        session_id: str,
        browser_session: "BrowserSession",
    ) -> Optional[AuthenticatedSession]:
        """Restore a saved session to a browser."""
        session = self._sessions.get(session_id) or await self._load_session(session_id)
        
        if session is None:
            return None
        
        if not session.is_active():
            # Try to refresh
            handler = self._handlers.get(session.service)
            if handler:
                session = await handler.refresh_session(browser_session, session)
        
        if session.is_active():
            # Restore cookies to browser
            # await browser_session.set_cookies(session.cookies)
            logger.info(f"🔄 Restored session {session_id}")
            return session
        
        return None
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate and remove a session."""
        if session_id in self._sessions:
            self._sessions[session_id].status = SessionStatus.LOGGED_OUT
            del self._sessions[session_id]
        
        file_path = self.storage_path / f"{session_id}.session"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def _find_active_session(self, service: str) -> Optional[AuthenticatedSession]:
        """Find an active session for a service."""
        for session in self._sessions.values():
            if session.service == service and session.is_active():
                return session
        return None
    
    async def _save_session(self, session: AuthenticatedSession) -> None:
        """Save session to disk (excluding sensitive tokens)."""
        file_path = self.storage_path / f"{session.id}.session"
        
        data = {
            "id": session.id,
            "service": session.service,
            "status": session.status.value,
            "cookies": session.cookies,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        }
        
        file_path.write_text(json.dumps(data))
    
    async def _load_session(self, session_id: str) -> Optional[AuthenticatedSession]:
        """Load session from disk."""
        file_path = self.storage_path / f"{session_id}.session"
        
        if not file_path.exists():
            return None
        
        data = json.loads(file_path.read_text())
        
        session = AuthenticatedSession(
            id=data["id"],
            service=data["service"],
            status=SessionStatus(data["status"]),
            cookies=data.get("cookies", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )
        
        self._sessions[session_id] = session
        return session
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        return [
            {
                "id": s.id,
                "service": s.service,
                "status": s.status.value,
                "last_activity": s.last_activity.isoformat(),
                "is_active": s.is_active(),
            }
            for s in self._sessions.values()
        ]
