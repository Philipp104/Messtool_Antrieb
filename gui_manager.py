"""
GUI Manager - Hauptfenster-Verwaltung
=====================================
Zentrale Klasse für die GUI-Steuerung des Messtools.
Koordiniert alle Sub-Manager (Layout, Events, Filter, Plots, Analyse)
und verwaltet den Anwendungszustand sowie die Datenverarbeitung.
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
import os
import sys
import subprocess
import time
import threading
import logging
import tempfile
from datetime import datetime
from pathlib import Path

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import ttkbootstrap as tb
from xhtml2pdf import pisa

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# ============================================================
#  IMPORTS – Eigene Klassen
# ============================================================
from hilfsklassen.zentrales_logging import get_protocol_logger
from hilfsklassen.datei_handler import FileHandler
from hilfsklassen.daten_validator import DataValidator
from hilfsklassen.filter_manager import FilterManager
from hilfsklassen.daten_verarbeiter import DatenVerarbeiter
from gui_module.plot_manager import PlotManager
from gui_module.gui_layout_manager import GuiLayoutManager
from gui_module.plot_fenster_manager import PlotWindowManager
from gui_module.oberflaechen_steuerung import UiControlManager
from gui_module.analyse_manager import AnalysisManager
from gui_module.mehrfachdatei_manager import MehrfachDateiManager
from konfiguration import Cfg

# ============================================================
#  LOGGING
# ============================================================
logger          = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()


# ============================================================
#  KLASSE
# ============================================================
class GuiManager:
    """Klasse für die gesamte GUI-Verwaltung als Instanz"""

    def __init__(self, get_resource_path):

        # --- Callback ---
        self.get_resource_path = get_resource_path

        # --- Datenstatus ---
        self.df              = None
        self.t               = None
        self.timestamps_full = None
        self.timestamps      = None
        self.nS              = None
        self.dt              = None
        self.CF              = None
        self.signals         = []
        self.value           = None
        self.headers         = []
        self.units           = []
        self.Gesamtpfad      = None
        self.temp_df         = None
        self.temp_headers    = []
        self.temp_units      = []
        self.spectrum_save_path = None

        # --- Signalauswahl ---
        self.selected_signal           = None
        self.selected_signals          = []
        self.signal_groups             = []
        self.max_groups                = Cfg.Defaults.MAX_GROUPS
        self.max_signals_per_selection = Cfg.Defaults.MAX_SIGNALS

        # --- Steuerflags ---
        self.reset_active      = False
        self.load_data_active  = False
        self.reset_gui_active  = False

        # --- Hilfsklassen ---
        self.data_validator  = DataValidator()
        self.filter_manager  = FilterManager()

        # --- Sub-Manager ---
        self.ui_control          = UiControlManager(self)
        self.plot_window_manager = PlotWindowManager(self)
        self.layout_manager      = GuiLayoutManager(self)
        self.analysis_manager    = AnalysisManager(self)
        self.multi_file_manager  = MehrfachDateiManager(self)

        # --- GUI-Elemente ---
        self.root                    = None
        self.entry1                  = None
        self.entry2                  = None
        self.entry3                  = None
        self.entry4                  = None
        self.entry5                  = None
        self.entry6                  = None
        self.entry7                  = None
        self.entry8                  = None
        self.entry9                  = None
        self.entry10                 = None
        self.entry11                 = None
        self.status_label            = None
        self.progress_label          = None
        self.sheet_combobox          = None
        self.import_button           = None
        self.Verarbeitung_button     = None
        self.path_selection_combobox = None
        self.reset_combobox          = None
        self.characteristic_window   = None
        self.filter_info_tree        = None

        # --- Offene Plot-Fenster ---
        self.open_plot_windows = []

    # --------------------------------------------------------
    #  GUI SETUP
    # --------------------------------------------------------

    def create_gui(self):
        """Erstellt GUI-Layout und startet die Mainloop."""
        self.layout_manager.create_gui()
        self.use_filtered_var = tk.BooleanVar(master=self.root, value=False)
        self.ui_control.apply_visual_defaults()
        self.ui_control.configure_root_lifecycle()
        self.root.mainloop()

    def _setup_placeholder(self, entry, placeholder_text):
        """Delegiert an UiControlManager."""
        return self.ui_control.setup_placeholder(entry, placeholder_text)

    def _prefill_from_df_and_enable(self):
        """
        Befüllt entry1..entry5 mit sinnvollen Zahlen aus self.df,
        ersetzt Placeholder, schaltet Felder frei und setzt Fenster-Combobox.
        """
        if self.df is None:
            return

        try:
            end_row_default = int(self.df.index.max())
        except Exception:
            logger.debug("Fallback: end_row_default aus len(self.df)")
            end_row_default = len(self.df)

        start_row_default = Cfg.Defaults.START_ROW_PREFILL

        try:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                start_col_default = int(self.df.columns.get_loc(numeric_cols[0]))
                end_col_default   = int(self.df.columns.get_loc(numeric_cols[-1]))
            else:
                start_col_default = 0
                end_col_default   = max(0, len(self.df.columns) - 1)
        except Exception:
            logger.debug("Fallback: Spaltenbereich auf gesamte Breite")
            start_col_default = 0
            end_col_default   = max(0, len(self.df.columns) - 1)

        sample_rate_default = Cfg.Defaults.SAMPLERATE

        for entry, val in [
            (self.entry1, start_row_default),
            (self.entry2, end_row_default),
            (self.entry3, start_col_default),
            (self.entry4, end_col_default),
            (self.entry5, sample_rate_default),
        ]:
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, str(val))
            entry._is_placeholder = False
            entry.config(style="EntryNormal.TEntry", state="normal")

        if hasattr(self, "entry6") and self.entry6:
            self.entry6.config(state="normal")
            if self.entry6.get().strip() in ("", Cfg.Ph.FENSTERTYP):
                self.entry6.set(Cfg.Defaults.FENSTERTYP)

        if hasattr(self, "Verarbeitung_button") and self.Verarbeitung_button:
            self.Verarbeitung_button.configure(state="normal")
        for rb in ('rb_plots_spectrum', 'rb_plots', 'rb_spectrum', 'rb_none'):
            if hasattr(self, rb):
                getattr(self, rb).state(["!disabled"])

    # --------------------------------------------------------
    #  LADE-ZUSTAND
    # --------------------------------------------------------

    def _enter_loading_state(self):
        """Startet Spinner und zeigt Lade-Status."""
        self.loading = True
        threading.Thread(target=self.loading_animation, daemon=True).start()
        self.progress_label.config(text=Cfg.Status.GUI_LOADING)

    def _exit_loading_state(self):
        """Stoppt den Spinner und leert das Lade-Label."""
        self.loading = False
        self.progress_label.config(text="")

    def loading_animation(self):
        """Steuert den Lade-Spinner."""
        self.flood_gauge.pack(side=tk.LEFT, padx=10)
        self.flood_gauge.start()
        while self.loading:
            time.sleep(0.1)
        self.flood_gauge.stop()
        self.flood_gauge.pack_forget()

    # --------------------------------------------------------
    #  DATEN LADEN
    # --------------------------------------------------------

    def load_data(self):
        """Lädt die erste Datei über den normalen Dateidialog und öffnet danach
        das Datei-Sammel-Fenster, in dem bei Bedarf weitere Dateien hinzugefügt
        werden können (Button "Mehr Dateien"), bevor mit "Fertig" fortgefahren wird.
        """
        self._enter_loading_state()
        protocol_logger.info(Cfg.Logs.GUI_IMPORT_CLICK)

        file_path = filedialog.askopenfilename(filetypes=Cfg.Export.SUPPORTED_FILETYPES)
        self._exit_loading_state()

        if not file_path:
            protocol_logger.info(Cfg.Logs.GUI_IMPORT_CANCELLED)
            self.status_label.config(text=Cfg.Status.GUI_IMPORT_CANCELLED)
            return

        self.multi_file_manager.open_file_accumulator([file_path])

    def _load_single_file(self, file_path):
        """Lädt genau eine Datei über den bestehenden Single-Datei-Weg."""
        protocol_logger.info(Cfg.Logs.GUI_FILE_SELECTED.format(file_path))
        self.status_label.config(text=Cfg.Status.GUI_FILE_SELECTED.format(file_path))
        self.Gesamtpfad = Path(file_path)

        try:
            ext = self.Gesamtpfad.suffix.lower()
            if ext in ['.xlsx', '.xls']:
                self._load_excel(file_path)
            elif ext == '.csv':
                self._load_csv(file_path)
            else:
                raise ValueError(Cfg.Errors.FILE_UNSUPPORTED_FORMAT)
        except Exception as e:
            self._handle_load_failure(str(e))

    def _load_excel(self, file_path):
        """Lädt Excel-Datei und aktualisiert Sheet-Combobox."""
        with open(file_path, 'rb') as f:
            excel_raw = f.read()
            logger.debug(Cfg.Logs.GUI_EXCEL_RAW_DATA.format(len(excel_raw)))

        excel_file  = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        protocol_logger.info(Cfg.Logs.GUI_EXCEL_LOADED.format(file_path, sheet_names))

        if self.sheet_combobox is not None:
            self.sheet_combobox['values'] = sheet_names
            self.sheet_combobox.set(sheet_names[0] if sheet_names else "")
            self.sheet_combobox.config(state='readonly')

        if self.progress_label is not None:
            self.progress_label.config(text=Cfg.Status.GUI_SELECT_SHEET)

    def _load_csv(self, file_path):
        """Lädt CSV-Datei und aktiviert Eingabefelder."""
        self.sheet_combobox['values'] = ['CSV']
        self.sheet_combobox.set('CSV')
        self.sheet_combobox.config(state='disabled')

        file_handler           = FileHandler()
        file_handler.file_path = str(self.Gesamtpfad)
        result                 = file_handler.read_top(self.status_label, self.progress_label)

        if self._apply_loaded_dataset(result, timestamps_full=file_handler.zeitstempel):
            self._log_dataset_preview("CSV")
            self.status_label.config(text=Cfg.Status.GUI_CSV_LOADED)
            protocol_logger.info(Cfg.Logs.GUI_CSV_LOADED.format(file_path))
        else:
            self.status_label.config(text=Cfg.Status.GUI_LOAD_ERROR)

        self._exit_loading_state()

    def on_sheet_selected(self, event):
        """Handler für Sheet-Auswahl."""
        if not (self.Gesamtpfad and self.sheet_combobox.get()):
            self.status_label.config(text=Cfg.Status.GUI_NO_SHEET_SELECTED)
            return

        protocol_logger.info(Cfg.Logs.GUI_SHEET_SELECTED.format(self.sheet_combobox.get()))
        self.status_label.config(text=Cfg.Status.GUI_SHEET_PROCESSING.format(self.sheet_combobox.get()))

        try:
            file_handler           = FileHandler()
            file_handler.file_path = str(self.Gesamtpfad)
            result = file_handler.read_dws_excel(
                self.sheet_combobox.get(), self.status_label, self.progress_label
            )

            if self._apply_loaded_dataset(result, disable_sheet=True, timestamps_full=file_handler.zeitstempel):
                self._log_dataset_preview(f"EXCEL sheet={self.sheet_combobox.get()}")
                self.status_label.config(text=Cfg.Status.GUI_SHEET_LOADED.format(self.sheet_combobox.get()))
            else:
                self.status_label.config(text=Cfg.Status.GUI_SHEET_LOAD_ERROR)

        except Exception as e:
            logger.exception(Cfg.Logs.GUI_SHEET_LOAD_ERROR.format(str(e)))
            self.status_label.config(text=Cfg.Status.GUI_SHEET_LOAD_ERROR)

    def _apply_loaded_dataset(self, result, disable_sheet=False, timestamps_full=None):
        """Wendet geladene Daten auf GUI an."""
        if result[0] is None:
            return False

        self.df, self.temp_headers, self.temp_units = result
        self.timestamps_full = timestamps_full
        logger.info(
            "[DEBUG-ZEITACHSE] _apply_loaded_dataset: timestamps_full=%s",
            "None" if self.timestamps_full is None
            else f"{len(self.timestamps_full)} Werte, erster={self.timestamps_full.iloc[0]}"
        )
        self.temp_df = self.df.copy()
        self._prefill_from_df_and_enable()
        self._enable_entries_after_load()
        self.import_button.config(state='disabled')
        self.update_processing_button_state()

        if disable_sheet:
            self.sheet_combobox.config(state='disabled')
            self.progress_label.config(text="")

        if hasattr(self, 'layout_manager'):
            self.layout_manager.blink_tab(0)

        return True

    def _handle_load_failure(self, message):
        """Behandelt Fehler beim Laden."""
        self._exit_loading_state()
        logger.error(Cfg.Logs.GUI_LOADING_ERROR.format(message))
        self.status_label.config(text=Cfg.Status.GUI_LOADING_ERROR.format(message))
        protocol_logger.info(Cfg.Logs.GUI_LOADING_ERROR.format(message))

    def _enable_entries_after_load(self):
        """Aktiviert Eingabefelder nach erfolgreichem Laden."""
        return self.ui_control.enable_entries_after_load()

    def apply_icon(self, window):
        """Setzt das Giraffen-Icon auf ein beliebiges Toplevel-Fenster."""
        ico = getattr(self.root, '_tmp_ico', None)
        if ico:
            window.after(0, lambda w=window, i=ico: w.iconbitmap(i))

    def _log_dataset_preview(self, context):
        """Loggt eine Vorschau der geladenen Daten."""
        if self.df is None:
            return
        try:
            logger.info(
                "DATA_PREVIEW %s | shape=%s | columns=%s",
                context, self.df.shape, list(self.df.columns),
            )
            logger.info("DATA_HEAD %s\n%s", context, self.df.head(10).to_string(index=False))
        except Exception as e:
            logger.exception("Fehler beim Loggen der Datenvorschau: %s", e)

    # --------------------------------------------------------
    #  DATENVERARBEITUNG
    # --------------------------------------------------------

    def verarbeitung_button_setup(self):
        """Handler für Datenverarbeitung."""
        self._enter_loading_state()
        self.progress_label.config(text=Cfg.Status.GUI_PROCESSING_START)
        self.root.update()

        protocol_logger.info(
            Cfg.Logs.GUI_PROCESSING_START.format(
                self.entry1.get().strip(), self.entry2.get().strip(),
                self.entry3.get().strip(), self.entry4.get().strip(),
                self.entry5.get().strip(),
                self.entry6.get().strip() if hasattr(self, "entry6") else ""
            )
        )

        self._apply_default_values()
        self._enable_analysis_buttons()
        self._sync_data_validator()

        result = self.data_validator.validate_and_process(
            self.entry1, self.entry2, self.entry3, self.entry4,
            self.entry5, self.status_label
        )

        if all(x is not None for x in result):
            self._process_validated_data(result)
        else:
            logger.warning(Cfg.Logs.GUI_PROCESSING_FAILED)
            self.status_label.config(text=Cfg.Status.GUI_PROCESSING_FAILED)
            self._exit_loading_state()

    def _apply_default_values(self):
        """Setzt Standardwerte für leere Eingabefelder."""
        entries      = [self.entry1, self.entry2, self.entry3, self.entry4, self.entry5, self.entry6]
        placeholders = Cfg.Ph.EINGABE + [Cfg.Ph.FENSTERTYP]
        config       = [
            (entry, ph, dv[0], dv[1])
            for entry, ph, dv in zip(entries, placeholders, Cfg.Defaults.VALUES_CONFIG)
        ]

        aenderungen = []
        for entry, placeholder, default_value, msg in config:
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.insert(0, default_value)
                aenderungen.append(msg)

        if aenderungen:
            messagebox.showinfo("Standardwerte", "Default Werte übernommen")

    def _enable_analysis_buttons(self):
        """Aktiviert Analyse-Buttons."""
        self.status_label.config(text=Cfg.Texts.STATUS_VERARBEITUNG)
        if hasattr(self, 'overview_window_button'):
            self.overview_window_button.config(state="normal")

    def _sync_data_validator(self):
        """Synchronisiert DataValidator mit aktuellen Daten."""
        self.data_validator.df           = self.df
        self.data_validator.temp_df      = self.temp_df
        self.data_validator.headers      = self.temp_headers
        self.data_validator.units        = self.temp_units
        self.data_validator.temp_headers = self.temp_headers
        self.data_validator.temp_units   = self.temp_units
        self.data_validator.reset_active = self.reset_active

    def _process_validated_data(self, validation_result, save_subdir=None, open_overlay=True):
        """Verarbeitet validierte Daten.

        save_subdir: optionaler Unterordner unter spektren/ (z.B. Dateiname beim Batch-Import,
                     damit Plots/Spektren mehrerer Dateien mit gleichnamigen Signalen sich
                     nicht gegenseitig ueberschreiben).
        open_overlay: False unterdrueckt das automatische Oeffnen des Signalauswahl-Fensters
                      (z.B. beim Batch-Import, wo pro Datei bereits automatisch gespeichert wird).
        """
        samplerate_fs, hann_fenster, self.value, self.headers, self.units = validation_result
        logger.debug(Cfg.Logs.GUI_PROCESSING_DATA.format(self.value.shape))

        mode          = self.save_mode.get() if hasattr(self, 'save_mode') else "none"
        save_plots    = mode in ("plots", "both")
        save_spectrum = mode in ("spectrum", "both")

        self.dt      = 1.0 / samplerate_fs if samplerate_fs and samplerate_fs > 0 else None
        n_samples    = self.value.shape[0]
        self.t       = np.arange(n_samples) * self.dt if self.dt is not None else np.arange(n_samples)
        self.signals = [self.value[:, i] for i in range(self.value.shape[1])]
        self.spectrum_save_path = None

        # --- Echte Zeitstempel auf denselben Zeilenbereich zuschneiden wie self.t ---
        self.timestamps = None
        if self.timestamps_full is not None:
            try:
                start_row = self.data_validator.start_row
                end_row   = self.data_validator.end_row
                ts_slice  = self.timestamps_full.loc[start_row:end_row].to_numpy()
                logger.info(
                    "[DEBUG-ZEITACHSE] _process_validated_data: start_row=%s, end_row=%s, len(ts_slice)=%s, n_samples=%s",
                    start_row, end_row, len(ts_slice), n_samples
                )
                if len(ts_slice) == n_samples:
                    self.timestamps = ts_slice
                else:
                    logger.info("[DEBUG-ZEITACHSE] LAENGEN-MISMATCH -> self.timestamps bleibt None")
            except Exception:
                logger.exception("Zeitstempel konnten nicht auf den Zeilenbereich zugeschnitten werden")
        else:
            logger.info("[DEBUG-ZEITACHSE] _process_validated_data: self.timestamps_full ist None")

        logger.info(
            "[DEBUG-ZEITACHSE] Ergebnis: self.timestamps=%s",
            "None" if self.timestamps is None else f"{len(self.timestamps)} Werte"
        )

        if (save_plots or save_spectrum) and self.dt and self.dt > 0:
            if self.Gesamtpfad:
                save_dir = self.Gesamtpfad.parent / Cfg.Export.DEFAULT_SPECTRUM_PATH
            else:
                save_dir = Path(Cfg.Export.DEFAULT_SPECTRUM_PATH)
            if save_subdir:
                save_dir = save_dir / save_subdir
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = str(save_dir)
            time_str  = self.Gesamtpfad.stem if self.Gesamtpfad else ""

            dv = DatenVerarbeiter()
            dv.dt = self.dt

            for i, (signal, header, unit) in enumerate(zip(self.signals, self.headers, self.units)):
                if save_plots:
                    PlotManager.save_time_domain_plot(
                        self.t, signal, header, unit, time_str, i + 1, save_path
                    )
                if save_spectrum:
                    f, sig_abs, sig_arg = dv.calculate_fft(signal, self.t)
                    if f is not None:
                        PlotManager.save_frequency_domain_plot(
                            f, sig_abs, sig_arg, header, unit, i + 100, save_path
                        )

            if save_plots:
                PlotManager.save_overview_plot(
                    self.t, self.signals, self.headers, self.units, time_str, save_path
                )
            self.spectrum_save_path = save_path

        self.status_label.config(text=Cfg.Status.GUI_PROCESSING_SUCCESS.format(
            len(self.signals), len(self.headers)
        ))

        self._exit_loading_state()
        self._finalize_after_processing(open_overlay=open_overlay)
        protocol_logger.info(
            Cfg.Logs.GUI_PROCESSING_DONE.format(
                len(self.signals) if self.signals is not None else 0,
                len(self.headers) if self.headers is not None else 0,
                len(self.units)   if self.units   is not None else 0,
            )
        )

        t0 = self.t[0] if self.t is not None and len(self.t) > 0 else 0.0
        t1 = self.t[-1] if self.t is not None and len(self.t) > 0 else 0.0
        df = samplerate_fs / n_samples if samplerate_fs and n_samples > 0 else 0.0

        self.ui_control.finalize_after_processing(
            startzeit=t0,
            endzeit=t1,
            samples=n_samples,
            dt=self.dt,
            df=df
        )

    def _finalize_after_processing(self, open_overlay=True):
        """Finalisiert GUI nach erfolgreicher Verarbeitung."""

        if hasattr(self, 'Verarbeitung_button') and self.Verarbeitung_button:
            self.Verarbeitung_button.configure(state="disabled")

        for rb in ('rb_plots_spectrum', 'rb_plots', 'rb_spectrum', 'rb_none'):
            if hasattr(self, rb):
                getattr(self, rb).state(["disabled"])

        if hasattr(self, 'layout_manager'):
            self.layout_manager.blink_tab(
                1,
                times=Cfg.PlotStyle.BUTTON_BLINK_TIMES,
                interval=Cfg.PlotStyle.BUTTON_BLINK_DURATION
            )

        if open_overlay:
            self.root.after(0, self.show_multi_signal_overlay_window)

    def check_processing_ready(self):
        """Prüft ob alle Voraussetzungen für Datenverarbeitung erfüllt sind."""
        return self.df is not None

    def update_processing_button_state(self):
        """Aktualisiert den Zustand des Verarbeitung-Buttons."""
        return self.ui_control.update_processing_button_state()

    def log_save_options(self):
        """Protokolliert die Speicheroptionen."""
        mode = self.save_mode.get() if hasattr(self, "save_mode") else "none"
        protocol_logger.info("SAVE_OPTIONS mode=%s", mode)

    # --------------------------------------------------------
    #  ÜBERSICHT & PLOTS
    # --------------------------------------------------------

    def show_overview_window(self):
        """Zeigt den Übersichtsplot in einem separaten Fenster."""
        data_ready = bool(self.signals and self.headers and self.t is not None)
        protocol_logger.info(Cfg.Logs.GUI_OVERVIEW_OPEN.format(data_ready))

        if not data_ready:
            logger.info(Cfg.Status.GUI_NO_DATA)
            self.status_label.config(text=Cfg.Status.GUI_NO_DATA)
            return

        win = tb.Toplevel(self.root)
        win.title(Cfg.Texts.OVERVIEW_WINDOW_TITLE)
        self.apply_icon(win)

        fig    = plt.Figure(figsize=Cfg.Layout.Figure.FIG_SIZE_OVERVIEW, dpi=Cfg.PlotStyle.DEFAULT_DPI)
        canvas = FigureCanvasTkAgg(fig, master=win)

        toolbar_frame = ttk.Frame(win)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        NavigationToolbar2Tk(canvas, toolbar_frame)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        fig.suptitle(
            Cfg.Texts.OVERVIEW_PLOT_TITLE.format(len(self.signals)),
            fontsize=Cfg.Fonts.HEADER
        )
        PlotManager.plot_overview(
            fig, self.t, self.signals, self.headers, self.units,
            line_width=Cfg.PlotStyle.DEFAULT_LINE_WIDTH,
            marker_size=Cfg.PlotStyle.DEFAULT_MARKER_SIZE
        )
        canvas.draw()

        self.status_label.config(text=Cfg.Status.GUI_OVERVIEW_CREATED)
        protocol_logger.info(Cfg.Logs.GUI_OVERVIEW_CREATED.format(len(self.signals)))

    def show_multi_signal_overlay_window(self):
        """Öffnet ein Fenster zur Auswahl beliebig vieler Signale."""
        return self.plot_window_manager.show_multi_signal_overlay_window()

    def update_all_plot_windows(self):
        """Aktualisiert alle offenen Plot-Fenster mit den aktuellen Filter-Einstellungen."""
        if not hasattr(self, 'open_plot_windows'):
            return

        for plot_data in self.open_plot_windows[:]:
            try:
                if 'window' in plot_data and plot_data['window'].winfo_exists():
                    self._update_single_plot_window(plot_data)
            except Exception:
                logger.exception("Fehler beim Aktualisieren des Plot-Fensters")
                self.open_plot_windows.remove(plot_data)

    def _update_single_plot_window(self, plot_data):
        """Aktualisiert ein einzelnes Plot-Fenster."""
        if 'signal_idx' not in plot_data or 'canvas' not in plot_data:
            return

        signal_idx = plot_data['signal_idx']
        if signal_idx < len(self.signals):
            signal          = self.signals[signal_idx]
            filtered_signal = self.filter_manager.apply_filter(signal)

            if 'fig' in plot_data and 'canvas' in plot_data:
                plot_data['fig'].clear()
                ax = plot_data['fig'].add_subplot(111)
                ax.plot(filtered_signal)
                ax.set_title(f"Signal {signal_idx}")
                plot_data['canvas'].draw()

    def create_live_plot_window(self, selected_signal):
        """Erstellt ein Plot-Fenster mit Live-Aktualisierung."""
        return self.plot_window_manager.create_live_plot_window(selected_signal)

    def update_single_plot(self, plot_window_data):
        """Aktualisiert einen einzelnen Plot (dynamische Achsen je Auswahl)."""
        return self.plot_window_manager.update_single_plot(plot_window_data)

    # --------------------------------------------------------
    #  FILTER
    # --------------------------------------------------------

    def on_filter_checkbox_changed(self):
        """Wird aufgerufen wenn Filter-Checkbox geändert wird."""
        if self.filter_active_var.get():
            self.ui_control.create_filter_setup_dialog(
                on_success=self._update_main_plot_with_filter,
                on_cancel=lambda: self.filter_active_var.set(False)
            )
        else:
            self._update_main_plot_without_filter()

    def _update_main_plot_with_filter(self):
        """Zeigt 2 Subplots: Original + gefiltertes Signal."""
        idx = self.selected_signal
        if idx is None:
            messagebox.showwarning("Hinweis", Cfg.Errors.GUI_SELECT_SIGNAL)
            self.filter_active_var.set(False)
            return

        t, original, _, header, unit = self.analysis_manager._get_signal_for_operations(idx)
        filtered = self.filter_manager.apply_filter(original)

        win = tb.Toplevel(self.root)
        win.title(Cfg.Texts.FILTER_PLOT_TITLE.format(header))
        self.apply_icon(win)

        fig    = plt.Figure(figsize=Cfg.Layout.Figure.FIG_SIZE_FILTER)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        ax1 = fig.add_subplot(211)
        ax1.plot(t, original, color=Cfg.Colors.SIGNAL_ORIGINAL,
                 label=f"{header} [{unit}]",
                 linewidth=Cfg.PlotStyle.DEFAULT_LINE_WIDTH)
        ax1.set_title(Cfg.Texts.FILTER_PLOT_ORIGINAL_TITLE.format(header))
        ax1.set_xlabel(Cfg.AxisLabels.TIME)
        ax1.set_ylabel(f"Amplitude [{unit}]")
        ax1.grid(True)
        ax1.legend()

        ax2 = fig.add_subplot(212, sharex=ax1)
        ax2.plot(t, filtered, color=Cfg.Colors.SIGNAL_FILTERED,
                 label=f"{header} {Cfg.Texts.FILTER_PLOT_FILTERED_TITLE.format(self.filter_manager.filter_type)} [{unit}]",
                 linewidth=Cfg.PlotStyle.DEFAULT_LINE_WIDTH)
        ax2.set_title(Cfg.Texts.FILTER_PLOT_FILTERED_TITLE_FULL.format(header, self.filter_manager.filter_type))
        ax2.set_xlabel(Cfg.AxisLabels.TIME)
        ax2.set_ylabel(f"Amplitude [{unit}]")
        ax2.grid(True)
        ax2.legend()

        fig.tight_layout()
        canvas.draw()
        self.status_label.config(text=Cfg.Status.FILTER_PLOT_CREATED)

    def _update_main_plot_without_filter(self):
        """Filter deaktiviert – aktualisiert Status."""
        self.status_label.config(text=Cfg.Status.FILTER_INACTIVE)
        protocol_logger.info(Cfg.Logs.GUI_FILTER_DEACTIVATED)

    def update_filter_plot(self):
        """Aktualisiert den Filter-Frequenzgang-Plot."""
        if not hasattr(self, 'filter_fig') or not hasattr(self, 'filter_canvas'):
            self.status_label.config(text=Cfg.Status.GUI_NO_FILTER_PLOT)
            return

        self.filter_fig.clear()
        w, magnitude_db, phase_deg = self.filter_manager.get_frequency_response()

        if w is None:
            self.status_label.config(text=Cfg.Status.FILTER_CALC_FAILED)
            return

        filter_info = {
            'type':           self.filter_manager.filter_type,
            'characteristic': self.filter_manager.characteristic,
            'order':          self.filter_manager.order,
            'sample_rate':    self.filter_manager.sample_rate,
            'cutoff':         self.filter_manager.cutoff_frequency,
            'cutoff2':        self.filter_manager.cutoff_frequency2,
        }

        PlotManager.plot_filter_response(self.filter_fig, w, magnitude_db, phase_deg, filter_info)
        self.filter_canvas.draw()
        self.status_label.config(text=Cfg.Status.FILTER_PLOT_UPDATED)

    def update_filter_plot_short(self):
        """Delegiert an UiControlManager."""
        return self.ui_control.update_filter_plot()

    def show_filter_characteristic_window(self):
        """Zeigt Fenster mit der aktuellen Filter-Charakteristik, Plot und Koeffizienten."""
        return self.ui_control.show_filter_characteristic_window()

    def create_filter_setup_dialog(self, on_success=None):
        """Öffnet einen Eingabe-Dialog für Filter-Parameter."""
        return self.ui_control.create_filter_setup_dialog(on_success)

    def _is_filter_ready(self) -> bool:
        """Prüft, ob Filter wirklich anwendbar ist (Typ, Grenzfrequenz(en), Samplerate, Nyquist)."""
        if not hasattr(self, "filter_manager") or not self.filter_manager:
            return False

        fm = self.filter_manager
        if fm.filter_type in (None, "", Cfg.Defaults.FILTER_TYP, "Filter wählen:"):
            return False

        # Samplefrequenz aus entry5 lesen - nach Datei laden enthält entry5 "Samplefrequenz = 20"
        fs = None
        try:
            fs_txt = self.entry5.get().strip()
            if fs_txt and "z.B." not in fs_txt and "auswählen" not in fs_txt:
                # Zahl extrahieren (aus "Samplefrequenz = 20" oder direkt "20")
                fs = float(fs_txt.split("=")[-1].strip().replace(",", "."))
        except Exception:
            pass

        # Fallback: Samplefrequenz vom Filter-Manager
        if (fs is None or fs <= 0) and fm.sample_rate:
            fs = fm.sample_rate

        if fs is None or fs <= 0:
            return False

        ny = fs / 2.0
        f1 = fm.cutoff_frequency
        f2 = fm.cutoff_frequency2

        if fm.filter_type in ("Tiefpass", "Hochpass"):
            if f1 is None or not (0 < f1 < ny):
                return False
        elif fm.filter_type == "Bandpass":
            if f2 is not None:
                if f1 is None or not (0 < f1 < ny) or not (0 < f2 < ny) or not (f1 < f2):
                    return False
            else:
                if f1 is None or not (0 < f1 < ny):
                    return False
        else:
            return False

        return True

    # --------------------------------------------------------
    #  RESET
    # --------------------------------------------------------

    def reset_all(self):
        """Komplett-Reset aller Daten und GUI-Elemente."""
        return self.ui_control.reset_all()

    def reset_inputs(self):
        """Setzt nur die Eingabefelder zurück (Daten bleiben geladen)."""
        return self.ui_control.reset_inputs()

    def on_reset_selected(self, selected):
        """Delegiert an UiControlManager."""
        return self.ui_control.on_reset_selected(selected)

    # --------------------------------------------------------
    #  ANALYSE
    # --------------------------------------------------------

    def _get_selected_signal_index(self):
        return self.analysis_manager._get_selected_signal_index()

    def _get_signal_for_operations(self, idx):
        return self.analysis_manager._get_signal_for_operations(idx)

    def _open_result_window(self, title, plot_func):
        return self.analysis_manager._open_result_window(title, plot_func)

    # --------------------------------------------------------
    #  EVENT HANDLER
    # --------------------------------------------------------

    def on_filter_changed(self, event=None):
        """Handler für Änderungen in den Filter-Comboboxen."""
        return self.ui_control.on_window_function_changed(event)

    def on_window_function_changed(self, event=None):
        """Delegiert an EventHandler und aktualisiert Button-Status."""
        self.ui_control.on_window_function_changed(event)
        self.update_processing_button_state()

    # --------------------------------------------------------
    #  PFADE & HILFE
    # --------------------------------------------------------

    def show_path_window(self, selected=None):
        """Delegiert an UiControlManager."""
        return self.ui_control.show_path_window(selected)

    def show_help(self):
        """Öffnet die Bedienungsanleitung als PDF."""
        html_path = self.get_resource_path("docs_bilder/Bedienungsanleitung_Messtool.html")
        pdf_path = self.get_resource_path("docs_bilder/Bedienungsanleitung_Messtool.pdf")

        if not os.path.exists(html_path):
            protocol_logger.error("HTML-Anleitung nicht gefunden: %s", html_path)
            messagebox.showerror("Fehler", f"Bedienungsanleitung nicht gefunden:\n{html_path}")
            return

        try:
            # HTML zu PDF konvertieren
            with open(html_path, 'r', encoding='utf-8') as html_file:
                html_content = html_file.read()

            with open(pdf_path, 'wb') as pdf_file:
                pisa_status = pisa.CreatePDF(
                    html_content,
                    pdf_file,
                    encoding='utf-8'
                )

            if pisa_status.err:
                protocol_logger.error("Fehler beim PDF-Konvertieren")
                messagebox.showerror("Fehler", "Die Bedienungsanleitung konnte nicht in PDF konvertiert werden.")
                return

            # PDF öffnen
            protocol_logger.info("HELP_OPEN pdf=%s", pdf_path)
            if sys.platform.startswith("win"):
                os.startfile(pdf_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", pdf_path])
            else:
                subprocess.call(["xdg-open", pdf_path])

        except Exception as e:
            protocol_logger.exception("Fehler beim Öffnen der Anleitung")
            messagebox.showerror("Fehler", f"Bedienungsanleitung konnte nicht geöffnet werden:\n{str(e)}")
