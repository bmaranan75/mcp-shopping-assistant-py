"""
OAuth Authentication for MCP Server.

Supports Google OAuth 2.0, Okta OAuth 2.0, and API key authentication.
"""

import os
from typing import Optional, Dict, Any
from authlib.integrations.starlette_client import OAuth
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
from itsdangerous import URLSafeTimedSerializer
import secrets


class OAuthConfig:
    """OAuth configuration settings."""
    
    def __init__(self):
        # OAuth provider selection
        self.oauth_provider = os.getenv("OAUTH_PROVIDER", "google").lower()
        
        # Google OAuth
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        # Okta OAuth
        self.okta_domain = os.getenv("OKTA_DOMAIN")
        self.okta_client_id = os.getenv("OKTA_CLIENT_ID")
        self.okta_client_secret = os.getenv("OKTA_CLIENT_SECRET")
        
        # Common OAuth settings
        self.oauth_redirect_uri = os.getenv(
            "OAUTH_REDIRECT_URI", 
            "http://localhost:8000/auth/callback"
        )
        self.secret_key = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
        self.api_keys = self._load_api_keys()
        self.auth_enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
        
    def _load_api_keys(self) -> set:
        """Load valid API keys from environment."""
        api_keys_str = os.getenv("API_KEYS", "")
        if api_keys_str:
            return set(key.strip() for key in api_keys_str.split(",") if key.strip())
        return set()
    
    def is_valid(self) -> bool:
        """Check if OAuth is properly configured."""
        if not self.auth_enabled:
            return True
        
        if self.oauth_provider == "google":
            return bool(self.google_client_id and self.google_client_secret)
        elif self.oauth_provider == "okta":
            return bool(self.okta_domain and self.okta_client_id and self.okta_client_secret)
        
        return False


class OAuthProvider:
    """OAuth provider for Google authentication."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self.oauth = OAuth()
        
        if config.google_client_id and config.google_client_secret:
            self.oauth.register(
                name='google',
                client_id=config.google_client_id,
                client_secret=config.google_client_secret,
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
    
    async def login(self, request: Request):
        """Initiate OAuth login flow."""
        redirect_uri = self.config.oauth_redirect_uri
        return await self.oauth.google.authorize_redirect(request, redirect_uri)
    
    async def callback(self, request: Request):
        """Handle OAuth callback."""
        try:
            token = await self.oauth.google.authorize_access_token(request)
            user_info = token.get('userinfo')
            
            if user_info:
                # Store user info in session
                request.session['user'] = {
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture'),
                    'authenticated': True
                }
                
                return JSONResponse({
                    'status': 'success',
                    'message': 'Authentication successful',
                    'user': {
                        'email': user_info.get('email'),
                        'name': user_info.get('name')
                    }
                })
            else:
                return JSONResponse(
                    {'status': 'error', 'message': 'Failed to get user info'},
                    status_code=400
                )
        except Exception as e:
            return JSONResponse(
                {'status': 'error', 'message': f'Authentication failed: {str(e)}'},
                status_code=400
            )
    
    async def logout(self, request: Request):
        """Handle logout."""
        request.session.clear()
        return JSONResponse({'status': 'success', 'message': 'Logged out successfully'})


class OktaOAuthProvider:
    """OAuth provider for Okta authentication."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self.oauth = OAuth()
        
        if config.okta_domain and config.okta_client_id and config.okta_client_secret:
            # Construct Okta server metadata URL
            server_metadata_url = f"https://{config.okta_domain}/.well-known/openid-configuration"
            
            self.oauth.register(
                name='okta',
                client_id=config.okta_client_id,
                client_secret=config.okta_client_secret,
                server_metadata_url=server_metadata_url,
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
    
    async def login(self, request: Request):
        """Initiate OAuth login flow."""
        redirect_uri = self.config.oauth_redirect_uri
        return await self.oauth.okta.authorize_redirect(request, redirect_uri)
    
    async def callback(self, request: Request):
        """Handle OAuth callback."""
        try:
            token = await self.oauth.okta.authorize_access_token(request)
            user_info = token.get('userinfo')
            
            if user_info:
                # Store user info in session
                request.session['user'] = {
                    'email': user_info.get('email'),
                    'name': user_info.get('name') or user_info.get('preferred_username'),
                    'sub': user_info.get('sub'),
                    'authenticated': True,
                    'provider': 'okta'
                }
                
                return JSONResponse({
                    'status': 'success',
                    'message': 'Authentication successful',
                    'user': {
                        'email': user_info.get('email'),
                        'name': user_info.get('name') or user_info.get('preferred_username')
                    }
                })
            else:
                return JSONResponse(
                    {'status': 'error', 'message': 'Failed to get user info'},
                    status_code=400
                )
        except Exception as e:
            return JSONResponse(
                {'status': 'error', 'message': f'Authentication failed: {str(e)}'},
                status_code=400
            )
    
    async def logout(self, request: Request):
        """Handle logout."""
        request.session.clear()
        return JSONResponse({'status': 'success', 'message': 'Logged out successfully'})


class APIKeyAuth:
    """Simple API key authentication."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate an API key."""
        if not self.config.api_keys:
            return False
        return api_key in self.config.api_keys


class AuthMiddleware:
    """Middleware to enforce authentication."""
    
    def __init__(self, app, config: OAuthConfig, api_key_auth: APIKeyAuth):
        self.app = app
        self.config = config
        self.api_key_auth = api_key_auth
        
        # Paths that don't require authentication
        self.public_paths = {
            '/health',
            '/auth/login',
            '/auth/callback',
            '/auth/logout',
            '/auth/status',
            '/favicon.ico'
        }
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Skip auth if disabled
        if not self.config.auth_enabled:
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        path = request.url.path
        
        # Allow public paths
        if path in self.public_paths or path.startswith('/auth/'):
            await self.app(scope, receive, send)
            return
        
        # Check for API key in header
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if api_key and self.api_key_auth.validate_api_key(api_key):
            # Valid API key
            print(f"[AUTH] Valid API key for {path}")
            await self.app(scope, receive, send)
            return
        
        # Check session for OAuth authentication
        # Only access session if SessionMiddleware is installed
        if "session" in scope:
            session = request.session
            user = session.get('user', {})
            
            print(f"[AUTH] Checking session for {path}: authenticated={user.get('authenticated')}, email={user.get('email')}")
            
            if user.get('authenticated'):
                # Valid OAuth session
                print(f"[AUTH] Valid OAuth session for {path}")
                await self.app(scope, receive, send)
                return
        else:
            print(f"[AUTH] No session in scope for {path}")
        
        # Unauthorized
        print(f"[AUTH] Unauthorized access to {path}")
        response = JSONResponse(
            {
                'status': 'error',
                'message': 'Authentication required',
                'hint': 'Provide X-API-Key header or authenticate via OAuth at /auth/login'
            },
            status_code=401
        )
        await response(scope, receive, send)


def create_auth_routes(oauth_provider) -> list:
    """Create authentication routes.
    
    Args:
        oauth_provider: Either OAuthProvider (Google) or OktaOAuthProvider (Okta)
    """
    
    async def login(request):
        return await oauth_provider.login(request)
    
    async def callback(request):
        return await oauth_provider.callback(request)
    
    async def logout(request):
        return await oauth_provider.logout(request)
    
    async def status(request):
        """Check authentication status."""
        user = {}
        if "session" in request.scope:
            user = request.session.get('user', {})
        
        if user.get('authenticated'):
            return JSONResponse({
                'authenticated': True,
                'provider': user.get('provider', 'google'),
                'user': {
                    'email': user.get('email'),
                    'name': user.get('name')
                }
            })
        else:
            return JSONResponse({
                'authenticated': False,
                'message': 'Not authenticated'
            })
    
    return [
        Route('/auth/login', login),
        Route('/auth/callback', callback),
        Route('/auth/logout', logout),
        Route('/auth/status', status),
    ]


def get_session_middleware(secret_key: str) -> Middleware:
    """Get session middleware."""
    return Middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie='mcp_session',
        max_age=86400,  # 24 hours
        https_only=False,  # Set to True in production with HTTPS
        same_site='lax',  # Allow cross-origin requests from same site
    )
