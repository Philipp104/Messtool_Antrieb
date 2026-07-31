"""
Live Plot Fenster Manager - Live-Plot-Verwaltung
==================================================
Verwaltet die Erstellung und Aktualisierung von Live-Plot-Fenstern
mit interaktiven Optionen für Signal, FFT, AVG, RMS, Differential und Integral.
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
import logging
import tkinter as tk
from tkinter import filedialog, ttk

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import numpy as np

# ============================================================
#  IMPORTS – Eigene Klassen
# ============================================================
from gui_module import meldungen as messagebox
from gui_module.plot_manager import PlotManager
from hilfsklassen.daten_verarbeiter import DatenVerarbeiter
from hilfsklassen.zentrales_logging import get_protocol_logger
from konfiguration import Cfg

# ============================================================
#  LOGGING
# ============================================================
logger          = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()

# ============================================================
#  KONSTANTEN
# ============================================================
_FFT_FARBEN = ['green', 'orange', 'red',  'blue',   'purple', 'brown']
_AVG_FARBEN = ['red',   'blue',   'green', 'orange', 'purple', 'brown']
_RMS_FARBEN = ['orange','blue',   'green', 'red',    'purple', 'brown']


# ============================================================
#  KLASSE
# ============================================================
class LivePlotFensterManager:
    """Verwaltet Live-Plot-Fenster."""

    def __init__(self, gui_manager, plot_window_manager):

        # --- Referenzen ---
        self.gui                 = gui_manager
        self.plot_window_manager = plot_window_manager

    # --------------------------------------------------------
    #  HILFSMETHODEN (intern)
    # --------------------------------------------------------

    def _get_t_max(self):
        """Gibt die maximale Zeit zurück, oder 10 als Fallback."""
        if isinstance(self.gui.t, (list, tuple)):
            return max((arr[-1] for arr in self.gui.t if len(arr) > 0), default=10)
        return self.gui.t[-1] if self.gui.t is not None and len(self.gui.t) > 0 else 10

    def _get_filter_info_if_active(self, plot_window_data):
        """Gibt filter_info zurück wenn Filter aktiv, sonst None."""
        is_filtered = plot_window_data.get('show_filtered_var', tk.BooleanVar()).get()
        if is_filtered and hasattr(self.gui, 'filter_manager'):
            return self.gui.filter_manager.get_filter_info()
        return None

    def _bind_var(self, var, name, callback):
        """Bindet eine tkinter-Variable mit Logging an einen Callback.
        Gibt die Trace-ID zurück, damit der Aufrufer den Trace bei Bedarf
        (z.B. beim Schliessen eines Fensters) wieder entfernen kann - wichtig
        bei geteilten/langlebigen Variablen wie self.gui.use_filtered_var,
        an die sonst bei jedem neuen Live-Plot-Fenster ein weiterer Callback
        gehängt würde, der nie wieder verschwindet."""
        def _wrapped(*_):
            try:
                protocol_logger.info("LIVE_PLOT_TOGGLE %s=%s", name, var.get())
            except Exception as e:
                logger.debug("LIVE_PLOT_TOGGLE-Log für '%s' fehlgeschlagen: %s", name, e)
            callback()
        try:
            return var.trace_add("write", _wrapped)
        except Exception:
            return var.trace("w", lambda *_: _wrapped())

    def _show_zeitbereich_and_update(self, plot_window_data, analyse_typ, zeitbereich_key, plot_window, title):
        """
        Öffnet Zeitbereich-Dialog für einen Analyse-Typ und speichert das Ergebnis.
        Wird für AVG, RMS und FFT verwendet.
        """
        signal_name = plot_window_data.get('signal_name', '')
        filter_info = self._get_filter_info_if_active(plot_window_data)

        def on_result(result):
            zeitbereiche = result.get(analyse_typ, [(None, None)])
            plot_window_data[zeitbereich_key] = zeitbereiche
            protocol_logger.info(
                "LIVE_PLOT_TIME_RANGE signal=%s | type=%s | ranges=%s",
                signal_name, analyse_typ, zeitbereiche,
            )
            self.update_single_plot(plot_window_data)

        PlotManager.show_zeitbereich_dialog(
            parent=plot_window,
            t_max=self._get_t_max(),
            callback=on_result,
            title=title,
            selected_signal=signal_name,
            is_filtered=bool(filter_info),
            filter_info=filter_info,
            analyse_typen=[analyse_typ]
        )

    def _get_var(self, plot_window_data, key, default=True):
        """Liest eine BooleanVar aus plot_window_data sicher aus."""
        var = plot_window_data.get(key)
        return var.get() if var is not None else default

    # --------------------------------------------------------
    #  FENSTER ERSTELLEN
    # --------------------------------------------------------

    def create_live_plot_window(self, selected_signal):
        """Erstellt ein Plot-Fenster mit Live-Aktualisierung."""
        if (not selected_signal
                or selected_signal == "Signal auswählen:"
                or not self.gui.signals
                or not self.gui.headers
                or self.gui.t is None):
            logger.info("Keine Daten zum Plotten verfügbar")
            return None

        protocol_logger.info("LIVE_PLOT_OPEN signal=%s", selected_signal)

        LP = Cfg.Layout.LivePlot
        T  = Cfg.Texts

        layout        = self.gui.layout_manager.create_live_plot_layout(selected_signal)
        plot_window   = layout['window']
        fig           = layout['fig']
        canvas        = layout['canvas']
        toolbar_frame = layout['toolbar_frame']
        options_frame = layout['options_frame']
        analysis_frame= layout['analysis_frame']

        # --- BooleanVars ---
        show_original_var   = tk.BooleanVar(value=True)
        show_filtered_var   = self.gui.use_filtered_var
        show_fft_master_var = tk.BooleanVar(value=False)
        show_amp_var        = tk.BooleanVar(value=False)
        show_phase_var      = tk.BooleanVar(value=False)
        show_avg_var        = tk.BooleanVar(value=False)
        show_rms_var        = tk.BooleanVar(value=False)
        show_diff_var       = tk.BooleanVar(value=False)
        show_integral_var   = tk.BooleanVar(value=False)

        # --- Plot-Daten-Dict ---
        plot_window_data = {
            'window':            plot_window,
            'signal_name':       selected_signal,
            'fig':               fig,
            'canvas':            canvas,
            'show_original_var': show_original_var,
            'show_filtered_var': show_filtered_var,
            'show_fft_master_var': show_fft_master_var,
            'show_amp_var':      show_amp_var,
            'show_phase_var':    show_phase_var,
            'show_avg_var':      show_avg_var,
            'show_rms_var':      show_rms_var,
            'show_diff_var':     show_diff_var,
            'show_integral_var': show_integral_var,
            'avg_zeitbereiche':  [],
            'rms_zeitbereiche':  [],
            'fft_zeitbereiche':  [],
        }

        # --------------------------------------------------------
        #  TOGGLE-HANDLER
        # --------------------------------------------------------

        def _on_filtered_toggled():
            if self.gui.use_filtered_var.get() and not self.gui._is_filter_ready():
                self.gui.use_filtered_var.set(False)
                messagebox.showwarning(T.LP_FILTER_NOT_READY, T.LP_FILTER_SELECT)
                return
            self.update_single_plot(plot_window_data)

        def _on_analyse_toggled(var, zeitbereich_key, analyse_typ, title):
            """Generischer Toggle-Handler für AVG, RMS, FFT."""
            if var.get():
                self._show_zeitbereich_and_update(
                    plot_window_data, analyse_typ, zeitbereich_key, plot_window, title
                )
            else:
                plot_window_data[zeitbereich_key] = []
                self.update_single_plot(plot_window_data)

        def _on_fft_master_toggled():
            on = show_fft_master_var.get()
            show_amp_var.set(on)
            show_phase_var.set(on)
            _on_analyse_toggled(show_fft_master_var, 'fft_zeitbereiche', 'FFT', T.LP_DIALOG_FFT)

        # --------------------------------------------------------
        #  WIDGETS – Options & Analyse
        # --------------------------------------------------------

        ttk.Checkbutton(options_frame, text=T.LP_ORIGINAL,   variable=show_original_var).pack(side=tk.LEFT, padx=LP.OPTIONS_ITEM_PAD_X)
        ttk.Checkbutton(options_frame, text=T.LP_FILTERED,   variable=show_filtered_var).pack(side=tk.LEFT, padx=LP.OPTIONS_ITEM_PAD_X)
        ttk.Separator(options_frame, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=LP.OPTIONS_ITEM_PAD_X)
        ttk.Checkbutton(options_frame, text=T.LP_FFT_MASTER, variable=show_fft_master_var).pack(side=tk.LEFT, padx=LP.OPTIONS_ITEM_PAD_X)
        ttk.Checkbutton(options_frame, text=T.LP_FFT_AMP,    variable=show_amp_var).pack(side=tk.LEFT, padx=LP.OPTIONS_ITEM_PAD_X)
        ttk.Checkbutton(options_frame, text=T.LP_FFT_PHASE,  variable=show_phase_var).pack(side=tk.LEFT, padx=LP.OPTIONS_ITEM_PAD_X)

        ttk.Checkbutton(analysis_frame, text=T.LP_AVG,         variable=show_avg_var).pack(side=tk.LEFT, padx=LP.ANALYSE_ITEM_PAD_X)
        ttk.Checkbutton(analysis_frame, text=T.LP_RMS,         variable=show_rms_var).pack(side=tk.LEFT, padx=LP.ANALYSE_ITEM_PAD_X)
        ttk.Checkbutton(analysis_frame, text=T.LP_DIFFERENTIAL,variable=show_diff_var).pack(side=tk.LEFT, padx=LP.ANALYSE_ITEM_PAD_X)
        ttk.Checkbutton(analysis_frame, text=T.LP_INTEGRAL,    variable=show_integral_var).pack(side=tk.LEFT, padx=LP.ANALYSE_ITEM_PAD_X)

        # --------------------------------------------------------
        #  VARIABLEN-BINDINGS
        # --------------------------------------------------------

        simple_update = lambda: self.update_single_plot(plot_window_data)

        self._bind_var(show_original_var,   "original",      simple_update)
        self._bind_var(show_amp_var,        "fft_amplitude", simple_update)
        self._bind_var(show_phase_var,      "fft_phase",     simple_update)
        self._bind_var(show_diff_var,       "differential",  simple_update)
        self._bind_var(show_integral_var,   "integral",      simple_update)
        filtered_trace_id = self._bind_var(show_filtered_var, "filtered", _on_filtered_toggled)
        self._bind_var(show_fft_master_var, "fft_master",    _on_fft_master_toggled)
        self._bind_var(show_avg_var, "avg", lambda: _on_analyse_toggled(
            show_avg_var, 'avg_zeitbereiche', 'AVG', "AVG - Zeitbereich auswählen"))
        self._bind_var(show_rms_var, "rms", lambda: _on_analyse_toggled(
            show_rms_var, 'rms_zeitbereiche', 'RMS', "RMS - Zeitbereich auswählen"))

        # --------------------------------------------------------
        #  EXPORT
        # --------------------------------------------------------

        def export_current_signal():
            """Exportiert den aktuell angezeigten Plot als PNG-Datei."""
            fig = plot_window_data.get('fig')
            if fig is None:
                self.gui.status_label.config(text="Kein Plot zum Export vorhanden.")
                return

            safe_name = "".join(c if c.isalnum() or c in " _-()" else "_" for c in selected_signal)
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG-Bild", "*.png")],
                initialfile=f"{safe_name}.png",
                parent=plot_window,
            )
            if not save_path:
                self.gui.status_label.config(text="Export abgebrochen.")
                return

            protocol_logger.info("EXPORT_LIVE_PNG path=%s | signal=%s", save_path, selected_signal)

            try:
                fig.savefig(save_path, dpi=300, bbox_inches="tight", format="png")
            except Exception as e:
                logger.exception("Fehler beim PNG-Export: %s", e)
                self.gui.status_label.config(text=f"Export fehlgeschlagen: {e}")
                return

            self.gui.status_label.config(text=f"Plot gespeichert unter: {save_path}")

        export_button = ttk.Button(toolbar_frame, text=T.LP_EXPORT, command=export_current_signal)
        export_button.pack(side=tk.RIGHT, padx=LP.TOOLBAR_BUTTON_PAD_X, pady=LP.TOOLBAR_PAD_Y)
        plot_window_data['export_button'] = export_button

        # --------------------------------------------------------
        #  FENSTER SCHLIESSEN
        # --------------------------------------------------------

        def on_window_close():
            if plot_window_data in self.gui.open_plot_windows:
                self.gui.open_plot_windows.remove(plot_window_data)
            # show_filtered_var ist self.gui.use_filtered_var - eine geteilte,
            # session-lange Variable. Ohne trace_remove wuerde der oben per
            # _bind_var angehaengte Callback (inkl. Referenz auf plot_window_data/
            # fig/canvas) fuer immer daran haengen bleiben, auch nach dem Schliessen
            # dieses Fensters.
            try:
                show_filtered_var.trace_remove("write", filtered_trace_id)
            except Exception as e:
                logger.debug("Trace-Cleanup für use_filtered_var fehlgeschlagen: %s", e)
            plot_window.destroy()

        plot_window.protocol("WM_DELETE_WINDOW", on_window_close)

        self.update_single_plot(plot_window_data)
        return plot_window_data

    # --------------------------------------------------------
    #  PLOT AKTUALISIEREN
    # --------------------------------------------------------

    def update_single_plot(self, plot_window_data):
        """Aktualisiert einen einzelnen Plot (dynamische Achsen je Auswahl)."""
        if not plot_window_data:
            logger.debug("plot_window_data ist None/leer")
            return
        try:
            if not plot_window_data['window'].winfo_exists():
                logger.info("Fenster existiert nicht mehr")
                return
        except Exception as e:
            logger.exception("Exception bei Fenster-Prüfung: %s", e)
            return

        selected = plot_window_data['signal_name']
        fig      = plot_window_data['fig']
        canvas   = plot_window_data['canvas']
        fig.clear()

        # --- Overview-Sonderfall ---
        if selected == "Overview":
            PlotManager.plot_overview(fig, self.gui.t, self.gui.signals, self.gui.headers, self.gui.units)
            canvas.draw()
            return

        # --- Zustand lesen ---
        getv = lambda key, default=True: self._get_var(plot_window_data, key, default)

        show_original   = getv('show_original_var',   True)
        show_filtered   = getv('show_filtered_var',   False) and self.gui._is_filter_ready()
        show_fft_master = getv('show_fft_master_var', False)
        show_amp        = getv('show_amp_var',        False) and show_fft_master
        show_phase      = getv('show_phase_var',      False) and show_fft_master
        show_avg        = getv('show_avg_var',        False)
        show_rms        = getv('show_rms_var',        False)
        show_diff       = getv('show_diff_var',       False)
        show_integral   = getv('show_integral_var',   False)

        fft_zeitbereiche = plot_window_data.get('fft_zeitbereiche', [])
        avg_zeitbereiche = plot_window_data.get('avg_zeitbereiche', [])
        rms_zeitbereiche = plot_window_data.get('rms_zeitbereiche', [])

        # --- Signal laden ---
        try:
            idx = self.gui.headers.index(selected)
        except (ValueError, IndexError):
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Signal '{selected}' nicht gefunden.",
                    ha="center", va="center", transform=ax.transAxes)
            canvas.draw()
            return

        original_signal = self.gui.signals[idx]
        unit            = self.gui.units[idx] if idx < len(self.gui.units) else ""
        t               = PlotManager.t_for_idx(self.gui.t, idx)
        filter_type     = Cfg.Defaults.FILTER_TYP

        filtered_signal = original_signal
        if show_filtered and self.gui.filter_manager and self.gui.filter_manager.filter_type != Cfg.Defaults.FILTER_TYP:
            filtered_signal = self.gui.filter_manager.apply_filter(original_signal)
            filter_type     = self.gui.filter_manager.filter_type

        # --- FFT-Daten berechnen ---
        fft_daten = []
        if show_amp or show_phase:
            quellen = fft_zeitbereiche if fft_zeitbereiche else [(None, None)]
            for i, (start, ende) in enumerate(quellen):
                if start is not None:
                    maske   = (t >= start) & (t <= ende)
                    segment = original_signal[maske]
                else:
                    segment = original_signal

                if show_filtered and self.gui.filter_manager and filter_type != Cfg.Defaults.FILTER_TYP:
                    segment = self.gui.filter_manager.apply_filter(segment)
                    label   = f"FFT {start}-{ende}s (gefiltert)" if start else "FFT (gefiltert)"
                else:
                    label   = f"FFT {start}-{ende}s" if start else "FFT (ganzes Signal)"

                f_axis, amp, phase = DatenVerarbeiter.compute_fft(segment, self.gui.dt)
                fft_daten.append((f_axis, amp, phase, label, _FFT_FARBEN[i % len(_FFT_FARBEN)]))

        # --- Subplot-Anzahl berechnen ---
        num_subplots = (
            1
            + int(show_amp)
            + int(show_phase)
            + int(show_diff)
            + int(show_integral)
            + (2 if show_avg and avg_zeitbereiche else 0)
            + (2 if show_rms and rms_zeitbereiche else 0)
        )
        current_subplot = 1

        # --------------------------------------------------------
        #  SUBPLOT ZEICHNEN
        # --------------------------------------------------------

        def _next_ax():
            nonlocal current_subplot
            ax = fig.add_subplot(num_subplots, 1, current_subplot)
            current_subplot += 1
            return ax

        # --- Haupt-Signal ---
        ax1 = _next_ax()
        if show_original:
            ax1.plot(t, original_signal, color=Cfg.Colors.SIGNAL_ORIGINAL,
                     label=f"Original [{unit}]", alpha=0.7)
        if show_filtered and filter_type != Cfg.Defaults.FILTER_TYP:
            ax1.plot(t, filtered_signal, color="crimson",
                     label=f"Gefiltert ({filter_type}) [{unit}]")
        ax1.set_title(f"{selected} [{unit}]")
        ax1.set_xlabel("Zeit [s]")
        ax1.set_ylabel(f"Amplitude [{unit}]")
        ax1.grid(True)
        ax1.legend()

        # --- FFT Amplitude ---
        if show_amp and fft_daten:
            ax_amp = _next_ax()
            for f_axis, amp, phase, label, farbe in fft_daten:
                ax_amp.plot(f_axis, amp, color=farbe, label=label)
            ax_amp.set_title(f"FFT Amplitude [{unit}]")
            ax_amp.set_xlabel("Frequenz [Hz]")
            ax_amp.set_ylabel("Amplitude")
            ax_amp.grid(True)
            ax_amp.legend()

        # --- FFT Phase ---
        if show_phase and fft_daten:
            ax_phase = _next_ax()
            for f_axis, amp, phase, label, farbe in fft_daten:
                ax_phase.plot(f_axis, phase, color=farbe, label=label)
            ax_phase.set_title("FFT Phase [rad]")
            ax_phase.set_xlabel("Frequenz [Hz]")
            ax_phase.set_ylabel("Phase [rad]")
            ax_phase.grid(True)
            ax_phase.legend()

        # --- Differential ---
        if show_diff:
            ax_diff = _next_ax()
            ax_diff.plot(t, np.gradient(original_signal, t), color="darkorange")
            ax_diff.set_title(f"Differential (Ableitung) [{unit}/s]")
            ax_diff.set_xlabel("Zeit [s]")
            ax_diff.set_ylabel(f"d/dt [{unit}/s]")
            ax_diff.grid(True)

        # --- Integral ---
        if show_integral:
            ax_int     = _next_ax()
            dt_arr     = np.diff(t)
            signal_for_integral = filtered_signal if show_filtered else original_signal
            integral   = np.concatenate([[0], np.cumsum((signal_for_integral[:-1] + signal_for_integral[1:]) * dt_arr / 2)])
            ax_int.plot(t, integral, color="teal")
            ax_int.set_title(f"Integral [{unit}*s]")
            ax_int.set_xlabel("Zeit [s]")
            ax_int.set_ylabel(f"Integral [{unit}*s]")
            ax_int.grid(True)

        # --- AVG (Signal + Histogramm) ---
        if show_avg and avg_zeitbereiche:
            ax_avg  = _next_ax()
            ax_hist = _next_ax()
            signal_for_avg = filtered_signal if show_filtered else original_signal

            for i, (start, ende) in enumerate(avg_zeitbereiche):
                farbe = _AVG_FARBEN[i % len(_AVG_FARBEN)]
                if start is None:
                    seg, t_seg = signal_for_avg, t
                    lbl_base   = "Ganzes Signal"
                else:
                    maske      = (t >= start) & (t <= ende)
                    seg, t_seg = signal_for_avg[maske], t[maske]
                    lbl_base   = f"{start}-{ende}s"
                avg_val = float(np.nanmean(seg))

                ax_avg.plot(t_seg, seg, color=farbe, alpha=0.7, label=f"{lbl_base}, AVG={avg_val:.4g}")
                ax_avg.axhline(avg_val, color=farbe, linestyle="--", linewidth=2)
                ax_hist.hist(seg[~np.isnan(seg)], bins=50, color=farbe, alpha=0.5, label=lbl_base)
                ax_hist.axvline(avg_val, color=farbe, linestyle="--", linewidth=2)

            ax_avg.set_title(f"{selected} - AVG Analyse [{unit}]")
            ax_avg.set_xlabel("Zeit [s]")
            ax_avg.set_ylabel(f"Amplitude [{unit}]")
            ax_avg.grid(True)
            ax_avg.legend()

            ax_hist.set_title(f"Histogramm - AVG Vergleich [{unit}]")
            ax_hist.set_xlabel(f"Wert [{unit}]")
            ax_hist.set_ylabel("Häufigkeit")
            ax_hist.grid(True)
            ax_hist.legend()

        # --- RMS (Signal + Signal²) ---
        if show_rms and rms_zeitbereiche:
            ax_rms = _next_ax()
            ax_sq  = _next_ax()
            signal_for_rms = filtered_signal if show_filtered else original_signal

            for i, (start, ende) in enumerate(rms_zeitbereiche):
                farbe = _RMS_FARBEN[i % len(_RMS_FARBEN)]
                if start is None:
                    seg, t_seg = signal_for_rms, t
                    lbl_base   = "Ganzes Signal"
                else:
                    maske      = (t >= start) & (t <= ende)
                    seg, t_seg = signal_for_rms[maske], t[maske]
                    lbl_base   = f"{start}-{ende}s"
                rms_val = float(np.sqrt(np.nanmean(seg**2)))

                ax_rms.plot(t_seg, seg, color=farbe, alpha=0.7, label=f"{lbl_base}, RMS={rms_val:.4g}")
                ax_rms.axhline( rms_val, color=farbe, linestyle="--", linewidth=2)
                ax_rms.axhline(-rms_val, color=farbe, linestyle="--", linewidth=2)
                ax_sq.plot(t_seg, seg**2, color=farbe, alpha=0.7, label=lbl_base)
                ax_sq.axhline(rms_val**2, color=farbe, linestyle="--", linewidth=2)

            ax_rms.set_title(f"{selected} - RMS Analyse [{unit}]")
            ax_rms.set_xlabel("Zeit [s]")
            ax_rms.set_ylabel(f"Amplitude [{unit}]")
            ax_rms.grid(True)
            ax_rms.legend()

            ax_sq.set_title(f"Signal² - RMS Vergleich [{unit}^2]")
            ax_sq.set_xlabel("Zeit [s]")
            ax_sq.set_ylabel(f"Amplitude² [{unit}²]")
            ax_sq.grid(True)
            ax_sq.legend()

        fig.tight_layout()
        canvas.draw()