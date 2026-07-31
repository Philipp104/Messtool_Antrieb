
"""
Plot Manager - Basis-Visualisierungsfunktionen
================================================
Stellt statische Methoden für Basis-Plot-Operationen bereit:
Zeit- und Frequenzbereichsdarstellung, FFT-Plots, Filter-Charakteristiken,
interaktive Cursor und Multi-Signal-Overlays.
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
import logging
import tkinter as tk
from tkinter import ttk

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ttkbootstrap as tb
from matplotlib import gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.transforms import blended_transform_factory
from matplotlib.colors import to_hex as _mpl_color_to_hex
from matplotlib.colors import to_rgb as _mpl_color_to_rgb

# ============================================================
#  IMPORTS – Eigene Klassen
# ============================================================
from hilfsklassen.zentrales_logging import get_protocol_logger
from gui_module.gui_hilfsfunktionen import center_window
from konfiguration import Cfg

# ============================================================
#  LOGGING
# ============================================================
logger          = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()


# ============================================================
#  KLASSE
# ============================================================
class PlotManager:
    """Klasse für Basis-Plot-Funktionen mit gemeinsamen Parametern"""

    # --------------------------------------------------------
    #  HILFSMETHODEN
    # --------------------------------------------------------

    @staticmethod
    def t_for_idx(t, idx):
        """Loest die Zeitachse fuer ein einzelnes Signal auf.

        Normalerweise ist t EIN gemeinsames Array fuer alle Signale (Einzeldatei/
        Zusammenfuehren-Modus). Beim kombinierten Signal-Pool (Batch-Modus mit
        Dateien unterschiedlicher Laenge) ist t stattdessen eine Liste von Arrays,
        eines pro Signal (gleiche Reihenfolge wie gui.signals) - dann wird hier
        das zum Index passende Array herausgegriffen."""
        if isinstance(t, (list, tuple)):
            return t[idx]
        return t

    @staticmethod
    def _apply_fine_grid(ax):
        """Macht das Grid feiner mit Major- und Minor-Gridlines."""
        ax.minorticks_on()
        ax.grid(True, which='major', linestyle=Cfg.Colors.GRID_LINESTYLE,
                alpha=Cfg.Colors.GRID_ALPHA, color=Cfg.Colors.GRID_COLOR, linewidth=0.8)
        ax.grid(True, which='minor', linestyle=':', alpha=Cfg.Colors.GRID_ALPHA * 0.5,
                color=Cfg.Colors.GRID_COLOR, linewidth=0.3)

    @staticmethod
    def _interpolate_signal(t, sig, factor=5):
        """Interpoliert Signal mit höherer Auflösung für glattere Plots."""
        from scipy.interpolate import interp1d
        try:
            f = interp1d(t, sig, kind='cubic', fill_value='extrapolate')
            t_new = np.linspace(t[0], t[-1], len(t) * factor)
            sig_new = f(t_new)
            return t_new, sig_new
        except Exception:
            return t, sig

    @staticmethod
    def _apply_axis_margin(start, end, margin_percent=Cfg.Layout.Figure.AXIS_MARGIN_PERCENT):
        """
        Fügt prozentuale Margin zu Start/End hinzu für bessere Achsen-Sichtbarkeit.
        Args:
            start:          Start-Wert (Zeit oder Frequenz)
            end:            End-Wert (Zeit oder Frequenz)
            margin_percent: Margin in % der Gesamtbreite (default 5%)
        Returns:
            tuple: (new_start, new_end) mit Margin
        Beispiel:
            start_zeit=5, end_zeit=10, margin_percent=5
            → start_zeit=4.75, end_zeit=10.25 (Margin=0.25s)
        """
        range_width = end - start
        if range_width <= 0:
            return start, end
        margin = (range_width / 100) * margin_percent
        return start - margin, end + margin

    @staticmethod
    def _estimate_legend_ncol(ax, labels):
        """Schätzt, wie viele Legenden-Einträge nebeneinander in die Breite
        des Plots passen (für legend_below), damit sie bei Bedarf in eine
        neue Zeile darunter umbrechen. Grobe Schätzung anhand der
        Beschriftungslänge - es gibt keine exakte Breitenmessung ohne
        Renderer, siehe auch ähnliche Schätzungen bei den Cursor-Boxen."""
        if not labels:
            return 1
        fig = ax.get_figure()
        avg_len = sum(len(l) for l in labels) / len(labels)
        fontsize_pt = Cfg.Fonts.Plots.LEGEND
        # ~0.55 * Schriftgröße pro Zeichen (typisch für proportionale
        # Schriften) + Platz für Linien-Symbol und Innenabstand (~4 Zeichen).
        # matplotlib bricht bei zu knapper Schätzung NICHT selbst um (die
        # angegebene Spaltenzahl wird stur gerendert und läuft dann über den
        # Rand hinaus) - deshalb bewusst mit Sicherheitsfaktor lieber eine
        # Zeile zu viel als eine abgeschnittene Legende.
        SAFETY_FACTOR = 1.6
        entry_width_in = (avg_len * 0.55 + 4) * fontsize_pt / 72 * SAFETY_FACTOR
        ncol = max(1, int(fig.get_figwidth() / entry_width_in))
        return min(ncol, len(labels))

    @staticmethod
    def _configure_ax(ax, ylabel, xlabel=None, title=None, show_legend=True, legend_below=False):
        """Konfiguriert einen Subplot einheitlich.

        legend_below: Legende unter dem Plot statt rechts daneben, Einträge
        nebeneinander mit automatischem Zeilenumbruch (siehe
        _estimate_legend_ncol), statt einer Spalte rechts.
        """
        ax.set_ylabel(ylabel, fontsize=Cfg.Fonts.Plots.AXIS_LABELS)
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=Cfg.Fonts.Plots.AXIS_LABELS)
        if title:
            ax.set_title(title, fontsize=Cfg.Fonts.Plots.AXIS_TITLE)
        ax.grid(
            True,
            linestyle=Cfg.Colors.GRID_LINESTYLE,
            alpha=Cfg.Colors.GRID_ALPHA,
            color=Cfg.Colors.GRID_COLOR
        )
        if show_legend:
            if legend_below:
                # Wird HIER absichtlich noch nicht erzeugt: eine Achsen-Fraktion
                # (0-1 relativ zu DIESER Achse) ist nicht auf einen konstanten
                # Achsen-zu-Achse-Abstand übertragbar (steht ausserdem erst
                # nach fig.subplots_adjust(...) endgültig fest, da viele
                # gestapelte Subplots stark unterschiedliche Höhen haben können).
                # Siehe PlotManager.finalize_group_legends: die wird NACH dem
                # finalen Layout aufgerufen und positioniert in absoluten
                # Zoll-Abständen (figur-transform), damit der Abstand zur
                # X-Achsen-Beschriftung überall gleich groß ist.
                pass
            else:
                ax.legend(
                    loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0,
                    fontsize=Cfg.Fonts.Plots.LEGEND
                )

    @staticmethod
    def finalize_group_legends(axes, clearance_in=0.55, max_legend_height_in=0.9):
        """Erzeugt für Gruppen-Plots (legend_below=True in _configure_ax) die
        Unter-dem-Plot-Legende, in FIGUR-Koordinaten (nicht Achsen-Fraktion)
        positioniert - dadurch hat jede Legende denselben absoluten Abstand
        zur X-Achsen-Beschriftung, unabhängig von der Höhe des jeweiligen
        Subplots. Muss NACH fig.subplots_adjust(...) aufgerufen werden (siehe
        get_group_legend_margins für die dazu passenden bottom/hspace-Werte),
        weil ax.get_position() erst dann feststeht."""
        for ax in axes:
            handles, labels = ax.get_legend_handles_labels()
            if not labels:
                continue
            fig = ax.get_figure()
            pos = ax.get_position()
            x_center = (pos.x0 + pos.x1) / 2
            y_top = pos.y0 - clearance_in / fig.get_figheight()
            ax.legend(
                handles, labels,
                loc="upper center", bbox_to_anchor=(x_center, y_top),
                bbox_transform=fig.transFigure,
                ncol=PlotManager._estimate_legend_ncol(ax, labels),
                fontsize=Cfg.Fonts.Plots.LEGEND,
            )

    @staticmethod
    def get_group_legend_margins(fig, clearance_in=0.55, max_legend_height_in=0.9):
        """Berechnet bottom/hspace für fig.subplots_adjust(...) so, dass IMMER
        mindestens (clearance_in + max_legend_height_in) Zoll absoluter Platz
        für die Unter-dem-Plot-Legende reserviert sind - unabhängig davon, wie
        wenige/viele Subplots die Figur hat. Eine feste Bruchzahl (z.B.
        bottom=0.18) reicht bei EINEM Subplot (Figurhöhe nur 3 Zoll) nicht,
        ist bei VIELEN Subplots (Figur wächst proportional mit) aber unnötig
        knapp bemessen bzw. verschwenderisch - deshalb hier aus der
        tatsächlichen Figurhöhe zurückgerechnet."""
        reserve_in = clearance_in + max_legend_height_in
        bottom = min(0.5, reserve_in / fig.get_figheight())
        hspace = min(2.5, reserve_in / 1.6)
        return bottom, hspace

    @staticmethod
    def _hide_xticklabels(axes_list):
        """Versteckt X-Achsen-Labels für alle Axes in der Liste."""
        for ax in axes_list:
            plt.setp(ax.get_xticklabels(), visible=False)

    @staticmethod
    def _setup_subplot_grid(fig, n_signals, plot_types, is_filtered=False):
        """Erstellt Subplot-Grid: Jedes Signal bekommt eigenen Subplot, gruppiert nach Plot-Typ."""
        n_types        = len(plot_types)
        total_subplots = n_signals * n_types
        gs             = gridspec.GridSpec(total_subplots, 1)
        axes_dict      = {ptype: [] for ptype in plot_types}

        subplot_idx = 0
        for ptype in plot_types:
            for sig_idx in range(n_signals):
                ax = fig.add_subplot(gs[subplot_idx])
                axes_dict[ptype].append(ax)
                subplot_idx += 1

        return axes_dict

    # --------------------------------------------------------
    #  CURSOR & ZOOM
    # --------------------------------------------------------

    @staticmethod
    def add_cursor_and_zoom_logic(
        fig, axes, signal_data,
        axes_groups=None,
        sync_enabled=None,
        range_selected_callback=None,
        range_cleared_callback=None,
        selection_filter=None,
        multi_cursor_var=None,
        cursor_panel=None,
        on_cursor_panel_visibility=None,
    ):
        """Fügt interaktiven Cursor, Selektion und Zoom zu einem Plot hinzu.

        multi_cursor_var: optionale tk.BooleanVar. Ist sie True ("Mehrere"),
        setzt ein Klick einen bleibenden Cursor (statt der Zoom-Selektion)
        an der geklickten Stelle - synchronisiert über dieselben Achsgruppen
        wie der Hover-Cursor.

        cursor_panel: optionales ttk.Frame (Tkinter, ausserhalb der Figure).
        Bei Gruppen-Plots (mehrere überlagerte Signale in einer Achse) werden
        die Wertetabellen gepinnter Cursor ("Mehrere"-Modus) hier als eigene
        Karten-Widgets angezeigt statt als matplotlib-Annotation im Plot -
        das hat unabhängig von der Subplot-Höhe beliebig viel Platz. Ohne
        cursor_panel bleibt nur der dicke Strich + Nummer im Plot sichtbar,
        ohne Wertetabelle. Der normale Hover-Fadenkreuz (Boxen links, oben)
        ist davon unberührt.

        on_cursor_panel_visibility: optionaler Callback(bool) - wird mit True
        aufgerufen, sobald die erste Karte im cursor_panel entsteht, und mit
        False, sobald keine Karte mehr da ist. Der Aufrufer kann damit das
        Panel selbst ein-/ausblenden (z.B. aus dem PanedWindow entfernen),
        damit es nicht leer sichtbar bleibt, solange kein Cursor gesetzt ist.
        """
        vlines         = {}
        hlines         = {}
        annotations    = {}
        selection_start   = {}
        selection_start_y = {}
        selection_lines   = {}
        selection_markers = {}
        # Bei Gruppen-Plots bekommt die Zwei-Klick-Bereichsauswahl ("Einer")
        # dieselbe Optik wie ein gepinnter Cursor ("Mehrere"): dicker Strich +
        # eingekreiste Nummer im Plot, Wertetabelle als Karte im cursor_panel -
        # statt der einfachen "Start/End x=...y=..."-Box im Plot. Das Verhalten
        # (zweiter Klick zoomt rein) bleibt unverändert.
        selection_group_numbers = {}  # ax -> (start_number_ann, end_number_ann)
        selection_group_cards   = {}  # ax -> {"start": card_widget, "end": card_widget}
        original_limits   = {}
        hover_state    = {"ax": None, "x": None, "y": None, "axes": set()}

        def _left_ann_x(ax):
            """X-Position (Achsen-Fraktion) für die linken Gruppen-Cursorboxen -
            so nah wie möglich am Plot, aber ohne die Y-Achsen-Ticklabels/
            -Beschriftung zu schneiden. Wird per Renderer aus der TATSÄCHLICH
            gerenderten Breite der Y-Achsen-Beschriftung berechnet (die hängt
            von den Zahlenwerten/vom Achsentitel ab - eine feste Achsen-
            Fraktion ist mal zu knapp, mal unnötig weit weg)."""
            fig = ax.get_figure()
            renderer = getattr(fig.canvas, "get_renderer", lambda: None)()
            if renderer is None:
                return -0.14  # Fallback, bevor die Figur gezeichnet ist
            try:
                ax_bbox = ax.get_window_extent(renderer=renderer)
                y_bbox = ax.yaxis.get_tightbbox(renderer)
                if y_bbox is None or ax_bbox.width <= 0:
                    return -0.14
                overhang_px = max(0.0, ax_bbox.x0 - y_bbox.x0)
                value = -(overhang_px + 8) / ax_bbox.width  # +8px Sicherheitsabstand
                return min(value, -0.03)  # nie näher als -0.03, auch bei sehr schmaler Y-Beschriftung
            except Exception:
                return -0.14

        def _group_box_yfracs(ax, n):
            """Y-Positionen (Achsen-Fraktion) für n gestapelte Hover-
            Cursorboxen. Wird bei jedem Hover live neu berechnet (nicht beim
            Aufbau), weil dafür die TATSÄCHLICHE, endgültige Achsenhöhe
            (ax.get_position(), erst nach fig.subplots_adjust(...) korrekt)
            gebraucht wird - eine feste Achsen-Fraktion reicht bei kurzen/
            komprimierten Subplots nicht, die Boxen überlappen sich dann."""
            fig = ax.get_figure()
            try:
                ax_height_in = ax.get_position().height * fig.get_figheight()
            except Exception:
                ax_height_in = 2.0
            row_height_in = 0.30  # ~2 Zeilen kleine Schrift + Puffer
            step = row_height_in / ax_height_in if ax_height_in > 0.05 else 0.3
            step = min(step, 0.30)
            return [0.97 - i * step for i in range(n)]

        def _tint_color(color, amount=0.18):
            """Blendet eine Farbe leicht mit Weiss (amount=Anteil der Farbe) -
            für einen dezenten Hintergrund-Tint der aktiven Hover-Cursorbox."""
            r, g, b = _mpl_color_to_rgb(color)
            return (1 - amount) + amount * r, (1 - amount) + amount * g, (1 - amount) + amount * b

        def _circled_number(n):
            # Klartext-Ziffer statt Unicode-Kreiszeichen (①②...) - das
            # verlässt sich auf Font-Unterstützung, die nicht garantiert ist.
            # Der Kreis kommt stattdessen von der 'circle'-Bbox der Annotation.
            return str(n)

        def _group_table_text(rows):
            """rows: [(label, x, y), ...] - baut eine feste Tabelle 'x | y' mit
            den Signalnamen links (Monospace-Schrift für Spaltenausrichtung)."""
            label_w = max([len(r[0]) for r in rows] + [5])
            lines = [f"{'':<{label_w}} {'x':>9} {'y':>9}"]
            for label, xv, yv in rows:
                lines.append(f"{label:<{label_w}} {xv:>9.3f} {yv:>9.3f}")
            return "\n".join(lines)

        def _make_cursor_card(number, color, title, rows):
            """Baut eine kleine Karte (Tkinter, nicht matplotlib) für einen
            gepinnten Gruppen-Cursor im cursor_panel - unabhängig von der
            Subplot-Höhe, beliebig viele Karten möglich (mit eigener
            Scrollbar im Panel)."""
            color = _mpl_color_to_hex(color)  # matplotlib liefert RGB-Floats, Tk braucht Hex/Namen
            card = tk.Frame(cursor_panel, highlightbackground=color,
                             highlightcolor=color, highlightthickness=2, bd=0,
                             bg=Cfg.Colors.ANNOTATION_BG)
            header_row = tk.Frame(card, bg=Cfg.Colors.ANNOTATION_BG)
            header_row.pack(fill="x", padx=6, pady=(4, 0))

            # Eingekreiste Nummer wie im Plot (Canvas mit Oval, da Tkinter kein
            # rundes Label kennt), statt der Zahl als reiner Text davor. Grösse
            # wächst mit der Ziffernzahl, sonst schneidet der Kreis ab "10" in
            # die Zahl.
            _digits = len(str(number))
            _badge_size = 20 + max(0, _digits - 1) * 7
            badge = tk.Canvas(header_row, width=_badge_size, height=_badge_size,
                               highlightthickness=0, bg=Cfg.Colors.ANNOTATION_BG)
            badge.create_oval(2, 2, _badge_size - 2, _badge_size - 2,
                               outline=color, width=2, fill=Cfg.Colors.ANNOTATION_BG)
            badge.create_text(_badge_size / 2, _badge_size / 2, text=str(number),
                               fill=color,
                               font=(Cfg.Fonts.FAMILY, Cfg.Fonts.Plots.LEGEND, "bold"))
            badge.pack(side="left", padx=(0, 6))

            header = tk.Label(
                header_row, text=title, fg=color,
                bg=Cfg.Colors.ANNOTATION_BG,
                font=(Cfg.Fonts.FAMILY, Cfg.Fonts.Plots.LEGEND, "bold"), anchor="w",
            )
            header.pack(side="left", fill="x", expand=True)

            table_text = _group_table_text(rows)
            # Breite an die tatsächlich längste Zeile anpassen (+2 Puffer) -
            # eine feste Breite (z.B. 30) ist bei langen Signalnamen zu schmal
            # und bricht Zahlen mitten im Wort um ("795." + "0" in Zeile darunter).
            _width = max((len(line) for line in table_text.split("\n")), default=20) + 2
            body = tk.Text(
                card, height=len(rows) + 1, width=_width, font=("Consolas", 9),
                fg=color, bg=Cfg.Colors.ANNOTATION_BG, relief="flat", bd=0,
                highlightthickness=0, wrap="none",
            )
            body.insert("1.0", table_text)
            body.configure(state="disabled")
            body.pack(fill="x", padx=6, pady=(0, 6))
            card.pack(side="top", fill="x", padx=4, pady=4)

            # Mausrad-Scrollen des umgebenden Canvas (cursor_panel.master) auch
            # direkt über der Karte ermöglichen - ein Binding nur auf dem Canvas
            # feuert nicht, wenn die Maus über einem Kind-Widget (Karte/Label/
            # Text) steht.
            def _on_card_wheel(event):
                direction = -1 if event.delta > 0 else 1
                cursor_panel.master.yview_scroll(direction * 3, "units")

            for _w in (card, header_row, badge, header, body):
                _w.bind("<MouseWheel>", _on_card_wheel)

            return card

        def _notify_cursor_panel_visibility():
            if on_cursor_panel_visibility is None or cursor_panel is None:
                return
            has_cards = len(cursor_panel.winfo_children()) > 0
            on_cursor_panel_visibility(has_cards)

        def _rebuild_cursor_panel(entries):
            """entries: [(number, color, title, ax, x_snap), ...] in Reihenfolge.
            Baut das cursor_panel komplett neu auf (einfacher und robuster als
            gezielt einzelne Karten zu verschieben/löschen)."""
            if cursor_panel is None:
                return
            for child in cursor_panel.winfo_children():
                child.destroy()
            selection_group_cards.clear()  # ihre Karten wurden gerade mit zerstört
            for number, color, title, ax_b, x_snap in entries:
                rows = _group_rows_at(ax_b, x_snap)
                _make_cursor_card(number, color, title, rows)
            _notify_cursor_panel_visibility()

        def _update_selection_card(ax, kind, number, color, x_snap):
            """Legt/aktualisiert EINE Karte im cursor_panel für die Start- oder
            End-Markierung der Zwei-Klick-Bereichsauswahl (nur Gruppen-Plots) -
            ohne die restlichen Karten (gepinnte Cursor) anzufassen."""
            if cursor_panel is None:
                return
            entry = selection_group_cards.setdefault(ax, {})
            old = entry.get(kind)
            if old is not None:
                try:
                    old.destroy()
                except tk.TclError:
                    pass
            rows = _group_rows_at(ax, x_snap)
            title = f"{'Start' if kind == 'start' else 'Ende'} - {ax.get_title()}"
            entry[kind] = _make_cursor_card(number, color, title, rows)
            _notify_cursor_panel_visibility()

        def _clear_selection_cards(ax, kind=None):
            entry = selection_group_cards.get(ax)
            if not entry:
                return
            for k in ([kind] if kind else list(entry.keys())):
                card = entry.pop(k, None)
                if card is not None:
                    try:
                        card.destroy()
                    except tk.TclError:
                        pass
            if not entry:
                selection_group_cards.pop(ax, None)
            _notify_cursor_panel_visibility()

        # Bleibende ("gepinnte") Cursor im "Mehrere"-Modus: eine Liste von
        # "Batches" (ein Klick = ein Batch, ggf. auf mehrere synchronisierte
        # Achsen verteilt), damit Vor/Zurück sie einzeln ein-/ausblenden kann.
        pinned_batches      = []
        pinned_state        = {"visible": 0}
        pinned_color_cycle  = plt.cm.tab10.colors
        # Pannen mit gedrückter rechter Maustaste (Zusatzoption neben Fadenkreuz/Auswahl)
        pan_state           = {"ax": None, "x0_px": None, "y0_px": None, "limits": None}
        # Vor/Zurück-Navigation durch die Ansichts-Historie (ersetzt die
        # entsprechenden Pfeile aus der matplotlib-Toolbar).
        view_history        = {"stack": [], "index": -1}

        for ax in axes:
            saved_xlim = ax.get_xlim()
            saved_ylim = ax.get_ylim()

            vlines[ax] = ax.axvline(
                x=0,
                color=Cfg.Colors.CURSOR_PRIMARY_COLOR,
                linestyle=Cfg.Colors.CURSOR_LINESTYLE,
                linewidth=Cfg.Colors.CURSOR_LINEWIDTH,
                visible=False,
                alpha=Cfg.Colors.CURSOR_ALPHA
            )
            hlines[ax] = ax.axhline(
                y=0,
                color=Cfg.Colors.CURSOR_PRIMARY_COLOR,
                linestyle=Cfg.Colors.CURSOR_LINESTYLE,
                linewidth=Cfg.Colors.CURSOR_LINEWIDTH,
                visible=False,
                alpha=Cfg.Colors.CURSOR_ALPHA
            )
            _series_init = signal_data.get(ax)
            _is_multi = isinstance(_series_init, list) and len(_series_init) > 1
            if _is_multi:
                _line_colors = {
                    line.get_label(): line.get_color()
                    for line in ax.get_lines()
                    if not line.get_label().startswith('_')
                }
                # Feste Position oben links in Achsen-Fraktion (folgt NICHT dem
                # Cursor auf der X-Achse), damit die Boxen bei Gruppensignalen
                # nicht Teile des Signals oder die Legende (oben rechts) verdecken.
                # Die tatsächliche Y-Position wird erst live beim Hover berechnet
                # (_group_box_yfracs) - hier nur Platzhalter, da die endgültige
                # Achsenhöhe erst nach fig.subplots_adjust(...) feststeht.
                _ann_list = []
                for _i, _s in enumerate(_series_init):
                    _lbl   = _s[2] if len(_s) >= 3 else None
                    _col   = _line_colors.get(_lbl, Cfg.Colors.ANNOTATION_FG)
                    _ann   = ax.annotate(
                        '',
                        xy=(-0.14, 0.97), xycoords=ax.transAxes,
                        xytext=(0, 0), textcoords='offset points',
                        ha='right', va='top',
                        fontsize=Cfg.Fonts.Plots.LEGEND - 2,
                        color=_col,
                        bbox=dict(boxstyle='round', facecolor=Cfg.Colors.ANNOTATION_BG,
                                  edgecolor=_col, alpha=Cfg.Colors.ANNOTATION_BOX_ALPHA),
                        visible=False,
                        annotation_clip=False
                    )
                    _ann.set_clip_on(False)
                    _ann_list.append(_ann)
                annotations[ax] = _ann_list
            else:
                annotations[ax] = [ax.annotate(
                    '', xy=(0, 0), xytext=(8, 8), textcoords='offset points',
                    ha='left', va='bottom', fontsize=Cfg.Fonts.Plots.LEGEND,
                    bbox=dict(boxstyle='round', facecolor=Cfg.Colors.ANNOTATION_BG,
                              edgecolor=Cfg.Colors.ANNOTATION_BORDER,
                              alpha=Cfg.Colors.ANNOTATION_BOX_ALPHA),
                    visible=False
                )]
            # Bei Gruppen-Plots dicker (wie der gepinnte Cursor bei "Mehrere"),
            # damit Start/Ende der Zwei-Klick-Auswahl gleich aussehen.
            _selection_linewidth = Cfg.Colors.SELECTION_LINEWIDTH * (2.5 if _is_multi else 1.0)
            selection_lines[ax] = (
                ax.axvline(
                    x=0,
                    color=Cfg.Colors.CURSOR_SECONDARY_COLOR,
                    linestyle=Cfg.Colors.SELECTION_LINESTYLE,
                    linewidth=_selection_linewidth,
                    visible=False
                ),
                ax.axvline(
                    x=0,
                    color=Cfg.Colors.CURSOR_SECONDARY_COLOR,
                    linestyle=Cfg.Colors.SELECTION_LINESTYLE,
                    linewidth=_selection_linewidth,
                    visible=False
                ),
            )
            if _is_multi:
                _start_num = ax.annotate(
                    '', xy=(0, 1.0), xytext=(0, 4), textcoords='offset points',
                    xycoords=blended_transform_factory(ax.transData, ax.transAxes),
                    ha='center', va='bottom', fontsize=Cfg.Fonts.Plots.LEGEND + 1,
                    color=Cfg.Colors.CURSOR_SECONDARY_COLOR, fontweight='bold',
                    bbox=dict(boxstyle='circle', facecolor=Cfg.Colors.ANNOTATION_BG,
                              edgecolor=Cfg.Colors.CURSOR_SECONDARY_COLOR, alpha=0.9,
                              pad=0.15),
                    visible=False, annotation_clip=False, zorder=7,
                )
                _end_num = ax.annotate(
                    '', xy=(0, 1.0), xytext=(0, 4), textcoords='offset points',
                    xycoords=blended_transform_factory(ax.transData, ax.transAxes),
                    ha='center', va='bottom', fontsize=Cfg.Fonts.Plots.LEGEND + 1,
                    color=Cfg.Colors.CURSOR_PRIMARY_COLOR, fontweight='bold',
                    bbox=dict(boxstyle='circle', facecolor=Cfg.Colors.ANNOTATION_BG,
                              edgecolor=Cfg.Colors.CURSOR_PRIMARY_COLOR, alpha=0.9,
                              pad=0.15),
                    visible=False, annotation_clip=False, zorder=7,
                )
                selection_group_numbers[ax] = (_start_num, _end_num)
            _ann_start = ax.annotate(
                '', xy=(0, 0), xytext=(6, 6), textcoords='offset points',
                ha='left', va='bottom', fontsize=Cfg.Fonts.Plots.LEGEND,
                color=Cfg.Colors.CURSOR_SECONDARY_COLOR,
                bbox=dict(
                    boxstyle='round',
                    facecolor=Cfg.Colors.ANNOTATION_BG,
                    edgecolor=Cfg.Colors.CURSOR_SECONDARY_COLOR,
                    alpha=Cfg.Colors.ANNOTATION_BOX_ALPHA
                ),
                visible=False, zorder=6
            )
            _ann_end = ax.annotate(
                '', xy=(0, 0), xytext=(6, 6), textcoords='offset points',
                ha='left', va='bottom', fontsize=Cfg.Fonts.Plots.LEGEND,
                color=Cfg.Colors.CURSOR_PRIMARY_COLOR,
                bbox=dict(
                    boxstyle='round',
                    facecolor=Cfg.Colors.ANNOTATION_BG,
                    edgecolor=Cfg.Colors.CURSOR_PRIMARY_COLOR,
                    alpha=Cfg.Colors.ANNOTATION_BOX_ALPHA
                ),
                visible=False, zorder=6
            )
            selection_markers[ax] = (_ann_start, _ann_end)
            # Restore limits after adding cursor lines to prevent axhline(y=0)
            # from extending the y-axis to include 0 when data is far from 0.
            # Disable autoscale so the rendering pipeline cannot override these
            # limits again (e.g. when fig.set_size_inches triggers a redraw).
            ax.set_xlim(saved_xlim)
            ax.set_ylim(saved_ylim)
            ax.set_autoscale_on(False)
            original_limits[ax] = (saved_xlim, saved_ylim)

        # --- Interne Hilfsfunktionen ---

        def _get_series_list(ax):
            data = signal_data.get(ax)
            if data is None:
                return []
            return data if isinstance(data, list) else [data]

        def _group_rows_at(ax, x_target):
            """Liefert [(label, x, y), ...] für jedes Signal in ax am jeweils
            nächsten Datenpunkt zu x_target - für die Gruppen-Wertetabelle."""
            rows = []
            for series in _get_series_list(ax):
                _xd, _yd = series[:2]
                _lbl = series[2] if len(series) >= 3 else ""
                _idx = int(np.argmin(np.abs(np.array(_xd) - x_target)))
                rows.append((_lbl, float(np.array(_xd)[_idx]), float(np.array(_yd)[_idx])))
            return rows

        def _find_best_snap(ax, event):
            series_list = _get_series_list(ax)
            if not series_list:
                return None

            best     = None
            mouse_xy = np.array([event.x, event.y], dtype=float)

            for series in series_list:
                if len(series) == 2:
                    xdata, ydata = series
                    label = None
                else:
                    xdata, ydata, label = series

                x_arr  = np.array(xdata)
                idx    = np.argmin(np.abs(x_arr - event.xdata))
                x_snap = x_arr[idx]
                y_snap = np.array(ydata)[idx]

                snap_xy = ax.transData.transform((x_snap, y_snap))
                dist    = np.linalg.norm(snap_xy - mouse_xy)

                if best is None or dist < best["dist"]:
                    best = {"x": x_snap, "y": y_snap, "label": label, "dist": dist}

            return best

        def _apply_sync_or_single(ax, new_xlim, new_ylim):
            """Wendet neue Limits synchron auf Achsengruppe oder einzelne Achse an."""
            if axes_groups:
                for group_name, group_axes in axes_groups.items():
                    if ax in group_axes and len(group_axes) > 1:
                        sync_on = True
                        if sync_enabled and group_name in sync_enabled:
                            sync_on = sync_enabled[group_name].get()
                        target_axes = group_axes if sync_on else [ax]
                        for a in target_axes:
                            a.set_xlim(new_xlim)
                            a.set_ylim(new_ylim)
                        return
            ax.set_xlim(new_xlim)
            ax.set_ylim(new_ylim)

        def _get_synced_axes(ax):
            """Achsen, die gemeinsam mit ax den Cursor anzeigen sollen (folgt der
            'Synchron'-Einstellung der jeweiligen Achsengruppe, wie beim Zoom)."""
            if axes_groups:
                for group_name, group_axes in axes_groups.items():
                    if ax in group_axes and len(group_axes) > 1:
                        sync_on = True
                        if sync_enabled and group_name in sync_enabled:
                            sync_on = sync_enabled[group_name].get()
                        return set(group_axes) if sync_on else {ax}
            return {ax}

        def _view_snapshot():
            return {
                "axes":         {a: (a.get_xlim(), a.get_ylim()) for a in axes},
                "cursor_count": pinned_state["visible"],
            }

        def _set_pinned_visible_count(n):
            """Blendet gepinnte Cursor-Batches ein/aus, bis genau n Batches
            (von vorne gezählt) sichtbar sind - für Vor/Zurück im 'Mehrere'-
            Cursor-Modus."""
            n = max(0, min(n, len(pinned_batches)))
            current = pinned_state["visible"]
            if n < current:
                for batch in pinned_batches[n:current]:
                    for _ax, vline, ann, group_info in batch:
                        vline.set_visible(False)
                        if ann is not None:
                            ann.set_visible(False)
                        if group_info is not None:
                            group_info["number_ann"].set_visible(False)
            elif n > current:
                for batch in pinned_batches[current:n]:
                    for _ax, vline, ann, group_info in batch:
                        vline.set_visible(True)
                        if ann is not None:
                            ann.set_visible(True)
                        if group_info is not None:
                            group_info["number_ann"].set_visible(True)
            pinned_state["visible"] = n
            _renumber_pinned_cursors()

        def _restore_view_snapshot(snap):
            for a, (xlim, ylim) in snap["axes"].items():
                a.set_xlim(xlim)
                a.set_ylim(ylim)
            _set_pinned_visible_count(snap["cursor_count"])
            fig.canvas.draw_idle()

        def _push_history():
            """Merkt den aktuellen Zoom/Pan/Cursor-Zustand in der Vor/Zurück-
            Historie. Wird nach jeder abgeschlossenen Ansichtsänderung
            aufgerufen (Scroll-Zoom, Bereichsauswahl, Pan-Ende, gepinnter
            Cursor gesetzt, Zurücksetzen)."""
            snap = _view_snapshot()
            stack = view_history["stack"]
            idx   = view_history["index"]
            if idx >= 0 and stack[idx] == snap:
                return
            del stack[idx + 1:]
            stack.append(snap)
            view_history["index"] = len(stack) - 1

        def _history_back():
            if view_history["index"] > 0:
                view_history["index"] -= 1
                _restore_view_snapshot(view_history["stack"][view_history["index"]])

        def _history_forward():
            if view_history["index"] < len(view_history["stack"]) - 1:
                view_history["index"] += 1
                _restore_view_snapshot(view_history["stack"][view_history["index"]])

        def _apply_cursor_to_axis(ax, x_target):
            """Zeigt den Cursor (Fadenkreuz + Annotation) in ax am nächsten
            Datenpunkt zu x_target an."""
            series_list = _get_series_list(ax)
            if not series_list:
                return
            xdata0, ydata0 = series_list[0][:2]
            x_arr0 = np.array(xdata0)
            if len(x_arr0) == 0:
                return
            idx0   = int(np.argmin(np.abs(x_arr0 - x_target)))
            x_snap = x_arr0[idx0]
            y_snap = np.array(ydata0)[idx0]

            vlines[ax].set_xdata([x_snap, x_snap])
            hlines[ax].set_ydata([y_snap, y_snap])
            vlines[ax].set_visible(True)
            hlines[ax].set_visible(True)

            ann_list = annotations[ax]
            if len(series_list) > 1:
                _yf = _group_box_yfracs(ax, len(ann_list))
                _left_x = _left_ann_x(ax)
                for series, ann, _yfrac in zip(series_list, ann_list, _yf):
                    _xd, _yd = series[:2]
                    _lbl     = series[2] if len(series) >= 3 else ""
                    _idx     = int(np.argmin(np.abs(np.array(_xd) - x_snap)))
                    _yv      = float(np.array(_yd)[_idx])
                    ann.set_text(f"{_lbl}\nx={x_snap:.3f}  y={_yv:.3f}")
                    ann.xy = (_left_x, _yfrac)
                    ann.set_visible(True)
            else:
                ann = ann_list[0]
                ann.set_text(f"x={x_snap:.3f}\ny={y_snap:.3f}")
                ann.xy = (x_snap, y_snap)
                ann.set_visible(True)

        def _hide_cursor_on_axis(ax):
            vlines[ax].set_visible(False)
            hlines[ax].set_visible(False)
            for _a in annotations[ax]:
                _a.set_visible(False)

        def _next_pinned_color():
            """Jeweils zwei aufeinanderfolgende Klicks (=Cursor-Paare) teilen sich
            dieselbe Farbe, danach wechselt die Farbe."""
            pair_idx = len(pinned_batches) // 2
            return pinned_color_cycle[pair_idx % len(pinned_color_cycle)]

        def _pinned_count_on_axis(ax):
            return sum(1 for batch in pinned_batches for (a, _v, _a2, _a3) in batch if a is ax)

        def _place_pinned_cursor(ax, x_target, color):
            """Setzt einen bleibenden Cursor (Linie + Wert-Label) in ax am
            nächsten Datenpunkt zu x_target. Bei Gruppen-Plots (mehrere
            überlagerte Signale in einer Achse) wird der Strich dick +
            nummeriert (kleiner Kreis im Plot), die Wertetabelle selbst
            entsteht als Tkinter-Karte im cursor_panel (siehe
            _renumber_pinned_cursors/_rebuild_cursor_panel) - im Plot selbst
            ist dafür kein Platz, sobald eine Gruppe viele Signale hat. Gibt
            (vline, ann, group_info) zurück (ann und group_info sind je nach
            Fall der jeweils andere None), oder None wenn ax keine Daten hat."""
            series_list = _get_series_list(ax)
            if not series_list:
                return None
            x_arr0 = np.array(series_list[0][0])
            if len(x_arr0) == 0:
                return None
            idx0     = int(np.argmin(np.abs(x_arr0 - x_target)))
            x_snap   = x_arr0[idx0]
            is_group = len(series_list) > 1

            vline = ax.axvline(
                x=x_snap, color=color,
                linestyle=Cfg.Colors.CURSOR_LINESTYLE,
                linewidth=Cfg.Colors.CURSOR_LINEWIDTH * (2.5 if is_group else 1.0),
                alpha=Cfg.Colors.CURSOR_ALPHA,
            )

            if is_group:
                # Knapp OBERHALB des oberen Achsenrands, mit kleinem Abstand
                # zur Linie darunter (xytext=offset points, direkt über der
                # Linie zentriert statt die Linie zu berühren/durchzuschneiden).
                number_ann = ax.annotate(
                    '', xy=(x_snap, 1.0), xytext=(0, 4), textcoords='offset points',
                    xycoords=blended_transform_factory(ax.transData, ax.transAxes),
                    ha='center', va='bottom', fontsize=Cfg.Fonts.Plots.LEGEND + 1,
                    color=color, fontweight='bold',
                    bbox=dict(boxstyle='circle', facecolor=Cfg.Colors.ANNOTATION_BG,
                              edgecolor=color, alpha=0.9, pad=0.15),
                    annotation_clip=False, zorder=7,
                )
                group_info = {"number_ann": number_ann, "color": color, "title": ax.get_title()}
                return vline, None, group_info

            y_snap = np.array(series_list[0][1])[idx0]
            y_frac = 0.97 - (_pinned_count_on_axis(ax) % 6) * 0.08
            blend  = blended_transform_factory(ax.transData, ax.transAxes)
            ann = ax.annotate(
                f"x={x_snap:.3f}\ny={y_snap:.3f}",
                xy=(x_snap, y_frac), xycoords=blend,
                xytext=(6, 0), textcoords='offset points',
                ha='left', va='top', fontsize=Cfg.Fonts.Plots.LEGEND,
                color=color,
                bbox=dict(boxstyle='round', facecolor=Cfg.Colors.ANNOTATION_BG,
                          edgecolor=color, alpha=Cfg.Colors.ANNOTATION_BOX_ALPHA),
                annotation_clip=False,
            )
            return vline, ann, None

        def _renumber_pinned_cursors():
            """Nummeriert die sichtbaren gepinnten Gruppen-Cursor pro Achse neu
            (1,2,3,...), aktualisiert die Nummer-Kreise im Plot und baut das
            cursor_panel (Tkinter, unabhängig von der Subplot-Höhe) neu auf.
            Wird nach jeder Änderung der sichtbaren Cursor aufgerufen (neuer
            Klick, Vor/Zurück, Zurücksetzen)."""
            per_axis_index = {}
            panel_entries = []
            for batch_idx, batch in enumerate(pinned_batches):
                visible = batch_idx < pinned_state["visible"]
                for _ax_b, vline, _ann, group_info in batch:
                    if group_info is None:
                        continue  # kein Gruppen-Plot - normale Box, keine Nummer/Karte
                    number_ann = group_info["number_ann"]
                    if not visible:
                        number_ann.set_visible(False)
                        continue
                    i = per_axis_index.get(_ax_b, 0)
                    per_axis_index[_ax_b] = i + 1
                    number_ann.set_text(_circled_number(i + 1))
                    number_ann.set_visible(True)
                    x_snap = vline.get_xdata()[0]
                    panel_entries.append((i + 1, group_info["color"], group_info["title"], _ax_b, x_snap))
            _rebuild_cursor_panel(panel_entries)

        # --- Event Handler ---

        def on_move(event):
            if pan_state["ax"] is not None:
                if event.x is None or event.y is None:
                    return
                for a, (xlim0, ylim0) in pan_state["limits"].items():
                    inv            = a.transData.inverted()
                    x0_data, y0_data = inv.transform((pan_state["x0_px"], pan_state["y0_px"]))
                    x1_data, y1_data = inv.transform((event.x, event.y))
                    dx_data = x0_data - x1_data
                    dy_data = y0_data - y1_data
                    a.set_xlim(xlim0[0] + dx_data, xlim0[1] + dx_data)
                    a.set_ylim(ylim0[0] + dy_data, ylim0[1] + dy_data)
                fig.canvas.draw_idle()
                return

            if event.inaxes is None or event.xdata is None:
                return
            ax   = event.inaxes
            if ax not in signal_data:
                return
            best = _find_best_snap(ax, event)
            if best is None:
                return

            x_snap = best["x"]
            y_snap = best["y"]

            synced_axes = _get_synced_axes(ax)

            if hover_state["x"] == x_snap and hover_state["y"] == y_snap and hover_state["ax"] == ax:
                return

            for stale_ax in hover_state["axes"] - synced_axes:
                _hide_cursor_on_axis(stale_ax)

            hover_state["ax"]   = ax
            hover_state["x"]    = x_snap
            hover_state["y"]    = y_snap
            hover_state["axes"] = synced_axes

            vlines[ax].set_xdata([x_snap, x_snap])
            hlines[ax].set_ydata([y_snap, y_snap])
            vlines[ax].set_visible(True)
            hlines[ax].set_visible(True)

            series_list = _get_series_list(ax)
            ann_list    = annotations[ax]
            if len(series_list) > 1:
                _yf = _group_box_yfracs(ax, len(ann_list))
                _left_x = _left_ann_x(ax)
                for series, ann, _yfrac in zip(series_list, ann_list, _yf):
                    _xd, _yd   = series[:2]
                    _lbl       = series[2] if len(series) >= 3 else ""
                    _idx       = int(np.argmin(np.abs(np.array(_xd) - x_snap)))
                    _yv        = float(np.array(_yd)[_idx])
                    _is_active = bool(best["label"]) and _lbl == best["label"]
                    ann.set_text(f"{_lbl}\nx={x_snap:.3f}  y={_yv:.3f}")
                    ann.xy = (_left_x, _yfrac)
                    # Fett + minimale Größenzunahme + dickerer Rahmen + leichter
                    # Farbtint statt Deckkraft-Sprung - dezent, kein Riesensprung.
                    ann.set_fontweight('bold' if _is_active else 'normal')
                    ann.set_fontsize(Cfg.Fonts.Plots.LEGEND - 2 + (0.5 if _is_active else 0))
                    _bbox_patch = ann.get_bbox_patch()
                    if _bbox_patch is not None:
                        _bbox_patch.set_linewidth(1.4 if _is_active else 1.0)
                        if _is_active:
                            _bbox_patch.set_facecolor(_tint_color(_bbox_patch.get_edgecolor()))
                        else:
                            _bbox_patch.set_facecolor(Cfg.Colors.ANNOTATION_BG)
                    ann.set_zorder(6 if _is_active else 5)
                    ann.set_visible(True)
            else:
                ann   = ann_list[0]
                _pre  = f"{best['label']} | " if best["label"] else ""
                ann.set_text(f"{_pre}x={x_snap:.3f}\ny={y_snap:.3f}")
                ann.xy = (x_snap, y_snap)
                ann.set_visible(True)

            # --- Cursor synchron in den übrigen Achsen der Gruppe anzeigen ---
            for other_ax in synced_axes:
                if other_ax is ax:
                    continue
                _apply_cursor_to_axis(other_ax, x_snap)

            fig.canvas.draw_idle()

        def on_click(event):
            if event.inaxes is None or event.xdata is None or event.button != 1:
                return

            ax   = event.inaxes
            if ax not in signal_data:
                return
            best = _find_best_snap(ax, event)
            if best is None:
                return

            if multi_cursor_var is not None and multi_cursor_var.get():
                # Falls vorher "Zurück" gedrückt wurde, verwirft ein neuer Klick
                # die dadurch ausgeblendeten "Zukunfts"-Cursor endgültig (wie
                # bei Zoom/Pan-Historie mit neuer Aktion nach einem Rücksprung).
                if pinned_state["visible"] < len(pinned_batches):
                    for batch in pinned_batches[pinned_state["visible"]:]:
                        for _ax, vline, ann, group_info in batch:
                            vline.remove()
                            if ann is not None:
                                ann.remove()
                            if group_info is not None:
                                group_info["number_ann"].remove()
                    del pinned_batches[pinned_state["visible"]:]

                color = _next_pinned_color()
                batch = []
                for target_ax in _get_synced_axes(ax):
                    placed = _place_pinned_cursor(target_ax, best["x"], color)
                    if placed is not None:
                        vline, ann, group_info = placed
                        batch.append((target_ax, vline, ann, group_info))
                pinned_batches.append(batch)
                pinned_state["visible"] = len(pinned_batches)
                _renumber_pinned_cursors()
                _push_history()
                fig.canvas.draw_idle()
                return

            start_x                = selection_start.get(ax)
            start_line, end_line   = selection_lines[ax]
            start_dot, end_dot     = selection_markers[ax]
            is_group               = len(_get_series_list(ax)) > 1

            if start_x is None:
                selection_start[ax]   = best["x"]
                selection_start_y[ax] = best["y"]
                start_line.set_xdata([best["x"], best["x"]])
                start_line.set_visible(True)
                end_line.set_visible(False)
                if is_group:
                    # Wie beim gepinnten Cursor: dicker Strich + eingekreiste
                    # Nummer im Plot, Wertetabelle als Karte im cursor_panel -
                    # statt der einfachen Box im Plot.
                    start_dot.set_visible(False)
                    end_dot.set_visible(False)
                    _clear_selection_cards(ax, "end")
                    num_start, num_end = selection_group_numbers[ax]
                    # xytext=(0, 4 pt)/textcoords='offset points' bei der
                    # Erstellung sorgt dafür, dass die Textposition bei jedem
                    # .xy-Update automatisch live neu berechnet wird (anders
                    # als ohne xytext, wo matplotlib die Textposition beim
                    # ersten Zeichnen einfriert).
                    num_start.xy = (best["x"], 1.0)
                    num_start.set_text(_circled_number(1))
                    num_start.set_visible(True)
                    num_end.set_visible(False)
                    _update_selection_card(ax, "start", 1, Cfg.Colors.CURSOR_SECONDARY_COLOR, best["x"])
                else:
                    start_dot.set_text(f"Start\nx={best['x']:.3f}\ny={best['y']:.3f}")
                    start_dot.xy = (best["x"], best["y"])
                    start_dot.set_visible(True)
                    end_dot.set_visible(False)
                fig.canvas.draw_idle()
                return

            x0, x1             = sorted([start_x, best["x"]])
            y_at_x0             = selection_start_y.get(ax, best["y"])
            selection_start[ax] = None
            start_line.set_xdata([x0, x0])
            end_line.set_xdata([x1, x1])
            start_line.set_visible(True)
            end_line.set_visible(True)
            if is_group:
                num_start, num_end = selection_group_numbers[ax]
                num_start.xy = (x0, 1.0)
                num_start.set_text(_circled_number(1))
                num_start.set_visible(True)
                num_end.xy = (x1, 1.0)
                num_end.set_text(_circled_number(2))
                num_end.set_visible(True)
                _update_selection_card(ax, "start", 1, Cfg.Colors.CURSOR_SECONDARY_COLOR, x0)
                _update_selection_card(ax, "end", 2, Cfg.Colors.CURSOR_PRIMARY_COLOR, x1)
            else:
                start_dot.set_text(f"Start\nx={x0:.3f}\ny={y_at_x0:.3f}")
                start_dot.xy = (x0, y_at_x0)
                start_dot.set_visible(True)
                end_dot.set_text(f"End\nx={best['x']:.3f}\ny={best['y']:.3f}")
                end_dot.xy = (best["x"], best["y"])
                end_dot.set_visible(True)

            if range_selected_callback:
                allow = True
                if selection_filter is not None:
                    try:
                        allow = selection_filter(ax)
                    except Exception:
                        allow = False
                if allow:
                    widget = getattr(fig.canvas, "get_tk_widget", None)
                    if widget:
                        fig.canvas.get_tk_widget().after(0, lambda: range_selected_callback(x0, x1, ax))
                    else:
                        range_selected_callback(x0, x1, ax)

            y_values = []
            for series in _get_series_list(ax):
                xdata, ydata = series[:2]
                x_arr = np.array(xdata)
                y_arr = np.array(ydata)
                mask  = (x_arr >= x0) & (x_arr <= x1)
                if np.any(mask):
                    y_values.append(y_arr[mask])

            if y_values:
                y_concat       = np.concatenate(y_values)
                y_min, y_max   = PlotManager._apply_axis_margin(float(np.min(y_concat)), float(np.max(y_concat)))
            else:
                y_min, y_max   = ax.get_ylim()

            new_xlim = list(PlotManager._apply_axis_margin(x0, x1))
            new_ylim = [y_min, y_max]
            _apply_sync_or_single(ax, new_xlim, new_ylim)

            if is_group:
                # Nach dem Reinzoomen (2. Klick bei "Einzeln") ist die Auswahl
                # abgeschlossen - Strich/Zahl im Plot und Karte im
                # "Gesetzte Cursor"-Panel wieder ausblenden, statt sie stehen
                # zu lassen (Panel soll nur sichtbar sein, solange tatsächlich
                # ein Cursor "gesetzt" ist).
                start_line.set_visible(False)
                end_line.set_visible(False)
                num_start.set_visible(False)
                num_end.set_visible(False)
                _clear_selection_cards(ax)

            _push_history()
            fig.canvas.draw_idle()

        def on_scroll(event):
            ax = event.inaxes
            if ax is None:
                return
            scale  = 1.2 if event.button == 'down' else 0.8
            xdata  = event.xdata
            ydata  = event.ydata
            if xdata is None or ydata is None:
                return

            xlim     = ax.get_xlim()
            ylim     = ax.get_ylim()
            new_xlim = [xdata - (xdata - xlim[0]) * scale, xdata + (xlim[1] - xdata) * scale]
            new_ylim = [ydata - (ydata - ylim[0]) * scale, ydata + (ylim[1] - ydata) * scale]
            _apply_sync_or_single(ax, new_xlim, new_ylim)
            _push_history()
            fig.canvas.draw_idle()

        def on_leave(event):
            ax = event.inaxes
            if ax is None:
                return
            if ax in vlines and hover_state["ax"] == ax:
                for synced_ax in hover_state["axes"]:
                    _hide_cursor_on_axis(synced_ax)
                hover_state.update({"ax": None, "x": None, "y": None, "axes": set()})
            fig.canvas.draw_idle()

        def on_pan_press(event):
            """Startet das Pannen (Verschieben des sichtbaren Ausschnitts) bei
            gedrückter rechter Maustaste - Zusatzoption neben Fadenkreuz und
            Zwei-Klick-Bereichsauswahl (linke Maustaste, unverändert)."""
            if event.button != 3 or event.inaxes is None:
                return
            ax = event.inaxes
            if ax not in signal_data:
                return
            pan_state["ax"]     = ax
            pan_state["x0_px"]  = event.x
            pan_state["y0_px"]  = event.y
            pan_state["limits"] = {
                a: (a.get_xlim(), a.get_ylim()) for a in _get_synced_axes(ax)
            }

        def on_pan_release(event):
            if event.button == 3:
                was_panning = pan_state["ax"] is not None
                pan_state["ax"]     = None
                pan_state["limits"] = None
                if was_panning:
                    _push_history()

        def reset_selection():
            for ax in axes:
                selection_start[ax] = None
                start_line, end_line = selection_lines[ax]
                start_line.set_visible(False)
                end_line.set_visible(False)
                start_dot, end_dot = selection_markers[ax]
                start_dot.set_visible(False)
                end_dot.set_visible(False)
                if ax in selection_group_numbers:
                    num_start, num_end = selection_group_numbers[ax]
                    num_start.set_visible(False)
                    num_end.set_visible(False)
                _clear_selection_cards(ax)
                if ax in original_limits:
                    xlim, ylim = original_limits[ax]
                    ax.set_xlim(xlim)
                    ax.set_ylim(ylim)
            # Weich ausblenden statt Artists zu löschen, damit "Vor" nach dem
            # Zurücksetzen die gepinnten Cursor wieder herstellen kann.
            _set_pinned_visible_count(0)
            _push_history()
            fig.canvas.draw_idle()
            if range_cleared_callback:
                widget = getattr(fig.canvas, "get_tk_widget", None)
                if widget:
                    fig.canvas.get_tk_widget().after(0, range_cleared_callback)
                else:
                    range_cleared_callback()

        fig.canvas.mpl_connect('motion_notify_event',  on_move)
        fig.canvas.mpl_connect('axes_leave_event',     on_leave)
        fig.canvas.mpl_connect('scroll_event',         on_scroll)
        fig.canvas.mpl_connect('button_press_event',   on_click)
        fig.canvas.mpl_connect('button_press_event',   on_pan_press)
        fig.canvas.mpl_connect('button_release_event', on_pan_release)
        fig._reset_zoom_selection   = reset_selection
        fig._history_back          = _history_back
        fig._history_forward       = _history_forward
        fig._history_can_go_back    = lambda: view_history["index"] > 0
        fig._history_can_go_forward = lambda: view_history["index"] < len(view_history["stack"]) - 1
        _push_history()

    # --------------------------------------------------------
    #  ZEITBEREICH DIALOG
    # --------------------------------------------------------

    @staticmethod
    def show_zeitbereich_dialog(
        parent, t_max, callback,
        title="Zeitbereich auswählen",
        selected_signal=None,
        is_filtered=False,
        filter_info=None,
        analyse_typen=None,
        timestamps=None
    ):
        """
        Zentraler Zeitbereich-Dialog mit Notebook für mehrere Analyse-Typen.
        Args:
            parent:          Parent-Fenster
            t_max:           Maximale Zeit (für Voreinstellung Ende-Zeit)
            callback:        Funktion die mit dict {analyse_typ: [(start, ende), ...]} aufgerufen wird
            title:           Dialog-Titel
            selected_signal: Name des ausgewählten Signals (optional)
            is_filtered:     Ob gefiltert wird
            filter_info:     Dict mit 'type', 'order', 'characteristic' (optional)
            analyse_typen:   Liste von Analyse-Typen für Tabs, z.B. ["AVG", "RMS", "FFT"]
            timestamps:      Array echter Zeitstempel (parallel zu t), oder None
        """
        if analyse_typen is None:
            analyse_typen = ["Analyse"]

        uhrzeit_verfuegbar = timestamps is not None and len(timestamps) > 0
        start_ts = pd.Timestamp(timestamps[0]) if uhrzeit_verfuegbar else None
        logger.info(
            "[DEBUG-ZEITBEREICH] show_zeitbereich_dialog: uhrzeit_verfuegbar=%s, start_ts=%s",
            uhrzeit_verfuegbar, start_ts
        )

        def parse_zeit_eingabe(text):
            """Interpretiert Sekunden ('0.5') ODER Uhrzeit ('14:34:30') je nach Eingabe."""
            raw = text
            text = text.strip()
            if ":" in text:
                if not uhrzeit_verfuegbar:
                    logger.info("[DEBUG-ZEITBEREICH] parse_zeit_eingabe(%r) -> FEHLER: keine Zeitstempel verfuegbar", raw)
                    raise ValueError("Keine echten Zeitstempel verfügbar")
                eingabe_ts = pd.to_datetime(f"{start_ts.date()} {text.replace(',', '.')}")
                ergebnis = (eingabe_ts - start_ts).total_seconds()
                logger.info(
                    "[DEBUG-ZEITBEREICH] parse_zeit_eingabe(%r) -> Uhrzeit-Modus: eingabe_ts=%s, start_ts=%s, ergebnis(s)=%s",
                    raw, eingabe_ts, start_ts, ergebnis
                )
                return ergebnis
            ergebnis = float(text.replace(",", "."))
            logger.info("[DEBUG-ZEITBEREICH] parse_zeit_eingabe(%r) -> Sekunden-Modus: ergebnis(s)=%s", raw, ergebnis)
            return ergebnis

        dialog = tb.Toplevel(parent)
        dialog.title(title)
        dialog.transient(parent)
        dialog.grab_set()

        # --- Header ---
        header_frame = ttk.Frame(dialog)
        header_frame.pack(padx=10, pady=10, fill="x")

        if selected_signal:
            signal_length_text = f" ({t_max:.2f} s)" if t_max else ""
            if uhrzeit_verfuegbar and t_max:
                ende_ts = start_ts + pd.Timedelta(seconds=t_max)
                signal_length_text += f" | {start_ts.strftime('%H:%M:%S')} - {ende_ts.strftime('%H:%M:%S')}"
            ttk.Label(
                header_frame,
                text=f"Ausgewähltes Signal: {selected_signal}{signal_length_text}",
                font=("Arial", 10, "bold")
            ).pack(anchor="w")

        if uhrzeit_verfuegbar:
            ttk.Label(
                header_frame,
                text="Zeitbereich als Sekunden (z.B. 0.5) oder Uhrzeit (z.B. 14:34:30) eingeben"
            ).pack(anchor="w")

        if is_filtered and filter_info:
            filter_text = (
                f"Gefiltert: {filter_info.get('type', '-')}, "
                f"Ordnung: {filter_info.get('order', '-')}, "
                f"Charakteristik: {filter_info.get('characteristic', '-')}"
            )
            ttk.Label(header_frame, text=filter_text).pack(anchor="w")
        else:
            ttk.Label(header_frame, text=Cfg.Texts.DLG_UNFILTERED).pack(anchor="w")

        # --- Notebook ---
        notebook = ttk.Notebook(dialog)
        notebook.pack(padx=10, pady=10, fill="both", expand=True)
        tab_data = {}

        def create_tab(notebook, analyse_typ, t_max):
            """Erstellt einen Tab mit eigenem Scope für Variablen (löst Closure-Problem)."""
            tab_frame     = ttk.Frame(notebook)
            notebook.add(tab_frame, text=analyse_typ)

            this_ganzes_signal_var  = tk.BooleanVar(value=True)
            this_zeitbereich_felder = []

            checkbox_frame = ttk.Frame(tab_frame)
            checkbox_frame.pack(padx=10, pady=(10, 5))

            felder_frame = ttk.Frame(tab_frame)
            felder_frame.pack(padx=10, pady=5, fill="both", expand=True)

            plus_button = ttk.Button(tab_frame, text=Cfg.Texts.TIME_RANGE_ADD)
            plus_button.pack(pady=5)

            def toggle_felder():
                state = "disabled" if this_ganzes_signal_var.get() else "normal"
                for entry_start, entry_ende in this_zeitbereich_felder:
                    entry_start.config(state=state)
                    entry_ende.config(state=state)
                can_add = not this_ganzes_signal_var.get() and len(this_zeitbereich_felder) < 12
                plus_button.config(state="normal" if can_add else "disabled")

            def feld_hinzufuegen():
                if len(this_zeitbereich_felder) >= 12:
                    return
                zeile = len(this_zeitbereich_felder)

                row_frame = ttk.Frame(felder_frame)
                row_frame.pack(fill="x", pady=2)

                ttk.Label(row_frame, text=Cfg.Texts.TIME_RANGE_N.format(zeile + 1), width=15).pack(side=tk.LEFT)

                start_entry = ttk.Entry(row_frame, width=12)
                start_entry.insert(0, f"{zeile * 0.5:.1f}")
                start_entry.pack(side=tk.LEFT, padx=2)

                ttk.Label(row_frame, text="-").pack(side=tk.LEFT)

                ende_entry  = ttk.Entry(row_frame, width=12)
                ende_val    = min((zeile + 1) * 0.5, t_max) if t_max else (zeile + 1) * 0.5
                ende_entry.insert(0, f"{ende_val:.1f}")
                ende_entry.pack(side=tk.LEFT, padx=2)

                ttk.Label(row_frame, text=Cfg.Texts.UNIT_S).pack(side=tk.LEFT)
                this_zeitbereich_felder.append((start_entry, ende_entry))

                if len(this_zeitbereich_felder) >= 12:
                    plus_button.config(state="disabled")

            feld_hinzufuegen()
            plus_button.config(command=feld_hinzufuegen)

            ttk.Checkbutton(
                checkbox_frame,
                text="Ganzes Signal verwenden",
                variable=this_ganzes_signal_var,
                command=toggle_felder
            ).pack()

            toggle_felder()

            return {
                'ganzes_signal_var':   this_ganzes_signal_var,
                'zeitbereich_felder':  this_zeitbereich_felder,
            }

        for analyse_typ in analyse_typen:
            tab_data[analyse_typ] = create_tab(notebook, analyse_typ, t_max)

        # --- Berechnen ---
        def berechnen():
            result = {}
            for analyse_typ, data in tab_data.items():
                zeitbereiche = []
                if data['ganzes_signal_var'].get():
                    zeitbereiche.append((None, None))
                else:
                    for start_entry, ende_entry in data['zeitbereich_felder']:
                        try:
                            start = parse_zeit_eingabe(start_entry.get())
                            ende  = parse_zeit_eingabe(ende_entry.get())
                            zeitbereiche.append((start, ende))
                        except ValueError:
                            continue
                result[analyse_typ] = zeitbereiche

            logger.info("[DEBUG-ZEITBEREICH] berechnen(): finales result=%s", result)

            protocol_logger.info(
                "PLOT_TIME_RANGE title=%s | signal=%s | analyses=%s | ranges=%s",
                title, selected_signal, analyse_typen, result,
            )
            dialog.destroy()
            callback(result)

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="OK",        command=berechnen,       width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=dialog.destroy,  width=10).pack(side=tk.LEFT, padx=5)

        center_window(dialog)

    # --------------------------------------------------------
    #  SPEICHERN – Zeitbereich / Frequenzbereich / Übersicht
    # --------------------------------------------------------

    @staticmethod
    def save_time_domain_plot(t, signal, header, unit, time, figure_number, save_path):
        """Speichert einen Zeitbereichs-Plot als PNG."""
        filename = Cfg.Export.TIME_FMT.format(header=header)
        plt.figure(figure_number, figsize=Cfg.Layout.Figure.FIG_SIZE_SINGLE, dpi=100, facecolor="white")
        t_interp, signal_interp = PlotManager._interpolate_signal(t, signal, factor=5)
        plt.plot(t_interp, signal_interp, linewidth=1.5, color=Cfg.Colors.SIGNAL_ORIGINAL)
        ax = plt.gca()
        PlotManager._apply_fine_grid(ax)
        plt.title(f"{header} [{unit}] - {Cfg.Texts.STARTTIME_LABEL}: {time}", fontsize=Cfg.Fonts.Plots.AXIS_TITLE)
        plt.legend([header], fontsize=Cfg.Fonts.Plots.LEGEND, loc="upper right")
        plt.xlabel(Cfg.AxisLabels.TIME,            fontsize=Cfg.Fonts.Plots.LEGEND)
        plt.ylabel(f"{header} [{unit}]",           fontsize=Cfg.Fonts.Plots.LEGEND)
        plt.savefig(f"{save_path}/{filename}", dpi=300, bbox_inches="tight", format="png")
        plt.close()

    @staticmethod
    def save_frequency_domain_plot(f, sig_abs, sig_arg, header, unit, figure_number, save_path):
        """Speichert einen Frequenzbereichs-Plot (Amplitude + Phase) als PNG."""
        plt.figure(figure_number, figsize=Cfg.Layout.Figure.FIG_SIZE_DOUBLE)

        plt.subplot(2, 1, 1)
        plt.plot(f, sig_abs,
                 color='b',
                 linestyle=Cfg.Defaults.FILTER_RESPONSE_LINESTYLE,
                 linewidth=Cfg.Defaults.FILTER_RESPONSE_LINEWIDTH)
        plt.grid(True, linestyle=Cfg.Colors.GRID_LINESTYLE, alpha=Cfg.Colors.GRID_ALPHA, color=Cfg.Colors.GRID_COLOR)
        plt.title(f"{header} [{unit}]")
        plt.xlabel(Cfg.AxisLabels.FREQ)
        plt.ylabel(Cfg.AxisLabels.AMP)
        if Cfg.Defaults.FFT_LOG_SCALE:
            plt.xscale('log')
        plt.legend([f"{header} [{unit}]"])

        plt.subplot(2, 1, 2)
        plt.plot(f, np.angle(np.exp(1j * sig_arg), deg=True),
                 color='r',
                 linestyle=Cfg.Defaults.FILTER_RESPONSE_LINESTYLE,
                 linewidth=Cfg.Defaults.FILTER_RESPONSE_LINEWIDTH)
        plt.grid(True, linestyle=Cfg.Colors.GRID_LINESTYLE, alpha=Cfg.Colors.GRID_ALPHA, color=Cfg.Colors.GRID_COLOR)
        plt.xlabel(Cfg.AxisLabels.FREQ)
        plt.ylabel(Cfg.AxisLabels.PHASE)
        if Cfg.Defaults.FFT_LOG_SCALE:
            plt.xscale('log')

        plt.tight_layout()
        filename = Cfg.Export.FREQ_FMT.format(header=header)
        plt.savefig(f"{save_path}/{filename}", dpi=300, bbox_inches="tight", format="png")
        plt.close()

    @staticmethod
    def save_overview_plot(t, signals, headers, units, time, save_path):
        """Speichert einen Übersichts-Plot mit allen Signalen als PNG."""
        num_signals = len(signals)
        plt.figure(109, figsize=Cfg.Layout.Figure.FIG_SIZE_OVERVIEW)
        for i, (sig, header, unit) in enumerate(zip(signals, headers, units)):
            plt.subplot(num_signals, 1, i + 1)
            t_interp, sig_interp = PlotManager._interpolate_signal(PlotManager.t_for_idx(t, i), sig, factor=5)
            plt.plot(t_interp, sig_interp, linewidth=1.5, color=Cfg.Colors.SIGNAL_ORIGINAL)
            ax = plt.gca()
            PlotManager._apply_fine_grid(ax)
            if i == 0:
                plt.title(f"{header} [{unit}] - {Cfg.Texts.STARTTIME_LABEL}: {time}", fontsize=Cfg.Fonts.Plots.AXIS_TITLE)
            plt.legend([f"{header} [{unit}]"], fontsize=Cfg.Fonts.Plots.LEGEND, loc="upper right")
            plt.ylabel(f"[{unit}]", fontsize=Cfg.Fonts.Plots.LEGEND)
        plt.xlabel(Cfg.AxisLabels.TIME, fontsize=Cfg.Fonts.Plots.LEGEND)
        plt.tight_layout()
        plt.savefig(f"{save_path}/{Cfg.Export.OVERVIEW}", dpi=300, bbox_inches="tight", format="png")
        plt.close()

    # --------------------------------------------------------
    #  PLOT-METHODEN
    # --------------------------------------------------------

    @staticmethod
    def plot_overview(fig, t, signals, headers, units):
        """Zeigt alle Signale als vertikalen Stapel in einem Figure."""
        filtered_data = [
            (i, signals[i], headers[i], units[i] if i < len(units) else '')
            for i, header in enumerate(headers)
            if header not in Cfg.Data.EXCLUDE_COLUMNS and i < len(signals)
        ]
        if not filtered_data:
            return

        filtered_indices, filtered_signals, filtered_headers, filtered_units = zip(*filtered_data)
        num_signals = len(filtered_signals)

        for plot_i, (orig_idx, sig, header, unit) in enumerate(
            zip(filtered_indices, filtered_signals, filtered_headers, filtered_units)
        ):
            ax = fig.add_subplot(num_signals, 1, plot_i + 1)
            t_interp, sig_interp = PlotManager._interpolate_signal(PlotManager.t_for_idx(t, orig_idx), sig, factor=5)
            ax.plot(t_interp, sig_interp, label=f"{header} [{unit}]",
                    linewidth=Cfg.Colors.LINEWIDTH_ORIGINAL, color=Cfg.Colors.SIGNAL_ORIGINAL)
            ax.set_ylabel(f"[{unit}]", fontsize=Cfg.Fonts.Plots.LEGEND)
            PlotManager._apply_fine_grid(ax)
            ax.legend(loc='upper right', fontsize=Cfg.Fonts.Plots.LEGEND, framealpha=0.4)
            ax.tick_params(labelsize=Cfg.Fonts.SMALL)
            if plot_i == num_signals - 1:
                ax.set_xlabel(Cfg.AxisLabels.TIME, fontsize=Cfg.Fonts.Plots.LEGEND)

        fig.suptitle(Cfg.Texts.OVERVIEW_SUPTITLE.format(num_signals), fontsize=Cfg.Fonts.Plots.PLOT_TITLE, fontweight='bold')
        fig.tight_layout(pad=1.0, h_pad=1.5, w_pad=1.0)
        fig.subplots_adjust(top=0.95, hspace=0.3)

    @staticmethod
    def plot_filter_response(fig, w, magnitude_db, phase_deg, filter_info):
        """Zeigt Amplituden- und Phasengang eines Filters."""
        if w is not None and magnitude_db is not None and phase_deg is not None:
            ax1 = fig.add_subplot(2, 1, 1)
            ax1.plot(w, magnitude_db,
                     color='b',
                     linestyle=Cfg.Defaults.FILTER_RESPONSE_LINESTYLE,
                     linewidth=Cfg.Defaults.FILTER_RESPONSE_LINEWIDTH)
            ax1.set_ylabel(Cfg.AxisLabels.MAGNITUDE_DB)
            ax1.set_title(
                f"{filter_info['characteristic'].capitalize()} "
                f"{filter_info['type']} - {filter_info['order']}. Ordnung"
            )
            ax1.grid(True, linestyle=Cfg.Colors.GRID_LINESTYLE, alpha=Cfg.Colors.GRID_ALPHA, color=Cfg.Colors.GRID_COLOR)
            if Cfg.Defaults.FFT_LOG_SCALE:
                ax1.set_xscale('log')
            ax1.set_xlim(1, filter_info['sample_rate'] / 2 if filter_info['sample_rate'] else 1000)

            ax2 = fig.add_subplot(2, 1, 2)
            ax2.plot(w, phase_deg,
                     color='r',
                     linestyle=Cfg.Defaults.FILTER_RESPONSE_LINESTYLE,
                     linewidth=Cfg.Defaults.FILTER_RESPONSE_LINEWIDTH)
            ax2.set_ylabel(Cfg.AxisLabels.PHASE)
            ax2.set_xlabel(Cfg.AxisLabels.FREQ)
            ax2.grid(True, linestyle=Cfg.Colors.GRID_LINESTYLE, alpha=Cfg.Colors.GRID_ALPHA, color=Cfg.Colors.GRID_COLOR)
            ax2.set_xlim(0, filter_info['sample_rate'] / 2 if filter_info['sample_rate'] else 1000)

            if filter_info['cutoff']:
                ax1.axvline(
                    x=filter_info['cutoff'],
                    color=Cfg.Colors.SIGNAL_FILTERED,
                    linestyle=Cfg.Colors.CURSOR_LINESTYLE,
                    alpha=0.7,
                    label=f"Grenzfrequenz: {filter_info['cutoff']} Hz"
                )
                ax2.axvline(
                    x=filter_info['cutoff'],
                    color=Cfg.Colors.SIGNAL_FILTERED,
                    linestyle=Cfg.Colors.CURSOR_LINESTYLE,
                    alpha=0.7
                )
                ax1.legend()
        else:
            ax = fig.add_subplot(1, 1, 1)
            ax.text(0.5, 0.5, Cfg.Texts.PLOT_EMPTY,
                    ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_xticks([])
            ax.set_yticks([])

        fig.tight_layout(pad=1.0, h_pad=1.5, w_pad=1.0)

    @staticmethod
    def plot_selected_signals(
        parent_window, selected_headers, signals, units, t, dt,
        header_to_signal_idx, show_avg, show_rms, show_diff,
        show_integral, use_filtered, filter_manager
    ):
        """Öffnet ein Overlay-Fenster mit mehreren überlagerten Signalen."""
        if not selected_headers:
            logger.info("Keine Signale ausgewählt")
            return

        overlay_window = tb.Toplevel(parent_window)
        overlay_window.title("Überlagerte Signale")

        plot_frame = ttk.Frame(overlay_window)
        plot_frame.pack(fill=tk.BOTH, expand=True)

        fig       = plt.Figure(figsize=Cfg.Layout.Figure.FIG_SIZE_OVERVIEW)
        use_bottom = show_diff or show_integral
        ax_top    = fig.add_subplot(211) if use_bottom else fig.add_subplot(111)
        ax_bottom = fig.add_subplot(212, sharex=ax_top) if use_bottom else None
        colors    = plt.cm.get_cmap('Set1', len(selected_headers))

        for i, hdr in enumerate(selected_headers):
            sig_idx = header_to_signal_idx.get(hdr)
            if sig_idx is None or sig_idx >= len(signals):
                continue
            sig  = signals[sig_idx]
            unit = units[sig_idx] if sig_idx < len(units) else ""
            used = sig

            if use_filtered and filter_manager is not None:
                try:
                    used = filter_manager.apply_filter(sig)
                    ax_top.plot(t, sig,  color=colors(i), alpha=0.30, label=f"{hdr} [{unit}] (Original)")
                    ax_top.plot(t, used, color=colors(i), linewidth=1.8,
                                label=f"{hdr} [{unit}] (Gefiltert: {filter_manager.filter_type})")
                except Exception:
                    ax_top.plot(t, sig, color=colors(i), linewidth=1.5, label=f"{hdr} [{unit}]")
            else:
                ax_top.plot(t, sig, color=colors(i), linewidth=1.5, label=f"{hdr} [{unit}]")

            if show_avg:
                try:
                    ax_top.axhline(float(np.nanmean(used)),
                                   color=Cfg.Colors.SIGNAL_AVG, linestyle=Cfg.Colors.LINESTYLE_AVG, alpha=0.5, linewidth=1.2)
                except Exception as e:
                    logger.debug("AVG-Linie für '%s' konnte nicht gezeichnet werden: %s", hdr, e)
            if show_rms:
                try:
                    ax_top.axhline(float(np.sqrt(np.nanmean(used**2))),
                                   color=Cfg.Colors.SIGNAL_RMS, linestyle=Cfg.Colors.LINESTYLE_RMS, alpha=0.6, linewidth=1.2)
                except Exception as e:
                    logger.debug("RMS-Linie für '%s' konnte nicht gezeichnet werden: %s", hdr, e)

        ax_top.set_title(Cfg.Texts.OVERLAY_TITLE)
        ax_top.set_xlabel(Cfg.AxisLabels.TIME)
        ax_top.set_ylabel(Cfg.AxisLabels.AMP)
        ax_top.grid(True, linestyle=Cfg.Colors.GRID_LINESTYLE, alpha=Cfg.Colors.GRID_ALPHA, color=Cfg.Colors.GRID_COLOR)
        ax_top.legend(loc="upper right", fontsize=Cfg.Fonts.Plots.LEGEND)

        if use_bottom and ax_bottom is not None:
            for i, hdr in enumerate(selected_headers):
                sig_idx = header_to_signal_idx.get(hdr)
                if sig_idx is None or sig_idx >= len(signals):
                    continue
                sig  = signals[sig_idx]
                unit = units[sig_idx] if sig_idx < len(units) else ""
                used = sig
                if use_filtered and filter_manager is not None:
                    try:
                        used = filter_manager.apply_filter(sig)
                    except Exception:
                        used = sig

                if show_diff:
                    try:
                        diff      = np.gradient(used, dt)
                        unit_diff = Cfg.AxisLabels.diff(unit) if unit else "1/s"
                        ax_bottom.plot(t, diff, color=colors(i), alpha=0.85,
                                       linestyle=Cfg.Colors.LINESTYLE_DIFF,
                                       label=f"d({hdr})/dt [{unit_diff}]")
                    except Exception as e:
                        logger.debug("Differential-Plot für '%s' konnte nicht gezeichnet werden: %s", hdr, e)

                if show_integral:
                    try:
                        integ    = np.cumsum(used) * dt
                        unit_int = Cfg.AxisLabels.integral(unit) if unit else "unit·s"
                        ax_bottom.plot(t, integ, color=colors(i), alpha=0.90,
                                       linestyle=Cfg.Colors.LINESTYLE_INT,
                                       label=f"∫{hdr} dt [{unit_int}]")
                    except Exception as e:
                        logger.debug("Integral-Plot für '%s' konnte nicht gezeichnet werden: %s", hdr, e)

            ax_bottom.set_title(Cfg.Texts.DIFF_INT_TITLE)
            ax_bottom.set_xlabel("Zeit [s]")
            ax_bottom.set_ylabel("Wert")
            ax_bottom.legend(loc="lower right", fontsize=Cfg.Fonts.Plots.LEGEND)

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)

        # Speichere ursprüngliche Achsen-Limits für Reset
        original_limits = {}
        for ax in fig.get_axes():
            original_limits[ax] = (ax.get_xlim(), ax.get_ylim())

        def home_with_reset(*args, **kwargs):
            # Stelle ursprüngliche Limits wieder her
            for ax, (xlim, ylim) in original_limits.items():
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)
            try:
                fig.tight_layout(pad=1.0, h_pad=1.5, w_pad=1.0)
            except Exception as e:
                logger.debug("tight_layout beim Zurücksetzen der Achsen fehlgeschlagen: %s", e)
            canvas.draw_idle()

        toolbar.home = home_with_reset

        toolbar.pack(side=tk.RIGHT)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        def on_canvas_resize(event=None):
            try:
                fig.tight_layout(pad=1.0, h_pad=1.5, w_pad=1.0)
                canvas.draw_idle()
            except Exception as e:
                logger.debug("Canvas-Resize fehlgeschlagen: %s", e)

        canvas_widget.bind("<Configure>", on_canvas_resize)

        canvas.draw()
        center_window(overlay_window)

    @staticmethod
    def plot_signal_analysis(
        fig, t, original_signal, filtered_signal, signal_name, unit, dt,
        show_original=True, show_filtered=False, filter_type=None,
        show_avg=False, show_rms=False, show_diff=False, show_integral=False,
        show_amp=False, show_phase=False,
        f_axis=None, amp=None, phase=None,
        filter_order=None, filter_characteristic=None
    ):
        """Vollständige Signalanalyse-Darstellung: Zeitbereich + optionale FFT-Plots."""

        rows = 1 + int(show_amp) + int(show_phase)
        gs   = fig.add_gridspec(
            nrows=max(rows, 1), ncols=1,
            height_ratios=[2] + [1] * (max(rows, 1) - 1),
            hspace=0.35
        )
        ax1      = fig.add_subplot(gs[0, 0])
        drew_any = False

        if show_original and original_signal is not None:
            ax1.plot(t, original_signal, label="Original", alpha=0.8, color=Cfg.Colors.SIGNAL_ORIGINAL)
            drew_any = True

        if show_filtered and filtered_signal is not None and filter_type != Cfg.Defaults.FILTER_TYP:
            ax1.plot(t, filtered_signal,
                     label=f"Gefiltert ({filter_type})",
                     color=Cfg.Colors.SIGNAL_FILTERED, linewidth=2)
            drew_any = True

        chosen = (
            filtered_signal
            if (show_filtered and filter_type != Cfg.Defaults.FILTER_TYP and filtered_signal is not None)
            else original_signal
        )

        if show_avg and chosen is not None:
            avg_val = float(np.nanmean(chosen))
            ax1.axhline(avg_val, color=Cfg.Colors.SIGNAL_AVG,
                        linestyle=Cfg.Colors.LINESTYLE_AVG, linewidth=2,
                        label=f"AVG = {avg_val:.6g} {unit}")
            drew_any = True

        if show_rms and chosen is not None:
            rms_val = float(np.sqrt(np.nanmean(chosen**2)))
            ax1.axhline(rms_val, color=Cfg.Colors.SIGNAL_RMS,
                        linestyle=Cfg.Colors.LINESTYLE_RMS, linewidth=1.6,
                        label=f"RMS = {rms_val:.6g} {unit}")
            drew_any = True

        if (show_diff or show_integral) and chosen is not None and dt is not None:
            ax1b = ax1.twinx()
            if show_diff:
                diff      = np.gradient(chosen, dt)
                unit_diff = f"{unit}/s" if unit else "1/s"
                ax1b.plot(t, diff, color=Cfg.Colors.SIGNAL_DIFF, alpha=0.8,
                          linestyle=Cfg.Colors.LINESTYLE_DIFF, label=f"d/dt [{unit_diff}]")
                ax1b.set_ylabel(unit_diff)
            if show_integral:
                integ    = np.cumsum(chosen) * dt
                unit_int = f"{unit}·s" if unit else "unit·s"
                ax1b.plot(t, integ, color=Cfg.Colors.SIGNAL_INT, alpha=0.8,
                          linestyle=Cfg.Colors.LINESTYLE_INT, label=f"Integral [{unit_int}]")
                ax1b.set_ylabel(unit_int)
            ax1b.legend(loc='lower right', fontsize=Cfg.Fonts.Plots.LEGEND)

        if not drew_any:
            ax1.text(0.5, 0.5, "Keine Zeitkurve ausgewählt", ha="center", va="center", transform=ax1.transAxes)

        ax1.set_title(f"{signal_name} [{unit}]", fontsize=Cfg.Fonts.Plots.AXIS_TITLE)
        ax1.set_xlabel(Cfg.AxisLabels.TIME)
        ax1.set_ylabel(f"[{unit}]", fontsize=Cfg.Fonts.Plots.LEGEND)
        ax1.grid(True)
        if drew_any:
            ax1.legend(loc='upper right', fontsize=Cfg.Fonts.Plots.LEGEND)

        row_cursor = 1

        if show_amp and f_axis is not None and amp is not None:
            ax2 = fig.add_subplot(gs[row_cursor, 0])
            ax2.plot(f_axis, amp)
            ax2.set_title(f"Frequenz Spektrum [{unit}]", fontsize=Cfg.Fonts.Plots.AXIS_TITLE)
            ax2.set_xlabel(Cfg.AxisLabels.FREQ)
            ax2.set_ylabel("Amplitude", fontsize=Cfg.Fonts.Plots.LEGEND)
            ax2.grid(True)
            if Cfg.Defaults.FFT_LOG_SCALE:
                ax2.set_xscale('log')
            row_cursor += 1

        if show_phase and f_axis is not None and phase is not None:
            ax3          = fig.add_subplot(gs[row_cursor, 0])
            filter_title = ""
            if show_filtered and filter_type != Cfg.Defaults.FILTER_TYP:
                if filter_order and filter_characteristic:
                    filter_title = f" (Gefiltert: {filter_type}, {filter_order}, {filter_characteristic})"
                else:
                    filter_title = f" (Gefiltert: {filter_type})"
            ax3.plot(f_axis, phase)
            ax3.set_title(f"Phase Spektrum{filter_title} [Grad]", fontsize=Cfg.Fonts.Plots.AXIS_TITLE)
            ax3.set_xlabel(Cfg.AxisLabels.FREQ)
            ax3.set_ylabel("Phase [Grad]", fontsize=Cfg.Fonts.Plots.LEGEND)
            ax3.grid(True)

        fig.set_constrained_layout(False)