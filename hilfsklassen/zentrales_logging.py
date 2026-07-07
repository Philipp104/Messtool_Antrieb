import os
import json
import logging
import sys
import datetime
from logging.handlers import RotatingFileHandler
import warnings

DEV_MODE = 1
PROTOCOL_LOGGER_NAME = "user_protocol"
_session_end_logged = set()

AUTO_CLEAR_CHARS = 50_000  # Fehlerlog leeren nach dieser Zeichenzahl ohne ERROR/CRITICAL


class JsonFormatter(logging.Formatter):
    """Formatiert Log-Einträge als JSON Lines (ein JSON-Objekt pro Zeile)."""

    def format(self, record):
        obj = {
            "time":   datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level":  record.levelname,
            "thread": record.threadName,
            "logger": record.name,
            "file":   f"{record.filename}:{record.lineno}",
            "func":   record.funcName,
            "msg":    record.getMessage(),
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj, ensure_ascii=False)


class AutoClearFileHandler(logging.FileHandler):
    """
    Schreibt JSON-Log-Einträge in eine Datei.
    Wenn seit dem letzten ERROR/CRITICAL mehr als `clear_after_chars` Zeichen
    geschrieben wurden, wird die Datei geleert und das Logging startet neu.
    """

    def __init__(self, filename, clear_after_chars=AUTO_CLEAR_CHARS, encoding="utf-8"):
        super().__init__(filename, mode="a", encoding=encoding, delay=False)
        self._chars_since_last_error = 0
        self._clear_after_chars = clear_after_chars

    def emit(self, record):
        try:
            msg = self.format(record) + self.terminator

            if record.levelno >= logging.ERROR:
                # Fehler → Zähler zurücksetzen, Datei NICHT leeren
                self._chars_since_last_error = 0
            else:
                self._chars_since_last_error += len(msg)
                if self._chars_since_last_error >= self._clear_after_chars:
                    self._truncate_file()
                    self._chars_since_last_error = 0

            self.stream.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)

    def _truncate_file(self):
        self.stream.seek(0)
        self.stream.truncate()
        note = json.dumps({
            "time":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level": "INFO",
            "msg":   f"Log automatisch geleert nach {self._clear_after_chars} Zeichen ohne Fehler. Neues Logging beginnt.",
        }, ensure_ascii=False) + self.terminator
        self.stream.write(note)
        self.flush()


class StreamToLogger:

    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self._buffer = ""

    def write(self, message):
        if not message:
            return
        self._buffer += message
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self.logger.log(self.level, line)

    def flush(self):
        if self._buffer:
            self.logger.log(self.level, self._buffer)
            self._buffer = ""

    def isatty(self):
        return False


def _has_file_handler(logger, file_path):
    abs_path = os.path.abspath(file_path)
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == abs_path:
            return True
    return False


def _has_named_handler(logger, name):
    return any(getattr(handler, "name", None) == name for handler in logger.handlers)


def get_protocol_logger():
    return logging.getLogger(PROTOCOL_LOGGER_NAME)


def log_session_start(session_id, start_time, python_version, cwd, pid):
    app_logger = logging.getLogger(__name__)
    app_logger.info(
        "SESSION_START id=%s | %s | python=%s | cwd=%s | pid=%s",
        session_id, start_time, python_version, cwd, pid,
    )
    protocol_logger = get_protocol_logger()
    protocol_logger.info("SESSION_START id=%s | %s", session_id, start_time)


def log_session_end(session_id, end_time, reason="unknown"):
    if not session_id or session_id in _session_end_logged:
        return False
    _session_end_logged.add(session_id)
    app_logger = logging.getLogger(__name__)
    app_logger.info("SESSION_END id=%s | %s | reason=%s", session_id, end_time, reason)
    protocol_logger = get_protocol_logger()
    protocol_logger.info("SESSION_END id=%s | %s | reason=%s", session_id, end_time, reason)
    return True


def setup_logging(log_level=logging.INFO):

    if getattr(sys, 'frozen', False):
        project_root = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(base_dir, ".."))
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file      = os.path.join(log_dir, "messtool.log")
    protocol_file = os.path.join(log_dir, "user_protocol.log")

    json_formatter = JsonFormatter()

    # --- Haupt-Logger (messtool.log) mit Auto-Clear ---
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not _has_file_handler(root_logger, log_file):
        file_handler = AutoClearFileHandler(log_file, clear_after_chars=AUTO_CLEAR_CHARS)
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)

    # --- Protokoll-Logger (user_protocol.log) mit RotatingFileHandler ---
    protocol_logger = get_protocol_logger()
    protocol_logger.setLevel(logging.INFO)
    protocol_logger.propagate = False

    if not _has_file_handler(protocol_logger, protocol_file):
        protocol_handler = RotatingFileHandler(
            protocol_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
        )
        protocol_handler.setFormatter(json_formatter)
        protocol_handler.setLevel(logging.INFO)
        protocol_logger.addHandler(protocol_handler)

    # --- DEV: Fehler auch auf stderr ausgeben ---
    if DEV_MODE and not _has_named_handler(root_logger, "dev_console_error"):
        console_handler = logging.StreamHandler(stream=sys.stderr)
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(json_formatter)
        console_handler.name = "dev_console_error"
        root_logger.addHandler(console_handler)

    logging.captureWarnings(True)
    warnings.simplefilter("once")
    sys.stdout = StreamToLogger(logging.getLogger("stdout"), logging.INFO)
    sys.stderr = StreamToLogger(logging.getLogger("stderr"), logging.ERROR)
