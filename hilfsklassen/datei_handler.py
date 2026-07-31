"""
Datei Handler - Dateioperationen
==================================
Klasse für alle Datei-Operationen: Lesen von Excel, CSV
und DWS-Dateien, Encoding-Erkennung, Validierung und
Export von verarbeiteten Daten.
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
import csv
import logging
import os
import re
from datetime import datetime
from pathlib import Path

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import charset_normalizer
import numpy as np
import pandas as pd

# ============================================================
#  IMPORTS – Eigene Klassen
# ============================================================
from konfiguration import Cfg

# ============================================================
#  LOGGING
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
#  KLASSE
# ============================================================
class DateiHandler:
    """Klasse für alle Datei-Operationen mit Property-basierter Validierung"""

    def __init__(self):

        # --- Dateistatus ---
        self._file_path = None
        self._encoding  = None
        self._delimiter = None
        self._is_valid  = False

        # --- Geparste Zeitstempel (nicht in df.attrs, das bricht pandas' interne
        #     Attrs-Gleichheitspruefung bei astype()/concat() auf Series-Werten) ---
        self.zeitstempel = None

    # --------------------------------------------------------
    #  HILFSMETHODEN (statisch)
    # --------------------------------------------------------

    @staticmethod
    def split_header_unit(name: str) -> tuple[str, str]:
        """Trennt Signalname und Einheit aus einem kombinierten Spaltenheader.
        Unterstützt [Einheit], [Unit:Einheit] sowie (Einheit) am Ende als Fallback.
        """
        m = re.search(r"\[(.*?)]", name)
        if m:
            unit = m.group(1).strip()
            if unit.lower().startswith("unit:"):
                unit = unit.split(":", 1)[1].strip()
            header = re.sub(r"\s*\[.*?]\s*", "", name).strip()
            if unit:
                return header, unit
            # [] war leer -> Fallback auf (Einheit) am Ende
            m2 = re.search(r"\(([^)]+)\)\s*$", header)
            if m2:
                unit2 = m2.group(1).strip()
                header2 = re.sub(r"\s*\([^)]+\)\s*$", "", header).strip()
                return header2, unit2
            return header, ""
        # Kein [...] vorhanden -> Fallback auf (Einheit) am Ende
        m2 = re.search(r"\(([^)]+)\)\s*$", name)
        if m2:
            unit2 = m2.group(1).strip()
            header2 = re.sub(r"\s*\([^)]+\)\s*$", "", name).strip()
            return header2, unit2
        return name, ""

    @staticmethod
    def samplerate_from_timestamps(timestamps):
        """Berechnet die tatsaechliche Samplefrequenz (Hz) aus echten Zeitstempeln
        der Originalaufnahme - der Median der Zeitabstaende ist robuster gegen
        einzelne Ausreisser/Rundungsfehler als z.B. (letzter - erster)/(n-1).
        Gibt None zurueck, wenn timestamps None/zu kurz ist oder der Median-Abstand
        nicht positiv ist (z.B. doppelte/ungeordnete Zeitstempel)."""
        if timestamps is None or len(timestamps) < 2:
            return None
        try:
            ts = pd.to_datetime(pd.Series(timestamps).dropna())
            if len(ts) < 2:
                return None
            deltas_s = np.diff(ts.to_numpy()) / np.timedelta64(1, "s")
            median_dt = float(np.median(deltas_s))
        except Exception:
            logger.debug("Samplerate aus Zeitstempeln konnte nicht berechnet werden", exc_info=True)
            return None
        if median_dt <= 0:
            return None
        return 1.0 / median_dt

    # --------------------------------------------------------
    #  PROPERTIES
    # --------------------------------------------------------

    @property
    def file_path(self):
        return self._file_path

    @file_path.setter
    def file_path(self, path):
        if path is None:
            self._file_path = None
            self._is_valid  = False
            return

        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(Cfg.Errors.FILE_NOT_FOUND.format(path))
        if not path_obj.is_file():
            raise ValueError(f"Pfad ist keine Datei: {path}")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Datei nicht lesbar: {path}")

        self._file_path = path_obj
        self._is_valid  = True
        self._encoding  = None
        self._delimiter = None

    @property
    def encoding(self):
        if self._encoding is None and self._file_path is not None:
            self._encoding = self._detect_encoding()
        return self._encoding

    @encoding.setter
    def encoding(self, value):
        if value is not None and value not in Cfg.Export.SUPPORTED_ENCODINGS:
            raise ValueError(Cfg.Errors.FILE_INVALID_ENCODING.format(value, Cfg.Export.SUPPORTED_ENCODINGS))
        self._encoding = value

    @property
    def delimiter(self):
        if self._delimiter is None and self._file_path is not None and self.encoding is not None:
            self._delimiter = self._detect_csv_delimiter()
        return self._delimiter

    @delimiter.setter
    def delimiter(self, value):
        if value is not None and value not in Cfg.Export.SUPPORTED_DELIMITERS:
            raise ValueError(Cfg.Errors.FILE_INVALID_DELIMITER.format(value, Cfg.Export.SUPPORTED_DELIMITERS))
        self._delimiter = value

    @property
    def is_valid(self):
        return self._is_valid and self._file_path is not None and self._file_path.exists()

    @property
    def file_extension(self):
        return self._file_path.suffix.lower() if self._file_path else None

    @property
    def is_excel(self):
        return self.file_extension in ['.xlsx', '.xls'] if self.file_extension else False

    @property
    def is_csv(self):
        return self.file_extension == '.csv' if self.file_extension else False

    # --------------------------------------------------------
    #  ERKENNUNG (privat)
    # --------------------------------------------------------

    def _detect_encoding(self):
        """Erkennt das Encoding der Datei automatisch."""
        if not self.is_valid:
            raise ValueError(Cfg.Errors.FILE_NOT_FOUND.format(self._file_path))
        with open(self._file_path, 'rb') as f:
            result = charset_normalizer.detect(f.read())
        logger.info(Cfg.Logs.FILE_ENCODING_DETECTED.format(result['encoding']))
        return result['encoding']

    def _detect_csv_delimiter(self):
        """Erkennt das Trennzeichen der CSV-Datei automatisch."""
        if not self.is_valid:
            raise ValueError(Cfg.Errors.FILE_NOT_FOUND.format(self._file_path))
        if self._encoding is None:
            raise ValueError(Cfg.Errors.FILE_INVALID_ENCODING.format("Encoding", "Encoding muss zuerst erkannt werden"))

        try:
            with open(self._file_path, 'r', encoding=self.encoding) as f:
                first_line = f.readline()
            logger.debug("Das ist self.encoding: %s", self.encoding)
        except UnicodeDecodeError:
            logger.exception(Cfg.Errors.FILE_EXPORT_FAILED.format(f"Encoding-Fehler mit {self.encoding}"))
            return Cfg.Export.DEFAULT_DELIMITER

        delimiter_counts = {
            d: first_line.count(d)
            for d in Cfg.Export.SUPPORTED_DELIMITERS
            if first_line.count(d) > 0
        }

        if delimiter_counts:
            best = max(delimiter_counts, key=delimiter_counts.get)
            logger.info(Cfg.Logs.FILE_DELIMITER_DETECTED.format(best, delimiter_counts[best]))
            return best
        else:
            logger.info(Cfg.Logs.FILE_FALLBACK_DELIMITER.format(Cfg.Export.DEFAULT_DELIMITER))
            return Cfg.Export.DEFAULT_DELIMITER

    # --------------------------------------------------------
    #  LESEN – Excel / DWS
    # --------------------------------------------------------

    def read_dws_excel(self, sheet_name, status_label, progress_label):
        """Liest eine DWS-Excel-Datei mit MultiIndex-Header."""
        try:
            if not self.is_valid:
                status_label.config(text=Cfg.Errors.FILE_NOT_FOUND.format(self.file_path))
                return None, None, None

            if not self.is_excel:
                status_label.config(text=Cfg.Errors.FILE_NOT_EXCEL)
                return None, None, None

            logger.info(Cfg.Logs.FILE_LOADED.format(self.file_path))

            if not self.file_path.exists():
                status_label.config(text=Cfg.Errors.FILE_NOT_FOUND.format(self.file_path))
                return None, None, None

            df = pd.read_excel(self.file_path, sheet_name=sheet_name, header=[0, 1], parse_dates=False)
            df.index += 1

            temp_headers = [col[0] for col in df.columns]
            temp_units   = [col[1] for col in df.columns]
            parsed       = [self.split_header_unit(str(h)) for h in temp_headers]
            temp_headers = [h for h, _ in parsed]
            temp_units   = [
                u if u not in (None, "") else parsed[i][1]
                for i, u in enumerate(temp_units)
            ]

            if df.empty:
                logger.warning(Cfg.Logs.FILE_EXCEL_SHEET_EMPTY)
                status_label.config(text=Cfg.Errors.FILE_EMPTY)
                return None, None, None

        except Exception as e:
            logger.exception(Cfg.Errors.FILE_EXPORT_FAILED.format(e))
            status_label.config(text=Cfg.Errors.FILE_EXPORT_FAILED.format("Fehler beim Einlesen"))
            return None, None, None

        time_column = ("Time", "s")

        if time_column not in df.columns:
            logger.debug("Verfügbare Spalten: %s", df.columns.tolist())
            status_label.config(text=Cfg.Errors.FILE_NO_TIMESTAMP)
            return None, None, None

        logger.debug("Erste Zeitstempel-Werte:")
        logger.debug(df[time_column].head())

        try:
            df[time_column] = pd.to_datetime(
                df[time_column].astype(str),
                format="%d.%m.%Y %H:%M:%S.%f",
                dayfirst=True,
                errors="coerce"
            )

            if df[time_column].empty:
                status_label.config(text=Cfg.Errors.FILE_NO_TIMESTAMP)
                return None, None, None

            invalid_timestamps = df[time_column].isna().sum()
            if invalid_timestamps > 0:
                logger.warning(Cfg.Errors.FILE_INVALID_TIMESTAMP.format(invalid_timestamps))
                status_label.config(text=Cfg.Errors.FILE_INVALID_TIMESTAMP)
                return None, None, None

            self.zeitstempel = df[time_column]

        except Exception as e:
            logger.exception(Cfg.Errors.FILE_EXPORT_FAILED.format(e))
            logger.error("Problematischer Wert: %s", df[time_column].iloc[0])
            status_label.config(text=Cfg.Errors.FILE_EXPORT_FAILED.format(e))
            return None, None, None

        logger.info(Cfg.Logs.FILE_LOADED.format(self.file_path) + f" | Shape: {df.shape}")
        logger.info("Zeitstempel-Spalte: %s", time_column)
        logger.debug("Hauptüberschriften (Level 0): %s", df.columns.levels[0].tolist())
        logger.debug("Einheiten (Level 1): %s", df.columns.levels[1].tolist())
        logger.debug("Erste Zeilen der Daten:\n%s", df.head())

        columns = df.columns.levels[0].tolist()
        if not columns:
            status_label.config(text=Cfg.Errors.FILE_NO_COLUMNS)
            return None, None, None

        start_row = 1
        end_row   = df.shape[0]
        start_col = 0
        end_col   = len(columns) - 1
        logger.info("DWS Standard-Bereich: Zeilen %d-%d, Spalten %d-%d", start_row, end_row, start_col, end_col)

        status_label.config(text=Cfg.Status.FILE_LOADED)
        return df, temp_headers, temp_units

    # --------------------------------------------------------
    #  LESEN – CSV / TOP
    # --------------------------------------------------------

    def _parse_top_timestamps(self, df):
        """
        Parst echte Zeitstempel aus 'Date'+'Time'-Spalten einer TOP/CSV-Datei
        (Format z.B. '07.03.2025' + '14:34:28,090'). Gibt eine pd.Series mit
        datetime64-Werten zurück, oder None wenn keine/keine gültigen Spalten vorhanden sind.
        """
        date_col = next((c for c in df.columns if str(c).strip().lower() == "date"), None)
        time_col = next((c for c in df.columns if str(c).strip().lower() == "time"), None)

        logger.info(
            "[DEBUG-ZEITACHSE] _parse_top_timestamps: df.columns=%s%s | date_col=%r, time_col=%r",
            list(df.columns)[:15], "..." if len(df.columns) > 15 else "", date_col, time_col
        )

        if date_col is None and time_col is None:
            logger.info("[DEBUG-ZEITACHSE] Weder 'Date' noch 'Time' Spalte gefunden -> None")
            return None

        def _normalize_time_fraction(time_series):
            """Vereinheitlicht den Millisekunden-Trenner: ',' oder ':' (z.B. '14:34:28:090') -> '.'."""
            normalized = time_series.astype(str).str.strip()
            normalized = normalized.str.replace(",", ".", regex=False)
            normalized = normalized.str.replace(r":(\d{1,3})$", r".\1", regex=True)
            return normalized

        try:
            if date_col is not None and time_col is not None:
                logger.info(
                    "[DEBUG-ZEITACHSE] Rohwerte Date[:3]=%s | Time[:3]=%s",
                    df[date_col].astype(str).head(3).tolist(), df[time_col].astype(str).head(3).tolist()
                )
                combined = df[date_col].astype(str).str.strip() + " " + _normalize_time_fraction(df[time_col])
                logger.info("[DEBUG-ZEITACHSE] combined[:3]=%s", combined.head(3).tolist())
                timestamps = pd.to_datetime(
                    combined, format="%d.%m.%Y %H:%M:%S.%f", dayfirst=True, errors="coerce"
                )
            else:
                only_col = time_col if time_col is not None else date_col
                timestamps = pd.to_datetime(
                    _normalize_time_fraction(df[only_col]),
                    format="%H:%M:%S.%f", errors="coerce"
                )
        except Exception as e:
            logger.warning("[DEBUG-ZEITACHSE] EXCEPTION beim Parsen: %r", e)
            logger.warning("Zeitstempel-Parsing (TOP/CSV) fehlgeschlagen: %s", e)
            return None

        logger.info(
            "[DEBUG-ZEITACHSE] timestamps geparst: %s Werte, %s ungueltig (NaT), erste 3=%s",
            len(timestamps), int(timestamps.isna().sum()), timestamps.head(3).tolist()
        )

        if timestamps.isna().any():
            logger.warning(
                "Zeitstempel konnten nicht vollständig geparst werden (%d ungültig) - Uhrzeit-Achse nicht verfügbar",
                int(timestamps.isna().sum())
            )
            return None

        return timestamps

    def read_top(self, status_label, progress_label):
        """Liest eine TOP/CSV-Datei mit automatischer Encoding- und Delimiter-Erkennung."""
        try:
            if not self.is_valid:
                status_label.config(text=Cfg.Errors.FILE_NOT_FOUND.format(self.file_path))
                return None, None, None

            if not self.is_csv:
                status_label.config(text=Cfg.Errors.FILE_NOT_CSV)
                return None, None, None

            logger.info(Cfg.Logs.FILE_LOADED.format(self.file_path))

            if not self.file_path.exists():
                status_label.config(text=Cfg.Errors.FILE_NOT_FOUND.format(self.file_path))
                return None, None, None

            logger.info("Verwende Encoding: %s", self.encoding)
            logger.info("Verwende Delimiter: %s", self.delimiter)

            with open(self.file_path, 'r', encoding=self.encoding) as f:
                lines = f.readlines()
                logger.info(Cfg.Logs.FILE_CSV_PARSED.format(len(lines)))

            # --- Einheiten aus LOGITEM-Zeilen extrahieren ---
            delimiter = self.delimiter or Cfg.Export.DEFAULT_DELIMITER
            unit_map  = {}
            _logitem_diag = []
            for line in lines:
                line_stripped = line.lstrip()
                if not line_stripped.startswith("LOGITEM"):
                    continue
                parts = [p.strip() for p in line_stripped.split(delimiter)]
                if len(parts) < 2:
                    continue
                if len(_logitem_diag) < 3:
                    _logitem_diag.append(parts[:6])
                signal_name = parts[1]
                text = " ".join(parts[2:])

                # Zusätzlicher Key: "Ressource.Kurzname" (z.B. TOP1131-Format wo
                # parts[1]="GB_Netz_F.rTCU_U_Line", parts[4]=Beschreibung, parts[5]="VCU_A")
                resource = parts[5] if len(parts) >= 6 else ""
                full_name = (f"{resource}.{signal_name}"
                             if resource and "." not in resource
                             and not signal_name.startswith(resource + ".")
                             else "")

                def _store(unit_val):
                    unit_map[signal_name] = unit_val
                    if full_name:
                        unit_map[full_name] = unit_val

                # 1. [unit: X] Format (z.B. IITCU-Signale)
                m = re.search(r"\[unit\s*:\s*([^\]]+)\]", text, flags=re.IGNORECASE)
                if m:
                    _store(m.group(1).strip())
                else:
                    # 2. (Einheit) in gesamtem Text suchen – funktioniert für parts[3]
                    #    (TOP1131: Beschreibung) UND parts[4] (ältere Formate)
                    m2 = re.search(r"\(([^)]{1,20})\)", text)
                    if m2:
                        candidate = m2.group(1).strip()
                        if candidate:
                            _store(candidate)
                    if not unit_map.get(signal_name):
                        # [Einheit] – z.B. "[] [km/h] Reference Speed"
                        for bm in re.finditer(r"\[([^\]]{1,20})\]", text):
                            candidate = bm.group(1).strip()
                            if candidate:
                                _store(candidate)
                                break

            logger.info("LOGITEM erste 3 Zeilen (parts[:6]): %s", _logitem_diag)
            logger.info("LOGITEM unit_map: %s", unit_map)

            # --- Datenstartzeile suchen ---
            data_start_line = None
            for i, line in enumerate(lines):
                if "Nb" in line.split(delimiter):
                    data_start_line = i
                    logger.info("Nb gefunden in Zeile %d, Daten starten ab Zeile %d", i, data_start_line)
                    break

            if data_start_line is None:
                logger.info(Cfg.Logs.FILE_NO_DATA_START)
                data_start_line = 0

            df = pd.read_csv(
                self.file_path,
                skiprows=data_start_line,
                header=0,
                parse_dates=False,
                encoding=self.encoding,
                sep=delimiter
            )
            df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
            df.index = range(1, len(df) + 1)

            original_col_names = [str(col) for col in df.columns]
            parsed       = [self.split_header_unit(orig) for orig in original_col_names]
            temp_headers = [h for h, _ in parsed]
            temp_units   = [
                unit_map.get(orig) or unit_map.get(header) or unit
                for (header, unit), orig in zip(parsed, original_col_names)
            ]
            df.columns = temp_headers

            if df.empty:
                logger.warning(Cfg.Logs.FILE_EXCEL_SHEET_EMPTY)
                status_label.config(text=Cfg.Errors.FILE_EMPTY)
                return None, None, None

            logger.info("DataFrame Shape nach Bereinigung: %s", df.shape)
            logger.debug("Verfügbare Spalten: %s", df.columns.tolist())

        except Exception as e:
            logger.exception(Cfg.Errors.FILE_EXPORT_FAILED.format(e))
            status_label.config(text=Cfg.Errors.FILE_EXPORT_FAILED.format("Fehler beim Einlesen"))
            return None, None, None

        # --- Zeitspalte erkennen ---
        time_columns = [
            col for col in df.columns
            if any(kw in str(col).lower() for kw in ['time', 'zeit', 'timestamp', 'datetime', 'date'])
        ]

        if len(df.columns) == 0:
            status_label.config(text=Cfg.Errors.FILE_NO_COLUMNS)
            return None, None, None
        elif time_columns:
            time_column = time_columns[0]
            logger.info("Zeitspalte automatisch erkannt: %s", time_column)
        else:
            time_column = df.columns[0]
            logger.info("Keine Zeitspalte gefunden - verwende erste Spalte als Fallback: %s", time_column)

        logger.debug("Erste Zeitstempel-Werte:")
        logger.debug(df[time_column].head())
        logger.info("Zeitspalte '%s' wird als Index-Referenz beibehalten", time_column)
        logger.debug("Zeitwerte (unkonvertiert): %s", df[time_column].head(3).tolist())
        logger.info("Fokus liegt auf numerischen Messdaten - Zeitkonvertierung übersprungen")

        # --- Echte Zeitstempel aus Date+Time-Spalten parsen (für Uhrzeit-Achse) ---
        self.zeitstempel = self._parse_top_timestamps(df)

        progress_label.config(text="")

        logger.info(Cfg.Logs.FILE_LOADED.format(self.file_path) + f" | Shape: {df.shape}")
        logger.info("Referenz-Zeitspalte: %s", time_column)
        logger.info("\nAnzahl verfügbare Spalten: %d", len(df.columns))
        logger.info("Spalten (erste 10): %s", df.columns.tolist()[:10])

        # --- Spaltenbereich für Standardauswahl bestimmen ---
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        logger.info("Numerische Spalten: %d (erste 8: %s)", len(numeric_columns), numeric_columns[:8])
        if numeric_columns:
            logger.debug("%s", df[numeric_columns[:6]].head(3))
        else:
            logger.info(Cfg.Errors.FILE_NO_NUMERIC_COLUMNS)

        numeric_columns = [col for col in numeric_columns if col not in Cfg.Data.EXCLUDE_COLUMNS]

        filtered_pairs = [
            (h, u) for h, u in zip(temp_headers, temp_units)
            if h not in Cfg.Data.EXCLUDE_COLUMNS
        ]
        temp_headers = [h for h, _ in filtered_pairs]
        temp_units   = [u for _, u in filtered_pairs]

        if not df.columns.tolist():
            status_label.config(text=Cfg.Errors.FILE_NO_COLUMNS)
            return None, None, None

        status_label.config(text=Cfg.Status.FILE_LOADED)
        return df, temp_headers, temp_units

    # --------------------------------------------------------
    #  EXPORT
    # --------------------------------------------------------

    def export_signal_data(self, save_path,
                           t,
                           original,
                           used,
                           signal_name,
                           unit,
                           dt,
                           f_axis,
                           amp,
                           phase,
                           filter_info,
                           window_type,
                           show_avg=False,
                           show_rms=False,
                           show_diff=False,
                           show_integral=False):
        """
        Exportiert Signal-Daten nach Excel oder CSV (Fallback).
        Args:
            save_path:     Zieldateipfad (.xlsx)
            t:             Zeitarray
            original:      Original-Signal
            used:          Benutztes Signal (gefiltert oder original)
            signal_name:   Name des Signals
            unit:          Einheit
            dt:            Abtastzeit
            f_axis:        Frequenzachse (FFT)
            amp:           Amplitude (FFT)
            phase:         Phase (FFT)
            filter_info:   Dict mit filter_type, characteristic, order, cutoff1, cutoff2, sample_rate
            window_type:   Fensterfunktion
            show_avg, show_rms, show_diff, show_integral: Flags für optionale Berechnungen
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            N = len(t)
            if N < 2:
                return False, Cfg.Errors.FILE_EXPORT_FAILED.format("Zu wenige Punkte für Export")

            def pad_to_N(a, L):
                a   = np.asarray(a)
                out = np.full(L, np.nan, dtype=float)
                out[:min(len(a), L)] = a[:min(len(a), L)]
                return out

            freq_pad  = pad_to_N(f_axis, N)
            amp_pad   = pad_to_N(amp, N)
            phase_pad = pad_to_N(phase, N)

            # --- Optionale Kennwerte / Serien ---
            info_rows_extra = []
            extra_series    = {}

            if show_avg:
                avg_val = float(np.nanmean(used))
                info_rows_extra.append(["AVG (auf aktuell benutztem Signal)", f"{avg_val:.6g} {unit}"])

            if show_rms:
                rms_val = float(np.sqrt(np.nanmean(used**2)))
                info_rows_extra.append(["RMS (auf aktuell benutztem Signal)", f"{rms_val:.6g} {unit}"])

            if show_diff:
                diff      = np.gradient(used, dt)
                unit_diff = f"{unit}/s" if unit else "1/s"
                extra_series[f"d({signal_name})/dt [{unit_diff}]"] = pad_to_N(diff, N)

            if show_integral:
                integ    = np.cumsum(used) * dt
                unit_int = f"{unit}·s" if unit else "unit·s"
                extra_series[f"∫{signal_name} dt [{unit_int}]"] = pad_to_N(integ, N)

            # --- Metadaten-Block ---
            df_step     = 1.0 / (N * dt)
            fmt         = lambda x: "" if x is None else str(x)
            filter_type = filter_info.get('filter_type', Cfg.Defaults.FILTER_TYP)

            info_rows = [
                ["Export Timestamp",            datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["Signal Name",                 signal_name],
                ["Unit",                        unit],
                ["Samples (N)",                 str(N)],
                ["dt [s]",                      f"{dt:.6g}"],
                ["df [Hz]",                     f"{df_step:.6g}"],
                ["Window Type",                 window_type or Cfg.Defaults.FENSTERTYP],
                ["Filter Type",                 filter_type],
                ["Filter Characteristic",       filter_info.get('characteristic', Cfg.Defaults.FILTER_CHARAKTERISTIK)],
                ["Filter Order",                fmt(filter_info.get('order'))],
                ["Cutoff Frequency 1 [Hz]",     fmt(filter_info.get('cutoff1'))],
                ["Cutoff Frequency 2 [Hz]",     fmt(filter_info.get('cutoff2'))],
                ["Sample Rate [Hz]",            fmt(filter_info.get('sample_rate'))],
                ["Note",
                 "Daten ab Zeile 20: Time, (filtered), (original), Frequency, Amplitude, Phase"
                 + (", d()/dt"  if show_diff     else "")
                 + (", ∫()dt"   if show_integral else "")],
            ]
            info_rows.extend(info_rows_extra)

            info_df = pd.DataFrame(info_rows, columns=["Key", "Value"])

            # --- Daten-Block ---
            data_dict = {
                "Time [s]":                                    t,
                f"{signal_name} [{unit}] ({filter_type})":    used,
                f"{signal_name} [{unit}] (original)":         original,
                "Frequency [Hz]":                             freq_pad,
                "Amplitude":                                   amp_pad,
                "Phase [deg]":                                 phase_pad,
            }
            for col_name, series in extra_series.items():
                data_dict[col_name] = series

            data_df = pd.DataFrame(data_dict).replace([np.inf, -np.inf], np.nan)

            # --- Excel schreiben (mit Engine-Fallback) ---
            written  = False
            last_err = None

            for eng in Cfg.Export.EXCEL_ENGINES:
                try:
                    with pd.ExcelWriter(save_path, engine=eng) as writer:
                        info_df.to_excel(writer, sheet_name="Signal", index=False, startrow=0,  startcol=0)
                        data_df.to_excel(writer, sheet_name="Signal", index=False, startrow=19, startcol=0)
                    written = True
                    break
                except (ModuleNotFoundError, Exception) as e:
                    last_err = e
                    logger.warning("Excel-Export mit Engine '%s' fehlgeschlagen: %s", eng, e)

            # --- CSV-Fallback ---
            if not written:
                logger.warning(
                    "Excel-Export mit allen Engines (%s) fehlgeschlagen, letzter Fehler: %s - weiche auf CSV aus",
                    ", ".join(Cfg.Export.EXCEL_ENGINES), last_err
                )
                csv_path = os.path.splitext(save_path)[0] + "_Signal.csv"
                try:
                    with open(csv_path, "w", newline="", encoding="utf-8") as f:
                        w = csv.writer(f)
                        w.writerow(["Key", "Value"])
                        w.writerows(info_rows)
                        w.writerow([])
                        w.writerow([])
                        w.writerow(list(data_df.columns))
                        for _, row in data_df.iterrows():
                            w.writerow(list(row.values))
                    return True, Cfg.Status.FILE_EXPORT_FALLBACK_CSV.format(csv_path)
                except Exception as e:
                    return False, Cfg.Errors.FILE_EXPORT_FAILED.format(e)

            return True, Cfg.Status.FILE_EXPORT_SUCCESS.format(save_path)

        except Exception as e:
            return False, Cfg.Errors.FILE_EXPORT_FAILED.format(e)