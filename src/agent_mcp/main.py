"""
Main entry point for the MCP Agent application.
"""

import asyncio
import logging
from typing import Optional

from .agent import MCPAgent
from .config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main(config_path: Optional[str] = None) -> None:
    """
    Main entry point for the MCP Agent.
    
    Args:
        config_path: Optional path to configuration file
    """
    try:
        # Load configuration
        config = Config.load(config_path)
        
        # Create and start the agent
        agent = MCPAgent(config)
        await agent.start()
        
        # Keep the agent running
        await agent.run()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error running MCP Agent: {e}")
        raise
    finally:
        logger.info("MCP Agent shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())