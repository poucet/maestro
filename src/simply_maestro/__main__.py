"""Main entry point for Simply Maestro."""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from simply_maestro.mcp.server import start_mcp_server


def main() -> None:
    """Start the supervisor process."""
    # Load environment variables from .env file
    load_dotenv()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Simply Maestro process")
    
    try:
        start_mcp_server()
    except KeyboardInterrupt:
        logger.info("Simply Maestro process stopped by user")
    except Exception as e:
        logger.error(f"Error in Simply Maestro process: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
