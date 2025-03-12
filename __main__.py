"""Main entry point for the supervisor."""

import logging
import sys
from pathlib import Path

from supervisor.mcp.server import start_mcp_server


def main() -> None:
    """Start the supervisor process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting supervisor process")
    
    try:
        start_mcp_server()
    except KeyboardInterrupt:
        logger.info("Supervisor process stopped by user")
    except Exception as e:
        logger.error(f"Error in supervisor process: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
