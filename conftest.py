"""Zentrale Pytest-Konfiguration.

pytest importiert conftest.py automatisch vor der Testsammlung - deshalb
muss die Umleitung hier (und nicht erst in den Testdateien) stehen, damit
.pyc-Caches auch bei `pytest`-Läufen zentral in .pycache/ landen statt
verstreut in __pycache__/ neben jeder Datei (wie main.py es für den
normalen App-Start bereits macht).
"""
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.pycache_prefix = os.path.join(_HERE, ".pycache")

# Henne-Ei-Problem: pytest importiert conftest.py selbst, BEVOR die obige
# Umleitung greifen kann - Python schreibt sein .pyc deshalb einmalig noch
# in den alten Standardort (__pycache__/ neben dieser Datei). Direkt danach
# selbst aufräumen, damit trotzdem kein Ordner liegen bleibt.
_stray_cache = os.path.join(_HERE, "__pycache__")
if os.path.isdir(_stray_cache):
    shutil.rmtree(_stray_cache, ignore_errors=True)
