"""Production entry point for DeskBridge CLI-Hub.

Serves the Flask registry using waitress (production WSGI server)
instead of Flask's built-in development server.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hub.app import app

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="127.0.0.1", port=5000)