"""
Plot Fenster Manager - Plot-Fenster-Verwaltung
==============================================
Verwaltet Plot-Fenster (Erstellung, Aktualisierung, Events).
Delegiert spezialisierte Funktionen an andere Module.
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)

from gui_module.plot_manager import PlotManager
from gui_module.signal_auswahlmanager import SignalAuswahlManager
from gui_module.live_plot_fenster_manager import LivePlotFensterManager
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class PlotWindowManager:
    """Verwaltet Plot-Fenster (Erstellung, Aktualisierung, Events)."""

    def __init__(self, gui_manager):
        self.gui = gui_manager
        self.active_signal_window = None
        self.overlay_filter_state = {
            'enabled': False,
            'type': 'Kein Filter',
            'freq1': '',
            'freq2': '',
            'characteristic': 'butterworth',
            'order': '1.Ordnung'
        }
        # Speichere Referenzen zu Spezialisten
        self.signal_auswahlmanager = SignalAuswahlManager(gui_manager, self)
        self.live_plot_fenster = LivePlotFensterManager(gui_manager, self)

    def show_multi_signal_overlay_window(self):
        """Öffnet ein Fenster zur Auswahl beliebig vieler Signale und zeigt sie gemeinsam in einem Plot."""
        self.signal_auswahlmanager.show_multi_signal_overlay_window(self.active_signal_window)

    def show_overview_window(self):
        """Zeigt den Übersichtsplot in einem separaten Fenster."""
        if not self.gui.signals or not self.gui.headers or self.gui.t is None:
            logger.info("Keine Daten für Übersichtsplot verfügbar")
            return

        for widget in self.gui.mid_region.winfo_children():
            if isinstance(widget, ttk.Frame):
                widget.destroy()

        plot_frame = ttk.Frame(self.gui.mid_region)
        plot_frame.pack(fill=tk.BOTH, expand=True)

        fig = plt.Figure(figsize=(18, 14))
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)

        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)

        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        PlotManager.plot_overview(fig, self.gui.t, self.gui.signals, self.gui.headers, self.gui.units)
        canvas.draw()

    def update_all_plot_windows(self):
        """Aktualisiert alle offenen Plot-Fenster mit den aktuellen Filter-Einstellungen"""
        if not hasattr(self.gui, 'open_plot_windows'):
            return

        for plot_data in self.gui.open_plot_windows[:]:
            try:
                if 'window' in plot_data and plot_data['window'].winfo_exists():
                    self.live_plot_fenster.update_single_plot(plot_data)
            except Exception as e:
                logger.exception("Fehler beim Aktualisieren des Plot-Fensters: %s", e)
                self.gui.open_plot_windows.remove(plot_data)

    def create_live_plot_window(self, selected_signal):
        """Erstellt ein Plot-Fenster mit Live-Aktualisierung"""
        return self.live_plot_fenster.create_live_plot_window(selected_signal)

    def update_single_plot(self, plot_window_data):
        """Aktualisiert einen einzelnen Plot"""
        self.live_plot_fenster.update_single_plot(plot_window_data)

    def _zeitbereiche_ueberlappen(self, bereiche):
        """Prüft ob mindestens zwei Zeitbereiche sich überlappen."""
        if len(bereiche) <= 1:
            return True
        for i in range(len(bereiche)):
            s1, e1 = bereiche[i]
            if s1 is None or e1 is None:
                continue
            for j in range(i + 1, len(bereiche)):
                s2, e2 = bereiche[j]
                if s2 is None or e2 is None:
                    continue
                if not (e1 < s2 or e2 < s1):
                    return True
        return False

    def _create_notebook_window(self, select_window, selected_list, signal_indices, 
                                 selected_analyses, header_to_signal_idx, use_filtered,
                                 zeitbereiche_dict, grouped_headers=None):
        """Erstellt das Notebook-Fenster mit allen Analyse-Tabs."""
        from gui_module.analyse_plotter import AnalysePlotter

        window_type = (
            self.gui.entry6.get().strip() if hasattr(self.gui, "entry6") else None
        ) or None

        _ts = self.gui.timestamps
        logger.info(
            "[DEBUG-ZEITACHSE] _create_notebook_window: self.gui.timestamps=%s",
            "None" if _ts is None else f"{len(_ts)} Werte, erster={_ts[0]}"
        )

        result_window = tb.Toplevel(select_window)
        result_window.title("Analyse-Ergebnisse")
        result_window.state('zoomed')
        self.gui.apply_icon(result_window)

        notebook = ttk.Notebook(result_window)
        notebook.pack(fill=tk.BOTH, expand=True)

        for analyse_typ in selected_analyses:
            zeitbereiche = zeitbereiche_dict.get(analyse_typ, [(None, None)])
            
            if len(zeitbereiche) <= 1 or self._zeitbereiche_ueberlappen(zeitbereiche):
                tab = ttk.Frame(notebook)
                notebook.add(tab, text=analyse_typ)
                for start_zeit, ende_zeit in zeitbereiche:
                    if grouped_headers:
                        AnalysePlotter.create_group_analysis_tab(
                            frame=tab,
                            analyse_typ=analyse_typ,
                            grouped_headers=grouped_headers,
                            signals=self.gui.signals,
                            units=self.gui.units,
                            t=self.gui.t,
                            timestamps=self.gui.timestamps,
                            dt=self.gui.dt,
                            header_to_signal_idx=header_to_signal_idx,
                            use_filtered=use_filtered,
                            filter_manager=self.gui.filter_manager,
                            window_type=window_type,
                            start_zeit=start_zeit,
                            ende_zeit=ende_zeit
                        )
                    else:
                        AnalysePlotter.create_analysis_tab(
                            frame=tab,
                            analyse_typ=analyse_typ,
                            selected_headers=selected_list,
                            signals=self.gui.signals,
                            units=self.gui.units,
                            t=self.gui.t,
                            timestamps=self.gui.timestamps,
                            dt=self.gui.dt,
                            header_to_signal_idx=header_to_signal_idx,
                            use_filtered=use_filtered,
                            filter_manager=self.gui.filter_manager,
                            window_type=window_type,
                            start_zeit=start_zeit,
                            ende_zeit=ende_zeit
                        )
            else:
                for idx, (start_zeit, ende_zeit) in enumerate(zeitbereiche):
                    tab_name = f"{analyse_typ} ({idx+1})"
                    tab = ttk.Frame(notebook)
                    notebook.add(tab, text=tab_name)
                    if grouped_headers:
                        AnalysePlotter.create_group_analysis_tab(
                            frame=tab,
                            analyse_typ=analyse_typ,
                            grouped_headers=grouped_headers,
                            signals=self.gui.signals,
                            units=self.gui.units,
                            t=self.gui.t,
                            timestamps=self.gui.timestamps,
                            dt=self.gui.dt,
                            header_to_signal_idx=header_to_signal_idx,
                            use_filtered=use_filtered,
                            filter_manager=self.gui.filter_manager,
                            window_type=window_type,
                            start_zeit=start_zeit,
                            ende_zeit=ende_zeit
                        )
                    else:
                        AnalysePlotter.create_analysis_tab(
                            frame=tab,
                            analyse_typ=analyse_typ,
                            selected_headers=selected_list,
                            signals=self.gui.signals,
                            units=self.gui.units,
                            t=self.gui.t,
                            timestamps=self.gui.timestamps,
                            dt=self.gui.dt,
                            header_to_signal_idx=header_to_signal_idx,
                            use_filtered=use_filtered,
                            filter_manager=self.gui.filter_manager,
                            window_type=window_type,
                            start_zeit=start_zeit,
                            ende_zeit=ende_zeit
                        )
