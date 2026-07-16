"""
Mehrfachdatei Manager - Import mehrerer Messdateien
=====================================================
Erlaubt das gleichzeitige Einlesen mehrerer Excel/DWS/CSV/TOP-Dateien.
Ersetzt bei mehreren Dateien das Eingabedaten/Ausgabedaten-Notebook
unten im Hauptfenster durch einen zweistufigen Ablauf:
  Schritt 1: globale Einstellungen (Samplefrequenz, Fenstertyp)
  Schritt 2: ein Tab pro Datei mit eigenem Zeilen-/Spaltenbereich
             (oder "Ganze Datei verwenden")
Beim Verarbeiten laeuft jede Datei unabhaengig durch die bestehende
Einzel-Datei-Pipeline (gui._process_validated_data) - jede Datei bekommt
ihre eigenen Plots/Spektren in spektren/<Dateiname>/. Alle Signale aller
Dateien landen danach gemeinsam in EINEM Signalauswahl-Fenster (jedes
Signal behaelt seine eigene Zeitachse, siehe PlotManager.t_for_idx).
Bei genau einer Datei bleibt der bisherige Weg (bottom_notebook)
unveraendert aktiv.
"""

# ============================================================
#  IMPORTS - Standardbibliotheken
# ============================================================
import logging
from pathlib import Path

# ============================================================
#  IMPORTS - Drittanbieter
# ============================================================
import numpy as np
import pandas as pd
import ttkbootstrap as tb
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ============================================================
#  IMPORTS - Eigene Klassen
# ============================================================
from hilfsklassen.datei_handler import FileHandler
from hilfsklassen.daten_validator import DataValidator
from hilfsklassen.zentrales_logging import get_protocol_logger
from konfiguration import Cfg

# ============================================================
#  LOGGING
# ============================================================
logger          = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()

# --- Farbpalette fuer die Datei-Tab-Kopfzeilen ---
_TAB_COLORS = ["#3f6fa8", "#4a8a5c", "#a8703f", "#7a4a9c", "#b5424a", "#3f9c9c", "#8b4a52", "#5c7a3f"]


class _DummyLabel:
    """No-op Ersatz fuer status_label/progress_label Parameter (Panel zeigt eigene Fehler an)."""

    def config(self, **kwargs):
        pass


# ============================================================
#  KLASSE
# ============================================================
class MehrfachDateiManager:
    """Verwaltet das eingebettete Mehrfachdatei-Panel und die unabhaengige Batch-Verarbeitung aller Dateien."""

    def __init__(self, gui_manager):
        self.gui   = gui_manager
        self.files = []

    # --------------------------------------------------------
    #  HILFSMETHODEN
    # --------------------------------------------------------

    @staticmethod
    def _compute_default_range(df):
        """Berechnet Standard-Zeilen-/Spaltenbereich: Start immer 1, Ende via numerische Spalten-Erkennung."""
        try:
            end_row_default = int(df.index.max())
        except Exception:
            end_row_default = len(df)

        start_row_default = 1
        start_col_default = 1

        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                end_col_default = int(df.columns.get_loc(numeric_cols[-1]))
            else:
                end_col_default = max(0, len(df.columns) - 1)
        except Exception:
            end_col_default = max(0, len(df.columns) - 1)

        return start_row_default, end_row_default, start_col_default, end_col_default

    def _load_file_data(self, record):
        """Laedt (bzw. laedt neu bei Sheet-Wechsel) die Daten einer Datei in den Datensatz."""
        handler = FileHandler()
        handler.file_path = str(record["path"])
        dummy = _DummyLabel()

        try:
            if record["is_excel"]:
                sheet = record["sheet_cb"].get()
                df, headers, units = handler.read_dws_excel(sheet, dummy, dummy)
            else:
                df, headers, units = handler.read_top(dummy, dummy)
        except Exception as e:
            logger.exception("Fehler beim Laden von %s", record["path"])
            record["status_label"].config(text=f"Fehler: {e}", foreground="red")
            record["df"] = None
            return

        if df is None:
            record["status_label"].config(text="Datei konnte nicht geladen werden", foreground="red")
            record["df"] = None
            return

        record["handler"]      = handler
        record["df"]           = df
        record["temp_headers"] = headers
        record["temp_units"]   = units
        record["zeitstempel"]  = handler.zeitstempel

        hat_zeitstempel = handler.zeitstempel is not None
        ts_info = "mit echten Zeitstempeln" if hat_zeitstempel else "OHNE echte Zeitstempel"
        record["status_label"].config(
            text=f"{len(df)} Zeilen geladen ({ts_info})",
            foreground="black" if hat_zeitstempel else "#b36b00",
        )
        protocol_logger.info(
            "MULTIFILE_LOADED file=%s rows=%s zeitstempel=%s", record["filename"], len(df), hat_zeitstempel
        )

    def _refill_range_fields(self, record):
        """Fuellt Start/End-Zeile/Spalte mit sinnvollen Standardwerten (numerische Spalten)."""
        df = record["df"]
        if df is None:
            return
        start_row, end_row, start_col, end_col = self._compute_default_range(df)
        for entry, val in [
            (record["entry_start_row"], start_row),
            (record["entry_end_row"],   end_row),
            (record["entry_start_col"], start_col),
            (record["entry_end_col"],   end_col),
        ]:
            entry.delete(0, tk.END)
            entry.insert(0, str(val))

    def _show_panel(self):
        """Blendet das Eingabedaten/Ausgabedaten-Notebook aus und zeigt das Mehrfachdatei-Panel."""
        gui = self.gui
        gui.bottom_notebook.pack_forget()
        gui.multi_file_panel.pack(fill=tk.BOTH, expand=True)

        # Unteren Bereich vergroessern, damit Datei-Tabs + Buttons genug Platz haben
        # (die Trennleiste steht standardmaessig auf einer sehr kleinen Hoehe).
        try:
            gui.root.update_idletasks()
            self._original_sash_pos = gui.right_pane.sashpos(1)
            total_height   = gui.right_pane.winfo_height()
            desired_height = 550
            new_sash_pos   = max(100, total_height - desired_height)
            gui.right_pane.sashpos(1, new_sash_pos)
        except Exception:
            logger.exception("Trennleiste konnte nicht vergroessert werden")

    def _hide_panel(self):
        """Blendet das Mehrfachdatei-Panel wieder aus und zeigt das normale Notebook."""
        gui = self.gui
        gui.multi_file_panel.pack_forget()
        for child in gui.multi_file_panel.winfo_children():
            child.destroy()
        gui.bottom_notebook.pack(fill=tk.BOTH, expand=True)

        # Trennleiste wieder auf die urspruengliche Position zuruecksetzen
        original = getattr(self, "_original_sash_pos", None)
        if original is not None:
            try:
                gui.right_pane.sashpos(1, original)
            except Exception:
                logger.exception("Trennleiste konnte nicht zurueckgesetzt werden")

    # --------------------------------------------------------
    #  DATEI-SAMMEL-FENSTER (vor Schritt 1)
    # --------------------------------------------------------

    def open_file_accumulator(self, initial_paths):
        """
        Zeigt ein Ereignisfenster, in dem nacheinander weitere Dateien hinzugefuegt
        werden koennen (jede als farbiger Balken sichtbar), bis "Fertig" gedrueckt wird.
        Danach: 1 Datei -> normaler Single-Datei-Weg, 2+ Dateien -> Mehrfachdatei-Panel.
        """
        gui = self.gui
        acc_paths = list(initial_paths)
        acc_bars  = []

        dialog = tb.Toplevel(gui.root)
        dialog.title("Dateien auswählen")
        dialog.transient(gui.root)
        dialog.grab_set()
        dialog.geometry("500x420")
        gui.apply_icon(dialog)

        protocol_logger.info("FILE_ACCUMULATOR_OPEN initial=%s", len(acc_paths))

        ttk.Label(
            dialog, text="Ausgewählte Dateien:", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        def add_bar(path):
            idx        = len(acc_bars)
            color      = _TAB_COLORS[idx % len(_TAB_COLORS)]
            style_name = f"AccBar{color.lstrip('#')}.TLabel"
            ttk.Style().configure(
                style_name, background=color, foreground="white",
                font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold")
            )
            bar = ttk.Label(list_frame, text=f"  {Path(path).name}", anchor="w", style=style_name)
            bar.configure(style=style_name)
            bar.pack(fill=tk.X, pady=3, ipady=8)
            acc_bars.append(bar)

        for p in acc_paths:
            add_bar(p)

        def add_more():
            path = filedialog.askopenfilename(filetypes=Cfg.Export.SUPPORTED_FILETYPES)
            if path:
                acc_paths.append(path)
                add_bar(path)

        def finish():
            paths = list(acc_paths)
            dialog.destroy()
            protocol_logger.info("FILE_ACCUMULATOR_DONE count=%s", len(paths))
            if len(paths) == 1:
                gui._load_single_file(paths[0])
            else:
                self.show_multi_file_panel(paths)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=15)
        ttk.Button(btn_frame, text="Mehr Dateien", command=add_more).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Fertig", command=finish).pack(side=tk.RIGHT, padx=5)

    # --------------------------------------------------------
    #  PANEL AUFBAU (Schritt 1: globale Einstellungen)
    # --------------------------------------------------------

    def show_multi_file_panel(self, file_paths):
        """Aktiviert das Mehrfachdatei-Panel fuer die gegebenen Dateipfade (Schritt 1).
        Jede Datei wird unabhaengig verarbeitet (Batch) - eigene Plots/Spektren pro
        Datei, danach landen alle Signale gemeinsam im Signalauswahl-Fenster."""
        gui = self.gui
        self.files = []

        for child in gui.multi_file_panel.winfo_children():
            child.destroy()

        protocol_logger.info("MULTIFILE_PANEL_OPEN count=%s", len(file_paths))
        self._file_paths = [Path(p) for p in file_paths]

        self._build_step1(gui.multi_file_panel)
        self._show_panel()

    def _build_step1(self, parent):
        """Schritt 1: globale Einstellungen (Samplefrequenz, Fenstertyp)."""
        step1 = ttk.Frame(parent)
        self._step1_frame = step1

        ttk.Style().configure(
            "MultiFileStep1.TLabel", background=Cfg.Colors.TAB_INPUT, foreground="white",
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold")
        )
        header = ttk.Label(
            step1, text=f"  Globale Einstellungen ({len(self._file_paths)} Dateien)",
            anchor="w", style="MultiFileStep1.TLabel",
        )
        # ttkbootstrap setzt den style-Parameter beim Erstellen manchmal zurueck -
        # erneutes Zuweisen direkt danach behebt das zuverlaessig.
        header.configure(style="MultiFileStep1.TLabel")
        header.pack(fill=tk.X, ipady=6)

        content = ttk.Frame(step1)
        content.pack(fill=tk.X, padx=20, pady=20)

        ttk.Label(content, text="Samplefrequenz:").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        samplerate_entry = ttk.Entry(content, width=20, style="EntryPlaceholder.TEntry")
        samplerate_entry.insert(0, Cfg.Ph.SAMPLERATE)
        samplerate_entry._is_placeholder = True
        samplerate_entry.grid(row=0, column=1, sticky="w", padx=8, pady=8)

        def sr_focus_in(event):
            if getattr(samplerate_entry, "_is_placeholder", False):
                samplerate_entry.delete(0, tk.END)
                samplerate_entry.configure(style="EntryNormal.TEntry")
                samplerate_entry._is_placeholder = False

        def sr_focus_out(event):
            if not samplerate_entry.get().strip():
                samplerate_entry.insert(0, Cfg.Ph.SAMPLERATE)
                samplerate_entry.configure(style="EntryPlaceholder.TEntry")
                samplerate_entry._is_placeholder = True

        samplerate_entry.bind("<FocusIn>",  sr_focus_in)
        samplerate_entry.bind("<FocusOut>", sr_focus_out)

        ttk.Label(content, text="Fenstertyp:").grid(row=1, column=0, sticky="w", padx=8, pady=8)
        fenstertyp_cb = ttk.Combobox(
            content, values=Cfg.Defaults.FENSTER_TYPEN, state="readonly", width=18
        )
        fenstertyp_cb.set(Cfg.Ph.FENSTERTYP)
        fenstertyp_cb.grid(row=1, column=1, sticky="w", padx=8, pady=8)

        self._samplerate_entry = samplerate_entry
        self._fenstertyp_cb    = fenstertyp_cb

        btn_frame = ttk.Frame(step1)
        btn_frame.pack(side=tk.TOP, pady=10)
        ttk.Button(
            btn_frame, text="<- Zurück", command=self._cancel, width=28
        ).pack(side=tk.TOP, pady=4)
        ttk.Button(
            btn_frame, text="Weiter ->", command=self._go_to_step2, width=28
        ).pack(side=tk.TOP, pady=4)

        step1.pack(fill=tk.BOTH, expand=True)

    def _go_to_step2(self):
        """Uebernimmt Default-Werte falls nichts gewaehlt wurde, baut dann Schritt 2 (Datei-Tabs) auf."""
        aenderungen = []

        if getattr(self._samplerate_entry, "_is_placeholder", False) or not self._samplerate_entry.get().strip():
            self._samplerate_entry.delete(0, tk.END)
            self._samplerate_entry.insert(0, str(Cfg.Defaults.SAMPLERATE))
            self._samplerate_entry.configure(style="EntryNormal.TEntry")
            self._samplerate_entry._is_placeholder = False
            aenderungen.append(f"Samplefrequenz -> {Cfg.Defaults.SAMPLERATE}")

        if self._fenstertyp_cb.get() == Cfg.Ph.FENSTERTYP:
            self._fenstertyp_cb.set(Cfg.Defaults.FENSTERTYP)
            aenderungen.append(f"Fenstertyp -> {Cfg.Defaults.FENSTERTYP}")

        try:
            samplerate = float(self._samplerate_entry.get().strip().replace(",", "."))
            if samplerate <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Fehler", "Bitte eine gueltige Samplefrequenz eingeben.")
            return

        if aenderungen:
            messagebox.showinfo("Standardwerte", "Default Werte übernommen:\n" + "\n".join(aenderungen))

        self._step1_frame.pack_forget()
        self._build_step2(self.gui.multi_file_panel)

    # --------------------------------------------------------
    #  PANEL AUFBAU (Schritt 2: Datei-Tabs)
    # --------------------------------------------------------

    def _build_step2(self, parent):
        """Schritt 2: ein Tab pro Datei mit eigenem Zeilen-/Spaltenbereich."""
        step2 = ttk.Frame(parent)
        self._step2_frame = step2

        # Notebook OHNE expand=True: nimmt nur so viel Hoehe wie sein Inhalt
        # braucht, damit die Buttons direkt darunter erscheinen statt ganz
        # unten im Fenster.
        notebook = ttk.Notebook(step2)
        notebook.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.files = []
        for i, path in enumerate(self._file_paths):
            self._add_file_tab(notebook, path, _TAB_COLORS[i % len(_TAB_COLORS)])

        btn_frame = ttk.Frame(step2)
        btn_frame.pack(side=tk.TOP, pady=10)
        ttk.Button(
            btn_frame, text="<- Zurück", command=self._go_to_step1, width=28
        ).pack(side=tk.TOP, pady=4)
        ttk.Button(
            btn_frame, text="Verarbeiten ->", command=self._process_all_files_batch, width=28
        ).pack(side=tk.TOP, pady=4)

        step2.pack(fill=tk.BOTH, expand=True)

    def _go_to_step1(self):
        """Zurueck zu Schritt 1, behaelt bereits eingegebene globale Werte."""
        self._step2_frame.pack_forget()
        self._step2_frame.destroy()
        self._step1_frame.pack(fill=tk.BOTH, expand=True)

    def is_active(self):
        """True, wenn das Mehrfachdatei-Panel aktuell aktiv ist (statt der normalen
        Einzeldatei-Ansicht). Prueft ueber den Pack-Geometry-Manager statt
        winfo_ismapped(), da Letzteres von der Fenster-Sichtbarkeit des gesamten
        Fensterbaums abhaengt (z.B. minimiert) und nicht zuverlaessig ist."""
        try:
            return bool(self.gui.multi_file_panel.pack_info())
        except tk.TclError:
            return False

    def return_to_step1(self):
        """Schliesst ein offenes Signalauswahl-Fenster (falls vorhanden) und kehrt zu
        Schritt 1 (globale Einstellungen) zurueck, OHNE die geladenen Dateien zu
        verwerfen. Wird sowohl beim Schliessen des Signalauswahl-Fensters als auch
        beim Druecken von "Eingaben zuruecksetzen" aufgerufen, solange das
        Mehrfachdatei-Panel aktiv ist."""
        gui = self.gui
        protocol_logger.info("MULTIFILE_RETURN_TO_STEP1")

        active_window = gui.plot_window_manager.active_signal_window
        if active_window is not None:
            try:
                if active_window.winfo_exists():
                    active_window.destroy()
            except Exception:
                pass
            gui.plot_window_manager.active_signal_window = None

        if hasattr(self, "_step2_frame") and self._step2_frame.winfo_exists():
            self._go_to_step1()

    def _add_file_tab(self, notebook, path, color):
        """Erstellt einen farblich markierten Tab fuer eine einzelne Datei."""
        record = {
            "path":     path,
            "filename": path.name,
            "handler":  None,
            "df":       None,
            "temp_headers": [],
            "temp_units":   [],
            "zeitstempel":  None,
            "is_excel": path.suffix.lower() in (".xlsx", ".xls"),
        }

        tab = ttk.Frame(notebook)
        notebook.add(tab, text=record["filename"])

        # ttk.Style statt rohem tk.Label: ttkbootstrap ueberschreibt bg/fg von
        # rohen tk-Widgets aktiv, ein eigener ttk-Style pro Farbe wird respektiert
        # (gleiche Technik wie bei der Notebook-Tab-Faerbung in gui_layout_manager.py).
        style_name = f"MultiFileTab{color.lstrip('#')}.TLabel"
        ttk.Style().configure(style_name, background=color, foreground="white",
                               font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold"))
        header = ttk.Label(tab, text=f"  {record['filename']}", anchor="w", style=style_name)
        # ttkbootstrap setzt den style-Parameter beim Erstellen manchmal zurueck -
        # erneutes Zuweisen direkt danach behebt das zuverlaessig.
        header.configure(style=style_name)
        header.pack(fill=tk.X, ipady=6)

        status_label = ttk.Label(tab, text="Lade...", foreground="gray")
        status_label.pack(anchor="w", padx=10, pady=(10, 5))
        record["status_label"] = status_label

        sheet_names = []
        if record["is_excel"]:
            sheet_frame = ttk.Frame(tab)
            sheet_frame.pack(fill=tk.X, padx=10, pady=5)
            ttk.Label(sheet_frame, text="Sheet:").pack(side=tk.LEFT)
            sheet_cb = ttk.Combobox(sheet_frame, state="readonly", width=30)
            sheet_cb.pack(side=tk.LEFT, padx=5)
            record["sheet_cb"] = sheet_cb

            try:
                sheet_names = pd.ExcelFile(path).sheet_names
            except Exception as e:
                logger.exception("Fehler beim Oeffnen von %s", path)
                status_label.config(text=f"Fehler beim Oeffnen: {e}", foreground="red")

            sheet_cb["values"] = sheet_names
            if sheet_names:
                sheet_cb.set(sheet_names[0])

            def on_sheet_change(event=None, rec=record):
                self._load_file_data(rec)
                self._refill_range_fields(rec)

            sheet_cb.bind("<<ComboboxSelected>>", on_sheet_change)

        range_frame = ttk.Frame(tab)
        range_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(range_frame, text="Start Zeile:").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        entry_start_row = ttk.Entry(range_frame, width=12)
        entry_start_row.grid(row=0, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(range_frame, text="End Zeile:").grid(row=0, column=2, sticky="w", padx=5, pady=4)
        entry_end_row = ttk.Entry(range_frame, width=12)
        entry_end_row.grid(row=0, column=3, sticky="w", padx=5, pady=4)

        ttk.Label(range_frame, text="Start Spalte:").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        entry_start_col = ttk.Entry(range_frame, width=12)
        entry_start_col.grid(row=1, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(range_frame, text="End Spalte:").grid(row=1, column=2, sticky="w", padx=5, pady=4)
        entry_end_col = ttk.Entry(range_frame, width=12)
        entry_end_col.grid(row=1, column=3, sticky="w", padx=5, pady=4)

        record["entry_start_row"] = entry_start_row
        record["entry_end_row"]   = entry_end_row
        record["entry_start_col"] = entry_start_col
        record["entry_end_col"]   = entry_end_col

        def toggle_range_fields():
            state = "disabled" if ganze_datei_var.get() else "normal"
            for e in (entry_start_row, entry_end_row, entry_start_col, entry_end_col):
                e.config(state=state)

        # Standardmaessig angehakt: wenn nichts geaendert wird, wird die ganze Datei verwendet
        ganze_datei_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            tab, text="Ganze Datei verwenden", variable=ganze_datei_var, command=toggle_range_fields
        ).pack(anchor="w", padx=10, pady=(0, 10))
        record["ganze_datei_var"] = ganze_datei_var

        # Platzhalter fuer die Ausgabewerte (Startzeit/Endzeit/Samples/dt/df) -
        # wird erst nach dem Verarbeiten befuellt (siehe _render_output_stats).
        output_frame = ttk.Frame(tab)
        output_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        record["output_frame"] = output_frame

        self.files.append(record)

        if not record["is_excel"] or sheet_names:
            self._load_file_data(record)
            self._refill_range_fields(record)

        toggle_range_fields()

    # --------------------------------------------------------
    #  ABBRECHEN
    # --------------------------------------------------------

    def _cancel(self):
        """Bricht den Mehrfachdatei-Import ab und stellt das normale Notebook wieder her."""
        protocol_logger.info("MULTIFILE_PANEL_CANCEL")
        self.files = []
        self._hide_panel()

    # --------------------------------------------------------
    #  VERARBEITUNG
    # --------------------------------------------------------

    def _validate_global_inputs(self):
        """Validiert Samplefrequenz/Fenstertyp aus Schritt 1 und prueft, dass alle Dateien
        geladen sind. Gibt (samplerate, fenstertyp) zurueck, oder None (Fehler bereits angezeigt)."""
        try:
            samplerate = float(self._samplerate_entry.get().strip().replace(",", "."))
            if samplerate <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Fehler", "Bitte eine gueltige Samplefrequenz eingeben.")
            return None

        fenstertyp = self._fenstertyp_cb.get()
        if not fenstertyp or fenstertyp == Cfg.Ph.FENSTERTYP:
            messagebox.showerror("Fehler", "Bitte einen Fenstertyp waehlen.")
            return None

        if not self.files:
            messagebox.showerror("Fehler", "Keine Dateien geladen.")
            return None

        fehlerhaft = [r["filename"] for r in self.files if r["df"] is None]
        if fehlerhaft:
            messagebox.showerror(
                "Fehler", f"Diese Dateien konnten nicht geladen werden: {', '.join(fehlerhaft)}"
            )
            return None

        return samplerate, fenstertyp

    @staticmethod
    def _render_output_stats(record, t0, t1, n_samples, dt, df_step):
        """Befuellt den Ausgabewerte-Platzhalter eines Datei-Tabs (Startzeit/Endzeit/
        Samples/dt/df) nach erfolgreicher Verarbeitung - analog zu den Ausgabefeldern
        der Einzeldatei-Ansicht, aber pro Datei sichtbar statt nur einmal global."""
        frame = record.get("output_frame")
        if frame is None:
            return
        for child in frame.winfo_children():
            child.destroy()

        ttk.Label(
            frame, text="Ausgabewerte:", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(4, 2))

        rows = [
            ("Startzeit", f"{t0:.4g} s"),
            ("Endzeit",   f"{t1:.4g} s"),
            ("Samples",   str(n_samples)),
            ("dt",        f"{dt:.6g} s" if dt else "-"),
            ("df",        f"{df_step:.4g} Hz"),
        ]
        for i, (label, value) in enumerate(rows, start=1):
            ttk.Label(frame, text=f"{label}:").grid(row=i, column=0, sticky="w", padx=(0, 8), pady=1)
            ttk.Label(frame, text=value).grid(row=i, column=1, sticky="w", pady=1)

    @staticmethod
    def _dedupe_pool_header(header, file_stem, existing_headers):
        """Macht einen Signalnamen im kombinierten Pool eindeutig.

        Kollidiert der Name mit einem bereits im Pool vorhandenen Signal (z.B.
        "Kanal1" kommt in zwei Dateien vor), wird der Dateiname angehaengt;
        kollidiert das immer noch, zusaetzlich ein Zaehler ("_1", "_2", ...)."""
        if header not in existing_headers:
            return header
        candidate = f"{header} ({file_stem})"
        if candidate not in existing_headers:
            return candidate
        counter = 1
        while f"{candidate}_{counter}" in existing_headers:
            counter += 1
        return f"{candidate}_{counter}"

    def _process_all_files_batch(self):
        """Verarbeitet jede Datei unabhaengig durch die bestehende Einzel-Datei-Pipeline.
        Kein Zeit-Merge, keine Spaltenanzahl-Pruefung, kein Zeitstempel-Erfordernis -
        jede Datei bekommt ihre eigenen Plots/Spektren in spektren/<Dateiname>/. Ein
        Fehler in einer Datei bricht den Batch nicht ab, sondern wird gesammelt und
        am Ende gemeldet.

        Zusaetzlich werden alle Signale aller Dateien in einem gemeinsamen Pool
        gesammelt (jedes Signal behaelt seine EIGENE Zeitachse, da die Dateien
        unterschiedlich lang sein koennen) - am Ende oeffnet sich EINMAL das
        Signalauswahl-Fenster mit den Signalen aus allen Dateien zusammen."""
        gui = self.gui

        validated = self._validate_global_inputs()
        if validated is None:
            return
        samplerate, fenstertyp = validated

        gui.entry5.config(state="normal")
        gui.entry5.delete(0, tk.END)
        gui.entry5.insert(0, str(samplerate))

        gui.entry6.config(state="normal")
        gui.entry6.set(fenstertyp)

        dummy          = _DummyLabel()
        erfolgreich    = []
        fehlgeschlagen = []

        pool_signals    = []
        pool_headers    = []
        pool_units      = []
        pool_t          = []
        pool_timestamps = []

        for record in self.files:
            validator = DataValidator()
            validator.df           = record["df"]
            validator.temp_df      = record["df"]
            validator.headers      = record["temp_headers"]
            validator.units        = record["temp_units"]
            validator.temp_headers = record["temp_headers"]
            validator.temp_units   = record["temp_units"]

            try:
                if record["ganze_datei_var"].get():
                    start_row, end_row, start_col, end_col = self._compute_default_range(record["df"])
                else:
                    start_row = int(record["entry_start_row"].get().strip())
                    end_row   = int(record["entry_end_row"].get().strip())
                    start_col = int(record["entry_start_col"].get().strip())
                    end_col   = int(record["entry_end_col"].get().strip())

                validator.end_col       = end_col
                validator.start_col     = start_col
                validator.start_row     = start_row
                validator.end_row       = end_row
                validator.samplerate_fs = samplerate
            except ValueError as e:
                fehlgeschlagen.append(Cfg.Errors.VAL_MULTIFILE_FILE_FAILED.format(record["filename"], str(e)))
                continue

            if validator.dataframe_type == Cfg.Export.PROCESS_DWS:
                result = validator.validate_and_process_dws(dummy)
            else:
                result = validator.validate_and_process_top(dummy)

            _samplerate_fs, _hann, value, headers, units = result
            if value is None:
                fehlgeschlagen.append(
                    Cfg.Errors.VAL_MULTIFILE_FILE_FAILED.format(record["filename"], "Verarbeitung fehlgeschlagen")
                )
                continue

            gui.Gesamtpfad      = record["path"]
            gui.timestamps_full = None
            gui.data_validator  = validator

            gui._enter_loading_state()
            gui._enable_analysis_buttons()

            file_result = (samplerate, 1, value, headers, units)
            try:
                gui._process_validated_data(file_result, save_subdir=record["path"].stem, open_overlay=False)
            except Exception as e:
                logger.exception("Batch-Verarbeitung fehlgeschlagen fuer %s", record["filename"])
                fehlgeschlagen.append(Cfg.Errors.VAL_MULTIFILE_FILE_FAILED.format(record["filename"], str(e)))
                continue

            # Ausgabewerte dieser Datei berechnen und direkt in ihrem eigenen Tab
            # anzeigen (nicht nur einmal global, wie es die Einzeldatei-Ansicht tut -
            # bei mehreren Dateien braucht jede Datei ihre eigenen Ausgabewerte).
            n_samples_file = value.shape[0]
            t0_file = gui.t[0]  if gui.t is not None and len(gui.t) > 0 else 0.0
            t1_file = gui.t[-1] if gui.t is not None and len(gui.t) > 0 else 0.0
            df_file = samplerate / n_samples_file if samplerate and n_samples_file > 0 else 0.0
            self._render_output_stats(record, t0_file, t1_file, n_samples_file, gui.dt, df_file)

            # Echte Zeitstempel dieser Datei auf denselben Zeilenbereich zuschneiden
            # wie value/t (fuer die "Uhrzeit"-Achse im Analyse-Fenster) - None falls
            # die Datei keine gueltigen Zeitstempel hat oder die Laenge nicht passt.
            file_timestamps = None
            if record["zeitstempel"] is not None:
                try:
                    ts_slice = record["zeitstempel"].loc[validator.start_row:validator.end_row].to_numpy()
                    if len(ts_slice) == value.shape[0]:
                        file_timestamps = ts_slice
                except Exception:
                    logger.exception("Zeitstempel-Zuschnitt fehlgeschlagen fuer %s", record["filename"])

            # In den kombinierten Pool uebernehmen: gui.signals/headers/units/t
            # spiegeln jetzt genau DIESE Datei wider (von _process_validated_data
            # gerade gesetzt) - bevor die naechste Iteration das ueberschreibt,
            # hier herauskopieren.
            file_stem = record["path"].stem
            for sig, header, unit in zip(gui.signals, gui.headers, gui.units):
                pool_header = self._dedupe_pool_header(header, file_stem, pool_headers)
                pool_signals.append(sig)
                pool_headers.append(pool_header)
                pool_units.append(unit)
                pool_t.append(gui.t)
                pool_timestamps.append(file_timestamps)

            erfolgreich.append(record["filename"])
            protocol_logger.info(
                "BATCH_FILE_DONE file=%s rows=%s columns=%s", record["filename"], value.shape[0], len(headers)
            )

        protocol_logger.info(
            "BATCH_DONE total=%s erfolgreich=%s fehlgeschlagen=%s",
            len(self.files), len(erfolgreich), len(fehlgeschlagen)
        )

        summary = f"{len(erfolgreich)} von {len(self.files)} Dateien erfolgreich verarbeitet."
        if fehlgeschlagen:
            summary += "\n\nFehler:\n" + "\n".join(fehlgeschlagen)
        if pool_signals:
            summary += f"\n\n{len(pool_signals)} Signale aus {len(erfolgreich)} Datei(en) stehen jetzt gemeinsam in der Signalauswahl zur Verfuegung."
        messagebox.showinfo("Batch abgeschlossen", summary)

        # Panel bleibt bewusst auf Schritt 2 (Datei-Tabs mit Ein-/Ausgabewerten)
        # sichtbar statt zur Einzeldatei-Ansicht zu wechseln - siehe
        # return_to_step1() fuer den Weg zurueck zu Schritt 1.

        if pool_signals:
            # Kombinierter Signal-Pool: gui.t UND gui.timestamps sind hier bewusst
            # LISTEN (je ein Zeitarray/Zeitstempel-Array pro Signal, siehe
            # PlotManager.t_for_idx) statt eines einzelnen gemeinsamen Arrays -
            # die Dateien koennen unterschiedlich lang sein und zu unterschiedlichen
            # Zeiten aufgezeichnet worden sein.
            gui.headers          = pool_headers
            gui.units            = pool_units
            gui.signals          = pool_signals
            gui.t                = pool_t
            gui.value            = None
            gui.timestamps       = pool_timestamps
            gui.timestamps_full  = None

            protocol_logger.info("BATCH_POOL_READY signals=%s files=%s", len(pool_signals), len(erfolgreich))
            gui._enable_analysis_buttons()
            gui.root.after(0, gui.show_multi_signal_overlay_window)
