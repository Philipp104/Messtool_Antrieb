"""
Analyse Plotter - Analyse-Visualisierungsfunktionen
====================================================
Stellt Methoden für komplexe Analyse-Plots bereit:
Signal-, AVG-, RMS-, FFT-, Differential-, Integral-,
und Statistik-Analysen für Einzel- und Gruppensignale.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import tkinter as tk
from tkinter import ttk, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
import logging

logger = logging.getLogger(__name__)

from gui_module import meldungen as messagebox
from gui_module.plot_manager import PlotManager
from konfiguration import Cfg


class AnalysePlotter:
    """Klasse für alle Analyse-Plot-Funktionen"""

    @staticmethod
    def _export_figure_as_png(fig, parent_window, default_name="Plot"):
        """Exportiert die aktuell angezeigte Grafik (fig) als PNG-Datei."""
        safe_name = "".join(c if c.isalnum() or c in " _-()" else "_" for c in default_name)
        save_path = filedialog.asksaveasfilename(
            title="Plot als PNG exportieren",
            defaultextension=".png",
            filetypes=[("PNG-Bild", "*.png")],
            initialfile=f"{safe_name}.png",
            parent=parent_window,
        )
        if not save_path:
            return

        try:
            fig.savefig(save_path, dpi=300, bbox_inches="tight", format="png")
        except Exception as e:
            logger.exception("Fehler beim PNG-Export: %s", e)
            messagebox.showerror("Export fehlgeschlagen", str(e), parent=parent_window)
            return

        messagebox.showinfo("Export", f"Plot gespeichert unter:\n{save_path}", parent=parent_window)

    @staticmethod
    def _fft_amplitude(y, dt, window_type):
        """Amplitudenspektrum (einseitig) mit Fensterfunktion und korrekter Normierung.

        Ohne Fenster (rechteckig) leckt Energie benachbarter Frequenzen in jeden Bin
        (Leck-Effekt) und verschmiert Peaks. Die Fensterfunktion (Hanning/Hamming/
        Blackman) reduziert das, kostet aber Amplitude - deshalb Normierung auf
        sum(window) statt N. DC- und (bei geradem N) Nyquist-Bin haben kein
        gespiegeltes Gegenstück und werden daher nicht verdoppelt.
        """
        n = len(y)
        if window_type == "hanning":
            window = np.hanning(n)
        elif window_type == "hamming":
            window = np.hamming(n)
        elif window_type == "blackman":
            window = np.blackman(n)
        else:  # rectangular / None
            window = np.ones(n)

        freq = np.fft.rfftfreq(n, dt)
        fft_complex = np.fft.rfft(y * window)
        amplitude = np.abs(fft_complex) * 2 / window.sum()
        amplitude[0] /= 2
        if n % 2 == 0:
            amplitude[-1] /= 2
        return freq, amplitude, fft_complex

    @staticmethod
    def create_analysis_tab(frame, analyse_typ, selected_headers, signals, units, t, dt,
                            header_to_signal_idx, use_filtered, filter_manager,
                            start_zeit=None, ende_zeit=None, timestamps=None, window_type=None):
        """Erstellt einen Analyse-Plot: Jedes Signal bekommt eigenen Subplot."""
        t_full = t
        timestamps_full = timestamps
        if not hasattr(frame, "_cursor_range"):
            frame._cursor_range = None
        if not hasattr(frame, "_range_history"):
            # Historie der Zeitbereichs-Zooms (Bereichsauswahl) - überlebt den
            # kompletten Neuaufbau von frame in _render(), im Gegensatz zur
            # feineren Scroll/Pan-Historie, die pro Figure in plot_manager.py lebt.
            frame._range_history       = [None]
            frame._range_history_index = 0

        def _get_effective_range():
            cursor_range = getattr(frame, "_cursor_range", None)
            if cursor_range:
                return cursor_range[0], cursor_range[1], True
            if start_zeit is not None and ende_zeit is not None:
                return start_zeit, ende_zeit, False
            return None, None, False

        def _render():
            for child in frame.winfo_children():
                child.destroy()

            start_eff, end_eff, strict_range = _get_effective_range()
            xlim_start = None
            xlim_end = None
            mask_start = None
            mask_end = None

            if start_eff is not None and end_eff is not None:
                if strict_range:
                    mask_start, mask_end = start_eff, end_eff
                    xlim_start, xlim_end = PlotManager._apply_axis_margin(start_eff, end_eff, margin_percent=5)
                else:
                    margin_start, margin_end = PlotManager._apply_axis_margin(start_eff, end_eff, margin_percent=5)
                    xlim_start, xlim_end = margin_start, margin_end
                    mask_start, mask_end = margin_start, margin_end

            sns.set_theme(style="whitegrid")
            sns.set_context("notebook")
            sns.set_palette("husl")
            plt.rcParams.update(Cfg.PlotStyle.MPL_RCPARAMS)  # sns.set_theme() setzt figure.facecolor zurück auf Weiß

            n_signals = len(selected_headers)
            colors = sns.color_palette("husl", n_signals)

            is_filtered = (use_filtered and filter_manager and
                           filter_manager.filter_type != "Kein Filter")

            if is_filtered:
                filter_info = filter_manager.get_filter_info()
                filter_str = f" (Gefiltert: {filter_info['type']}, {filter_info['order']}, {filter_info['characteristic']})"
            else:
                filter_str = ""

            # Jedes Signal bekommt seine EIGENE Zeitachse (PlotManager.t_for_idx) -
            # im Normalfall (ein gemeinsames t fuer alle Signale) liefert das exakt
            # dasselbe wie vorher, im kombinierten Signal-Pool (Batch, verschiedene
            # Dateien/Laengen) je Signal dessen eigenes Zeitarray.
            signal_list = []
            skipped_out_of_range = 0
            for i, header in enumerate(selected_headers):
                idx = header_to_signal_idx.get(header)
                if idx is None or idx >= len(signals):
                    continue
                t_full_i = PlotManager.t_for_idx(t_full, idx)
                # Unmaskiert - der Startzeitpunkt fuer die "Uhrzeit"-Achse bezieht
                # sich immer auf t=0 der ganzen Datei, nicht auf den gezoomten Bereich.
                timestamps_i = PlotManager.t_for_idx(timestamps_full, idx)
                original = signals[idx]

                if mask_start is not None and mask_end is not None:
                    maske_i = (t_full_i >= mask_start) & (t_full_i <= mask_end)
                    if not np.any(maske_i):
                        skipped_out_of_range += 1
                        continue
                    t_local_i = t_full_i[maske_i]
                    original = original[maske_i]
                else:
                    t_local_i = t_full_i

                unit = units[idx] if idx < len(units) else ""
                color = colors[i]

                if is_filtered:
                    filtered = filter_manager.apply_filter(original)
                else:
                    filtered = original

                signal_list.append({
                    "header": header,
                    "original": original,
                    "filtered": filtered,
                    "unit": unit,
                    "color": color,
                    "t_local": t_local_i,
                    "timestamps_i": timestamps_i,
                })

            n_signals = len(signal_list)
            if n_signals == 0:
                message = (
                    "Kein Signal im gewaehlten Zeitbereich"
                    if skipped_out_of_range > 0
                    else "Keine gueltigen Signale ausgewaehlt"
                )
                fig = plt.Figure(figsize=(14, 8))
                ax = fig.add_subplot(111)
                ax.text(0.5, 0.5, message, ha="center", va="center")
                canvas = FigureCanvasTkAgg(fig, master=frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
                return

            if analyse_typ == "Signal":
                plot_types = ["Original", "Gefiltert"] if is_filtered else ["Original"]
            elif analyse_typ in ["AVG", "RMS"]:
                plot_types = ["Original", "Gefiltert", analyse_typ] if is_filtered else ["Original", analyse_typ]
            elif analyse_typ == "Differential":
                plot_types = ["Original", "Gefiltert", "Ableitung"] if is_filtered else ["Original", "Ableitung"]
            elif analyse_typ == "Integral":
                plot_types = ["Original", "Gefiltert", "Integral"] if is_filtered else ["Original", "Integral"]
            elif analyse_typ == "FFT":
                plot_types = ["Original", "Gefiltert", "Amplitude", "Phase"] if is_filtered else ["Original", "Amplitude", "Phase"]
            elif analyse_typ == "Statistik":
                plot_types = ["Original", "Gefiltert", "Statistik"] if is_filtered else ["Original", "Statistik"]
            else:
                plot_types = ["Original"]

            total_subplots = n_signals * len(plot_types)
            fig_height = max(3, total_subplots * 3)
            fig = plt.Figure(figsize=(14, fig_height))

            axes_dict = PlotManager._setup_subplot_grid(fig, n_signals, plot_types)

            all_axes = []
            signal_data = {}
            time_axes = set()

            for ptype in plot_types:
                for sig_idx, sig_info in enumerate(signal_list):
                    ax = axes_dict[ptype][sig_idx]
                    all_axes.append(ax)

                    header = sig_info["header"]
                    original = sig_info["original"]
                    filtered = sig_info["filtered"]
                    unit = sig_info["unit"]
                    color = sig_info["color"]
                    t_local = sig_info["t_local"]

                    if ptype == "Original":
                        sns.lineplot(x=t_local, y=original, ax=ax, color=color)
                        ax.set_title(f"{header} - Original [{unit}]")
                        signal_data[ax] = (t_local, original)
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude", show_legend=False)

                    elif ptype == "Gefiltert":
                        sns.lineplot(x=t_local, y=filtered, ax=ax, color=color)
                        ax.set_title(f"{header} - Gefiltert{filter_str} [{unit}]")
                        signal_data[ax] = (t_local, filtered)
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude", show_legend=False)

                    elif ptype == "AVG":
                        avg_value = float(np.nanmean(filtered))
                        sns.lineplot(x=t_local, y=filtered, ax=ax, color=color, label=f"{header}")
                        ax.axhline(avg_value, color="red", linestyle="--", linewidth=2,
                                   label=f"AVG = {avg_value:.4f} {unit}")
                        ax.set_title(f"{header} - AVG = {avg_value:.4f} [{unit}]")
                        signal_data[ax] = (t_local, filtered)
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude")

                    elif ptype == "RMS":
                        rms_value = float(np.sqrt(np.nanmean(filtered**2)))
                        sns.lineplot(x=t_local, y=filtered, ax=ax, color=color, label=f"{header}")
                        ax.axhline(rms_value, color="purple", linestyle="--", linewidth=2,
                                   label=f"RMS = {rms_value:.4f} {unit}")
                        ax.set_title(f"{header} - RMS = {rms_value:.4f} [{unit}]")
                        signal_data[ax] = (t_local, filtered)
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude")

                    elif ptype == "Ableitung":
                        diff = np.gradient(filtered, dt)
                        unit_diff = f"{unit}/s" if unit else "1/s"
                        sns.lineplot(x=t_local, y=diff, ax=ax, color="crimson")
                        ax.set_title(f"{header} - Ableitung [{unit_diff}]")
                        signal_data[ax] = (t_local, diff)
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, f"Ableitung [{unit_diff}]", show_legend=False)

                    elif ptype == "Integral":
                        integral = np.cumsum(filtered) * dt
                        unit_int = f"{unit}*s" if unit else "unit*s"
                        sns.lineplot(x=t_local, y=integral, ax=ax, color="darkgreen")
                        ax.set_title(f"{header} - Integral [{unit_int}]")
                        signal_data[ax] = (t_local, integral)
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, f"Integral [{unit_int}]", show_legend=False)

                    elif ptype == "Amplitude":
                        freq, fft_amp, _ = AnalysePlotter._fft_amplitude(filtered, dt, window_type)
                        sns.lineplot(x=freq, y=fft_amp, ax=ax, color=color)
                        ax.set_title(f"{header} - Amplitudenspektrum [{unit}]")
                        signal_data[ax] = (freq, fft_amp)
                        PlotManager._configure_ax(ax, "Amplitude", show_legend=False)

                    elif ptype == "Phase":
                        freq, _, fft_complex = AnalysePlotter._fft_amplitude(filtered, dt, window_type)
                        fft_phase = np.angle(fft_complex, deg=True)
                        sns.lineplot(x=freq, y=fft_phase, ax=ax, color=color)
                        ax.set_title(f"{header} - Phasenspektrum [Grad]")
                        signal_data[ax] = (freq, fft_phase)
                        PlotManager._configure_ax(ax, "Phase [Grad]", show_legend=False)

                    elif ptype == "Statistik":
                        mean_val = np.mean(filtered)
                        std_val = np.std(filtered)
                        sns.lineplot(x=t_local, y=filtered, ax=ax, color=color)
                        ax.axhline(y=mean_val, color=color, linestyle="--", alpha=0.5)
                        ax.fill_between(t_local, mean_val - std_val, mean_val + std_val, color=color, alpha=0.2)
                        ax.set_title(f"{header} - Mean={mean_val:.4f}, Std={std_val:.4f} [{unit}]")
                        signal_data[ax] = (t_local, filtered)
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude", show_legend=False)

            axis_mode = getattr(frame, "_axis_mode", "Relative Zeit (s)")
            is_pool   = isinstance(t_full, (list, tuple))

            def _make_zeit_formatter(ts_array):
                if ts_array is None or len(ts_array) == 0:
                    return None
                start_ts = pd.Timestamp(ts_array[0])

                def _fmt(x, pos=None):
                    try:
                        return (start_ts + pd.Timedelta(seconds=float(x))).strftime("%H:%M:%S")
                    except Exception:
                        return ""
                return _fmt

            if is_pool:
                # Signal-Pool (Batch-Import, mehrere Dateien): jedes Signal/jede
                # Zeile hat ihre EIGENE Zeitachse - deshalb pro Zeile eine eigene
                # Uhrzeit-Formatierung, und (anders als im Normalfall) jede Zeile
                # zeigt ihre eigene Tick-Beschriftung statt nur die unterste.
                for ptype in plot_types:
                    group_axes = axes_dict[ptype]
                    for row_idx, ax in enumerate(group_axes):
                        if ptype in ["Amplitude", "Phase"]:
                            if row_idx == len(group_axes) - 1:
                                ax.set_xlabel("Frequenz [Hz]")
                            continue
                        ts_i = signal_list[row_idx]["timestamps_i"] if row_idx < len(signal_list) else None
                        formatter = _make_zeit_formatter(ts_i) if axis_mode == "Uhrzeit" else None
                        if formatter is not None:
                            ax.set_xlabel("Uhrzeit")
                            ax.xaxis.set_major_formatter(mticker.FuncFormatter(formatter))
                        else:
                            ax.set_xlabel("Zeit [s]")
                        plt.setp(ax.get_xticklabels(), visible=True)
            else:
                uhrzeit_verfuegbar = timestamps_full is not None and len(timestamps_full) > 0
                zeit_formatter = (
                    _make_zeit_formatter(timestamps_full)
                    if (axis_mode == "Uhrzeit" and uhrzeit_verfuegbar) else None
                )

                for ptype in plot_types:
                    group_axes = axes_dict[ptype]
                    for ax in group_axes[:-1]:
                        plt.setp(ax.get_xticklabels(), visible=False)

                    last_ax = group_axes[-1]
                    if ptype in ["Amplitude", "Phase"]:
                        last_ax.set_xlabel("Frequenz [Hz]")
                    elif zeit_formatter is not None:
                        last_ax.set_xlabel("Uhrzeit")
                        last_ax.xaxis.set_major_formatter(mticker.FuncFormatter(zeit_formatter))
                    else:
                        last_ax.set_xlabel("Zeit [s]")

            toolbar_row = ttk.Frame(frame)
            toolbar_row.pack(side="top", fill="x", padx=5, pady=5)

            toolbar_panel = ttk.Frame(toolbar_row, style="LegendBox.TFrame")
            Cfg.Styles.force_apply(toolbar_panel, "LegendBox.TFrame")
            toolbar_panel.pack(side="left")

            # Zeitachse gehört mit ins violett umrahmte, graue Panel (zusammen
            # mit den 4 Buttons) - Synchron/Cursor stehen bewusst AUSSERHALB,
            # daneben (siehe extra_frame unten).
            zeitachse_frame = ttk.Frame(toolbar_panel, style="Panel.TFrame")
            Cfg.Styles.force_apply(zeitachse_frame, "Panel.TFrame")

            ttk.Label(zeitachse_frame, text="Zeitachse:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
            axis_mode_var = tk.StringVar(value=axis_mode)
            axis_mode_combo = ttk.Combobox(
                zeitachse_frame, textvariable=axis_mode_var,
                values=["Relative Zeit (s)", "Uhrzeit"],
                state="normal",
                width=16
            )
            axis_mode_combo.pack(side="left", padx=5)

            def _on_axis_mode_changed(event=None):
                frame._axis_mode = axis_mode_var.get()
                logger.info("[DEBUG-ZEITACHSE] Combobox-Auswahl geaendert auf: %r", frame._axis_mode)
                _render()

            axis_mode_combo.bind("<<ComboboxSelected>>", _on_axis_mode_changed)

            extra_frame = ttk.Frame(toolbar_row, style="LegendBox.TFrame")
            Cfg.Styles.force_apply(extra_frame, "LegendBox.TFrame")
            extra_frame.pack(side="left", padx=(20, 5), pady=5)

            sync_row = ttk.Frame(extra_frame, style="Panel.TFrame")
            Cfg.Styles.force_apply(sync_row, "Panel.TFrame")
            sync_row.pack(side="top", anchor="w", padx=5, pady=(5, 2))
            ttk.Label(sync_row, text="Synchron:", font=("Arial", 10, "bold")).pack(side="left", padx=5)

            sync_enabled = {}
            # Bei nur einem Signal/einer Gruppe hat jede Operationstyp-Gruppe
            # (Original/Gefiltert/AVG/...) nur eine einzige Achse - dort kann man
            # nicht "mehrere Achsen desselben Typs" synchronisieren. Stattdessen
            # wird in diesem Fall EINE Gruppe mit allen Operationen des einen
            # Signals gebildet, damit "Alle" trotzdem etwas zum Synchronisieren hat.
            single_signal_multi_op = (n_signals == 1 and len(plot_types) > 1)
            sync_groups = {"Alle Operationen": list(all_axes)} if single_signal_multi_op else axes_dict
            multi_signal_sync = any(len(axes_dict[ptype]) > 1 for ptype in plot_types)
            show_all_sync = multi_signal_sync or single_signal_multi_op
            # Eigene Typ-Checkboxen (z.B. "Original") nur bei einer echten Mischung
            # mehrerer Typen (z.B. Original + Gefiltert) anzeigen - ist nur ein
            # einziger Typ vorhanden, waere die Typ-Checkbox nur ein redundantes
            # Duplikat von "Alle" (beide wuerden exakt dasselbe synchronisieren).
            show_type_checkboxes = (not single_signal_multi_op) and len(plot_types) > 1
            if show_all_sync:
                all_sync_var = tk.BooleanVar(value=True)

                def _set_all_sync():
                    for var in sync_enabled.values():
                        var.set(all_sync_var.get())

                all_cb = ttk.Checkbutton(sync_row, text="Alle", variable=all_sync_var, command=_set_all_sync)
                all_cb.pack(side="left", padx=5)
            if single_signal_multi_op:
                sync_enabled["Alle Operationen"] = all_sync_var
            elif show_type_checkboxes:
                for ptype in plot_types:
                    if len(axes_dict[ptype]) > 1:
                        var = tk.BooleanVar(value=True)
                        sync_enabled[ptype] = var
                        cb = ttk.Checkbutton(sync_row, text=ptype, variable=var)
                        cb.pack(side="left", padx=5)
            else:
                # Nur ein Typ vorhanden: "Alle" deckt genau diesen einen Typ ab,
                # sync_enabled trotzdem befuellen, damit die Sync-Logik in
                # PlotManager.add_cursor_and_zoom_logic() den Typ per "Alle" findet.
                for ptype in plot_types:
                    if len(axes_dict[ptype]) > 1:
                        sync_enabled[ptype] = all_sync_var

            cursor_row = ttk.Frame(extra_frame, style="Panel.TFrame")
            Cfg.Styles.force_apply(cursor_row, "Panel.TFrame")
            cursor_row.pack(side="top", anchor="w", padx=5, pady=(2, 5))
            ttk.Label(cursor_row, text="Cursor:", font=("Arial", 10, "bold")).pack(side="left", padx=5)

            cursor_single_var = tk.BooleanVar(value=True)
            cursor_multi_var  = tk.BooleanVar(value=False)

            def _on_cursor_single_toggle():
                if cursor_single_var.get():
                    cursor_multi_var.set(False)
                else:
                    cursor_single_var.set(True)

            def _on_cursor_multi_toggle():
                if cursor_multi_var.get():
                    cursor_single_var.set(False)
                else:
                    cursor_multi_var.set(True)

            ttk.Checkbutton(
                cursor_row, text="Einer", variable=cursor_single_var,
                command=_on_cursor_single_toggle
            ).pack(side="left", padx=5)
            ttk.Checkbutton(
                cursor_row, text="Mehrere", variable=cursor_multi_var,
                command=_on_cursor_multi_toggle
            ).pack(side="left", padx=5)

            bedienung_frame = ttk.Frame(toolbar_row, style="LegendBox.TFrame")
            Cfg.Styles.force_apply(bedienung_frame, "LegendBox.TFrame")
            bedienung_frame.pack(side="left", padx=(10, 5), pady=5)

            bedienung_inner = ttk.Frame(bedienung_frame, style="Panel.TFrame")
            Cfg.Styles.force_apply(bedienung_inner, "Panel.TFrame")
            bedienung_inner.pack(padx=5, pady=5)

            ttk.Label(
                bedienung_inner, text="Plot-Bedienung", font=("Arial", 10, "bold"),
                style="Panel.TLabel"
            ).pack(side="top", anchor="w")
            ttk.Label(bedienung_inner, text="Linksklick: Zoom", style="Panel.TLabel").pack(side="top", anchor="w")
            ttk.Label(
                bedienung_inner, text="Rechtsklick halten: Verschieben", style="Panel.TLabel"
            ).pack(side="top", anchor="w")

            def _is_time_axis(ax):
                return ax in time_axes

            def _push_range_history(new_range):
                del frame._range_history[frame._range_history_index + 1:]
                frame._range_history.append(new_range)
                frame._range_history_index = len(frame._range_history) - 1

            def _on_cursor_range_selected(x0, x1, ax):
                prev = getattr(frame, "_cursor_range", None)
                new_range = (x0, x1)
                if prev == new_range:
                    return
                frame._cursor_range = new_range
                _push_range_history(new_range)
                _render()

            def _on_cursor_range_cleared():
                if getattr(frame, "_cursor_range", None) is None:
                    return
                frame._cursor_range = None
                _push_range_history(None)
                _render()

            def _history_back():
                fig = getattr(frame, "_current_fig", None)
                if fig is not None and getattr(fig, "_history_can_go_back", lambda: False)():
                    fig._history_back()
                    return
                if frame._range_history_index > 0:
                    frame._range_history_index -= 1
                    frame._cursor_range = frame._range_history[frame._range_history_index]
                    _render()

            def _history_forward():
                fig = getattr(frame, "_current_fig", None)
                if fig is not None and getattr(fig, "_history_can_go_forward", lambda: False)():
                    fig._history_forward()
                    return
                if frame._range_history_index < len(frame._range_history) - 1:
                    frame._range_history_index += 1
                    frame._cursor_range = frame._range_history[frame._range_history_index]
                    _render()

            PlotManager.add_cursor_and_zoom_logic(
                fig,
                all_axes,
                signal_data,
                sync_groups,
                sync_enabled,
                range_selected_callback=_on_cursor_range_selected,
                range_cleared_callback=_on_cursor_range_cleared,
                selection_filter=_is_time_axis,
                multi_cursor_var=cursor_multi_var,
            )
            frame._current_fig = fig

            reset_frame = ttk.Frame(toolbar_panel, style="Panel.TFrame")
            Cfg.Styles.force_apply(reset_frame, "Panel.TFrame")
            reset_frame.pack(side="top", padx=5, pady=(5, 2))

            def _reset_zoom_selection():
                if hasattr(fig, "_reset_zoom_selection"):
                    fig._reset_zoom_selection()

            ttk.Button(reset_frame, text="Zurücksetzen", command=_reset_zoom_selection).pack(side="left", padx=5)

            nav_frame = ttk.Frame(reset_frame, style="Panel.TFrame")
            Cfg.Styles.force_apply(nav_frame, "Panel.TFrame")
            nav_frame.pack(side="left", padx=5)

            ttk.Button(nav_frame, text="◀", width=3, command=_history_back).pack(side="left", padx=(2, 1), pady=2)
            ttk.Button(nav_frame, text="▶", width=3, command=_history_forward).pack(side="left", padx=(1, 2), pady=2)

            def _export():
                AnalysePlotter._export_figure_as_png(
                    fig, frame.winfo_toplevel(), default_name=f"{analyse_typ}_Plot"
                )

            ttk.Button(reset_frame, text="Export", command=_export).pack(side="left", padx=5)

            zeitachse_frame.pack(side="top", padx=5, pady=(2, 5))

            fig.tight_layout()
            # Rand links/rechts reservieren, damit Legende (rechts, ausserhalb)
            # und Gruppen-Cursorboxen (links, ausserhalb) nicht abgeschnitten werden.
            fig.subplots_adjust(left=0.16, right=0.8)

            fig_height_px = int(fig.get_figheight() * fig.get_dpi())
            fig_width_px = int(fig.get_figwidth() * fig.get_dpi())

            scroll_container = ttk.Frame(frame)
            scroll_container.pack(side="top", fill="both", expand=True)

            v_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical")
            v_scrollbar.pack(side="right", fill="y")

            h_scrollbar = ttk.Scrollbar(scroll_container, orient="horizontal")
            h_scrollbar.pack(side="bottom", fill="x")

            scroll_canvas = tk.Canvas(scroll_container,
                                       yscrollcommand=v_scrollbar.set,
                                       xscrollcommand=h_scrollbar.set)
            scroll_canvas.pack(side="left", fill="both", expand=True)

            v_scrollbar.configure(command=scroll_canvas.yview)
            h_scrollbar.configure(command=scroll_canvas.xview)

            inner_frame = ttk.Frame(scroll_canvas)
            scroll_canvas.create_window((0, 0), window=inner_frame, anchor="nw")

            canvas = FigureCanvasTkAgg(fig, master=inner_frame)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.configure(height=fig_height_px, width=fig_width_px)
            canvas_widget.pack(fill="none", expand=False)

            def _on_configure(event):
                scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            inner_frame.bind("<Configure>", _on_configure)

            def _on_figure_scroll(event):
                # Über einer Achse macht PlotManager mit dem Mausrad Zoom (siehe
                # add_cursor_and_zoom_logic) - das bleibt unangetastet. Nur wenn
                # der Rand daneben liegt (event.inaxes ist dann None - z.B. über
                # den Cursorboxen links oder der Legende rechts), scrollt das
                # Mausrad stattdessen das Plot-Fenster hoch/runter, damit man
                # nicht immer die Scrollbar manuell ziehen muss.
                if event.inaxes is not None:
                    return
                direction = -1 if event.button == "up" else 1
                scroll_canvas.yview_scroll(direction * 3, "units")

            fig.canvas.mpl_connect("scroll_event", _on_figure_scroll)

            def _on_blank_area_scroll(event):
                # Der weisse Bereich neben der eingebetteten Figur (die hat eine
                # feste Pixelgroesse) gehoert nicht mehr zu matplotlib, sondern
                # ist einfach der Hintergrund von scroll_canvas selbst - dahin
                # kommt _on_figure_scroll oben nie. Deshalb hier zusaetzlich ein
                # normaler Tkinter-Mausrad-Handler direkt auf scroll_canvas.
                direction = -1 if event.delta > 0 else 1
                scroll_canvas.yview_scroll(direction * 3, "units")

            scroll_canvas.bind("<MouseWheel>", _on_blank_area_scroll)


        _render()

    @staticmethod
    def create_group_analysis_tab(frame, analyse_typ, grouped_headers, signals, units, t, dt,
                                  header_to_signal_idx, use_filtered, filter_manager,
                                  start_zeit=None, ende_zeit=None, timestamps=None, window_type=None):
        """Erstellt einen Analyse-Plot: pro Gruppe ein Subplot mit allen Signalen (keine Aggregation)."""
        t_full = t
        timestamps_full = timestamps
        if not hasattr(frame, "_cursor_range"):
            frame._cursor_range = None
        if not hasattr(frame, "_range_history"):
            # Historie der Zeitbereichs-Zooms (Bereichsauswahl) - überlebt den
            # kompletten Neuaufbau von frame in _render(), im Gegensatz zur
            # feineren Scroll/Pan-Historie, die pro Figure in plot_manager.py lebt.
            frame._range_history       = [None]
            frame._range_history_index = 0

        def _get_effective_range():
            cursor_range = getattr(frame, "_cursor_range", None)
            if cursor_range:
                return cursor_range[0], cursor_range[1], True
            if start_zeit is not None and ende_zeit is not None:
                return start_zeit, ende_zeit, False
            return None, None, False

        def _render():
            for child in frame.winfo_children():
                child.destroy()

            start_eff, end_eff, strict_range = _get_effective_range()
            xlim_start = None
            xlim_end = None
            mask_start = None
            mask_end = None

            if start_eff is not None and end_eff is not None:
                if strict_range:
                    mask_start, mask_end = start_eff, end_eff
                    xlim_start, xlim_end = PlotManager._apply_axis_margin(start_eff, end_eff, margin_percent=5)
                else:
                    margin_start, margin_end = PlotManager._apply_axis_margin(start_eff, end_eff, margin_percent=5)
                    xlim_start, xlim_end = margin_start, margin_end
                    mask_start, mask_end = margin_start, margin_end

            sns.set_theme(style="whitegrid")
            sns.set_context("notebook")
            sns.set_palette("husl")
            plt.rcParams.update(Cfg.PlotStyle.MPL_RCPARAMS)  # sns.set_theme() setzt figure.facecolor zurück auf Weiß

            cleaned_groups = []
            for group in grouped_headers or []:
                cleaned = []
                for header in group:
                    idx = header_to_signal_idx.get(header)
                    if idx is None or idx >= len(signals):
                        continue
                    cleaned.append(header)
                if cleaned:
                    cleaned_groups.append(cleaned)

            # Referenz-Zeitstempel pro Gruppe (fuer die "Uhrzeit"-Achse im Pool-Modus):
            # das erste Signal jeder Gruppe bestimmt den Startzeitpunkt der Zeile -
            # bei Gruppen mit Signalen aus mehreren Dateien ist das ein Kompromiss,
            # da eine gemeinsame Achse nicht mehrere Startzeiten gleichzeitig zeigen kann.
            group_timestamps_ref = []
            for group in cleaned_groups:
                idx0 = header_to_signal_idx.get(group[0])
                group_timestamps_ref.append(
                    PlotManager.t_for_idx(timestamps_full, idx0) if idx0 is not None else None
                )

            n_groups = len(cleaned_groups)
            if n_groups == 0:
                fig = plt.Figure(figsize=(14, 8))
                ax = fig.add_subplot(111)
                ax.text(0.5, 0.5, "Keine gueltigen Gruppen ausgewaehlt", ha="center", va="center")
                canvas = FigureCanvasTkAgg(fig, master=frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
                return

            is_filtered = (use_filtered and filter_manager and
                           filter_manager.filter_type != "Kein Filter")

            if is_filtered:
                filter_info = filter_manager.get_filter_info()
                filter_str = f" (Gefiltert: {filter_info['type']}, {filter_info['order']}, {filter_info['characteristic']})"
            else:
                filter_str = ""

            # Flache, eindeutige Signal-Liste ueber alle Gruppen hinweg (fuer den
            # Export-Button - unabhaengig von der Gruppen/ptype-Darstellung unten).
            export_entries = []
            seen_export_headers = set()
            for group in cleaned_groups:
                for header in group:
                    if header in seen_export_headers:
                        continue
                    seen_export_headers.add(header)
                    idx = header_to_signal_idx.get(header)
                    if idx is None or idx >= len(signals):
                        continue
                    t_full_i = PlotManager.t_for_idx(t_full, idx)
                    original_i = signals[idx]
                    if mask_start is not None and mask_end is not None:
                        maske_i = (t_full_i >= mask_start) & (t_full_i <= mask_end)
                        if not np.any(maske_i):
                            continue
                        t_local_i = t_full_i[maske_i]
                        original_i = original_i[maske_i]
                    else:
                        t_local_i = t_full_i
                    unit_i = units[idx] if idx < len(units) else ""
                    filtered_i = filter_manager.apply_filter(original_i) if is_filtered else original_i
                    export_entries.append({
                        "header": header, "original": original_i, "filtered": filtered_i,
                        "unit": unit_i, "t_local": t_local_i,
                    })

            if analyse_typ == "Signal":
                plot_types = ["Original", "Gefiltert"] if is_filtered else ["Original"]
            elif analyse_typ in ["AVG", "RMS"]:
                plot_types = ["Original", "Gefiltert", analyse_typ] if is_filtered else ["Original", analyse_typ]
            elif analyse_typ == "Differential":
                plot_types = ["Original", "Gefiltert", "Ableitung"] if is_filtered else ["Original", "Ableitung"]
            elif analyse_typ == "Integral":
                plot_types = ["Original", "Gefiltert", "Integral"] if is_filtered else ["Original", "Integral"]
            elif analyse_typ == "FFT":
                plot_types = ["Original", "Gefiltert", "Amplitude", "Phase"] if is_filtered else ["Original", "Amplitude", "Phase"]
            elif analyse_typ == "Statistik":
                plot_types = ["Original", "Gefiltert", "Statistik"] if is_filtered else ["Original", "Statistik"]
            else:
                plot_types = ["Original"]

            total_subplots = n_groups * len(plot_types)
            fig_height = max(3, total_subplots * 3.8)
            fig = plt.Figure(figsize=(14, fig_height))
            # Schon hier berechnet (statt erst kurz vor dem canvas_widget.configure()
            # weiter unten), damit _show_cursor_panel() (siehe unten) die reale
            # Plot-Breite kennt, auch falls sie durch einen wiederhergestellten
            # Cursor-Zustand schon waehrend add_cursor_and_zoom_logic() aufgerufen wird.
            fig_height_px = int(fig.get_figheight() * fig.get_dpi())
            fig_width_px  = int(fig.get_figwidth() * fig.get_dpi())

            axes_dict = PlotManager._setup_subplot_grid(fig, n_groups, plot_types)

            all_axes = []
            signal_data = {}
            time_axes = set()

            for ptype in plot_types:
                for group_idx, group_headers in enumerate(cleaned_groups):
                    ax = axes_dict[ptype][group_idx]
                    all_axes.append(ax)

                    group_signals = []
                    unit_set = set()

                    for header in group_headers:
                        idx = header_to_signal_idx.get(header)
                        if idx is None or idx >= len(signals):
                            continue

                        t_full_i = PlotManager.t_for_idx(t_full, idx)
                        original = signals[idx]

                        if mask_start is not None and mask_end is not None:
                            maske_i = (t_full_i >= mask_start) & (t_full_i <= mask_end)
                            if not np.any(maske_i):
                                continue
                            t_local_i = t_full_i[maske_i]
                            original = original[maske_i]
                        else:
                            t_local_i = t_full_i

                        unit = units[idx] if idx < len(units) else ""
                        unit_set.add(unit)

                        if is_filtered:
                            filtered = filter_manager.apply_filter(original)
                        else:
                            filtered = original

                        group_signals.append({
                            "header": header,
                            "original": original,
                            "filtered": filtered,
                            "unit": unit,
                            "t_local": t_local_i,
                        })

                    if not group_signals:
                        continue

                    unit_display = unit_set.pop() if len(unit_set) == 1 else "Einheiten: gemischt"

                    if ptype == "Original":
                        for sig in group_signals:
                            sns.lineplot(x=sig["t_local"], y=sig["original"], ax=ax, linewidth=1.5, label=sig["header"])
                            signal_data.setdefault(ax, []).append((sig["t_local"], sig["original"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude", legend_below=True)

                    elif ptype == "Gefiltert":
                        for sig in group_signals:
                            sns.lineplot(x=sig["t_local"], y=sig["filtered"], ax=ax, linewidth=1.5, label=sig["header"])
                            signal_data.setdefault(ax, []).append((sig["t_local"], sig["filtered"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude", legend_below=True)

                    elif ptype == "AVG":
                        for sig in group_signals:
                            avg_value = float(np.nanmean(sig["filtered"]))
                            sns.lineplot(x=sig["t_local"], y=sig["filtered"], ax=ax, linewidth=1.2, label=sig["header"])
                            ax.axhline(avg_value, linestyle="--", linewidth=1,
                                       label=f"{sig['header']} AVG={avg_value:.4g} {sig['unit']}")
                            signal_data.setdefault(ax, []).append((sig["t_local"], sig["filtered"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude", legend_below=True)

                    elif ptype == "RMS":
                        for sig in group_signals:
                            rms_value = float(np.sqrt(np.nanmean(sig["filtered"]**2)))
                            sns.lineplot(x=sig["t_local"], y=sig["filtered"], ax=ax, linewidth=1.2, label=sig["header"])
                            ax.axhline(rms_value, linestyle="--", linewidth=1,
                                       label=f"{sig['header']} RMS={rms_value:.4g} {sig['unit']}")
                            signal_data.setdefault(ax, []).append((sig["t_local"], sig["filtered"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude", legend_below=True)

                    elif ptype == "Ableitung":
                        for sig in group_signals:
                            diff = np.gradient(sig["filtered"], dt)
                            sns.lineplot(x=sig["t_local"], y=diff, ax=ax, linewidth=1.2, label=sig["header"])
                            signal_data.setdefault(ax, []).append((sig["t_local"], diff, sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        unit_diff = f"{unit_display}/s" if unit_display != "Einheiten: gemischt" else "Einheiten: gemischt"
                        PlotManager._configure_ax(ax, f"Ableitung [{unit_diff}]", show_legend=True, legend_below=True)

                    elif ptype == "Integral":
                        for sig in group_signals:
                            integral = np.cumsum(sig["filtered"]) * dt
                            sns.lineplot(x=sig["t_local"], y=integral, ax=ax, linewidth=1.2, label=sig["header"])
                            signal_data.setdefault(ax, []).append((sig["t_local"], integral, sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        unit_int = f"{unit_display}*s" if unit_display != "Einheiten: gemischt" else "Einheiten: gemischt"
                        PlotManager._configure_ax(ax, f"Integral [{unit_int}]", show_legend=True, legend_below=True)

                    elif ptype == "Amplitude":
                        for sig in group_signals:
                            freq, fft_amp, _ = AnalysePlotter._fft_amplitude(sig["filtered"], dt, window_type)
                            sns.lineplot(x=freq, y=fft_amp, ax=ax, linewidth=1.2, label=sig["header"])
                            signal_data.setdefault(ax, []).append((freq, fft_amp, sig["header"]))
                        PlotManager._configure_ax(ax, "Amplitude", show_legend=True, legend_below=True)

                    elif ptype == "Phase":
                        for sig in group_signals:
                            freq, _, fft_complex = AnalysePlotter._fft_amplitude(sig["filtered"], dt, window_type)
                            fft_phase = np.angle(fft_complex, deg=True)
                            sns.lineplot(x=freq, y=fft_phase, ax=ax, linewidth=1.2, label=sig["header"])
                            signal_data.setdefault(ax, []).append((freq, fft_phase, sig["header"]))
                        PlotManager._configure_ax(ax, "Phase [Grad]", show_legend=True, legend_below=True)

                    elif ptype == "Statistik":
                        for sig in group_signals:
                            mean_val = np.mean(sig["filtered"])
                            std_val = np.std(sig["filtered"])
                            sns.lineplot(x=sig["t_local"], y=sig["filtered"], ax=ax, linewidth=1.2, label=sig["header"])
                            ax.axhline(y=mean_val, linestyle="--", linewidth=1,
                                       label=f"{sig['header']} Mean={mean_val:.4g}, Std={std_val:.4g}")
                            signal_data.setdefault(ax, []).append((sig["t_local"], sig["filtered"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude", legend_below=True)

                    unit_suffix = f" [{unit_display}]"
                    if ptype == "Ableitung":
                        unit_suffix = f" [{unit_diff}]"
                    elif ptype == "Integral":
                        unit_suffix = f" [{unit_int}]"
                    elif ptype == "Phase":
                        unit_suffix = " [Grad]"
                    title_filter_suffix = filter_str if ptype == "Gefiltert" else ""
                    # pad deutlich groesser als der Matplotlib-Standard (6pt): die
                    # nummerierten Cursor-Kreise (siehe PlotManager._set_pinned_cursor)
                    # sitzen knapp oberhalb des Achsenrands (xy=(x, 1.0), xytext=(0,4))
                    # und schneiden sonst in den Titeltext.
                    ax.set_title(f"Gruppe {group_idx + 1} - {ptype}{title_filter_suffix}{unit_suffix}", pad=22)

            axis_mode = getattr(frame, "_axis_mode", "Relative Zeit (s)")
            is_pool   = isinstance(t_full, (list, tuple))

            def _make_zeit_formatter(ts_array):
                if ts_array is None or len(ts_array) == 0:
                    return None
                start_ts = pd.Timestamp(ts_array[0])

                def _fmt(x, pos=None):
                    try:
                        return (start_ts + pd.Timedelta(seconds=float(x))).strftime("%H:%M:%S")
                    except Exception:
                        return ""
                return _fmt

            if is_pool:
                # Signal-Pool: jede Gruppe/Zeile bekommt ihre eigene Uhrzeit-
                # Formatierung (Referenz: erstes Signal der Gruppe, siehe
                # group_timestamps_ref) und zeigt ihre eigene Tick-Beschriftung.
                for ptype in plot_types:
                    group_axes = axes_dict[ptype]
                    for row_idx, ax in enumerate(group_axes):
                        if ptype in ["Amplitude", "Phase"]:
                            if row_idx == len(group_axes) - 1:
                                ax.set_xlabel("Frequenz [Hz]")
                            continue
                        ts_i = group_timestamps_ref[row_idx] if row_idx < len(group_timestamps_ref) else None
                        formatter = _make_zeit_formatter(ts_i) if axis_mode == "Uhrzeit" else None
                        if formatter is not None:
                            ax.set_xlabel("Uhrzeit")
                            ax.xaxis.set_major_formatter(mticker.FuncFormatter(formatter))
                        else:
                            ax.set_xlabel("Zeit [s]")
                        plt.setp(ax.get_xticklabels(), visible=True)
            else:
                uhrzeit_verfuegbar = timestamps_full is not None and len(timestamps_full) > 0
                zeit_formatter = (
                    _make_zeit_formatter(timestamps_full)
                    if (axis_mode == "Uhrzeit" and uhrzeit_verfuegbar) else None
                )

                for ptype in plot_types:
                    group_axes = axes_dict[ptype]
                    for ax in group_axes[:-1]:
                        plt.setp(ax.get_xticklabels(), visible=False)

                    last_ax = group_axes[-1]
                    if ptype in ["Amplitude", "Phase"]:
                        last_ax.set_xlabel("Frequenz [Hz]")
                    elif zeit_formatter is not None:
                        last_ax.set_xlabel("Uhrzeit")
                        last_ax.xaxis.set_major_formatter(mticker.FuncFormatter(zeit_formatter))
                    else:
                        last_ax.set_xlabel("Zeit [s]")

            toolbar_row = ttk.Frame(frame)
            toolbar_row.pack(side="top", fill="x", padx=5, pady=5)

            toolbar_panel = ttk.Frame(toolbar_row, style="LegendBox.TFrame")
            Cfg.Styles.force_apply(toolbar_panel, "LegendBox.TFrame")
            toolbar_panel.pack(side="left")

            # Zeitachse gehört mit ins violett umrahmte, graue Panel (zusammen
            # mit den 4 Buttons) - Synchron/Cursor stehen bewusst AUSSERHALB,
            # daneben (siehe extra_frame unten).
            zeitachse_frame = ttk.Frame(toolbar_panel, style="Panel.TFrame")
            Cfg.Styles.force_apply(zeitachse_frame, "Panel.TFrame")

            ttk.Label(zeitachse_frame, text="Zeitachse:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
            axis_mode_var = tk.StringVar(value=axis_mode)
            axis_mode_combo = ttk.Combobox(
                zeitachse_frame, textvariable=axis_mode_var,
                values=["Relative Zeit (s)", "Uhrzeit"],
                state="normal",
                width=16
            )
            axis_mode_combo.pack(side="left", padx=5)

            def _on_axis_mode_changed(event=None):
                frame._axis_mode = axis_mode_var.get()
                logger.info("[DEBUG-ZEITACHSE] Combobox-Auswahl geaendert auf: %r", frame._axis_mode)
                _render()

            axis_mode_combo.bind("<<ComboboxSelected>>", _on_axis_mode_changed)

            extra_frame = ttk.Frame(toolbar_row, style="LegendBox.TFrame")
            Cfg.Styles.force_apply(extra_frame, "LegendBox.TFrame")
            extra_frame.pack(side="left", padx=(20, 5), pady=5)

            sync_row = ttk.Frame(extra_frame, style="Panel.TFrame")
            Cfg.Styles.force_apply(sync_row, "Panel.TFrame")
            sync_row.pack(side="top", anchor="w", padx=5, pady=(5, 2))
            ttk.Label(sync_row, text="Synchron:", font=("Arial", 10, "bold")).pack(side="left", padx=5)

            sync_enabled = {}
            # Bei nur einem Signal/einer Gruppe hat jede Operationstyp-Gruppe
            # (Original/Gefiltert/AVG/...) nur eine einzige Achse - dort kann man
            # nicht "mehrere Achsen desselben Typs" synchronisieren. Stattdessen
            # wird in diesem Fall EINE Gruppe mit allen Operationen der einen
            # Signalgruppe gebildet, damit "Alle" trotzdem etwas zum Synchronisieren hat.
            single_signal_multi_op = (n_groups == 1 and len(plot_types) > 1)
            sync_groups = {"Alle Operationen": list(all_axes)} if single_signal_multi_op else axes_dict
            multi_signal_sync = any(len(axes_dict[ptype]) > 1 for ptype in plot_types)
            show_all_sync = multi_signal_sync or single_signal_multi_op
            # Eigene Typ-Checkboxen (z.B. "Original") nur bei einer echten Mischung
            # mehrerer Typen (z.B. Original + Gefiltert) anzeigen - ist nur ein
            # einziger Typ vorhanden, waere die Typ-Checkbox nur ein redundantes
            # Duplikat von "Alle" (beide wuerden exakt dasselbe synchronisieren).
            show_type_checkboxes = (not single_signal_multi_op) and len(plot_types) > 1
            if show_all_sync:
                all_sync_var = tk.BooleanVar(value=True)

                def _set_all_sync():
                    for var in sync_enabled.values():
                        var.set(all_sync_var.get())

                all_cb = ttk.Checkbutton(sync_row, text="Alle", variable=all_sync_var, command=_set_all_sync)
                all_cb.pack(side="left", padx=5)
            if single_signal_multi_op:
                sync_enabled["Alle Operationen"] = all_sync_var
            elif show_type_checkboxes:
                for ptype in plot_types:
                    if len(axes_dict[ptype]) > 1:
                        var = tk.BooleanVar(value=True)
                        sync_enabled[ptype] = var
                        cb = ttk.Checkbutton(sync_row, text=ptype, variable=var)
                        cb.pack(side="left", padx=5)
            else:
                # Nur ein Typ vorhanden: "Alle" deckt genau diesen einen Typ ab,
                # sync_enabled trotzdem befuellen, damit die Sync-Logik in
                # PlotManager.add_cursor_and_zoom_logic() den Typ per "Alle" findet.
                for ptype in plot_types:
                    if len(axes_dict[ptype]) > 1:
                        sync_enabled[ptype] = all_sync_var

            cursor_row = ttk.Frame(extra_frame, style="Panel.TFrame")
            Cfg.Styles.force_apply(cursor_row, "Panel.TFrame")
            cursor_row.pack(side="top", anchor="w", padx=5, pady=(2, 5))
            ttk.Label(cursor_row, text="Cursor:", font=("Arial", 10, "bold")).pack(side="left", padx=5)

            cursor_single_var = tk.BooleanVar(value=True)
            cursor_multi_var  = tk.BooleanVar(value=False)

            def _on_cursor_single_toggle():
                if cursor_single_var.get():
                    cursor_multi_var.set(False)
                else:
                    cursor_single_var.set(True)

            def _on_cursor_multi_toggle():
                if cursor_multi_var.get():
                    cursor_single_var.set(False)
                else:
                    cursor_multi_var.set(True)

            ttk.Checkbutton(
                cursor_row, text="Einer", variable=cursor_single_var,
                command=_on_cursor_single_toggle
            ).pack(side="left", padx=5)
            ttk.Checkbutton(
                cursor_row, text="Mehrere", variable=cursor_multi_var,
                command=_on_cursor_multi_toggle
            ).pack(side="left", padx=5)

            bedienung_frame = ttk.Frame(toolbar_row, style="LegendBox.TFrame")
            Cfg.Styles.force_apply(bedienung_frame, "LegendBox.TFrame")
            bedienung_frame.pack(side="left", padx=(10, 5), pady=5)

            bedienung_inner = ttk.Frame(bedienung_frame, style="Panel.TFrame")
            Cfg.Styles.force_apply(bedienung_inner, "Panel.TFrame")
            bedienung_inner.pack(padx=5, pady=5)

            ttk.Label(
                bedienung_inner, text="Plot-Bedienung", font=("Arial", 10, "bold"),
                style="Panel.TLabel"
            ).pack(side="top", anchor="w")
            ttk.Label(bedienung_inner, text="Linksklick: Zoom", style="Panel.TLabel").pack(side="top", anchor="w")
            ttk.Label(
                bedienung_inner, text="Rechtsklick halten: Verschieben", style="Panel.TLabel"
            ).pack(side="top", anchor="w")

            def _is_time_axis(ax):
                return ax in time_axes

            def _push_range_history(new_range):
                del frame._range_history[frame._range_history_index + 1:]
                frame._range_history.append(new_range)
                frame._range_history_index = len(frame._range_history) - 1

            def _on_cursor_range_selected(x0, x1, ax):
                prev = getattr(frame, "_cursor_range", None)
                new_range = (x0, x1)
                if prev == new_range:
                    return
                frame._cursor_range = new_range
                _push_range_history(new_range)
                _render()

            def _on_cursor_range_cleared():
                if getattr(frame, "_cursor_range", None) is None:
                    return
                frame._cursor_range = None
                _push_range_history(None)
                _render()

            def _history_back():
                fig = getattr(frame, "_current_fig", None)
                if fig is not None and getattr(fig, "_history_can_go_back", lambda: False)():
                    fig._history_back()
                    return
                if frame._range_history_index > 0:
                    frame._range_history_index -= 1
                    frame._cursor_range = frame._range_history[frame._range_history_index]
                    _render()

            def _history_forward():
                fig = getattr(frame, "_current_fig", None)
                if fig is not None and getattr(fig, "_history_can_go_forward", lambda: False)():
                    fig._history_forward()
                    return
                if frame._range_history_index < len(frame._range_history) - 1:
                    frame._range_history_index += 1
                    frame._cursor_range = frame._range_history[frame._range_history_index]
                    _render()

            # Eigener, unabhängig scrollbarer Bereich für die Wertetabellen
            # gepinnter Cursor ("Mehrere"-Modus) - als Tkinter-Karten statt als
            # matplotlib-Annotation im Plot, damit auch Gruppen mit vielen
            # Signalen (hohe Tabellen) nicht von benachbarten Subplots verdeckt
            # werden. content_row ist ein PanedWindow mit Plot (links) und
            # diesem Panel (rechts) - der Sash dazwischen lässt sich mit der
            # Maus ziehen, um das Panel breiter/schmaler zu machen.
            # scroll_container wird schon hier angelegt (leer) und weiter unten
            # mit Scrollbars/Canvas befüllt, damit die Reihenfolge im
            # PanedWindow (Plot links, Panel rechts) stimmt.
            content_row = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
            content_row.pack(side="top", fill="both", expand=True)

            scroll_container = ttk.Frame(content_row)
            content_row.add(scroll_container, weight=3)

            cursor_panel_outer = ttk.Frame(content_row, style="Panel.TFrame")
            Cfg.Styles.force_apply(cursor_panel_outer, "Panel.TFrame")
            # Bleibt technisch immer im PanedWindow (add/forget bei ttk.PanedWindow
            # hat sich als unzuverlässig erwiesen - die Sash-Position danach neu
            # zu setzen, hat im echten Fenster nicht sichtbar gegriffen). Stattdessen
            # wird das Panel über die SASH-POSITION ein-/ausgeblendet: auf 0 Breite
            # geschoben (unsichtbar), bis der erste Cursor gesetzt wird.
            content_row.add(cursor_panel_outer, weight=1)

            def _hide_cursor_panel():
                try:
                    content_row.sashpos(0, content_row.winfo_width())
                except Exception:
                    pass

            def _show_cursor_panel():
                try:
                    total_width = content_row.winfo_width()
                    if total_width > 250:
                        panel_width = 220
                        # Sash direkt hinter dem tatsaechlichen Plot positionieren
                        # (fig_width_px + etwas Rand fuer die vertikale Scrollbar),
                        # NICHT proportional zur Fensterbreite - der Plot hat eine
                        # feste Pixelbreite (siehe canvas_widget.configure(width=...)
                        # weiter unten). Auf breiten Bildschirmen klaffte sonst eine
                        # grosse Luecke zwischen Plot-Ende und Cursor-Panel.
                        sash_pos = min(fig_width_px + 24, total_width - panel_width)
                        content_row.sashpos(0, max(sash_pos, 100))
                except Exception:
                    pass

            # _show_cursor_panel() setzt die Sash-Position (=Breite) fest -
            # das darf NUR beim allerersten Cursor passieren. Sonst würde jeder
            # weitere gesetzte Cursor die vom Nutzer per Hand gezogene Breite
            # wieder auf die Startgrösse zurücksetzen.
            _cursor_panel_state = {"visible": False}

            # Ein einmaliges after(200, ...) ist eine reine Race Condition:
            # bis das Layout tatsächlich seine echte Grösse hat, kann es je
            # nach Fensteraufbau (Tab noch nicht sichtbar, langsameres System,
            # ...) länger dauern - dann liefert winfo_width() beim Timer noch
            # den Platzhalterwert und das Panel bleibt sichtbar. Stattdessen
            # bei JEDEM Configure (Grössenänderung) von content_row erneut
            # ausblenden, solange noch kein Cursor gesetzt wurde - das greift
            # zuverlässig unabhängig davon, wann das echte Layout steht.
            def _on_content_row_configure(_event):
                if not _cursor_panel_state["visible"]:
                    _hide_cursor_panel()
            content_row.bind("<Configure>", _on_content_row_configure)

            def _on_cursor_panel_visibility(has_cards):
                if has_cards and not _cursor_panel_state["visible"]:
                    _show_cursor_panel()
                    _cursor_panel_state["visible"] = True
                elif not has_cards and _cursor_panel_state["visible"]:
                    _hide_cursor_panel()
                    _cursor_panel_state["visible"] = False

            cursor_panel_heading = ttk.Frame(cursor_panel_outer, style="LegendBox.TFrame")
            Cfg.Styles.force_apply(cursor_panel_heading, "LegendBox.TFrame")
            cursor_panel_heading.pack(side="top", anchor="w", padx=6, pady=(6, 2))

            ttk.Label(
                cursor_panel_heading, text="Gesetzte Cursor", font=("Arial", 10, "bold"),
                style="Panel.TLabel"
            ).pack(padx=8, pady=3)

            cursor_panel_scrollbar = ttk.Scrollbar(cursor_panel_outer, orient="vertical")
            cursor_panel_scrollbar.pack(side="right", fill="y")

            cursor_panel_h_scrollbar = ttk.Scrollbar(cursor_panel_outer, orient="horizontal")
            cursor_panel_h_scrollbar.pack(side="bottom", fill="x")

            cursor_panel_canvas = tk.Canvas(
                cursor_panel_outer, yscrollcommand=cursor_panel_scrollbar.set,
                xscrollcommand=cursor_panel_h_scrollbar.set,
                highlightthickness=0, bg=Cfg.Colors.PANEL_BG,
            )
            cursor_panel_canvas.pack(side="left", fill="both", expand=True)
            cursor_panel_scrollbar.configure(command=cursor_panel_canvas.yview)
            cursor_panel_h_scrollbar.configure(command=cursor_panel_canvas.xview)

            cursor_panel = ttk.Frame(cursor_panel_canvas, style="Panel.TFrame")
            Cfg.Styles.force_apply(cursor_panel, "Panel.TFrame")
            cursor_panel_canvas.create_window((0, 0), window=cursor_panel, anchor="nw")

            def _on_cursor_panel_configure(event):
                cursor_panel_canvas.configure(scrollregion=cursor_panel_canvas.bbox("all"))
            cursor_panel.bind("<Configure>", _on_cursor_panel_configure)

            def _on_cursor_panel_scroll(event):
                direction = -1 if event.delta > 0 else 1
                cursor_panel_canvas.yview_scroll(direction * 3, "units")
            cursor_panel_canvas.bind("<MouseWheel>", _on_cursor_panel_scroll)
            # Jede Karte (PlotManager._make_cursor_card) bindet das Mausrad
            # zusätzlich rekursiv auf sich selbst - sonst würde Scrollen nur im
            # Leerraum zwischen Karten funktionieren, nicht direkt über einer
            # Karte (Kind-Widgets bekommen das Canvas-Event sonst nicht).

            PlotManager.add_cursor_and_zoom_logic(
                fig,
                all_axes,
                signal_data,
                sync_groups,
                sync_enabled,
                range_selected_callback=_on_cursor_range_selected,
                range_cleared_callback=_on_cursor_range_cleared,
                selection_filter=_is_time_axis,
                multi_cursor_var=cursor_multi_var,
                cursor_panel=cursor_panel,
                on_cursor_panel_visibility=_on_cursor_panel_visibility,
            )
            frame._current_fig = fig

            reset_frame = ttk.Frame(toolbar_panel, style="Panel.TFrame")
            Cfg.Styles.force_apply(reset_frame, "Panel.TFrame")
            reset_frame.pack(side="top", padx=5, pady=(5, 2))

            def _reset_zoom_selection():
                if hasattr(fig, "_reset_zoom_selection"):
                    fig._reset_zoom_selection()

            ttk.Button(reset_frame, text="Zurücksetzen", command=_reset_zoom_selection).pack(side="left", padx=5)

            nav_frame = ttk.Frame(reset_frame, style="Panel.TFrame")
            Cfg.Styles.force_apply(nav_frame, "Panel.TFrame")
            nav_frame.pack(side="left", padx=5)

            ttk.Button(nav_frame, text="◀", width=3, command=_history_back).pack(side="left", padx=(2, 1), pady=2)
            ttk.Button(nav_frame, text="▶", width=3, command=_history_forward).pack(side="left", padx=(1, 2), pady=2)

            def _export():
                AnalysePlotter._export_figure_as_png(
                    fig, frame.winfo_toplevel(), default_name=f"{analyse_typ}_Plot"
                )

            ttk.Button(reset_frame, text="Export", command=_export).pack(side="left", padx=5)

            zeitachse_frame.pack(side="top", padx=5, pady=(2, 5))

            fig.tight_layout()
            # Rand links reservieren, damit die Gruppen-Cursorboxen (links,
            # ausserhalb, MULTI_ANN_X=-0.14 in plot_manager.py) nicht die
            # Y-Achsen-Beschriftung überlappen oder abgeschnitten werden -
            # deshalb deutlich mehr als früher (0.16 -> 0.24). bottom/hspace
            # für die Unter-dem-Plot-Legenden werden aus der TATSÄCHLICHEN
            # Figurhöhe zurückgerechnet (get_group_legend_margins) - eine
            # feste Bruchzahl reicht bei EINEM Subplot (Figur nur 3 Zoll hoch)
            # nicht, ist bei VIELEN Subplots aber unnötig knapp/verschwenderisch.
            _legend_bottom, _legend_hspace = PlotManager.get_group_legend_margins(fig)
            fig.subplots_adjust(left=0.24, right=0.8, hspace=_legend_hspace, bottom=_legend_bottom)

            # Erst JETZT (nach dem finalen Layout) die Unter-dem-Plot-Legenden
            # erzeugen - die Achsenposition (ax.get_position()) steht erst nach
            # subplots_adjust fest, und die Legende wird in Figur- statt
            # Achsen-Koordinaten platziert (siehe finalize_group_legends),
            # damit der Abstand zur X-Achsen-Beschriftung überall gleich groß
            # ist, egal wie hoch/niedrig der jeweilige Subplot ausfällt.
            PlotManager.finalize_group_legends(all_axes)

            v_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical")
            v_scrollbar.pack(side="right", fill="y")

            h_scrollbar = ttk.Scrollbar(scroll_container, orient="horizontal")
            h_scrollbar.pack(side="bottom", fill="x")

            scroll_canvas = tk.Canvas(scroll_container,
                                       yscrollcommand=v_scrollbar.set,
                                       xscrollcommand=h_scrollbar.set)
            scroll_canvas.pack(side="left", fill="both", expand=True)

            v_scrollbar.configure(command=scroll_canvas.yview)
            h_scrollbar.configure(command=scroll_canvas.xview)

            inner_frame = ttk.Frame(scroll_canvas)
            scroll_canvas.create_window((0, 0), window=inner_frame, anchor="nw")

            canvas = FigureCanvasTkAgg(fig, master=inner_frame)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.configure(height=fig_height_px, width=fig_width_px)
            canvas_widget.pack(fill="none", expand=False)

            def _on_configure(event):
                scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            inner_frame.bind("<Configure>", _on_configure)

            def _on_figure_scroll(event):
                # Über einer Achse macht PlotManager mit dem Mausrad Zoom (siehe
                # add_cursor_and_zoom_logic) - das bleibt unangetastet. Nur wenn
                # der Rand daneben liegt (event.inaxes ist dann None - z.B. über
                # den Cursorboxen links oder der Legende rechts), scrollt das
                # Mausrad stattdessen das Plot-Fenster hoch/runter, damit man
                # nicht immer die Scrollbar manuell ziehen muss.
                if event.inaxes is not None:
                    return
                direction = -1 if event.button == "up" else 1
                scroll_canvas.yview_scroll(direction * 3, "units")

            fig.canvas.mpl_connect("scroll_event", _on_figure_scroll)

            def _on_blank_area_scroll(event):
                # Der weisse Bereich neben der eingebetteten Figur (die hat eine
                # feste Pixelgroesse) gehoert nicht mehr zu matplotlib, sondern
                # ist einfach der Hintergrund von scroll_canvas selbst - dahin
                # kommt _on_figure_scroll oben nie. Deshalb hier zusaetzlich ein
                # normaler Tkinter-Mausrad-Handler direkt auf scroll_canvas.
                direction = -1 if event.delta > 0 else 1
                scroll_canvas.yview_scroll(direction * 3, "units")

            scroll_canvas.bind("<MouseWheel>", _on_blank_area_scroll)


        _render()