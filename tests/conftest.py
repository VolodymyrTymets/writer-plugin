"""Shared setup for the plugin's own tests.

Hooks will be plain scripts run as `python3 bin/<name>.py`, so hook tests drive them the same way (a subprocess fed a
JSON payload on stdin). `bin/` goes on sys.path only so a test can import a helper directly.
"""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN / 'bin'))
