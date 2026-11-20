"""CLI entrypoint to run the video pipeline worker."""

import asyncio
import sys

from app.workers.video_pipeline import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
