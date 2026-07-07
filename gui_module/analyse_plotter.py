"""
Analyse Plotter - Analyse-Visualisierungsfunktionen
====================================================
Stellt Methoden für komplexe Analyse-Plots bereit:
Signal-, AVG-, RMS-, FFT-, Differential-, Integral-,
und Statistik-Analysen für Einzel- und Gruppensignale.
"""

import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import seaborn as sns
import logging

logger = logging.getLogger(__name__)

from gui_module.plot_manager import PlotManager


class AnalysePlotter:
    """Klasse für alle Analyse-Plot-Funktionen"""

    @staticmethod
    def create_analysis_tab(frame, analyse_typ, selected_headers, signals, units, t, dt,
                            header_to_signal_idx, use_filtered, filter_manager,
                            start_zeit=None, ende_zeit=None):
        """Erstellt einen Analyse-Plot: Jedes Signal bekommt eigenen Subplot."""
        t_full = t
        if not hasattr(frame, "_cursor_range"):
            frame._cursor_range = None

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
            maske = None
            xlim_start = None
            xlim_end = None
            t_local = t_full

            if start_eff is not None and end_eff is not None:
                if strict_range:
                    maske = (t_full >= start_eff) & (t_full <= end_eff)
                    xlim_start, xlim_end = PlotManager._apply_axis_margin(start_eff, end_eff, margin_percent=5)
                else:
                    margin_start, margin_end = PlotManager._apply_axis_margin(start_eff, end_eff, margin_percent=5)
                    xlim_start, xlim_end = margin_start, margin_end
                    maske = (t_full >= margin_start) & (t_full <= margin_end)

                if not np.any(maske):
                    fig = plt.Figure(figsize=(14, 8))
                    ax = fig.add_subplot(111)
                    ax.text(0.5, 0.5, "Kein Signal im gewaehlten Zeitbereich", ha="center", va="center")
                    canvas = FigureCanvasTkAgg(fig, master=frame)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill="both", expand=True)
                    return

                t_local = t_full[maske]

            sns.set_theme(style="whitegrid")
            sns.set_context("notebook")
            sns.set_palette("husl")

            n_signals = len(selected_headers)
            colors = sns.color_palette("husl", n_signals)

            is_filtered = (use_filtered and filter_manager and 
                           filter_manager.filter_type != "Kein Filter")

            if is_filtered:
                filter_info = filter_manager.get_filter_info()
                filter_str = f" (Gefiltert: {filter_info['type']}, {filter_info['order']}, {filter_info['characteristic']})"
            else:
                filter_str = ""

            signal_list = []
            for i, header in enumerate(selected_headers):
                idx = header_to_signal_idx.get(header)
                if idx is None or idx >= len(signals):
                    continue
                original = signals[idx]
                if maske is not None:
                    original = original[maske]
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
                })

            n_signals = len(signal_list)
            if n_signals == 0:
                fig = plt.Figure(figsize=(14, 8))
                ax = fig.add_subplot(111)
                ax.text(0.5, 0.5, "Keine gueltigen Signale ausgewaehlt", ha="center", va="center")
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
                        n = len(filtered)
                        freq = np.fft.rfftfreq(n, dt)
                        fft_complex = np.fft.rfft(filtered)
                        fft_amp = np.abs(fft_complex) * 2 / n
                        sns.lineplot(x=freq, y=fft_amp, ax=ax, color=color)
                        ax.set_title(f"{header} - Amplitudenspektrum [{unit}]")
                        signal_data[ax] = (freq, fft_amp)
                        PlotManager._configure_ax(ax, "Amplitude", show_legend=False)

                    elif ptype == "Phase":
                        n = len(filtered)
                        freq = np.fft.rfftfreq(n, dt)
                        fft_complex = np.fft.rfft(filtered)
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

            for ptype in plot_types:
                group_axes = axes_dict[ptype]
                for ax in group_axes[:-1]:
                    plt.setp(ax.get_xticklabels(), visible=False)

                last_ax = group_axes[-1]
                if ptype in ["Amplitude", "Phase"]:
                    last_ax.set_xlabel("Frequenz [Hz]")
                else:
                    last_ax.set_xlabel("Zeit [s]")

            control_frame = ttk.Frame(frame)
            control_frame.pack(side="top", fill="x", padx=5, pady=5)

            ttk.Label(control_frame, text="Synchroner Zoom:", font=("Arial", 10, "bold")).pack(side="left", padx=5)

            sync_enabled = {}
            show_all_sync = any(len(axes_dict[ptype]) > 1 for ptype in plot_types)
            if show_all_sync:
                all_sync_var = tk.BooleanVar(value=True)

                def _set_all_sync():
                    for var in sync_enabled.values():
                        var.set(all_sync_var.get())

                all_cb = ttk.Checkbutton(control_frame, text="Alle", variable=all_sync_var, command=_set_all_sync)
                all_cb.pack(side="left", padx=5)
            for ptype in plot_types:
                if len(axes_dict[ptype]) > 1:
                    var = tk.BooleanVar(value=True)
                    sync_enabled[ptype] = var
                    cb = ttk.Checkbutton(control_frame, text=ptype, variable=var)
                    cb.pack(side="left", padx=5)

            def _is_time_axis(ax):
                return ax in time_axes

            def _on_cursor_range_selected(x0, x1, ax):
                prev = getattr(frame, "_cursor_range", None)
                new_range = (x0, x1)
                if prev == new_range:
                    return
                frame._cursor_range = new_range
                _render()

            def _on_cursor_range_cleared():
                if getattr(frame, "_cursor_range", None) is None:
                    return
                frame._cursor_range = None
                _render()

            PlotManager.add_cursor_and_zoom_logic(
                fig,
                all_axes,
                signal_data,
                axes_dict,
                sync_enabled,
                range_selected_callback=_on_cursor_range_selected,
                range_cleared_callback=_on_cursor_range_cleared,
                selection_filter=_is_time_axis,
            )

            reset_frame = ttk.Frame(frame)
            reset_frame.pack(side="top", fill="x", padx=5, pady=(0, 5))

            def _reset_zoom_selection():
                if hasattr(fig, "_reset_zoom_selection"):
                    fig._reset_zoom_selection()

            ttk.Button(reset_frame, text="Zuruecksetzen", command=_reset_zoom_selection).pack(side="left", padx=5)

            fig.tight_layout()

            fig_height_px = int(fig.get_figheight() * fig.get_dpi())
            fig_width_px = int(fig.get_figwidth() * fig.get_dpi())

            toolbar_frame = ttk.Frame(frame)
            toolbar_frame.pack(side="top", fill="x")

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

            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
            toolbar.pack(side="right")

            def _on_configure(event):
                scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            inner_frame.bind("<Configure>", _on_configure)


        _render()

    @staticmethod
    def create_group_analysis_tab(frame, analyse_typ, grouped_headers, signals, units, t, dt,
                                  header_to_signal_idx, use_filtered, filter_manager,
                                  start_zeit=None, ende_zeit=None):
        """Erstellt einen Analyse-Plot: pro Gruppe ein Subplot mit allen Signalen (keine Aggregation)."""
        t_full = t
        if not hasattr(frame, "_cursor_range"):
            frame._cursor_range = None

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
            maske = None
            xlim_start = None
            xlim_end = None
            t_local = t_full

            if start_eff is not None and end_eff is not None:
                if strict_range:
                    maske = (t_full >= start_eff) & (t_full <= end_eff)
                    xlim_start, xlim_end = PlotManager._apply_axis_margin(start_eff, end_eff, margin_percent=5)
                else:
                    margin_start, margin_end = PlotManager._apply_axis_margin(start_eff, end_eff, margin_percent=5)
                    xlim_start, xlim_end = margin_start, margin_end
                    maske = (t_full >= margin_start) & (t_full <= margin_end)

                if not np.any(maske):
                    fig = plt.Figure(figsize=(14, 8))
                    ax = fig.add_subplot(111)
                    ax.text(0.5, 0.5, "Kein Signal im gewaehlten Zeitbereich", ha="center", va="center")
                    canvas = FigureCanvasTkAgg(fig, master=frame)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill="both", expand=True)
                    return

                t_local = t_full[maske]

            sns.set_theme(style="whitegrid")
            sns.set_context("notebook")
            sns.set_palette("husl")

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
            fig_height = max(3, total_subplots * 3)
            fig = plt.Figure(figsize=(14, fig_height))

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

                        original = signals[idx]
                        if maske is not None:
                            original = original[maske]

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
                            "unit": unit
                        })

                    if not group_signals:
                        continue

                    unit_display = unit_set.pop() if len(unit_set) == 1 else "Einheiten: gemischt"

                    if ptype == "Original":
                        for sig in group_signals:
                            sns.lineplot(x=t_local, y=sig["original"], ax=ax, linewidth=1.5, label=sig["header"])
                            signal_data.setdefault(ax, []).append((t_local, sig["original"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude")

                    elif ptype == "Gefiltert":
                        for sig in group_signals:
                            sns.lineplot(x=t_local, y=sig["filtered"], ax=ax, linewidth=1.5, label=sig["header"])
                            signal_data.setdefault(ax, []).append((t_local, sig["filtered"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude")

                    elif ptype == "AVG":
                        for sig in group_signals:
                            avg_value = float(np.nanmean(sig["filtered"]))
                            sns.lineplot(x=t_local, y=sig["filtered"], ax=ax, linewidth=1.2, label=sig["header"])
                            ax.axhline(avg_value, linestyle="--", linewidth=1,
                                       label=f"{sig['header']} AVG={avg_value:.4g} {sig['unit']}")
                            signal_data.setdefault(ax, []).append((t_local, sig["filtered"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude")

                    elif ptype == "RMS":
                        for sig in group_signals:
                            rms_value = float(np.sqrt(np.nanmean(sig["filtered"]**2)))
                            sns.lineplot(x=t_local, y=sig["filtered"], ax=ax, linewidth=1.2, label=sig["header"])
                            ax.axhline(rms_value, linestyle="--", linewidth=1,
                                       label=f"{sig['header']} RMS={rms_value:.4g} {sig['unit']}")
                            signal_data.setdefault(ax, []).append((t_local, sig["filtered"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude")

                    elif ptype == "Ableitung":
                        for sig in group_signals:
                            diff = np.gradient(sig["filtered"], dt)
                            sns.lineplot(x=t_local, y=diff, ax=ax, linewidth=1.2, label=sig["header"])
                            signal_data.setdefault(ax, []).append((t_local, diff, sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        unit_diff = f"{unit_display}/s" if unit_display != "Einheiten: gemischt" else "Einheiten: gemischt"
                        PlotManager._configure_ax(ax, f"Ableitung [{unit_diff}]", show_legend=True)

                    elif ptype == "Integral":
                        for sig in group_signals:
                            integral = np.cumsum(sig["filtered"]) * dt
                            sns.lineplot(x=t_local, y=integral, ax=ax, linewidth=1.2, label=sig["header"])
                            signal_data.setdefault(ax, []).append((t_local, integral, sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        unit_int = f"{unit_display}*s" if unit_display != "Einheiten: gemischt" else "Einheiten: gemischt"
                        PlotManager._configure_ax(ax, f"Integral [{unit_int}]", show_legend=True)

                    elif ptype == "Amplitude":
                        for sig in group_signals:
                            n = len(sig["filtered"])
                            freq = np.fft.rfftfreq(n, dt)
                            fft_complex = np.fft.rfft(sig["filtered"])
                            fft_amp = np.abs(fft_complex) * 2 / n
                            sns.lineplot(x=freq, y=fft_amp, ax=ax, linewidth=1.2, label=sig["header"])
                            signal_data.setdefault(ax, []).append((freq, fft_amp, sig["header"]))
                        PlotManager._configure_ax(ax, "Amplitude", show_legend=True)

                    elif ptype == "Phase":
                        for sig in group_signals:
                            n = len(sig["filtered"])
                            freq = np.fft.rfftfreq(n, dt)
                            fft_complex = np.fft.rfft(sig["filtered"])
                            fft_phase = np.angle(fft_complex, deg=True)
                            sns.lineplot(x=freq, y=fft_phase, ax=ax, linewidth=1.2, label=sig["header"])
                            signal_data.setdefault(ax, []).append((freq, fft_phase, sig["header"]))
                        PlotManager._configure_ax(ax, "Phase [Grad]", show_legend=True)

                    elif ptype == "Statistik":
                        for sig in group_signals:
                            mean_val = np.mean(sig["filtered"])
                            std_val = np.std(sig["filtered"])
                            sns.lineplot(x=t_local, y=sig["filtered"], ax=ax, linewidth=1.2, label=sig["header"])
                            ax.axhline(y=mean_val, linestyle="--", linewidth=1,
                                       label=f"{sig['header']} Mean={mean_val:.4g}")
                            signal_data.setdefault(ax, []).append((t_local, sig["filtered"], sig["header"]))
                        time_axes.add(ax)
                        if xlim_start is not None and xlim_end is not None:
                            ax.set_xlim(xlim_start, xlim_end)
                        PlotManager._configure_ax(ax, "Amplitude")

                    unit_suffix = f" [{unit_display}]"
                    if ptype == "Ableitung":
                        unit_suffix = f" [{unit_diff}]"
                    elif ptype == "Integral":
                        unit_suffix = f" [{unit_int}]"
                    elif ptype == "Phase":
                        unit_suffix = " [Grad]"
                    ax.set_title(f"Gruppe {group_idx + 1} - {ptype}{unit_suffix}")

            for ptype in plot_types:
                group_axes = axes_dict[ptype]
                for ax in group_axes[:-1]:
                    plt.setp(ax.get_xticklabels(), visible=False)

                last_ax = group_axes[-1]
                if ptype in ["Amplitude", "Phase"]:
                    last_ax.set_xlabel("Frequenz [Hz]")
                else:
                    last_ax.set_xlabel("Zeit [s]")

            control_frame = ttk.Frame(frame)
            control_frame.pack(side="top", fill="x", padx=5, pady=5)

            ttk.Label(control_frame, text="Synchroner Zoom:", font=("Arial", 10, "bold")).pack(side="left", padx=5)

            sync_enabled = {}
            show_all_sync = any(len(axes_dict[ptype]) > 1 for ptype in plot_types)
            if show_all_sync:
                all_sync_var = tk.BooleanVar(value=True)

                def _set_all_sync():
                    for var in sync_enabled.values():
                        var.set(all_sync_var.get())

                all_cb = ttk.Checkbutton(control_frame, text="Alle", variable=all_sync_var, command=_set_all_sync)
                all_cb.pack(side="left", padx=5)
            for ptype in plot_types:
                if len(axes_dict[ptype]) > 1:
                    var = tk.BooleanVar(value=True)
                    sync_enabled[ptype] = var
                    cb = ttk.Checkbutton(control_frame, text=ptype, variable=var)
                    cb.pack(side="left", padx=5)

            def _is_time_axis(ax):
                return ax in time_axes

            def _on_cursor_range_selected(x0, x1, ax):
                prev = getattr(frame, "_cursor_range", None)
                new_range = (x0, x1)
                if prev == new_range:
                    return
                frame._cursor_range = new_range
                _render()

            def _on_cursor_range_cleared():
                if getattr(frame, "_cursor_range", None) is None:
                    return
                frame._cursor_range = None
                _render()

            PlotManager.add_cursor_and_zoom_logic(
                fig,
                all_axes,
                signal_data,
                axes_dict,
                sync_enabled,
                range_selected_callback=_on_cursor_range_selected,
                range_cleared_callback=_on_cursor_range_cleared,
                selection_filter=_is_time_axis,
            )

            reset_frame = ttk.Frame(frame)
            reset_frame.pack(side="top", fill="x", padx=5, pady=(0, 5))

            def _reset_zoom_selection():
                if hasattr(fig, "_reset_zoom_selection"):
                    fig._reset_zoom_selection()

            ttk.Button(reset_frame, text="Zuruecksetzen", command=_reset_zoom_selection).pack(side="left", padx=5)

            fig.tight_layout()

            fig_height_px = int(fig.get_figheight() * fig.get_dpi())
            fig_width_px = int(fig.get_figwidth() * fig.get_dpi())

            toolbar_frame = ttk.Frame(frame)
            toolbar_frame.pack(side="top", fill="x")

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

            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
            toolbar.pack(side="right")

            def _on_configure(event):
                scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            inner_frame.bind("<Configure>", _on_configure)


        _render()