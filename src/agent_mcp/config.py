"""
Configuration management for the MCP Agent.
"""

import json
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """
    Configuration class for MCP Agent settings.
    """
    
    # Agent settings
    agent_name: str = "mcp-agent"
    log_level: str = "INFO"
    
    # Protocol settings
    protocol_version: str = "1.0"
    timeout: int = 30
    
    # Connection settings
    host: str = "localhost"
    port: int = 8080
    
    # Tool settings
    tools_enabled: bool = True
    tools_directory: Optional[str] = None
    
    # OAuth settings
    oauth_enabled: bool = False
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    oauth_redirect_uri: str = "http://localhost:8000/auth/callback"
    secret_key: Optional[str] = None
    api_keys: Optional[str] = None  # Comma-separated API keys
    
    # LangGraph settings
    langgraph_base_url: str = "http://localhost:2024"
    
    # Additional configuration
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        Load configuration from file or environment variables.
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            Configuration instance
        """
        config_data = {}
        
        # Load from file if provided
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        
        # Override with environment variables
        env_mapping = {
            "MCP_AGENT_NAME": "agent_name",
            "MCP_LOG_LEVEL": "log_level",
            "MCP_PROTOCOL_VERSION": "protocol_version",
            "MCP_TIMEOUT": "timeout",
            "MCP_HOST": "host",
            "MCP_PORT": "port",
            "MCP_TOOLS_ENABLED": "tools_enabled",
            "MCP_TOOLS_DIRECTORY": "tools_directory",
            "OAUTH_ENABLED": "oauth_enabled",
            "GOOGLE_CLIENT_ID": "google_client_id",
            "GOOGLE_CLIENT_SECRET": "google_client_secret",
            "OAUTH_REDIRECT_URI": "oauth_redirect_uri",
            "SECRET_KEY": "secret_key",
            "API_KEYS": "api_keys",
            "LANGGRAPH_BASE_URL": "langgraph_base_url",
        }
        
        for env_var, config_key in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert types as needed
                if config_key in ["timeout", "port"]:
                    config_data[config_key] = int(env_value)
                elif config_key in ["tools_enabled", "oauth_enabled"]:
                    config_data[config_key] = env_value.lower() == "true"
                else:
                    config_data[config_key] = env_value
        
        return cls(**config_data)
    
    def save(self, config_path: str) -> None:
        """
        Save configuration to file.
        
        Args:
            config_path: Path to save configuration file
        """
        config_dict = {
            "agent_name": self.agent_name,
            "log_level": self.log_level,
            "protocol_version": self.protocol_version,
            "timeout": self.timeout,
            "host": self.host,
            "port": self.port,
            "tools_enabled": self.tools_enabled,
            "tools_directory": self.tools_directory,
            "extra_config": self.extra_config,
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)