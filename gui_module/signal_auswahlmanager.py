"""
Signal Auswahlmanager - Signalauswahl-Verwaltung
==================================================
Verwaltet das Signalauswahl-Fenster mit Listbox,
Gruppen-Management und Export-Funktionen.
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
import numpy as np
import ttkbootstrap as tb

# ============================================================
#  IMPORTS – Eigene Klassen
# ============================================================
from gui_module import meldungen as messagebox
from gui_module.plot_manager import PlotManager
from hilfsklassen.zentrales_logging import get_protocol_logger
from konfiguration import Cfg

# ============================================================
#  LOGGING
# ============================================================
logger          = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()


# ============================================================
#  KLASSE
# ============================================================
class SignalAuswahlManager:
    """Verwaltet das Signal-Auswahl-Fenster"""

    def __init__(self, gui_manager, plot_window_manager):

        # --- Referenzen ---
        self.gui                 = gui_manager
        self.plot_window_manager = plot_window_manager

        # --- UI-Elemente ---
        self.filter_char_button = None

    # --------------------------------------------------------
    #  FENSTER ÖFFNEN
    # --------------------------------------------------------

    def show_multi_signal_overlay_window(self, active_window=None):
        """Öffnet ein Fenster zur Auswahl beliebig vieler Signale und zeigt sie gemeinsam in einem Plot."""
        protocol_logger.info("OVERLAY_WINDOW_OPEN")

        # --- Bereits geöffnetes Fenster prüfen ---
        if active_window is not None:
            try:
                if active_window.winfo_exists():
                    return
            except Exception as e:
                logger.debug("Prüfung auf bereits geöffnetes Overlay-Fenster fehlgeschlagen: %s", e)
            active_window = None

        if not self.gui.signals or not self.gui.headers or self.gui.t is None:
            logger.info("Keine Daten verfügbar")
            return

        # --------------------------------------------------------
        #  DATEN VORBEREITEN
        # --------------------------------------------------------

        selectable_headers = [
            h for i, h in enumerate(self.gui.headers)
            if h not in Cfg.Data.EXCLUDE_COLUMNS and i < len(self.gui.signals)
        ]

        def get_unit(h):
            idx = self.gui.headers.index(h)
            return self.gui.units[idx].lower() if idx < len(self.gui.units) else ""

        selectable_headers.sort(key=get_unit)

        header_to_signal_idx = {
            h: self.gui.headers.index(h)
            for h in selectable_headers
            if self.gui.headers.index(h) < len(self.gui.signals)
        }

        unique_units  = sorted(set(
            self.gui.units[self.gui.headers.index(h)].strip()
            if self.gui.headers.index(h) < len(self.gui.units) else ""
            for h in selectable_headers
        ))
        # Dynamisch erzeugte Palette statt fester Farbliste: bei mehreren gleichzeitig
        # geladenen Dateien kommen leicht mehr unterschiedliche Einheiten zusammen,
        # als eine feste Liste Farben hatte - generate_unit_palette liefert immer
        # genau len(unique_units) paarweise unterscheidbare Farben, nie eine Dopplung.
        pastel_colors, accent_colors = Cfg.Colors.generate_unit_palette(len(unique_units))
        unit_colors = dict(zip(unique_units, pastel_colors))
        # Kräftigere Farben nur für die Legenden-Swatches - die pastelligen
        # unit_colors sind auf einem kleinen 14x14-Feld kaum zu unterscheiden.
        unit_legend_colors = dict(zip(unique_units, accent_colors))

        def _is_zero_signal(h):
            """Prüft, ob ein Signal über den gesamten Verlauf (nahezu) konstant 0 ist."""
            idx = self.gui.headers.index(h)
            if idx >= len(self.gui.signals):
                return False
            arr = self.gui.signals[idx]
            try:
                return bool(np.all(np.abs(arr) < 1e-9))
            except (TypeError, ValueError) as e:
                logger.debug("Null-Signal-Prüfung für '%s' fehlgeschlagen: %s", h, e)
                return False

        zero_signal_headers = {h for h in selectable_headers if _is_zero_signal(h)}

        selected_list      = []
        last_clicked_index = [None]
        select_window      = None

        # --------------------------------------------------------
        #  FENSTER AUFBAUEN
        # --------------------------------------------------------

        def on_window_close():
            # Wird über den <Destroy>-Event von select_window ausgelöst (siehe
            # create_signal_selection_layout) - läuft also unabhängig davon, wer
            # das Panel zerstört (erneutes Öffnen der Signalauswahl, Übersichtsplot,
            # ...). Ruft select_window.destroy() NICHT selbst auf, das würde
            # innerhalb des eigenen <Destroy>-Handlers eine TclError auslösen.
            self.plot_window_manager.active_signal_window = None
            if hasattr(self.gui, 'overview_window_button'):
                self.gui.overview_window_button.config(state="normal")
            # Bei mehreren Dateien (Signal-Pool): zurueck zu Schritt 1 des
            # Mehrfachdatei-Panels statt zur normalen Einzeldatei-Ansicht.
            if hasattr(self.gui, "multi_file_manager") and self.gui.multi_file_manager.is_active():
                self.gui.multi_file_manager.return_to_step1()

        layout        = self.gui.layout_manager.create_signal_selection_layout(on_window_close, unit_colors=unit_legend_colors)
        select_window = layout["select_window"]

        self.plot_window_manager.active_signal_window = select_window

        if hasattr(self.gui, 'overview_window_button'):
            self.gui.overview_window_button.config(state="disabled")

        search_var           = layout["search_var"]
        search_entry         = layout["search_entry"]
        selected_display_var = layout["selected_display_var"]
        listbox              = layout["listbox"]
        groups_container     = layout["groups_container"]
        groups_canvas        = layout["groups_canvas"]
        groups_wrapper       = layout["groups_wrapper"]
        paned_window         = layout["paned_window"]
        group_buttons_frame  = layout["group_buttons_frame"]
        opts_frame           = layout["opts_frame"]
        actions_frame        = layout["actions_frame"]
        legend_rows              = layout["legend_rows"]
        legend_zero_row          = layout["legend_zero_row"]
        legend_zero_marker_label = layout["legend_zero_marker_label"]
        legend_zero_text_label   = layout["legend_zero_text_label"]

        # --------------------------------------------------------
        #  LISTBOX HILFSFUNKTIONEN
        # --------------------------------------------------------

        visible_items = []
        _syncing      = [False]

        def update_legend_highlight():
            """Hebt in der Legende die Einheit(en) der aktuell ausgewählten Signale
            hervor (und den "!"-Nullsignal-Marker, falls ein ausgewähltes Signal
            konstant 0 ist)."""
            active_units = set()
            any_zero     = False
            for h in selected_list:
                idx = self.gui.headers.index(h)
                active_units.add(self.gui.units[idx].strip() if idx < len(self.gui.units) else "")
                if h in zero_signal_headers:
                    any_zero = True

            for unit, (row_frame, unit_label) in legend_rows.items():
                active = unit in active_units
                Cfg.Styles.force_apply(row_frame, "LegendActive.TFrame" if active else "Legend.TFrame")
                Cfg.Styles.force_apply(unit_label, "LegendActive.TLabel" if active else "Legend.TLabel")
                row_frame.configure(relief="solid" if active else "flat", borderwidth=2 if active else 0)

            Cfg.Styles.force_apply(legend_zero_row, "LegendActive.TFrame" if any_zero else "Legend.TFrame")
            legend_zero_row.configure(relief="solid" if any_zero else "flat", borderwidth=2 if any_zero else 0)
            Cfg.Styles.force_apply(
                legend_zero_marker_label, "ZeroMarkerActive.TLabel" if any_zero else "ZeroMarker.TLabel"
            )
            Cfg.Styles.force_apply(legend_zero_text_label, "LegendActive.TLabel" if any_zero else "Legend.TLabel")

        def update_selected_display():
            selected_display_var.set(
                ", ".join(selected_list) if selected_list else Cfg.Texts.STATUS_KEIN_SIGNAL
            )
            update_legend_highlight()

        def selection_clear_all():
            selected = listbox.selection()
            if selected:
                listbox.selection_remove(*selected)

        def selection_set_index(index: int):
            item_ids = listbox.get_children("")
            if 0 <= index < len(item_ids):
                listbox.selection_add(item_ids[index])

        def selection_clear_index(index: int):
            item_ids = listbox.get_children("")
            if 0 <= index < len(item_ids):
                listbox.selection_remove(item_ids[index])

        def get_selected_indices():
            item_ids = listbox.get_children("")
            selected = set(listbox.selection())
            return [i for i, iid in enumerate(item_ids) if iid in selected]

        def nearest_index(y_pos: int):
            item_ids = listbox.get_children("")
            if not item_ids:
                return -1
            row_id = listbox.identify_row(y_pos)
            if not row_id:
                return -1
            try:
                return item_ids.index(row_id)
            except ValueError:
                return -1

        def update_listbox(filter_text: str = ""):
            nonlocal visible_items
            current_items = listbox.get_children()
            if current_items:
                listbox.delete(*current_items)

            ft            = filter_text.lower().strip()
            visible_items = [h for h in selectable_headers if ft in h.lower()] if ft else selectable_headers

            if not visible_items:
                listbox.insert("", tk.END, text="Kein Signal gefunden")
                selection_clear_all()
                return

            for unit, color in unit_colors.items():
                tag_name = f"unit_{unit}" if unit else "unit_none"
                listbox.tag_configure(tag_name, background=color)
            listbox.tag_configure("zero_signal", foreground=Cfg.Colors.DANGER)

            for h in visible_items:
                idx          = self.gui.headers.index(h)
                unit         = self.gui.units[idx].strip() if idx < len(self.gui.units) else ""
                tag_name     = f"unit_{unit}" if unit else "unit_none"
                is_zero      = h in zero_signal_headers
                display_text = f"{h} {Cfg.Texts.ZERO_SIGNAL_MARKER}" if is_zero else h
                row_tags     = (tag_name, "zero_signal") if is_zero else (tag_name,)
                listbox.insert("", tk.END, text=display_text, tags=row_tags)

            selection_clear_all()
            for i, h in enumerate(visible_items):
                if h in selected_list:
                    selection_set_index(i)

        update_listbox()

        # --------------------------------------------------------
        #  GRUPPEN-ANZEIGE
        # --------------------------------------------------------

        style = ttk.Style(select_window)
        style.configure("GroupSelected.TFrame", background=Cfg.Colors.GROUP_SELECTED_BG)
        style.configure("GroupSelected.TLabel", foreground=Cfg.Colors.GROUP_LABEL, background=Cfg.Colors.GROUP_SELECTED_BG)

        selected_group_indices = {"indices": []}

        # Automatische Höhe des Gruppen-Bereichs: wächst/schrumpft mit der Anzahl
        # Gruppen, ohne feste Obergrenze - der Nutzer sieht so alle Gruppen ohne
        # scrollen zu müssen. Manuelles Verkleinern per Splitter (PanedWindow-
        # Sash) bleibt davon unberührt, das läuft unabhängig über fill/expand.
        GROUP_ROW_HEIGHT  = 30
        MIN_AUTO_HEIGHT   = 40

        def update_group_display():
            """Aktualisiert die Anzeige aller Gruppen."""
            for widget in groups_container.winfo_children():
                widget.destroy()

            for i, group_data in enumerate(self.gui.signal_groups):
                is_selected = i in selected_group_indices["indices"]
                group_frame = ttk.Frame(groups_container)
                Cfg.Styles.force_apply(group_frame, "GroupSelected.TFrame" if is_selected else "Panel.TFrame")
                group_frame.pack(fill=tk.X, padx=5, pady=2)

                if is_selected:
                    group_frame.configure(relief="solid", borderwidth=2)

                group_signals = group_data['signals'] if isinstance(group_data, dict) else group_data
                group_name = group_data.get('name', f'Gruppe {i+1}') if isinstance(group_data, dict) else f'Gruppe {i+1}'

                signal_text = ", ".join(group_signals[:3]) + ("..." if len(group_signals) > 3 else "")

                group_label = ttk.Label(
                    group_frame,
                    text=f"{group_name}: ({signal_text})",
                    font=(
                        (Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold")
                        if is_selected else
                        (Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL)
                    ),
                    anchor="w",
                )
                Cfg.Styles.force_apply(group_label, "GroupSelected.TLabel" if is_selected else "Panel.TLabel")
                group_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

                if len(group_signals) > 3:
                    def _show_all_signals(group_idx=i):
                        group_data = self.gui.signal_groups[group_idx]
                        group_signals = group_data['signals'] if isinstance(group_data, dict) else group_data
                        group_name = group_data.get('name', f'Gruppe {group_idx+1}') if isinstance(group_data, dict) else f'Gruppe {group_idx+1}'
                        messagebox.showinfo(
                            f"{group_name} - Alle Signale",
                            "\n".join(group_signals)
                        )
                    ttk.Button(group_frame, text="mehr", command=_show_all_signals).pack(side=tk.RIGHT, padx=5)

                def _make_click_handler(idx):
                    return lambda event: _select_group(idx)

                group_label.bind("<Button-1>", _make_click_handler(i))
                group_frame.bind("<Button-1>",  _make_click_handler(i))

            n = len(self.gui.signal_groups)
            content_height = max(MIN_AUTO_HEIGHT, n * GROUP_ROW_HEIGHT)
            groups_canvas.configure(height=content_height)

            # groups_canvas.configure(height=...) allein bewirkt nichts - ein
            # ttk.PanedWindow fragt die Grösse eines Kind-Widgets nicht erneut ab,
            # sobald das Layout einmal steht. Die Pane muss über die Sash-Position
            # aktiv verschoben werden, um tatsächlich sichtbar zu wachsen/schrumpfen.
            # Zielhöhe der ganzen Pane über winfo_reqheight() ermitteln (nicht nur
            # die Canvas-Höhe!), damit auch group_buttons_frame ("Gruppe erstellen"/
            # "Gruppe(n) löschen") und der LabelFrame-Rahmen genug Platz behalten
            # und nicht abgeschnitten werden.
            groups_wrapper.update_idletasks()
            total_height = groups_wrapper.winfo_reqheight()

            paned_window.update_idletasks()
            pw_height = paned_window.winfo_height()
            if pw_height > 1:  # > 1 heisst: Fenster ist schon echt gemappt/vermessen
                new_sash = max(0, pw_height - total_height)
                paned_window.sashpos(0, new_sash)

        def _select_group(idx: int):
            """Wählt/Entwählt eine Gruppe (Toggle)."""
            if idx >= len(self.gui.signal_groups):
                return
            if idx in selected_group_indices["indices"]:
                selected_group_indices["indices"].remove(idx)
            else:
                selected_group_indices["indices"].append(idx)
            update_group_display()

        update_group_display()

        # --------------------------------------------------------
        #  GRUPPEN-MODUS
        # --------------------------------------------------------

        group_selection_active = {"active": False}
        opts_frame_ref         = {"frame": opts_frame}
        action_widgets         = []

        def _set_children_state(parent, enabled: bool):
            """Aktiviert/Deaktiviert rekursiv alle untergeordneten Widgets."""
            for child in parent.winfo_children():
                try:
                    if isinstance(child, ttk.Widget):
                        child.state(["!disabled"] if enabled else ["disabled"])
                    else:
                        child.config(state="normal" if enabled else "disabled")
                except Exception as e:
                    logger.debug("Widget-Status (enabled=%s) konnte nicht gesetzt werden: %s", enabled, e)
                _set_children_state(child, enabled)

        def set_group_selection_mode(active: bool):
            """Schaltet den Gruppenauswahl-Modus ein/aus."""
            group_selection_active["active"] = active
            if opts_frame_ref["frame"] is not None:
                _set_children_state(opts_frame_ref["frame"], not active)
            for widget in action_widgets:
                try:
                    if isinstance(widget, ttk.Widget):
                        widget.state(["!disabled"] if not active else ["disabled"])
                    else:
                        widget.config(state="normal" if not active else "disabled")
                except Exception as e:
                    logger.debug("Widget-Status im Gruppenauswahl-Modus konnte nicht gesetzt werden: %s", e)

        def create_group_manually():
            """Erstellt eine neue Gruppe aus der aktuellen Auswahl."""
            if not group_selection_active["active"]:
                if not get_selected_indices() and not selected_list:
                    set_group_selection_mode(True)
                    messagebox.showinfo(
                        "Signale auswählen",
                        "Bitte wählen Sie die Signale für die Gruppe aus.\n"
                        "Hinweis: Am besten ähnliche Signale für eine übersichtliche Gruppe.",
                        parent=select_window
                    )
                    return

            selected_list[:] = [
                visible_items[i]
                for i in get_selected_indices()
                if i < len(visible_items)
            ]

            if len(selected_list) < Cfg.Limits.MIN_SIGNALS_FOR_GROUP:
                messagebox.showwarning(Cfg.Texts.HINT, Cfg.Texts.GRUPPE_ZU_WENIG_SIGNALE, parent=select_window)
                return

            if len(self.gui.signal_groups) >= Cfg.Limits.MAX_GROUPS:
                messagebox.showwarning(
                    Cfg.Texts.HINT,
                    Cfg.Texts.GRUPPE_MAX_ERREICHT.format(Cfg.Limits.MAX_GROUPS),
                    parent=select_window
                )
                return

            group_number = len(self.gui.signal_groups) + 1
            default_name = f"Gruppe {group_number}"

            group_data = {
                'signals': selected_list.copy(),
                'name': default_name
            }

            group_popup = tb.Toplevel(select_window)
            group_popup.title("Gruppenname definieren")
            group_popup.transient(select_window)
            group_popup.grab_set()
            self.gui.apply_icon(group_popup)

            ttk.Label(group_popup, text="Gruppenname definieren:").pack(pady=10, padx=20)

            name_entry = ttk.Entry(group_popup, width=40)
            name_entry.pack(pady=5, padx=20, fill=tk.X)
            name_entry.insert(0, default_name)
            name_entry.focus_set()
            name_entry.select_range(0, tk.END)

            result = {"confirmed": False}

            def on_ok():
                group_name = name_entry.get().strip()
                if not group_name:
                    group_name = default_name
                group_data['name'] = group_name
                result["confirmed"] = True
                group_popup.destroy()

            def on_cancel():
                group_popup.destroy()

            button_frame = ttk.Frame(group_popup)
            button_frame.pack(pady=10)
            ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Abbrechen", command=on_cancel).pack(side=tk.LEFT, padx=5)

            self.gui.center_window(group_popup)

            group_popup.wait_window()

            if not result["confirmed"]:
                return

            self.gui.signal_groups.append(group_data)
            messagebox.showinfo(
                "Gruppe erstellt",
                f'Gruppe "{group_data["name"]}" wurde erstellt mit {len(selected_list)} Signal(en).',
                parent=select_window
            )

            selected_list.clear()
            selection_clear_all()
            update_selected_display()
            update_group_display()
            set_group_selection_mode(False)

        def cancel_group_selection():
            """Bricht die Gruppenauswahl ab oder löscht markierte Gruppen."""
            if group_selection_active["active"]:
                selected_list.clear()
                selection_clear_all()
                update_selected_display()
                set_group_selection_mode(False)
                return

            if not selected_group_indices["indices"]:
                messagebox.showinfo("Keine Gruppe gewählt", "Bitte mindestens eine Gruppe anklicken.", parent=select_window)
                return

            anzahl = len(selected_group_indices["indices"])
            if messagebox.askyesno(
                Cfg.Texts.HINT,
                Cfg.Texts.GRUPPE_LOESCHEN_BESTAETIGUNG.format(anzahl),
                parent=select_window
            ):
                for idx in sorted(selected_group_indices["indices"], reverse=True):
                    if idx < len(self.gui.signal_groups):
                        del self.gui.signal_groups[idx]
                selected_group_indices["indices"].clear()
                update_group_display()

        ttk.Button(
            group_buttons_frame, text=Cfg.Texts.BTN_GRUPPE_ERSTELLEN,
            command=create_group_manually
        ).pack(side=tk.LEFT, padx=Cfg.Layout.Sidebar.CARD_PAD_X)

        ttk.Button(
            group_buttons_frame, text=Cfg.Texts.BTN_GRUPPE_LOESCHEN,
            command=cancel_group_selection
        ).pack(side=tk.LEFT, padx=Cfg.Layout.Sidebar.CARD_PAD_X)

        # --------------------------------------------------------
        #  ANALYSE-OPTIONEN
        # --------------------------------------------------------

        show_avg_var      = tk.BooleanVar(value=False)
        show_rms_var      = tk.BooleanVar(value=False)
        show_diff_var     = tk.BooleanVar(value=False)
        show_integral_var = tk.BooleanVar(value=False)
        show_fft_var      = tk.BooleanVar(value=False)
        show_varianz_var  = tk.BooleanVar(value=False)
        show_filtered_var = self.gui.use_filtered_var

        # --------------------------------------------------------
        #  LISTBOX EVENTS
        # --------------------------------------------------------

        def on_listbox_press(event):
            """Setzt Sync-Flag bevor Treeview intern die Selection ändert."""
            _syncing[0] = True

        def on_listbox_click(event):
            """Behandelt Klicks auf die Listbox mit Shift-Unterstützung."""
            try:
                clicked_index = nearest_index(event.y)
                if clicked_index < 0 or clicked_index >= len(visible_items):
                    return

                clicked_header = visible_items[clicked_index]

                if event.state & 0x1:  # Shift-Taste gedrückt
                    if last_clicked_index[0] is not None:
                        start = min(last_clicked_index[0], clicked_index)
                        end   = max(last_clicked_index[0], clicked_index)
                        for i in range(start, end + 1):
                            if i < len(visible_items):
                                h = visible_items[i]
                                if h not in selected_list:
                                    selected_list.append(h)
                                selection_set_index(i)
                    else:
                        if clicked_header in selected_list:
                            selected_list.remove(clicked_header)
                            selection_clear_index(clicked_index)
                        else:
                            selected_list.append(clicked_header)
                            selection_set_index(clicked_index)
                else:
                    if clicked_header in selected_list:
                        selected_list.remove(clicked_header)
                        selection_clear_index(clicked_index)
                    else:
                        selected_list.append(clicked_header)
                        selection_set_index(clicked_index)

                last_clicked_index[0] = clicked_index

                # Treeview-Marks vollständig mit selected_list synchronisieren
                # (Treeview löscht beim Klick intern alle anderen Markierungen)
                item_ids_current = listbox.get_children("")
                for i, iid in enumerate(item_ids_current):
                    if i < len(visible_items) and visible_items[i] in selected_list:
                        listbox.selection_add(iid)
                    else:
                        listbox.selection_remove(iid)

                update_selected_display()
            finally:
                _syncing[0] = False

        def on_treeview_select(event=None):
            """Synct selected_list bei Tastatur-Navigation (Pfeiltasten, Leertaste)."""
            if _syncing[0]:
                return
            item_ids     = listbox.get_children("")
            selected_ids = set(listbox.selection())
            selected_list[:] = [
                visible_items[i]
                for i, iid in enumerate(item_ids)
                if iid in selected_ids and i < len(visible_items)
            ]
            update_selected_display()

        listbox.bind("<Button-1>",        on_listbox_press)
        listbox.bind("<ButtonRelease-1>", on_listbox_click)
        listbox.bind("<<TreeviewSelect>>", on_treeview_select)

        def on_search_change(*args):
            update_listbox(search_var.get())

        search_var.trace_add("write", on_search_change)

        # --------------------------------------------------------
        #  FILTER DIALOG
        # --------------------------------------------------------

        def open_filter_popup():
            """Öffnet den Filter-Einstellungs-Dialog."""
            protocol_logger.info("FILTER_DIALOG_OPEN")

            popup = tb.Toplevel(select_window)
            popup.title(Cfg.Texts.FILTER_DIALOG_TITEL)
            popup.transient(select_window)
            self.gui.apply_icon(popup)

            ttk.Label(popup, text="Filter wählen:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
            filter_type_cb = ttk.Combobox(popup, values=Cfg.Defaults.FILTER_TYPEN, state="readonly", width=20)
            filter_type_cb.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="ew")

            ttk.Label(popup, text="Grenzfrequenz 1 z.B. 2").grid(row=1, column=0, padx=10, pady=5, sticky="w")
            freq1_entry = ttk.Entry(popup, width=15)
            freq1_entry.insert(0, str(Cfg.Defaults.GRENZFREQUENZ_1))
            freq1_entry.config(state="disabled")
            freq1_entry.grid(row=1, column=1, padx=10, pady=5)

            ttk.Label(popup, text="Grenzfrequenz 2 z.B. 6").grid(row=1, column=2, padx=10, pady=5, sticky="w")
            freq2_entry = ttk.Entry(popup, width=15)
            freq2_entry.insert(0, str(Cfg.Defaults.GRENZFREQUENZ_2))
            freq2_entry.config(state="disabled")
            freq2_entry.grid(row=1, column=3, padx=10, pady=5)

            char_cb = ttk.Combobox(popup, values=Cfg.Defaults.FILTER_CHARAKTERISTIKEN, state="disabled", width=20)
            char_cb.set("Charakteristik auswählen:")
            char_cb.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

            order_cb = ttk.Combobox(popup, values=Cfg.Defaults.FILTER_ORDNUNGEN, state="disabled", width=20)
            order_cb.set("Ordnung auswählen:")
            order_cb.grid(row=2, column=2, columnspan=2, padx=10, pady=5, sticky="ew")

            def on_filter_type_change(event=None):
                ftype = filter_type_cb.get()
                if ftype == Cfg.Defaults.FILTER_TYP:
                    freq1_entry.config(state="disabled")
                    freq2_entry.config(state="disabled")
                    char_cb.config(state="disabled")
                    order_cb.config(state="disabled")
                elif ftype == "Bandpass":
                    freq1_entry.config(state="normal")
                    freq2_entry.config(state="normal")
                    char_cb.config(state="readonly")
                    order_cb.config(state="readonly")
                else:
                    freq1_entry.config(state="normal")
                    freq2_entry.config(state="disabled")
                    char_cb.config(state="readonly")
                    order_cb.config(state="readonly")

            filter_type_cb.bind("<<ComboboxSelected>>", on_filter_type_change)

            def apply_filter(then_show_characteristic=False):
                ftype         = filter_type_cb.get()
                defaults_used = False

                if not ftype or ftype == Cfg.Defaults.FILTER_TYP:
                    ftype = "Tiefpass"
                    filter_type_cb.set(ftype)
                    defaults_used = True

                freq1     = freq1_entry.get().strip()
                freq2_str = freq2_entry.get().strip()

                if ftype == "Bandpass":
                    if not freq1 or not freq2_str:
                        messagebox.showerror(
                            "Fehler - Fehlende Grenzfrequenz",
                            "Bandpass-Filter benötigt BEIDE Grenzfrequenzen!\n\n"
                            "Bitte geben Sie sowohl die untere als auch die obere Grenzfrequenz ein."
                        )
                        return
                    try:
                        freq1_float = float(freq1)
                        freq2_float = float(freq2_str)
                    except ValueError:
                        messagebox.showerror("Fehler - Ungültige Eingabe", "Beide Grenzfrequenzen müssen gültige Zahlen sein!")
                        return
                    if freq1_float >= freq2_float:
                        messagebox.showerror(
                            "Fehler - Ungültige Frequenzreihenfolge",
                            f"Die untere Grenzfrequenz ({freq1_float} Hz) muss kleiner sein\n"
                            f"als die obere Grenzfrequenz ({freq2_float} Hz)!"
                        )
                        return

                if not freq1 or freq1 == str(Cfg.Defaults.GRENZFREQUENZ_1):
                    freq1         = str(Cfg.Defaults.GRENZFREQUENZ_1)
                    defaults_used = True

                characteristic = char_cb.get()
                if not characteristic or characteristic == "Charakteristik auswählen:":
                    characteristic = Cfg.Defaults.FILTER_CHARAKTERISTIK
                    char_cb.set(characteristic)
                    defaults_used = True

                order = order_cb.get()
                if not order or order == "Ordnung auswählen:":
                    order = Cfg.Defaults.FILTER_ORDNUNG
                    order_cb.set(order)
                    defaults_used = True

                if defaults_used:
                    messagebox.showinfo("Standardwerte", "Default Werte übernommen")

                try:
                    order_int = int(order.split('.')[0])
                except (ValueError, IndexError):
                    order_int = 1

                try:
                    freq1_float = float(freq1)
                except ValueError:
                    freq1_float = float(Cfg.Defaults.GRENZFREQUENZ_1)

                freq2_float = None
                if freq2_str := freq2_entry.get().strip():
                    try:
                        freq2_float = float(freq2_str)
                    except ValueError:
                        freq2_float = None

                fs_text = self.gui.entry5.get().strip()
                if not fs_text or fs_text == Cfg.Ph.SAMPLERATE:
                    fs = float(Cfg.Defaults.SAMPLERATE)
                else:
                    fs_candidate = fs_text.split("=")[-1].strip().replace(",", ".")
                    try:
                        fs = float(fs_candidate)
                    except ValueError:
                        messagebox.showerror(
                            "Fehler - Ungültige Samplingfrequenz",
                            f"Die Samplingfrequenz '{fs_text}' ist keine gültige Zahl."
                        )
                        return

                self.gui.filter_manager.set_filter_parameters(ftype, freq1_float, fs, cutoff_frequency2=freq2_float)
                self.gui.filter_manager.set_filter_characteristics(characteristic, order_int)

                protocol_logger.info(
                    "FILTER_SET type=%s | cutoff1=%s | cutoff2=%s | characteristic=%s | order=%s | fs=%s",
                    ftype, freq1_float, freq2_float, characteristic, order_int, fs,
                )

                if ftype == Cfg.Defaults.FILTER_TYP:
                    show_filtered_var.set(False)
                else:
                    show_filtered_var.set(True)
                    if hasattr(self, "filter_char_button"):
                        self.filter_char_button.config(state="normal")

                self.plot_window_manager.update_all_plot_windows()

                popup.destroy()
                if then_show_characteristic and ftype != Cfg.Defaults.FILTER_TYP:
                    self.gui.ui_control.show_filter_characteristic_window()

            # --- Aktuellen Filterzustand in Dialog eintragen ---
            filter_type_cb.set(self.gui.filter_manager.filter_type or "Tiefpass")
            if self.gui.filter_manager.cutoff_frequency:
                freq1_entry.config(state="normal")
                freq1_entry.delete(0, tk.END)
                freq1_entry.insert(0, str(self.gui.filter_manager.cutoff_frequency))
            if self.gui.filter_manager.cutoff_frequency2:
                freq2_entry.config(state="normal")
                freq2_entry.delete(0, tk.END)
                freq2_entry.insert(0, str(self.gui.filter_manager.cutoff_frequency2))
            if self.gui.filter_manager.characteristic:
                char_cb.set(self.gui.filter_manager.characteristic)
            if self.gui.filter_manager.order:
                order_cb.set(f"{self.gui.filter_manager.order}.Ordnung")
            on_filter_type_change()

            btn_row = ttk.Frame(popup)
            btn_row.grid(row=3, column=0, columnspan=4, pady=15)

            ttk.Button(btn_row, text="Anwenden", command=apply_filter).pack(side=tk.LEFT, padx=6)

            char_state = "normal" if self.gui.filter_manager.filter_type not in (
                None, "", Cfg.Defaults.FILTER_TYP
            ) else "disabled"
            self.filter_char_button = ttk.Button(
                btn_row, text="Charakteristik anzeigen", state=char_state,
                command=lambda: apply_filter(then_show_characteristic=True)
            )
            self.filter_char_button.pack(side=tk.LEFT, padx=6)

            self.gui.center_window(popup)

        def on_filtered_master_toggled():
            """Handler für Filter-Master-Toggle."""
            self.plot_window_manager.update_all_plot_windows()

        # --- Opts-Frame Buttons & Checkboxen ---
        ttk.Button(opts_frame, text=Cfg.Texts.BTN_FILTER, command=open_filter_popup).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="Filter", variable=self.gui.use_filtered_var, command=on_filtered_master_toggled).pack(side=tk.LEFT, padx=6)

        ttk.Checkbutton(opts_frame, text="AVG",          variable=show_avg_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="RMS",          variable=show_rms_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="Differential", variable=show_diff_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="Integral",     variable=show_integral_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="FFT",          variable=show_fft_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="Statistik",    variable=show_varianz_var).pack(side=tk.LEFT, padx=6)

        # --------------------------------------------------------
        #  PLOT
        # --------------------------------------------------------

        def _get_selected_groups():
            """Gibt ausgewählte Gruppen als Liste von Signallisten zurück."""
            groups = []
            for idx in sorted(selected_group_indices["indices"]):
                if idx < len(self.gui.signal_groups):
                    group_data = self.gui.signal_groups[idx]
                    group_signals = group_data['signals'] if isinstance(group_data, dict) else group_data
                    if group_signals:
                        groups.append(group_signals)
            return groups

        def plot_selected():
            """Button-Callback – öffnet Notebook mit Tabs für jede Analyseart."""
            selected_groups = _get_selected_groups()

            if selected_groups:
                grouped_headers    = [list(dict.fromkeys(g)) for g in selected_groups]
                effective_selected = [h for group in grouped_headers for h in group]
            else:
                grouped_headers    = None
                effective_selected = selected_list.copy()

            if not effective_selected:
                self.gui.status_label.config(text=Cfg.Texts.STATUS_KEIN_SIGNAL)
                return

            selected_analyses = [
                label for label, var in [
                    ("AVG",          show_avg_var),
                    ("RMS",          show_rms_var),
                    ("FFT",          show_fft_var),
                    ("Differential", show_diff_var),
                    ("Integral",     show_integral_var),
                    ("Statistik",    show_varianz_var),
                ]
                if var.get()
            ] or ["Signal"]

            self.gui.selected_signal  = effective_selected[-1]
            self.gui.selected_signals = effective_selected.copy()

            zeitbereich_analysen = [a for a in selected_analyses if a in ["AVG", "RMS", "FFT"]]
            direkt_analysen      = [a for a in selected_analyses if a not in ["AVG", "RMS", "FFT"]]

            signal_indices = []
            for signal_name in effective_selected:
                try:
                    signal_indices.append(self.gui.headers.index(signal_name))
                except ValueError:
                    continue

            is_filter_ready = self.gui._is_filter_ready()
            if not is_filter_ready:
                self.gui.use_filtered_var.set(False)

            use_filtered = self.gui.use_filtered_var.get() and is_filter_ready

            protocol_logger.info(
                "PLOT_SELECTION signals=%s | analyses=%s | filtered=%s | grouped=%s",
                effective_selected, selected_analyses, use_filtered, bool(selected_groups),
            )

            if zeitbereich_analysen:
                if isinstance(self.gui.t, (list, tuple)):
                    # Signal-Pool (Batch-Import): jedes Signal hat seine eigene Zeitachse -
                    # der Dialog-Schieberegler geht bis zur laengsten Dauer aller Signale.
                    t_max = max((arr[-1] for arr in self.gui.t if len(arr) > 0), default=10)
                    # Fuer den Dialog wird EIN Zeitstempel-Array gebraucht (fuer die
                    # "14:34:30"-Uhrzeit-Eingabe) - das des ersten ausgewaehlten
                    # Signals dient als Referenz.
                    dialog_timestamps = (
                        PlotManager.t_for_idx(self.gui.timestamps, signal_indices[0])
                        if signal_indices and isinstance(self.gui.timestamps, (list, tuple))
                        else None
                    )
                else:
                    t_max = self.gui.t[-1] if self.gui.t is not None and len(self.gui.t) > 0 else 10
                    dialog_timestamps = self.gui.timestamps
                selected_label = ", ".join(effective_selected[:3])
                if len(effective_selected) > 3:
                    selected_label += f" (+{len(effective_selected) - 3} weitere)"

                filter_info = (
                    self.gui.filter_manager.get_filter_info()
                    if use_filtered and hasattr(self.gui, 'filter_manager')
                    else None
                )

                def on_zeitbereich(result):
                    alle_analysen = zeitbereich_analysen + direkt_analysen or ["Signal"]
                    self.plot_window_manager._create_notebook_window(
                        select_window=select_window,
                        selected_list=effective_selected,
                        signal_indices=signal_indices,
                        selected_analyses=alle_analysen,
                        header_to_signal_idx=header_to_signal_idx,
                        use_filtered=use_filtered,
                        zeitbereiche_dict=result,
                        grouped_headers=grouped_headers
                    )

                PlotManager.show_zeitbereich_dialog(
                    parent=select_window,
                    t_max=t_max,
                    callback=on_zeitbereich,
                    title="Zeitbereich für Analyse auswählen",
                    selected_signal=selected_label,
                    is_filtered=use_filtered,
                    filter_info=filter_info,
                    analyse_typen=zeitbereich_analysen,
                    timestamps=dialog_timestamps
                )
            else:
                self.plot_window_manager._create_notebook_window(
                    select_window=select_window,
                    selected_list=effective_selected,
                    signal_indices=signal_indices,
                    selected_analyses=direkt_analysen or ["Signal"],
                    header_to_signal_idx=header_to_signal_idx,
                    use_filtered=use_filtered,
                    zeitbereiche_dict={},
                    grouped_headers=grouped_headers
                )

        # --------------------------------------------------------
        #  CLEAR
        # --------------------------------------------------------

        def clear_all():
            """Setzt alle Auswahlen, Gruppen und Optionen zurück."""
            selected_list.clear()
            selected_group_indices["indices"].clear()
            self.gui.signal_groups.clear()
            set_group_selection_mode(False)

            update_group_display()
            update_listbox("")
            update_selected_display()
            logger.info("Alle Auswahlen gelöscht.")

            search_entry.select_clear()
            search_entry.delete(0, tk.END)
            search_entry.focus_set()

            for var in [show_avg_var, show_rms_var, show_diff_var, show_integral_var, show_fft_var, show_varianz_var]:
                var.set(False)

            for key, default in [
                ('type',           'Kein Filter'),
                ('freq1',          ''),
                ('freq2',          ''),
                ('characteristic', 'butterworth'),
                ('order',          '1.Ordnung'),
                ('enabled',        False),
            ]:
                self.plot_window_manager.overlay_filter_state[key] = default

            self.gui.use_filtered_var.set(False)
            protocol_logger.info("SELECTION_CLEAR_ALL")

            if self.filter_char_button is not None and self.filter_char_button.winfo_exists():
                self.filter_char_button.config(state="disabled")

        # --------------------------------------------------------
        #  ACTION BUTTONS
        # --------------------------------------------------------

        btn_plot   = ttk.Button(actions_frame, text=Cfg.Texts.BTN_PLOT,   command=plot_selected)
        btn_clear  = ttk.Button(actions_frame, text=Cfg.Texts.BTN_CLEAR,  command=clear_all)

        #Buttons
        btn_plot.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.X, expand=True)
        btn_clear.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.X, expand=True)

        action_widgets.extend([btn_plot, btn_clear])