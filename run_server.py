import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path("D:/ai-code-reviewer")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.config import HOST, PORT

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Starting AI Code Review and Bug Detection System")
    print(f"🌐 Dashboard URL: http://{HOST}:{PORT}")
    print(f"📂 Project Root:  {PROJECT_ROOT}")
    print("=" * 70)
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
