"""
Analyse Manager - Signalanalyse-Funktionen
============================================
Kapselt mathematische Analysefunktionen für Messsignale:
Mittelwert (AVG), Effektivwert (RMS), Differential, Integral,
Varianz und Autokorrelation mit zugehörigen Ergebnisfenstern.
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
from __future__ import annotations

import logging
import tkinter as tk

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ============================================================
#  IMPORTS – Eigene Klassen
# ============================================================
from gui_module import meldungen as messagebox
from gui_module.plot_manager import PlotManager
from gui_module.analyse_plotter import AnalysePlotter
from hilfsklassen.daten_verarbeiter import DatenVerarbeiter
from konfiguration import Cfg

# ============================================================
#  LOGGING & THEME
# ============================================================
logger = logging.getLogger(__name__)

sns.set_theme(
    style=Cfg.PlotStyle.STYLE,
    context=Cfg.PlotStyle.CONTEXT,
    palette=Cfg.PlotStyle.PALETTE,
)
# Wende die centralisierten Schriftgrößen an (überschreibt seaborn defaults)
plt.rcParams.update(Cfg.PlotStyle.MPL_RCPARAMS)


# ============================================================
#  KLASSE
# ============================================================
class AnalysisManager:
    """
    Kapselt die Analyse-Funktionen:
    - AVG, RMS, FFT, Differential, Integral, Varianz/Statistik
    - inkl. der Helfer für Signal-Auswahl und Ergebnisfenster
    """

    def __init__(self, gui_manager):

        # --- Referenzen ---
        self.gui = gui_manager

    # --------------------------------------------------------
    #  HILFSMETHODEN – Signal-Auswahl & Filterstatus
    # --------------------------------------------------------

    def _get_selected_signal_index(self):
        """Gibt den Index des ausgewählten Signals zurück, oder None bei Fehler."""
        if not self.gui.headers or not self.gui.signals or self.gui.t is None:
            messagebox.showwarning(Cfg.Texts.HINT, Cfg.Texts.NO_DATA)
            return None
        selected = getattr(self.gui, "selected_signal", None)
        if not selected or selected == Cfg.Texts.SELECT_SIGNAL:
            messagebox.showinfo(Cfg.Texts.HINT, Cfg.Texts.SELECT_SIGNAL_FIRST)
            return None
        try:
            return self.gui.headers.index(selected)
        except ValueError:
            messagebox.showerror(Cfg.Texts.ERROR, Cfg.Texts.SIGNAL_NOT_FOUND.format(selected))
            return None

    def _get_signal_for_operations(self, idx):
        """Gibt (t, original, used, header, unit) für einen Signal-Index zurück."""
        t      = PlotManager.t_for_idx(self.gui.t, idx)
        header = (self.gui.headers[idx] if idx < len(self.gui.headers)
                  else Cfg.Texts.SIGNAL_FALLBACK.format(idx))
        unit   = self.gui.units[idx] if idx < len(self.gui.units) else ""
        original = self.gui.signals[idx]

        if (getattr(self.gui, "use_filtered_var", None)
                and self.gui.use_filtered_var.get()
                and getattr(self.gui, "filter_manager", None)
                and self.gui.filter_manager.filter_type != Cfg.Defaults.FILTER_TYP):
            try:
                used = self.gui.filter_manager.apply_filter(original)
            except Exception as e:
                logger.exception("Filterfehler: %s", e)
                used = original
        else:
            used = original

        return t, original, used, header, unit

    def _get_filter_context(self):
        """Gibt (use_filtered, filter_manager) aus dem aktuellen GUI-Zustand zurück."""
        use_filtered   = bool(getattr(self.gui, "use_filtered_var", None)
                              and self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)
        return use_filtered, filter_manager

    def _get_t_max(self):
        """Gibt die maximale Zeit zurück, oder 10 als Fallback."""
        if isinstance(self.gui.t, (list, tuple)):
            return max((arr[-1] for arr in self.gui.t if len(arr) > 0), default=10)
        return self.gui.t[-1] if self.gui.t is not None and len(self.gui.t) > 0 else 10

    # --------------------------------------------------------
    #  HILFSMETHODEN – Ergebnisfenster & Plot
    # --------------------------------------------------------

    def _open_result_window(self, title, plot_func):
        """Öffnet ein Ergebnisfenster und ruft plot_func(frame) darin auf."""
        layout = self.gui.layout_manager.create_analysis_result_window(title)
        frame  = layout["frame"]
        try:
            plot_func(frame)
        except Exception as e:
            # Basis-Größe wird später vom Configure-Event angepasst
            fig = plt.Figure(figsize=(10, 6), dpi=100)
            ax  = fig.add_subplot(111)
            ax.text(
                Cfg.Layout.Figure.ERROR_TEXT_POS[0],
                Cfg.Layout.Figure.ERROR_TEXT_POS[1],
                Cfg.Texts.PLOT_ERROR.format(e),
                ha=Cfg.Layout.Figure.ERROR_TEXT_ALIGN[0],
                va=Cfg.Layout.Figure.ERROR_TEXT_ALIGN[1],
                font=Cfg.Layout.Figure.ERROR_TEXT_FONT,
                color=Cfg.Layout.Figure.ERROR_TEXT_COLOR,
                transform=ax.transAxes,
            )
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            # Event-Handler für dynamische Figure-Größe bei Canvas-Resize
            # Standard DPI für konsistente Berechnung
            target_dpi = 100
            fig.set_dpi(target_dpi)

            def on_canvas_configure(event):
                """Passt Figure-Größe an Canvas-Widget-Größe an."""
                # Mindestens 400x300 Pixel erforderlich
                if event.width > 200 and event.height > 150:
                    new_width = event.width / target_dpi
                    new_height = event.height / target_dpi
                    fig.set_size_inches(new_width, new_height)
                    canvas.draw_idle()

            canvas_widget.bind("<Configure>", on_canvas_configure)

            # Erzwinge Layout und dann Initial-Resize
            canvas_widget.update_idletasks()
            # Hole die tatsächliche Canvas-Größe und rufe on_canvas_configure manuell auf
            width = canvas_widget.winfo_width()
            height = canvas_widget.winfo_height()
            if width > 200 and height > 150:
                on_canvas_configure(type('event', (), {'width': width, 'height': height})())

            canvas.draw()

    def _make_plot_func(self, analyse_name, selected_headers,
                        header_to_signal_idx, use_filtered, filter_manager,
                        start_zeit=None, ende_zeit=None):
        """
        Erzeugt eine plot_func(frame)-Closure für _open_result_window.
        Zentralisiert den identischen PlotManager.create_analysis_tab-Aufruf.
        """
        def _plot(frame):
            AnalysePlotter.create_analysis_tab(
                frame=frame,
                analyse_typ=analyse_name,
                selected_headers=selected_headers,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager,
                start_zeit=start_zeit,
                ende_zeit=ende_zeit,
                window_type=(
                    self.gui.entry6.get().strip() if hasattr(self.gui, "entry6") else None
                ) or None,
            )
        return _plot

    def _run_single(self, analyse_key, title_key, idx,
                    start_zeit=None, ende_zeit=None, dt_required=True):
        """
        Führt eine Einzelsignal-Analyse aus.
        analyse_key: Schlüssel in Cfg.Analysis.NAMES
        title_key:   Schlüssel in Cfg.Texts (z.B. 'AVG_ANALYSE_TITLE')
        """
        if dt_required and self.gui.dt is None:
            messagebox.showerror(Cfg.Texts.ERROR, Cfg.Texts.NO_DT)
            return
        header               = self.gui.headers[idx]
        header_to_signal_idx = {header: idx}
        use_filtered, filter_manager = self._get_filter_context()
        self._open_result_window(
            getattr(Cfg.Texts, title_key),
            self._make_plot_func(
                Cfg.Analysis.NAMES[analyse_key],
                [header], header_to_signal_idx,
                use_filtered, filter_manager,
                start_zeit, ende_zeit,
            )
        )

    def _run_multi(self, analyse_key, title_key, signal_indices,
                   start_zeit=None, ende_zeit=None, dt_required=True):
        """
        Führt eine Multi-Signal-Analyse aus.
        Delegiert an _run_single wenn nur ein Signal übergeben wird.
        """
        if dt_required and self.gui.dt is None:
            messagebox.showerror(Cfg.Texts.ERROR, Cfg.Texts.NO_DT)
            return
        if len(signal_indices) == 1:
            # Für single_fallback_key verwenden wir den Einzelsignal-Aufruf
            self._run_single(analyse_key, title_key, signal_indices[0],
                             start_zeit, ende_zeit, dt_required)
            return
        selected_headers     = [self.gui.headers[i] for i in signal_indices]
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in selected_headers}
        use_filtered, filter_manager = self._get_filter_context()
        self._open_result_window(
            getattr(Cfg.Texts, title_key),
            self._make_plot_func(
                Cfg.Analysis.NAMES[analyse_key],
                selected_headers, header_to_signal_idx,
                use_filtered, filter_manager,
                start_zeit, ende_zeit,
            )
        )

    def _resolve_single_idx(self, signal_idx):
        """
        Gibt signal_idx zurück wenn angegeben, sonst aus GUI-Auswahl.
        Gibt None zurück wenn kein Signal ausgewählt.
        """
        if signal_idx is not None:
            return signal_idx
        return self._get_selected_signal_index()

    def _resolve_selected_signals(self, fallback_attr='selected_signals'):
        """
        Gibt die aktuell ausgewählten Signal-Headers zurück.
        Fällt auf GUI-Einzelauswahl zurück wenn kein Multi-Signal gesetzt ist.
        """
        signals = getattr(self.gui, fallback_attr, [])
        if not signals:
            idx = self._get_selected_signal_index()
            if idx is None:
                return None
            signals = [self.gui.headers[idx]]
        return signals

    # --------------------------------------------------------
    #  ANALYSE-METHODEN – Einzelsignal
    # --------------------------------------------------------

    def avg_anwendung(self, start_zeit=None, ende_zeit=None, signal_idx=None):
        """Mittelwert-Analyse für ein Signal."""
        idx = self._resolve_single_idx(signal_idx)
        if idx is None:
            return
        self._run_single("AVG", "AVG_ANALYSE_TITLE", idx, start_zeit, ende_zeit)

    def rms_anwendung(self, start_zeit=None, ende_zeit=None, signal_idx=None):
        """Effektivwert-Analyse für ein Signal."""
        idx = self._resolve_single_idx(signal_idx)
        if idx is None:
            return
        self._run_single("RMS", "RMS_ANALYSE_TITLE", idx, start_zeit, ende_zeit)

    def fft_anwendung(self, start=None, ende=None, signal_idx=None):
        """FFT-Analyse für ein Signal."""
        idx = self._resolve_single_idx(signal_idx)
        if idx is None:
            return
        self._run_single("FFT", "FFT_ANALYSE_TITLE", idx, start, ende)

    def differential_anwendung(self):
        """Differential-Analyse für ein oder mehrere ausgewählte Signale."""
        signals = self._resolve_selected_signals()
        if signals is None:
            return
        if self.gui.dt is None:
            messagebox.showerror(Cfg.Texts.ERROR, Cfg.Texts.NO_DT)
            return
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in signals}
        use_filtered, filter_manager = self._get_filter_context()
        self._open_result_window(
            Cfg.Texts.DIFFERENTIAL_ANALYSE_TITLE,
            self._make_plot_func("DIFFERENTIAL", signals, header_to_signal_idx,
                                 use_filtered, filter_manager)
        )

    def integral_anwendung(self):
        """Integral-Analyse für ein oder mehrere ausgewählte Signale."""
        signals = self._resolve_selected_signals()
        if signals is None:
            return
        if self.gui.dt is None:
            messagebox.showerror(Cfg.Texts.ERROR, Cfg.Texts.NO_DT)
            return
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in signals}
        use_filtered, filter_manager = self._get_filter_context()
        self._open_result_window(
            Cfg.Texts.INTEGRAL_ANALYSE_TITLE,
            self._make_plot_func("INTEGRAL", signals, header_to_signal_idx,
                                 use_filtered, filter_manager)
        )

    def varianz_anwendung(self):
        """Statistik/Varianz-Analyse für ein oder mehrere ausgewählte Signale."""
        signals = self._resolve_selected_signals()
        if signals is None:
            return
        if self.gui.dt is None:
            messagebox.showerror(Cfg.Texts.ERROR, Cfg.Texts.NO_DT)
            return
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in signals}
        use_filtered, filter_manager = self._get_filter_context()
        self._open_result_window(
            Cfg.Texts.VARIANZ_ANALYSE_TITLE,
            self._make_plot_func("STATISTIK", signals, header_to_signal_idx,
                                 use_filtered, filter_manager)
        )

    # --------------------------------------------------------
    #  ANALYSE-METHODEN – Multi-Signal
    # --------------------------------------------------------

    def avg_multi_anwendung(self, signal_indices, start_zeit=None, ende_zeit=None):
        """Mittelwert-Analyse für mehrere Signale."""
        self._run_multi("AVG", "AVG_ANALYSE_MULTI_TITLE",
                        signal_indices, start_zeit, ende_zeit)

    def rms_multi_anwendung(self, signal_indices, start_zeit=None, ende_zeit=None):
        """Effektivwert-Analyse für mehrere Signale."""
        self._run_multi("RMS", "RMS_ANALYSE_MULTI_TITLE",
                        signal_indices, start_zeit, ende_zeit)

    def fft_multi_anwendung(self, signal_indices, start=None, ende=None):
        """FFT-Analyse für mehrere Signale."""
        self._run_multi("FFT", "FFT_ANALYSE_MULTI_TITLE",
                        signal_indices, start, ende)

    def differential_multi_anwendung(self, signal_indices):
        """Differential-Analyse für mehrere Signale."""
        if len(signal_indices) == 1:
            self.gui.selected_signals = [self.gui.headers[signal_indices[0]]]
            self.differential_anwendung()
            return
        self._run_multi("DIFFERENTIAL", "DIFFERENTIAL_ANALYSE_MULTI_TITLE",
                        signal_indices, dt_required=True)

    def integral_multi_anwendung(self, signal_indices):
        """Integral-Analyse für mehrere Signale."""
        if len(signal_indices) == 1:
            self.gui.selected_signals = [self.gui.headers[signal_indices[0]]]
            self.integral_anwendung()
            return
        self._run_multi("INTEGRAL", "INTEGRAL_ANALYSE_MULTI_TITLE",
                        signal_indices, dt_required=True)

    def varianz_multi_anwendung(self, signal_indices):
        """Statistik/Varianz-Analyse für mehrere Signale."""
        if len(signal_indices) == 1:
            self.gui.selected_signals = [self.gui.headers[signal_indices[0]]]
            self.varianz_anwendung()
            return
        self._run_multi("STATISTIK", "VARIANZ_ANALYSE_MULTI_TITLE",
                        signal_indices, dt_required=True)

    # --------------------------------------------------------
    #  ZEITBEREICH-DIALOGE
    # --------------------------------------------------------

    def zeige_zeitbereich_dialog(self, berechnungs_typ, signal_idx=None):
        """Öffnet Zeitbereich-Dialog und führt Einzelsignal-Analyse aus."""
        selected_signal = None
        if signal_idx is not None and signal_idx < len(self.gui.headers):
            selected_signal = self.gui.headers[signal_idx]
        elif hasattr(self.gui, 'selected_signal'):
            selected_signal = self.gui.selected_signal

        use_filtered, filter_manager = self._get_filter_context()
        filter_info = filter_manager.get_filter_info() if (use_filtered and filter_manager) else None

        def on_berechnen(result):
            zeitbereiche = result.get(berechnungs_typ, [(None, None)])
            for start_zeit, ende_zeit in zeitbereiche:
                if berechnungs_typ == Cfg.Analysis.NAMES["AVG"]:
                    self.avg_anwendung(start_zeit, ende_zeit, signal_idx)
                elif berechnungs_typ == Cfg.Analysis.NAMES["RMS"]:
                    self.rms_anwendung(start_zeit, ende_zeit, signal_idx)
                elif berechnungs_typ == Cfg.Analysis.NAMES["FFT"]:
                    self.fft_anwendung(start_zeit, ende_zeit)

        PlotManager.show_zeitbereich_dialog(
            parent=self.gui.root,
            t_max=self._get_t_max(),
            callback=on_berechnen,
            title=Cfg.Texts.ZEITBEREICH_DIALOG_TITLE.format(berechnungs_typ),
            selected_signal=selected_signal,
            is_filtered=use_filtered,
            filter_info=filter_info,
            analyse_typen=[berechnungs_typ],
        )

    def zeige_zeitbereich_dialog_multi(self, analysis_type, selected_signals):
        """Öffnet Zeitbereich-Dialog für Multi-Signal-Ansicht."""
        signal_indices = []
        for signal_name in selected_signals:
            try:
                signal_indices.append(self.gui.headers.index(signal_name))
            except ValueError:
                continue

        # Anzeigenamen für den Dialog kürzen
        display_name = ", ".join(selected_signals[:3])
        if len(selected_signals) > 3:
            display_name += " " + Cfg.Texts.MULTI_SIGNAL_SUFFIX.format(len(selected_signals) - 3)

        use_filtered, filter_manager = self._get_filter_context()
        filter_info = filter_manager.get_filter_info() if (use_filtered and filter_manager) else None

        # Dispatch-Tabelle: Analysetyp → Methode mit Zeitbereich
        _zeitbereich_dispatch = {
            Cfg.Analysis.NAMES["AVG"]: lambda s, e: self.avg_multi_anwendung(signal_indices, s, e),
            Cfg.Analysis.NAMES["RMS"]: lambda s, e: self.rms_multi_anwendung(signal_indices, s, e),
            Cfg.Analysis.NAMES["FFT"]: lambda s, e: self.fft_multi_anwendung(signal_indices, s, e),
        }
        # Analysetypen ohne Zeitbereich
        _direkt_dispatch = {
            Cfg.Analysis.NAMES["DIFFERENTIAL"]: lambda: self.differential_multi_anwendung(signal_indices),
            Cfg.Analysis.NAMES["INTEGRAL"]:     lambda: self.integral_multi_anwendung(signal_indices),
            Cfg.Analysis.NAMES["STATISTIK"]:    lambda: self.varianz_multi_anwendung(signal_indices),
        }

        def on_berechnen(result):
            zeitbereiche = result.get(analysis_type, [(None, None)])
            if analysis_type in _zeitbereich_dispatch:
                for start_zeit, ende_zeit in zeitbereiche:
                    _zeitbereich_dispatch[analysis_type](start_zeit, ende_zeit)
            elif analysis_type in _direkt_dispatch:
                _direkt_dispatch[analysis_type]()

        PlotManager.show_zeitbereich_dialog(
            parent=self.gui.root,
            t_max=self._get_t_max(),
            callback=on_berechnen,
            title=Cfg.Texts.ZEITBEREICH_DIALOG_TITLE.format(analysis_type),
            selected_signal=display_name,
            is_filtered=use_filtered,
            filter_info=filter_info,
            analyse_typen=[analysis_type],
        )