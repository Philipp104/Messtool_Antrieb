"""
Daten Validator - Eingabevalidierung
=====================================
Klasse für Validierung der Benutzereingaben:
Zeilen-/Spaltenbereich, Samplerate, DataFrame-Extraktion
und Konvertierung von Spaltennamen.
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
import logging
from collections import deque

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import pandas as pd

# ============================================================
#  IMPORTS – Eigene Klassen
# ============================================================
from konfiguration import Cfg
from gui_module import meldungen

# ============================================================
#  LOGGING
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
#  KLASSE
# ============================================================
class DatenValidator:
    """Klasse für Validierung und Verarbeitung mit DataFrame und Entry-Parametern"""

    def __init__(self):

        # --- Bereichs-Parameter ---
        self._start_row     = None
        self._end_row       = None
        self._start_col     = None
        self._end_col       = None
        self._samplerate_fs = Cfg.Defaults.SAMPLERATE

        # --- Datenstatus ---
        self.df           = None
        self.temp_df      = None
        self.headers      = []
        self.units        = []
        self.temp_headers = []
        self.temp_units   = []
        self.reset_active = False

        # Unterdrueckt den "wurde automatisch auf X begrenzt"-Hinweis in
        # _adjust_row_range/_adjust_col_range. Wird vom Aufrufer gesetzt, wenn der
        # Bereich ohnehin automatisch aus der Datei berechnet wurde (z.B. "Ganze
        # Datei verwenden") - eine Anpassung ist dort ein normaler, erwarteter
        # Rechenschritt und kein Hinweis auf eine zu grosse manuelle Eingabe.
        self.suppress_range_hints = False

        # Optionaler Dateiname, der Hinweis-Meldungen vorangestellt wird (siehe
        # _adjust_row_range/_adjust_col_range) - vom Mehrfachdatei-Import gesetzt
        # (mehrfachdatei_manager.py), damit bei mehreren Dateien klar ist, auf
        # welche Datei sich ein "wurde begrenzt"-Hinweis bezieht. Beim
        # Einzeldatei-Weg bleibt es None (dort gibt es ohnehin nur eine Datei).
        self.filename_context = None

    # --------------------------------------------------------
    #  PROPERTIES – Bereich
    # --------------------------------------------------------

    @property
    def start_row(self):
        return self._start_row

    @start_row.setter
    def start_row(self, value):
        if value < Cfg.Limits.MIN_ROW:
            raise ValueError(Cfg.Errors.VAL_NEGATIVE_ROW)
        if self._end_row is not None and value > self._end_row:
            raise ValueError(Cfg.Errors.VAL_ROW_ORDER)
        self._start_row = value

    @property
    def end_row(self):
        return self._end_row

    @end_row.setter
    def end_row(self, value):
        if value < Cfg.Limits.MIN_ROW:
            raise ValueError(Cfg.Errors.VAL_NEGATIVE_ROW)
        if self._start_row is not None and value < self._start_row:
            raise ValueError(Cfg.Errors.VAL_ROW_ORDER)
        self._end_row = value

    @property
    def start_col(self):
        return self._start_col

    @start_col.setter
    def start_col(self, value):
        if value < Cfg.Limits.MIN_COL:
            raise ValueError(Cfg.Errors.VAL_NEGATIVE_COL)
        if self._end_col is not None and value > self._end_col:
            raise ValueError(Cfg.Errors.VAL_COL_ORDER)
        self._start_col = value

    @property
    def end_col(self):
        return self._end_col

    @end_col.setter
    def end_col(self, value):
        if value < Cfg.Limits.MIN_COL:
            raise ValueError(Cfg.Errors.VAL_NEGATIVE_COL)
        if self._start_col is not None and value < self._start_col:
            raise ValueError(Cfg.Errors.VAL_COL_ORDER)
        self._end_col = value

    @property
    def samplerate_fs(self):
        return self._samplerate_fs

    @samplerate_fs.setter
    def samplerate_fs(self, value):
        if value <= Cfg.Limits.SAMPLE_RATE_MIN:
            raise ValueError(Cfg.Errors.VAL_INVALID_SAMPLERATE)
        if value > Cfg.Limits.SAMPLE_RATE_MAX:
            logger.warning("Samplerate > {0} - möglicherweise unrealistisch".format(Cfg.Limits.SAMPLE_RATE_MAX))
        self._samplerate_fs = value

    # --------------------------------------------------------
    #  PROPERTIES – Zustand (read-only)
    # --------------------------------------------------------

    @property
    def is_valid_range(self):
        """Prüft automatisch, ob alle Bereiche gültig sind."""
        return (
            self._start_row is not None and
            self._end_row   is not None and
            self._start_row < self._end_row and
            self._start_col is not None and
            self._end_col   is not None and
            self._start_col < self._end_col
        )

    @property
    def total_samples(self):
        """Berechnet Anzahl zu verarbeitender Samples."""
        if self.is_valid_range:
            return (self._end_row - self._start_row + 1) * (self._end_col - self._start_col + 1)
        return 0

    @property
    def processing_time_estimate(self):
        """Schätzt Verarbeitungszeit basierend auf Datenmenge."""
        samples = self.total_samples
        if samples > 0:
            return f"~{samples // Cfg.Limits.SAMPLES_PER_SECOND}s geschätzte Verarbeitungszeit"
        return Cfg.Status.VAL_NO_DATA

    @property
    def dataframe_type(self):
        """Erkennt automatisch den DataFrame-Typ."""
        if self.df is None:
            return Cfg.Export.PROCESS_FALLBACK
        elif hasattr(self.df.columns, 'levels') and len(self.df.columns.levels) == 2:
            return Cfg.Export.PROCESS_DWS
        else:
            return Cfg.Export.PROCESS_TOP

    @property
    def can_process(self):
        """Prüft, ob Verarbeitung möglich ist."""
        return (
            self.df is not None and
            not self.df.empty and
            self.is_valid_range and
            self._samplerate_fs is not None
        )

    @property
    def data_loaded(self):
        """Prüft automatisch, ob Daten verfügbar sind."""
        return (
            self.df is not None and
            not self.df.empty and
            self.headers
        )

    # --------------------------------------------------------
    #  HILFSMETHODEN
    # --------------------------------------------------------

    def excel_column_to_number(self, col):
        """Konvertiert Excel-Spaltenbezeichner (z.B. 'A', 'BC') in eine Zahl."""
        if not col:
            raise ValueError(Cfg.Errors.VAL_COLUMN_NOT_FOUND.format("leer"))
        col    = col.upper()
        result = 0
        for k in col:
            result = result * 26 + (ord(k) - ord('A') + 1)
        logger.debug(Cfg.Logs.VAL_EXCEL_COLUMN_DETECTED.format(col, result))
        return result

    def _select_df(self):
        """Gibt temp_df zurück wenn reset aktiv, sonst df."""
        return self.temp_df if (self.reset_active and self.temp_df is not None) else self.df

    def _with_filename_context(self, msg):
        """Stellt msg den Dateinamen voran, falls filename_context gesetzt ist
        (Mehrfachdatei-Import - siehe __init__)."""
        return f"{self.filename_context}\n\n{msg}" if self.filename_context else msg

    def _adjust_row_range(self, df_to_use):
        """Passt End-Zeile an maximalen Index an; meldet Start-Zeile außerhalb des Bereichs."""
        max_rows = df_to_use.index.max()

        if self._start_row is not None and self._start_row > max_rows:
            msg = Cfg.Errors.VAL_START_ROW_OUT_OF_RANGE.format(self._start_row, max_rows)
            meldungen.showerror(Cfg.Texts.ERROR, self._with_filename_context(msg))
            raise ValueError(msg)

        if self._end_row > max_rows:
            old = self._end_row
            self.end_row = max_rows
            logger.info(Cfg.Logs.VAL_RANGE_ADJUSTED.format("End-Zeile", old, max_rows))
            if not self.suppress_range_hints:
                msg = Cfg.Status.VAL_END_ROW_CLAMPED.format(old, max_rows)
                meldungen.showinfo(Cfg.Texts.HINT, self._with_filename_context(msg))

    def _adjust_col_range(self, df_to_use, is_multiindex=False):
        """Passt End-Spalte an maximale Spaltenanzahl an."""
        max_cols = len(df_to_use.columns.levels[0]) if is_multiindex else len(df_to_use.columns)
        if self._end_col >= max_cols:
            old = self._end_col
            self.end_col = max_cols - 1
            logger.info(Cfg.Logs.VAL_RANGE_ADJUSTED.format("End-Spalte", old, max_cols - 1))
            if not self.suppress_range_hints:
                msg = Cfg.Status.VAL_END_COL_CLAMPED.format(old, max_cols - 1)
                meldungen.showinfo(Cfg.Texts.HINT, self._with_filename_context(msg))

    # --------------------------------------------------------
    #  GUI-EINGABEN EINLESEN
    # --------------------------------------------------------

    def set_entries_from_gui(self, entry1, entry2, entry3, entry4, entry5):
        """Setzt Properties aus GUI-Eingaben."""
        try:
            placeholders = Cfg.Ph.EINGABE

            # --- Spalten verarbeiten (mit Excel-Buchstaben-Support) ---
            for attr, entry, label in [
                ('end_col',   entry4, "End-Spalte"),
                ('start_col', entry3, "Start-Spalte"),
            ]:
                text = entry.get().strip()
                if not text:
                    raise ValueError(Cfg.Errors.VAL_COLUMN_NOT_FOUND.format(label))
                if text.isalpha():
                    setattr(self, attr, self.excel_column_to_number(text))
                else:
                    setattr(self, attr, int(text))
                    logger.info(Cfg.Logs.VAL_RANGE_ADJUSTED.format(label, text, text))

            # --- Übrige Entries validieren ---
            entries = [entry1, entry2, entry3, entry4, entry5]
            values  = []
            for entry, placeholder in zip(entries, placeholders):
                value = entry.get().strip()
                if not value or value == placeholder:
                    raise ValueError(f"Bitte alle Felder ausfüllen (fehlt: {placeholder})")
                values.append(value)

            self.start_row     = int(values[0])
            self.end_row       = int(values[1])
            self.samplerate_fs = float(values[4])

            return True

        except ValueError as e:
            logger.exception(Cfg.Errors.VAL_PROCESSING_FAILED.format(e))
            return False

    # --------------------------------------------------------
    #  VERARBEITUNG – DWS / Excel
    # --------------------------------------------------------

    def validate_and_process_dws(self, status_label):
        """DWS/Excel Verarbeitung als Instanzmethode."""
        logger.info(Cfg.Logs.VAL_START.format(Cfg.Export.PROCESS_DWS))
        logger.info(Cfg.Logs.VAL_DATAFRAME_TYPE.format(self.dataframe_type))

        if not self.data_loaded:
            logger.info(Cfg.Logs.VAL_DATAFRAME_EMPTY)
            status_label.config(text=Cfg.Status.VAL_NO_DATA)
            return None, None, None, None, None

        if self.dataframe_type != Cfg.Export.PROCESS_DWS:
            logger.info(Cfg.Status.VAL_INVALID_FORMAT.format(Cfg.Export.PROCESS_DWS))
            status_label.config(text=Cfg.Status.VAL_INVALID_FORMAT.format("DWS/Excel"))
            return None, None, None, None, None

        if not self.can_process:
            status_label.config(text=Cfg.Status.VAL_FAILED)
            return None, None, None, None, None

        try:
            df_to_use = self._select_df()
            self._adjust_row_range(df_to_use)
            self._adjust_col_range(df_to_use, is_multiindex=True)
        except Exception as e:
            error_msg = Cfg.Errors.VAL_PROCESSING_FAILED.format(e)
            logger.exception(error_msg)
            status_label.config(text=error_msg)
            return None, None, None, None, None

        try:
            logger.info(Cfg.Logs.VAL_RANGE_VALIDATION.format(
                self._start_row, self._end_row, self._start_col, self._end_col
            ))
            logger.info(Cfg.Logs.VAL_PROCESSING_TIME.format(self.processing_time_estimate))

            df_to_use        = self._select_df()
            selected_columns = df_to_use.columns[self._start_col:self._end_col + 1]
            data_slice       = df_to_use.loc[self._start_row:self._end_row][selected_columns]

            data_converted = data_slice.astype(object).replace({True: 1, False: 0})
            data_converted = data_converted.astype(str).replace(",", ".", regex=True)
            value          = data_converted.apply(pd.to_numeric, errors='coerce').to_numpy()

            if self.reset_active and self.temp_df is not None:
                headers = [self.temp_headers[i] for i in range(self._start_col, min(self._end_col + 1, len(self.temp_headers)))]
                units   = [self.temp_units[i]   for i in range(self._start_col, min(self._end_col + 1, len(self.temp_units)))]
            else:
                headers = [col[0] for col in selected_columns]
                units   = [col[1] for col in selected_columns]
                if self.temp_units:
                    for i in range(len(units)):
                        if not units[i]:
                            idx = self._start_col + i
                            if idx < len(self.temp_units):
                                units[i] = self.temp_units[idx]

            if len(headers) != len(units) or len(headers) != value.shape[1]:
                raise ValueError(Cfg.Errors.VAL_INCONSISTENT_DIMS)

            logger.info(Cfg.Logs.VAL_DATA_EXTRACTED.format(Cfg.Export.PROCESS_DWS, len(headers)))
            status_label.config(text=Cfg.Status.VAL_DWS_PROCESSED)

            return self._samplerate_fs, 1, value, headers, units

        except (ValueError, IndexError) as e:
            error_msg = Cfg.Errors.VAL_PROCESSING_FAILED.format(e)
            logger.exception(error_msg)
            status_label.config(text=error_msg)
            return None, None, None, None, None

    # --------------------------------------------------------
    #  VERARBEITUNG – TOP / CSV
    # --------------------------------------------------------

    def validate_and_process_top(self, status_label):
        """TOP/CSV Verarbeitung als Instanzmethode."""
        logger.info(Cfg.Logs.VAL_START.format(Cfg.Export.PROCESS_TOP))
        logger.info(Cfg.Logs.VAL_DATAFRAME_TYPE.format(self.dataframe_type))

        if not self.data_loaded:
            logger.info(Cfg.Logs.VAL_DATAFRAME_EMPTY)
            status_label.config(text=Cfg.Status.VAL_NO_DATA)
            return None, None, None, None, None

        if not self.can_process:
            status_label.config(text=Cfg.Status.VAL_FAILED)
            return None, None, None, None, None

        try:
            df_to_use = self._select_df()
            self._adjust_row_range(df_to_use)
            self._adjust_col_range(df_to_use, is_multiindex=False)
        except Exception as e:
            error_msg = Cfg.Errors.VAL_PROCESSING_FAILED.format(e)
            logger.exception(error_msg)
            status_label.config(text=error_msg)
            return None, None, None, None, None

        try:
            logger.info(Cfg.Logs.VAL_RANGE_VALIDATION.format(
                self._start_row, self._end_row, self._start_col, self._end_col
            ))
            logger.info(Cfg.Logs.VAL_PROCESSING_TIME.format(self.processing_time_estimate))

            df_to_use        = self._select_df()
            selected_columns = df_to_use.columns[self._start_col:self._end_col + 1]
            data_slice       = df_to_use.loc[self._start_row:self._end_row][selected_columns]

            data_converted = data_slice.astype(object).replace({True: 1, False: 0})
            data_converted = data_converted.astype(str).replace(",", ".", regex=True)
            value          = data_converted.apply(pd.to_numeric, errors='coerce').to_numpy()

            headers = [str(col) for col in selected_columns]
            logger.info("TOP validate - selected_columns: %s", list(selected_columns))
            logger.info("TOP validate - temp_headers: %s", self.temp_headers)
            logger.info("TOP validate - temp_units:   %s", self.temp_units)
            if self.temp_headers and self.temp_units:
                # Nicht direkt dict(zip(temp_headers, temp_units)) - bei zwei Spalten mit
                # gleichem Namen (z.B. nach dem Entfernen der Einheit aus dem Spaltentitel)
                # wuerde ein Name->Einheit-Dict auf die letzte Einheit kollabieren und
                # beiden Spalten dieselbe (teils falsche) Einheit zuweisen. Stattdessen wird
                # pro Name eine Warteschlange der Positionen in temp_headers gefuehrt und
                # bei jedem Namens-Treffer in Spaltenreihenfolge abgearbeitet - so bekommt
                # bei doppelten Namen jede Spalte ihre EIGENE, korrekte Einheit. (Direkte
                # Positionsindizierung über _start_col geht hier NICHT: temp_headers/
                # temp_units haben Cfg.Data.EXCLUDE_COLUMNS bereits herausgefiltert und sind
                # dadurch kürzer/anders indiziert als df_to_use.columns, aus dem _start_col
                # stammt.)
                name_to_indices = {}
                for i, h in enumerate(self.temp_headers):
                    name_to_indices.setdefault(h, deque()).append(i)

                units = []
                for col in selected_columns:
                    indices = name_to_indices.get(str(col))
                    if indices:
                        idx = indices.popleft()
                        units.append(self.temp_units[idx] if idx < len(self.temp_units) else "")
                    else:
                        units.append("")
                logger.info("TOP validate - units result: %s", units)
            else:
                units = [''] * len(selected_columns)

            if len(headers) != len(units) or len(headers) != value.shape[1]:
                raise ValueError(Cfg.Errors.VAL_INCONSISTENT_DIMS)

            logger.info(Cfg.Logs.VAL_DATA_EXTRACTED.format(Cfg.Export.PROCESS_TOP, len(headers)))
            status_label.config(text=Cfg.Status.VAL_TOP_PROCESSED)

            return self._samplerate_fs, 1, value, headers, units

        except (ValueError, IndexError) as e:
            error_msg = Cfg.Errors.VAL_PROCESSING_FAILED.format(e)
            logger.exception(error_msg)
            status_label.config(text=error_msg)
            return None, None, None, None, None

    # --------------------------------------------------------
    #  HAUPTVERARBEITUNG
    # --------------------------------------------------------

    def validate_and_process(self, entry1, entry2, entry3, entry4, entry5, status_label):
        """Hauptverarbeitungsmethode – wählt automatisch DWS oder TOP."""
        logger.info(Cfg.Status.VAL_READY)

        if not self.set_entries_from_gui(entry1, entry2, entry3, entry4, entry5):
            status_label.config(text=Cfg.Status.VAL_FAILED)
            return None, None, None, None, None

        if self.df is None or not isinstance(self.df, pd.DataFrame):
            if self.temp_df is not None and isinstance(self.temp_df, pd.DataFrame):
                self.df = self.temp_df.copy()
                logger.info(Cfg.Logs.VAL_FALLBACK_TO_TEMP)
            else:
                logger.info(Cfg.Errors.VAL_NO_DATAFRAME)
                return None, None, None, None, None

        if self.dataframe_type == Cfg.Export.PROCESS_DWS:
            logger.info("MultiIndex erkannt - verwende DWS/Excel Verarbeitung")
            return self.validate_and_process_dws(status_label)
        else:
            logger.info("Einfacher Index erkannt - verwende TOP Verarbeitung")
            return self.validate_and_process_top(status_label)