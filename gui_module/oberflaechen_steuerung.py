"""
GUI Manager - Zentrale Verwaltung aller GUI-Elemente
======================================================
Kombiniert State Management, Event-Handling und Dialog-Verwaltung:
- GUI-Zustandsverwaltung (Reset, Enable/Disable)
- Event-Verarbeitung (Button-Clicks, Combobox-Auswahl)
- Dialog-Fenster (Filter-Charakteristik, etc.)
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from tkinter import ttk

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import pandas as pd

# ============================================================
#  IMPORTS – Eigene Klassen
# ============================================================
from gui_module import meldungen as messagebox
from gui_module.plot_manager import PlotManager
from hilfsklassen.datei_handler import DateiHandler
from hilfsklassen.zentrales_logging import get_protocol_logger, log_session_end
from konfiguration import Cfg

# ============================================================
#  LOGGING
# ============================================================
logger          = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()


# ============================================================
#  KLASSE
# ============================================================
class OberflaechenSteuerung:
    """
    Zentrale Verwaltung aller GUI-Operationen:
    - State Management (reset_all, reset_inputs, enable_entries_after_load)
    - Event-Handling (on_reset_selected, on_sheet_selected, show_path_window)
    - Dialog-Verwaltung (show_filter_characteristic_window, etc.)

    Diese Klasse ersetzt die bisherigen drei Manager für bessere Lesbarkeit
    und weniger Dateien/Imports.
    """

    def __init__(self, gui_manager):

        # --- Referenzen ---
        self.gui = gui_manager

    # --------------------------------------------------------
    #  VISUELLE KONFIGURATION
    # --------------------------------------------------------

    def apply_visual_defaults(self):
        """Setzt zentrale visuelle Defaults für das Hauptfenster."""
        self.gui.root.option_add("*Font", f"{Cfg.Fonts.FAMILY} {Cfg.Fonts.SMALL}")
        style = ttk.Style(self.gui.root)
        style.configure(".",               font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(2, 1))
        style.configure("TLabel",          font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(2, 1))
        style.configure("Status.TLabel",   font=(Cfg.Fonts.FAMILY, Cfg.Fonts.STATUS))
        style.configure("TButton",         padding=(10, 5))
        style.configure("TEntry",          font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(4, 2))
        style.configure("TCombobox",       font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(4, 2))
        style.configure("TCheckbutton",    font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(2, 1))
        style.configure("TLabelframe.Label", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold"))
        style.configure("EntryNormal.TEntry",      foreground="black")
        style.configure("EntryPlaceholder.TEntry", foreground="gray45")
        style.map("EntryNormal.TEntry",      foreground=[("readonly", "black"),  ("disabled", "black")])
        style.map("EntryPlaceholder.TEntry", foreground=[("readonly", "gray45"), ("disabled", "gray45")])
        style.map("TEntry",    foreground=[("readonly", "black"),  ("disabled", "gray45")])
        style.map("TCombobox", foreground=[("readonly", "black"),  ("disabled", "gray45")])

    def configure_root_lifecycle(self):
        """Registriert zentrale Root-Callbacks (Close + Exception-Handling)."""
        def on_main_window_close():
            session_id = getattr(self.gui, "session_id", None)
            end_time   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_session_end(session_id=session_id, end_time=end_time, reason="window_close")
            self.gui.root.destroy()

        def report_callback_exception(exc_type, exc_value, exc_traceback):
            logger.exception(
                "Unhandled Tkinter callback exception",
                exc_info=(exc_type, exc_value, exc_traceback),
            )

        self.gui.root.report_callback_exception = report_callback_exception
        self.gui.root.protocol("WM_DELETE_WINDOW", on_main_window_close)

    def setup_placeholder(self, entry, placeholder_text):
        """Richtet Placeholder-Verhalten für Entry-Felder ein."""
        try:
            entry.unbind('<FocusIn>')
            entry.unbind('<FocusOut>')
        except Exception as e:
            logger.debug("Placeholder-Bindings konnten nicht entfernt werden: %s", e)

        def on_focus_in(event):
            is_placeholder = getattr(entry, "_is_placeholder", False)
            if entry.get() == placeholder_text or is_placeholder:
                entry.delete(0, tk.END)
                entry.configure(style="EntryNormal.TEntry")
                entry._is_placeholder = False

        def on_focus_out(event):
            current_text = entry.get().strip()
            if not current_text or current_text == placeholder_text:
                entry.delete(0, tk.END)
                entry.insert(0, placeholder_text)
                entry.configure(style="EntryPlaceholder.TEntry")
                entry._is_placeholder = True

        entry.delete(0, tk.END)
        entry.insert(0, placeholder_text)
        entry.configure(style="EntryPlaceholder.TEntry")
        entry._is_placeholder = True

        entry.bind('<FocusIn>',  on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    # --------------------------------------------------------
    #  HILFSMETHODEN (intern)
    # --------------------------------------------------------

    def _reset_input_entries(self, disable_after=False):
        """Setzt Eingabe-Entries (entry1–5) auf Platzhalter zurück."""
        if hasattr(self.gui, "ganze_datei_var"):
            self.gui.ganze_datei_var.set(True)
        if hasattr(self.gui, "datei_info_label") and self.gui.datei_info_label is not None:
            self.gui.datei_info_label.config(text="")

        placeholders = Cfg.Ph.EINGABE
        entries      = [self.gui.entry1, self.gui.entry2, self.gui.entry3,
                        self.gui.entry4, self.gui.entry5]
        for entry, placeholder in zip(entries, placeholders):
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.configure(style="EntryPlaceholder.TEntry")
            entry._is_placeholder = True
            if disable_after:
                entry.config(state="disabled")

    def _reset_output_entries(self):
        """Setzt Ausgabe-Entries (entry7–11) auf Platzhalter zurück."""
        output_placeholders = Cfg.Ph.AUSGABE
        output_entries      = [self.gui.entry7, self.gui.entry8, self.gui.entry9,
                                self.gui.entry10, self.gui.entry11]
        for entry, placeholder in zip(output_entries, output_placeholders):
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.configure(style="EntryPlaceholder.TEntry")
            entry._is_placeholder = True
            entry.config(state="readonly")

    def _set_radiobutton_state(self, state: str):
        """Setzt alle Radiobuttons auf 'normal' oder 'disabled'."""
        for rb in ('rb_plots_spectrum', 'rb_plots', 'rb_spectrum', 'rb_none'):
            if hasattr(self.gui, rb):
                if state == "normal":
                    getattr(self.gui, rb).state(["!disabled"])
                else:
                    getattr(self.gui, rb).state(["disabled"])

    # --------------------------------------------------------
    #  STATE MANAGEMENT
    # --------------------------------------------------------

    def reset_all(self):
        """Setzt die gesamte GUI und alle Daten zurück."""
        protocol_logger.info("RESET action=all")
        self.gui.reset_active = True

        # --- Mehrfachdatei-Panel ggf. schließen und normales Notebook wiederherstellen ---
        # is_active() statt winfo_ismapped(): Letzteres haengt von der Sichtbarkeit
        # des gesamten Fensterbaums ab und liefert in manchen Zustaenden faelschlich
        # False, obwohl das Panel tatsaechlich angezeigt wird - dann wuerde _cancel()
        # hier uebersprungen und das Panel bliebe stehen (siehe is_active()-Docstring).
        if hasattr(self.gui, 'multi_file_manager') and self.gui.multi_file_manager.is_active():
            self.gui.multi_file_manager._cancel()

        # --- Offene Fenster schließen ---
        for plot_data in self.gui.open_plot_windows:
            if plot_data.get('window') is not None and plot_data['window'].winfo_exists():
                plot_data['window'].destroy()
        self.gui.open_plot_windows.clear()

        # Schließe auch Analysis-Fenster
        self.gui.plot_window_manager.close_all_analysis_windows()

        if self.gui.plot_window_manager.active_signal_window is not None:
            try:
                self.gui.plot_window_manager.active_signal_window.destroy()
            except Exception as e:
                logger.debug("Aktives Signalfenster konnte nicht geschlossen werden: %s", e)
            self.gui.plot_window_manager.active_signal_window = None

        # --- Datenstatus zurücksetzen ---
        self.gui.t            = None
        self.gui.timestamps_full = None
        self.gui.timestamps   = None
        self.gui.nS           = None
        self.gui.dt           = None
        self.gui.CF           = None
        self.gui.signals      = []
        self.gui.value        = None
        self.gui.df           = None
        self.gui.headers      = []
        self.gui.units        = []
        self.gui.Gesamtpfad   = None
        self.gui.temp_df      = None
        self.gui.temp_headers = []
        self.gui.temp_units   = []

        # --- GUI zurücksetzen ---
        self._reset_input_entries(disable_after=True)

        self.gui.entry6.config(state='normal')
        self.gui.entry6.set(Cfg.Defaults.FENSTERTYP)
        self.gui.entry6.config(state='disabled')

        self.gui.flood_gauge.stop()
        self.gui.flood_gauge.pack_forget()

        self._reset_output_entries()

        self.gui.sheet_combobox.set(Cfg.Texts.CB_CSV_DEFAULT)
        self.gui.sheet_combobox['values'] = [Cfg.Texts.CB_CSV_DEFAULT]
        self.gui.sheet_combobox.config(state="disabled")

        if hasattr(self.gui, 'save_mode'):
            self.gui.save_mode.set("none")
        self._set_radiobutton_state("disabled")

        if hasattr(self.gui, 'overview_window_button'):
            self.gui.overview_window_button.config(state="disabled")

        self.gui.import_button.config(state="normal")
        self.gui.status_label.config(text=Cfg.Texts.STATUS_NEUE_EINGABEN)
        self.gui.progress_label.config(text="")

        self.gui.load_data_active  = False
        self.gui.reset_gui_active  = False

    def reset_inputs(self):
        """Setzt nur die Eingabefelder zurück, bewahrt aber die Daten."""
        protocol_logger.info("RESET action=inputs")

        if self.gui.temp_df is not None and isinstance(self.gui.temp_df, pd.DataFrame):
            self.gui.df = self.gui.temp_df.copy()
            logger.info("DataFrame für erneute Verarbeitung wiederhergestellt")

        self.gui.reset_active = False

        self._reset_input_entries(disable_after=False)

        self.gui.entry6.config(state='normal')
        self.gui.entry6.set(Cfg.Defaults.FENSTERTYP)

        self._reset_output_entries()

        if self.gui.Gesamtpfad:
            if self.gui.Gesamtpfad.suffix.lower() in ['.xlsx', '.xls']:
                self.gui.sheet_combobox.config(state="readonly")
            else:
                self.gui.sheet_combobox.config(state="disabled")
        else:
            self.gui.sheet_combobox.config(state="disabled")

        self.gui.status_label.config(text=Cfg.Texts.STATUS_NEUE_EINGABEN)
        self.gui.Verarbeitung_button.config(state="normal")
        self._set_radiobutton_state("normal")
        if hasattr(self.gui, 'overview_window_button'):
            self.gui.overview_window_button.config(state="disabled")

        # --- Offene Fenster schließen ---
        for plot_data in self.gui.open_plot_windows:
            if plot_data.get('window') is not None and plot_data['window'].winfo_exists():
                plot_data['window'].destroy()
        self.gui.open_plot_windows.clear()

        if self.gui.plot_window_manager.active_signal_window is not None:
            try:
                self.gui.plot_window_manager.active_signal_window.destroy()
            except Exception as e:
                logger.debug("Aktives Signalfenster konnte nicht geschlossen werden: %s", e)
            self.gui.plot_window_manager.active_signal_window = None

    def enable_entries_after_load(self):
        """Aktiviert alle Eingabefelder nach dem Laden einer Datei."""
        placeholders = Cfg.Ph.EINGABE
        entries      = [self.gui.entry1, self.gui.entry2, self.gui.entry3, self.gui.entry4]
        for entry, placeholder in zip(entries, placeholders):
            entry.config(state='normal')
            self.setup_placeholder(entry, placeholder)

        # entry5 (Samplerate): NUR mit Placeholder-Verhalten einrichten, wenn es
        # gerade nicht gesperrt ist. _prefill_from_df_and_enable() (laeuft VOR
        # dieser Methode) sperrt es und traegt die aus echten Zeitstempeln
        # berechnete reale Samplerate ein, sobald die Datei welche hat - das
        # wuerde hier sonst sofort wieder ueberschrieben.
        if str(self.gui.entry5.cget('state')) != 'disabled':
            self.gui.entry5.config(state='normal')
            self.setup_placeholder(self.gui.entry5, Cfg.Ph.SAMPLERATE)

        self.gui.entry6.config(state='normal')

    def update_processing_button_state(self):
        """Aktualisiert den State des Verarbeitungs-Buttons und der Radiobuttons."""
        state = "normal" if self.gui.check_processing_ready() else "disabled"
        self.gui.Verarbeitung_button.configure(state=state)
        self._set_radiobutton_state(state)

    # --------------------------------------------------------
    #  EVENT HANDLING
    # --------------------------------------------------------

    def on_reset_selected(self, selected):
        """Handler für Reset-Auswahl per Button."""
        protocol_logger.info("UI_SELECT reset=%s", selected)
        if selected == Cfg.Texts.RESET_KOMPLETT_DESC:
            self.reset_all()
            if hasattr(self.gui, 'layout_manager'):
                self.gui.layout_manager.expand_sidebar_if_collapsed()
                self.gui.layout_manager.expand_bottom_panel_if_collapsed()
        elif selected == Cfg.Texts.RESET_EINGABE_DESC:
            # Bei mehreren Dateien (Mehrfachdatei-Panel aktiv): nicht die normale
            # Einzeldatei-Eingabe zuruecksetzen (die geladenen Dateien sollen
            # erhalten bleiben), sondern Signalauswahl schliessen und zurueck zu
            # Schritt 1 (Samplefrequenz/Fensterfunktion).
            if hasattr(self.gui, "multi_file_manager") and self.gui.multi_file_manager.is_active():
                self.gui.multi_file_manager.return_to_step1()
            else:
                self.reset_inputs()
                self.gui.flood_gauge.stop()
                self.gui.flood_gauge.pack_forget()
            if hasattr(self.gui, 'layout_manager'):
                self.gui.layout_manager.expand_bottom_panel_if_collapsed()

    def on_sheet_selected(self, event):
        """Handler für Sheet-Auswahl in Excel-Dateien."""
        if not (self.gui.Gesamtpfad and self.gui.sheet_combobox.get()):
            return
        try:
            file_handler           = DateiHandler()
            file_handler.file_path = str(self.gui.Gesamtpfad)
            result = file_handler.read_dws_excel(
                self.gui.sheet_combobox.get(),
                self.gui.status_label,
                self.gui.progress_label
            )
            self.gui._apply_loaded_dataset(result, disable_sheet=True)
        except Exception as e:
            logger.exception("Fehler beim Laden des Sheets: %s", e)
            self.gui.status_label.config(text=f"{Cfg.Texts.ERROR_SHEET_LOAD} {str(e)}")

    def on_window_function_changed(self, event=None):
        """Handler für Änderungen der Fensterfunktion."""
        selected = self.gui.entry6.get()
        if selected == Cfg.Ph.FENSTERTYP:
            return
        logger.info("Fensterfunktion geändert auf: %s", selected)
        protocol_logger.info("WINDOW_FUNCTION selected=%s", selected)

    def show_path_window(self, selected=None):
        """Zeigt ein Fenster mit dem gewählten Pfad an."""
        if selected == Cfg.Texts.BTN_HERKUNFTSPFAD:
            path  = str(self.gui.Gesamtpfad) if self.gui.Gesamtpfad else Cfg.Texts.PFAD_HERKUNFT_EMPTY
            title = Cfg.Texts.PFAD_HERKUNFT_TITLE
        elif selected == Cfg.Texts.BTN_SPEICHERPFAD:
            path  = str(self.gui.spectrum_save_path) if self.gui.spectrum_save_path else Cfg.Texts.PFAD_SPEICHER_EMPTY
            title = Cfg.Texts.PFAD_SPEICHER_TITLE
        else:
            return
        messagebox.showinfo(title, path)
        protocol_logger.info("PATH_VIEW type=%s", selected)

    # --------------------------------------------------------
    #  DIALOG-VERWALTUNG
    # --------------------------------------------------------

    def show_filter_characteristic_window(self):
        """
        Zeigt Fenster mit der aktuellen Filter-Charakteristik:
        - Filter-Parameter oben
        - Frequenzgang-Plot links
        - Filter-Koeffizienten rechts
        """
        if not hasattr(self.gui, 'filter_manager') or not self.gui.filter_manager:
            logger.info("Kein FilterManager verfügbar")
            return

        protocol_logger.info("FILTER_CHARACTERISTIC_OPEN")

        if self.gui.characteristic_window and self.gui.characteristic_window.winfo_exists():
            self.gui.characteristic_window.destroy()

        filter_info      = self.gui.filter_manager.get_filter_info()
        layout           = self.gui.layout_manager.create_filter_characteristic_layout(filter_info)
        info_text_widget = layout["info_text_widget"]

        b, a, sos = self.gui.filter_manager.get_filter_coefficients()

        self.update_filter_plot()

        if b is None or a is None:
            sr = filter_info.get('sample_rate')
            cf = filter_info.get('cutoff')
            if sr and cf and cf >= sr / 2:
                info_text = (
                    f"FEHLER: Ungültige Filter-Parameter!\n\n"
                    f"Die Grenzfrequenz ({cf} Hz) muss kleiner als die\n"
                    f"Nyquist-Frequenz ({sr/2} Hz) sein!\n\n"
                    f"Nyquist-Frequenz = Abtastrate / 2 = {sr} / 2 = {sr/2} Hz\n\n"
                    f"Bitte korrigieren Sie die Grenzfrequenz oder erhöhen\n"
                    f"Sie die Abtastrate.\n"
                )
            else:
                info_text = (
                    "Filter-Koeffizienten konnten nicht berechnet werden.\n\n"
                    "Mögliche Ursachen:\n"
                    "- Grenzfrequenz nicht gesetzt\n"
                    "- Abtastrate nicht gesetzt\n"
                    "- Ungültige Frequenzkombination\n"
                )
        else:
            info_text = self.gui.filter_manager.format_filter_info_text(
            )

        for line in info_text.splitlines():
            info_text_widget.insert("", tk.END, values=(line,))

        self.gui.center_window(self.gui.characteristic_window)

    def update_filter_plot(self):
        """Aktualisiert den Filter-Frequenzgang-Plot."""
        if not hasattr(self.gui, 'filter_fig') or not hasattr(self.gui, 'filter_canvas'):
            return

        self.gui.filter_fig.clear()

        w, magnitude_db, phase_deg = self.gui.filter_manager.get_frequency_response()

        filter_info = {
            'type':           self.gui.filter_manager.filter_type,
            'characteristic': self.gui.filter_manager.characteristic,
            'order':          self.gui.filter_manager.order,
            'sample_rate':    self.gui.filter_manager.sample_rate,
            'cutoff':         self.gui.filter_manager.cutoff_frequency,
            'cutoff2':        self.gui.filter_manager.cutoff_frequency2,
        }

        PlotManager.plot_filter_response(self.gui.filter_fig, w, magnitude_db, phase_deg, filter_info)
        self.gui.filter_canvas.draw()

    def close_all_dialogs(self):
        """Schließt alle offenen Dialoge."""
        if hasattr(self.gui, 'characteristic_window') and self.gui.characteristic_window:
            try:
                if self.gui.characteristic_window.winfo_exists():
                    self.gui.characteristic_window.destroy()
            except tk.TclError:
                pass

    def get_open_dialog(self, dialog_name):
        """Gibt ein offenes Dialog-Fenster zurück, falls es existiert."""
        if dialog_name == 'characteristic' and hasattr(self.gui, 'characteristic_window'):
            if self.gui.characteristic_window and self.gui.characteristic_window.winfo_exists():
                return self.gui.characteristic_window
        return None

    # --------------------------------------------------------
    #  PLATZHALTER (zukünftige Erweiterungen)
    # --------------------------------------------------------

    def create_filter_setup_dialog(self, on_success=None):
        """Platzhalter für zukünftigen Filter-Setup-Dialog."""
        pass

    def show_settings_dialog(self):
        """Platzhalter für zukünftige Settings-Dialoge."""
        pass

    def show_export_dialog(self):
        """Platzhalter für Export-Dialog."""
        pass

    def finalize_after_processing(self, startzeit, endzeit, samples, dt, df):
        """Fixiert Eingabefelder und befüllt Ausgabefelder nach Datenverarbeitung."""

        # -------- Eingabefelder fixieren --------
        input_map = [
            (self.gui.entry1, Cfg.Ph.START_REIHE),
            (self.gui.entry2, Cfg.Ph.END_REIHE),
            (self.gui.entry3, Cfg.Ph.START_SPALTE),
            (self.gui.entry4, Cfg.Ph.END_SPALTE),
            (self.gui.entry5, Cfg.Ph.SAMPLERATE),
        ]

        for entry, label in input_map:
            entry.config(state="normal")
            value = entry.get()
            base_label = label.split(" z")[0]
            entry.delete(0, tk.END)
            entry.insert(0, f"{base_label} = {value}")
            entry.config(style="EntryNormal.TEntry", state="readonly")

        # -------- Combobox fixieren --------
        self.gui.entry6.config(state="disabled")

        # -------- Ausgabefelder befüllen --------
        outputs = [
            (self.gui.entry7,  Cfg.Ph.STARTZEIT, startzeit),
            (self.gui.entry8,  Cfg.Ph.ENDZEIT,   endzeit),
            (self.gui.entry9,  Cfg.Ph.SAMPLES,   samples),
            (self.gui.entry10, Cfg.Ph.DT,        dt),
            (self.gui.entry11, Cfg.Ph.DF,        df),
        ]

        for entry, label, value in outputs:
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, f"{label} = {value}")
            entry.config(style="EntryNormal.TEntry", state="readonly")