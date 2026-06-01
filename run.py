"""
Entry point — run from the project root:

    python run.py
    # or
    uvicorn backend.main:app --host 0.0.0.0 --port 3721 --reload
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=3721,
        reload=True,     # watches backend/ and frontend/ for changes
    )
