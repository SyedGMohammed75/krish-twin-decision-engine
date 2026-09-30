import os
import sys

# Ensure krishi-twin-backend subfolder is prioritized in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "krishi-twin-backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Remove root path temporarily to prevent circular self-import of root main.py
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir in sys.path:
    sys.path.remove(root_dir)

import main as backend_module
app = backend_module.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
