"""
Messtool - Haupteinstiegspunkt
==============================
Startet die grafische Benutzeroberfläche des Messdaten-Analyse-Tools.
Dieses Tool ermöglicht das Importieren, Verarbeiten und Analysieren von
Messdaten aus verschiedenen Dateiformaten (Excel, CSV, DWS).
"""
    
import sys
import os
import logging
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Alle .pyc-Caches zentral in .pycache/ statt verstreut in __pycache__/-Ordnern
# neben jeder Datei ablegen (muss vor den Projekt-Imports gesetzt werden).
sys.pycache_prefix = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pycache")

from gui_manager import GuiManager
from hilfsklassen.zentrales_logging import setup_logging, log_session_start, log_session_end

def _install_exception_hooks():
    logger = logging.getLogger(__name__)

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            return
        logger.exception(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    def handle_thread_exception(args):
        logger.exception(
            "Unhandled Exceptions in Threads %s",
            args.thread.name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
        )

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception

def get_resource_path(relative_path):
    """
    Gibt den korrekten Pfad zu Ressourcen zurück.
    Funktioniert sowohl im Dev-Modus als auch im PyInstaller Executable.
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def main():
    setup_logging(logging.INFO)
    logger = logging.getLogger(__name__)

    # Windows-Taskleistensymbol: AppUserModelID vor dem Fenster setzen
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Messtool.Antrieb.App")
    except Exception as e:
        logger.debug("AppUserModelID konnte nicht gesetzt werden (kein Windows?): %s", e)

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    log_session_start(
        session_id=session_id,
        start_time=start_time,
        python_version=sys.version.split()[0],
        cwd=os.getcwd(),
        pid=os.getpid(),
    )

    _install_exception_hooks()
    try:
        gui = GuiManager(get_resource_path)
        gui.session_id = session_id
        gui.create_gui()
    except Exception as e:
        logger.exception("Fehler beim Starten vom GUI")
    finally:
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_session_end(session_id=session_id, end_time=end_time, reason="mainloop_exit")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.getLogger(__name__).critical("Unbehandelte Ausnahme: %s", e, exc_info=True)
        raise