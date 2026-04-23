import os
import uvicorn
from backend.api import app  # noqa: F401 — re-exported for uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info",
        reload=False,
    )
