"""
GRABIT Backend Entry Point
"""

import uvicorn
import logging
import asyncio
from api import app
from config import get_config, validate_startup

def main():
    """Main entry point for GRABIT backend."""
    try:
        # Validate configuration
        validate_startup()
        config = get_config()
        
        # Setup logging
        config.setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("Starting GRABIT backend server...")
        logger.info(f"Server will run on {config.HOST}:{config.PORT}")
        logger.info(f"Workers: {config.WORKERS}")
        logger.info(f"Debug mode: {config.DEBUG}")
        
        # Run server
        uvicorn.run(
            "api:app",
            host=config.HOST,
            port=config.PORT,
            workers=1 if config.DEBUG else config.WORKERS,
            reload=config.DEBUG,
            access_log=config.DEBUG,
            log_level=config.LOG_LEVEL.lower()
        )
        
    except Exception as e:
        print(f"Failed to start GRABIT backend: {e}")
        raise e


if __name__ == "__main__":
    main()