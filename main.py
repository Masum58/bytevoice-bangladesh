"""Entrypoint for ByteVoice Bangladesh FastAPI server.

Allows running standard development commands:
    uvicorn main:app --reload --port 8000
    fastapi dev main.py
    python main.py
"""

import sys
from pathlib import Path

# Automatically inject 'src' into sys.path
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from bytevoice.api import create_app
from bytevoice.config import get_settings

app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("main:app", host="0.0.0.0", port=settings.api_port, reload=True)

