"""
GUI Layout Manager - Benutzeroberflächen-Aufbau
=================================================
Erstellt und verwaltet das komplette GUI-Layout:
Frames, Buttons, Eingabefelder, Comboboxen und deren
Positionierung im Hauptfenster.
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
import logging
import os
import tempfile
import tkinter as tk
from tkinter import ttk

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import matplotlib.pyplot as plt
import ttkbootstrap as tb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from PIL import Image, ImageTk

# ============================================================
#  IMPORTS – Eigene Klassen
# ============================================================
from konfiguration import Cfg

# ============================================================
#  LOGGING
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
#  KLASSE
# ============================================================
class GuiLayoutManager:
    """Erstellt und verwaltet das Layout der GUI (Frames, Buttons, Comboboxen)."""

    def __init__(self, gui_manager):

        # --- Referenzen ---
        self.gui = gui_manager

        # --- Layout-Defaults ---
        self.pad_x_medium = 10
        self.pad_y_medium = 8

    # --------------------------------------------------------
    #  NOTEBOOK TABS
    # --------------------------------------------------------

    def blink_tab(self, tab_index, times=15, interval=300):
        """Lässt einen Notebook-Tab mehrfach blinken."""
        if not hasattr(self.gui, 'bottom_notebook'):
            return

        self._blinking             = True
        self._blink_tab_index      = tab_index
        self._blink_original_text  = None
        self._blink_job            = None
        notebook             = self.gui.bottom_notebook
        original_text        = notebook.tab(tab_index, "text")
        self._blink_original_text = original_text
        style                = ttk.Style()

        colors      = {0: Cfg.Colors.TAB_INPUT, 1: Cfg.Colors.TAB_OUTPUT}
        blink_color = colors.get(tab_index, "#0d6efd")
        notebook.select(tab_index)

        def do_blink(count):
            if count <= 0:
                self._stop_blink()
                return
            if count % 2 == 0:
                style.map("Custom.TNotebook.Tab",
                    background=[("selected", blink_color),            ("!selected", Cfg.Colors.TAB_INACTIVE)],
                    foreground=[("selected", Cfg.Colors.TAB_TEXT_ACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)],
                )
            else:
                style.map("Custom.TNotebook.Tab",
                    background=[("selected", Cfg.Colors.TAB_INACTIVE), ("!selected", Cfg.Colors.TAB_INACTIVE)],
                    foreground=[("selected", Cfg.Colors.TAB_TEXT_INACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)],
                )
            self._blink_job = notebook.after(interval, lambda: do_blink(count - 1))

        do_blink(times * 2)

    def _stop_blink(self):
        """Beendet ein laufendes Blinken: Timer stoppen, Original-Tab-Text
        wiederherstellen und die Tab-Farbe an die aktuelle Auswahl anpassen."""
        if not getattr(self, '_blinking', False):
            return
        notebook = self.gui.bottom_notebook
        if getattr(self, '_blink_job', None) is not None:
            notebook.after_cancel(self._blink_job)
            self._blink_job = None
        self._blinking = False
        notebook.tab(self._blink_tab_index, text=self._blink_original_text)
        self._update_tab_style()

    def _on_tab_changed(self, event=None):
        """Reagiert auf Tab-Wechsel.

        Während des Blinkens: ein bewusster Klick auf einen ANDEREN Tab
        bricht das Blinken sofort ab und lässt die Navigation zu, statt sie
        rückgängig zu machen (der programmatische select() beim Blink-Start
        selbst löst hier keinen Abbruch aus, da er auf den Blink-Tab zeigt).
        """
        if getattr(self, '_blinking', False) and event is not None:
            notebook = self.gui.bottom_notebook
            if notebook.index(notebook.select()) != self._blink_tab_index:
                self._stop_blink()
            return

        self._update_tab_style()

    def _update_tab_style(self):
        """Setzt die Tab-Farbe passend zur aktuell ausgewählten Tab."""
        style    = ttk.Style()
        notebook = self.gui.bottom_notebook
        selected = notebook.index(notebook.select())

        tab_color = Cfg.Colors.TAB_INPUT if selected == 0 else Cfg.Colors.TAB_OUTPUT
        style.map("Custom.TNotebook.Tab",
            background=[("selected", tab_color),                ("!selected", Cfg.Colors.TAB_INACTIVE)],
            foreground=[("selected", Cfg.Colors.TAB_TEXT_ACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)],
        )

    # --------------------------------------------------------
    #  HAUPTFENSTER ERSTELLEN
    # --------------------------------------------------------

    def create_gui(self):
        """Erstellt ausschließlich das Hauptfenster-Layout."""
        self.gui.root = tb.Window(themename="cosmo")

        # -------- ZENTRALE Schriftgrößen aus setup.py anwenden --------
        style = ttk.Style()

        # Registriere custom Button-Styles für die Sidebar-Karten
        Cfg.Styles.register()

        # Allgemeine UI Schriftgrößen
        style.configure("TEntry", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.MEDIUM))
        style.configure("TCombobox", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.MEDIUM))
        style.configure("TLabel", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.MEDIUM))
        style.configure("TButton", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE))

        # Status‑Label
        style.configure("Status.TLabel", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.STATUS))

        # Notebook‑Tabs im Hauptfenster
        style.configure("TNotebook.Tab", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.TABS))

        self.gui.root.title(Cfg.Texts.WINDOW_TITLE)

        # --- Fenster-Icon: verzögert setzen damit ttkbootstrap nicht überschreibt ---
        try:
            icon_path = self.gui.get_resource_path(
                os.path.join("docs_bilder", "Giraffe.png")
            )
            pil_icon = Image.open(icon_path).convert("RGBA")
            tmp = tempfile.NamedTemporaryFile(suffix=".ico", delete=False)
            tmp.close()
            pil_icon.save(tmp.name, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            self.gui.root._tmp_ico = tmp.name

            def _apply_icon():
                try:
                    self.gui.root.iconbitmap(self.gui.root._tmp_ico)
                except Exception:
                    logging.getLogger(__name__).exception("iconbitmap fehlgeschlagen")

            self.gui.root.after(0, _apply_icon)
        except Exception:
            logging.getLogger(__name__).exception("Icon konnte nicht gesetzt werden")

        screen_width  = self.gui.root.winfo_screenwidth()
        screen_height = self.gui.root.winfo_screenheight()
        self.gui.root.geometry(f"{screen_width}x{screen_height}+0+0")

        # --- Haupt-Pane ---
        main_pane = ttk.Panedwindow(self.gui.root, orient=tk.HORIZONTAL)
        main_pane.grid(row=0, column=0, sticky="nsew")
        self.gui.root.grid_rowconfigure(0, weight=1)
        self.gui.root.grid_columnconfigure(0, weight=1)

        # --- Sidebar ---
        sidebar_frame = ttk.Frame(main_pane, width=Cfg.Layout.Global.SIDEBAR_WIDTH)
        sidebar_frame.pack_propagate(False)  # verhindert Zusammenstauchen
        main_pane.add(sidebar_frame, weight=0)

        sidebar_canvas    = tk.Canvas(sidebar_frame, highlightthickness=0, bd=0, bg="#f0f0f0")
        sidebar_scrollbar = ttk.Scrollbar(sidebar_frame, orient="vertical", command=sidebar_canvas.yview)
        sidebar_inner     = ttk.Frame(sidebar_canvas, padding=(Cfg.Layout.Sidebar.PAD_X, Cfg.Layout.Sidebar.PAD_Y))
        sidebar_canvas.configure(width=Cfg.Layout.Global.SIDEBAR_WIDTH)

        _scrollregion_job = [None]  # Debounce für scrollregion

        def _on_inner_resize(e):
            if _scrollregion_job[0]:
                sidebar_canvas.after_cancel(_scrollregion_job[0])
            _scrollregion_job[0] = sidebar_canvas.after(
                50,
                lambda: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
            )

        sidebar_inner.bind("<Configure>", _on_inner_resize)
        sidebar_window_id = sidebar_canvas.create_window((0, 0), window=sidebar_inner, anchor="nw")
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        _resize_job = [None]  # Debounce für Canvas-Resize

        def _on_canvas_resize(e):
            if _resize_job[0]:
                sidebar_canvas.after_cancel(_resize_job[0])
            _resize_job[0] = sidebar_canvas.after(
                50,
                lambda: sidebar_canvas.itemconfig(
                    sidebar_window_id,
                    width=max(e.width - 5, Cfg.Layout.Global.SIDEBAR_WIDTH - 20)
                )
            )

        sidebar_canvas.bind("<Configure>", _on_canvas_resize)

        sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_sidebar_mousewheel(event):
            if event.delta:
                sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                sidebar_canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                sidebar_canvas.yview_scroll(3, "units")

        sidebar_canvas.bind("<Enter>", lambda e: (
            sidebar_canvas.bind_all("<MouseWheel>", _on_sidebar_mousewheel),
            sidebar_canvas.bind_all("<Button-4>",   _on_sidebar_mousewheel),
            sidebar_canvas.bind_all("<Button-5>",   _on_sidebar_mousewheel),
        ))
        sidebar_canvas.bind("<Leave>", lambda e: (
            sidebar_canvas.unbind_all("<MouseWheel>"),
            sidebar_canvas.unbind_all("<Button-4>"),
            sidebar_canvas.unbind_all("<Button-5>"),
        ))

        self.gui.sidebar_canvas = sidebar_canvas
        self.gui.sidebar_inner  = sidebar_inner

        # --- Rechte Seite ---
        right_container = ttk.Frame(main_pane, padding=Cfg.Layout.Main.REGION_PAD)
        main_pane.add(right_container, weight=1)
        right_container.grid_rowconfigure(0, weight=1)
        right_container.grid_columnconfigure(0, weight=1)

        right_pane  = ttk.Panedwindow(right_container, orient=tk.VERTICAL)
        right_pane.pack(fill=tk.BOTH, expand=True)

        top_region    = ttk.Frame(right_pane, padding=Cfg.Layout.Main.INNER_REGION_PAD)
        mid_region    = ttk.Frame(right_pane, padding=Cfg.Layout.Main.INNER_REGION_PAD)
        bottom_region = ttk.Frame(right_pane, padding=Cfg.Layout.Main.INNER_REGION_PAD)
        self.gui.mid_region = mid_region

        right_pane.add(top_region,    weight=0)
        right_pane.add(mid_region,    weight=1)
        right_pane.add(bottom_region, weight=0)

        self.gui.right_pane = right_pane

        self._create_status_bar(top_region)
        self._create_logo_background(mid_region)

        # --- Notebook ---
        self.gui.bottom_region   = bottom_region
        self.gui.bottom_notebook = ttk.Notebook(bottom_region)
        self.gui.bottom_notebook.pack(fill=tk.BOTH, expand=True)

        input_tab  = ttk.Frame(self.gui.bottom_notebook)
        output_tab = ttk.Frame(self.gui.bottom_notebook)
        self._create_input_section(input_tab)
        self._create_output_section(output_tab)
        self.gui.bottom_notebook.add(input_tab,  text=Cfg.Texts.TAB_EINGABE)
        self.gui.bottom_notebook.add(output_tab, text=Cfg.Texts.TAB_AUSGABE)

        # --- Mehrfachdatei-Panel (ersetzt bottom_notebook nur wenn mehrere Dateien geladen werden) ---
        self.gui.multi_file_panel = ttk.Frame(bottom_region)

        style = ttk.Style()
        style.configure(".", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.TABS))
        style.configure("Custom.TNotebook.Tab",
                        padding=list(Cfg.Layout.Notebook.TAB_PAD),
                        font=(Cfg.Fonts.FAMILY, Cfg.Fonts.TABS))
        style.map("Custom.TNotebook.Tab",
            background=[("selected", Cfg.Colors.TAB_INPUT),       ("!selected", Cfg.Colors.TAB_INACTIVE)],
            foreground=[("selected", Cfg.Colors.TAB_TEXT_ACTIVE),  ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)],
        )
        self.gui.bottom_notebook.configure(style="Custom.TNotebook")
        self.gui.bottom_notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # --- Sidebar-Inhalt ---
        self._create_sidebar_content(sidebar_inner)

        return self.gui.root

    # --------------------------------------------------------
    #  SIDEBAR
    # --------------------------------------------------------

    def _create_sidebar_content(self, parent):
        """Erstellt alle Sidebar-Sektionen mit nummeriertem Workflow-Design."""

        # --------------------------------------------------------
        #  HILFSFUNKTIONEN (intern)
        # --------------------------------------------------------

        def _make_card(step_num, title, color, icon, expand=False):
            custom_hex_colors = {
                "wine_muted":  Cfg.Colors.CARD_IMPORT,    # #8b4a52
                "light_blue":  Cfg.Colors.CARD_PROCESS,   # #4a7ab5
                "muted_green": Cfg.Colors.CARD_SIGNAL,    # #4a8a5c
            }
            
            if color in custom_hex_colors:
                frame_s, label_s = {
                    "wine_muted":  (Cfg.Styles.WINE_FRAME,  Cfg.Styles.WINE_LABEL),
                    "light_blue":  (Cfg.Styles.BLUE_FRAME,  Cfg.Styles.BLUE_LABEL),
                    "muted_green": (Cfg.Styles.GREEN_FRAME, Cfg.Styles.GREEN_LABEL),
                }[color]

                card = tb.Frame(parent)
                Cfg.Styles.force_apply(card, frame_s)
                card.pack(fill=tk.X, expand=False, pady=(0, Cfg.Layout.Sidebar.CARD_PAD_Y), padx=2)

                header = tb.Label(card, text=f"{icon}{' ' * Cfg.Texts.CARD_ICON_SPACING}{step_num}. {title}",
                                font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE, "bold"), anchor="center")
                Cfg.Styles.force_apply(header, label_s)
                header.pack(fill=tk.X, padx=Cfg.Layout.InputOutput.HEADER_PAD_X,
                            pady=Cfg.Layout.InputOutput.HEADER_PAD_Y, anchor="w")

                content = tb.Frame(card)
                content.pack(fill=tk.X, expand=False,
                            padx=Cfg.Layout.Sidebar.CARD_PAD_X,
                            pady=Cfg.Layout.InputOutput.SECTION_PAD_Y)
                return content
            else:
                # Original bootstyle
                style_map = {"wine": "danger", "primary": "primary", "success": "success", 
                            "warning": "warning", "secondary": "secondary"}
                bs = style_map.get(color, "secondary")
                card = tb.Frame(parent, bootstyle=bs)
                card.pack(fill=tk.X, expand=False, pady=(0, Cfg.Layout.Sidebar.CARD_PAD_Y), padx=2)
                
                header = tb.Label(card, text=f"{icon}{' ' * Cfg.Texts.CARD_ICON_SPACING}{step_num}. {title}",
                                font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE, "bold"), anchor="center")
                header.pack(fill=tk.X, padx=Cfg.Layout.InputOutput.HEADER_PAD_X,
                            pady=Cfg.Layout.InputOutput.HEADER_PAD_Y)
                
                content = tb.Frame(card)
                content.pack(fill=tk.X, expand=False,
                            padx=Cfg.Layout.Sidebar.CARD_PAD_X, pady=Cfg.Layout.InputOutput.SECTION_PAD_Y)
                return content

        def _make_info_card(step_num, title, color, icon="", expand=False):
            style_map = {
                "wine": "danger",
                "primary": "primary",
                "success": "success",
                "warning": "warning",
                "secondary": "secondary",
            }

            bs = style_map.get(color, "secondary")

            card = tb.Frame(parent, bootstyle=bs)
            card.pack(fill=tk.X, expand=False, pady=(0, Cfg.Layout.Sidebar.CARD_PAD_Y), padx=2)

            if step_num:
                label_text = f"{icon}{' ' * Cfg.Texts.CARD_ICON_SPACING}{step_num}. {title}"
            else:
                label_text = f"{icon}{' ' * Cfg.Texts.CARD_ICON_SPACING}{title}"

            header = tb.Label(
                card,
                text=label_text,
                bootstyle=f"inverse-{bs}",
                font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE, "bold"),
                anchor="center",
            )
            header.pack(fill=tk.X, padx=Cfg.Layout.InputOutput.HEADER_PAD_X,
                        pady=Cfg.Layout.InputOutput.HEADER_PAD_Y)

            content = tb.Frame(card)
            content.pack(fill=tk.X, expand=False,
                        padx=Cfg.Layout.Sidebar.CARD_PAD_X, pady=Cfg.Layout.InputOutput.SECTION_PAD_Y)
            return content

        BT_PAD  = Cfg.Layout.Buttons
        SD_PAD  = Cfg.Layout.Sidebar

        # --------------------------------------------------------
        #  1. DATENIMPORT
        # --------------------------------------------------------

        import_content = _make_card("1", Cfg.Texts.CARD_IMPORT_TITLE, "wine_muted", Cfg.Texts.CARD_IMPORT_ICON)

        self.gui.sheet_combobox = ttk.Combobox(import_content, values=[Cfg.Texts.CB_CSV_DEFAULT], state="readonly")
        self.gui.sheet_combobox.set(Cfg.Texts.CB_CSV_DEFAULT)
        self.gui.sheet_combobox.pack(fill=tk.X, pady=BT_PAD.PAD_Y, padx=BT_PAD.PAD_X)
        self.gui.sheet_combobox.bind('<<ComboboxSelected>>', self.gui.on_sheet_selected)

        # BUTTON 1 - Datenimport (Weinrot)
        self.gui.import_button = ttk.Button(
            import_content, text=Cfg.Texts.BTN_IMPORT, command=self.gui.load_data
        )
        Cfg.Styles.force_apply(self.gui.import_button, Cfg.Styles.WINE_BTN)
        self.gui.import_button.pack(fill=tk.X, pady=BT_PAD.PAD_Y, padx=BT_PAD.PAD_X)

        # --------------------------------------------------------
        #  2. VERARBEITUNG
        # --------------------------------------------------------

        ver_content = _make_card("2", Cfg.Texts.CARD_VERARBEITUNG_TITLE, "light_blue", Cfg.Texts.CARD_VERARBEITUNG_ICON)

        self.gui.save_mode = tk.StringVar(value="none")

        self.gui.rb_plots_spectrum = tb.Radiobutton(
            ver_content, text=Cfg.Texts.RB_PLOTS_SPEKTRUM, value="both",
            variable=self.gui.save_mode, command=self.gui.log_save_options, bootstyle="secondary",
        )
        self.gui.rb_plots_spectrum.state(["disabled"])
        self.gui.rb_plots_spectrum.pack(fill=tk.X, pady=BT_PAD.SMALL_PAD_Y, padx=BT_PAD.PAD_X)

        self.gui.rb_spectrum = tb.Radiobutton(
            ver_content, text=Cfg.Texts.RB_SPEKTRUM, value="spectrum",
            variable=self.gui.save_mode, command=self.gui.log_save_options, bootstyle="secondary",
        )
        self.gui.rb_spectrum.state(["disabled"])
        self.gui.rb_spectrum.pack(fill=tk.X, pady=BT_PAD.SMALL_PAD_Y, padx=BT_PAD.PAD_X)

        self.gui.rb_plots = tb.Radiobutton(
            ver_content, text=Cfg.Texts.RB_PLOTS, value="plots",
            variable=self.gui.save_mode, command=self.gui.log_save_options, bootstyle="secondary",
        )
        self.gui.rb_plots.state(["disabled"])
        self.gui.rb_plots.pack(fill=tk.X, pady=BT_PAD.SMALL_PAD_Y, padx=BT_PAD.PAD_X)

        self.gui.rb_none = tb.Radiobutton(
            ver_content, text=Cfg.Texts.RB_NICHTS, value="none",
            variable=self.gui.save_mode, command=self.gui.log_save_options, bootstyle="secondary",
        )
        self.gui.rb_none.state(["disabled"])
        self.gui.rb_none.pack(fill=tk.X, pady=BT_PAD.SMALL_PAD_Y, padx=BT_PAD.PAD_X)

        # BUTTON 2 - Verarbeitung (Hellblau)
        self.gui.Verarbeitung_button = ttk.Button(
            ver_content, text=Cfg.Texts.BTN_VERARBEITUNG,
            command=self.gui.verarbeitung_button_setup
        )
        Cfg.Styles.force_apply(self.gui.Verarbeitung_button, Cfg.Styles.BLUE_BTN)
        self.gui.Verarbeitung_button.pack(fill=tk.X, pady=BT_PAD.PAD_Y, padx=BT_PAD.PAD_X)
        self.gui.Verarbeitung_button.state(["disabled"])

        # --------------------------------------------------------
        #  ALLGEMEINES
        # --------------------------------------------------------

        allg_content = _make_info_card("", Cfg.Texts.CARD_ALLGEMEIN_TITLE, "secondary", Cfg.Texts.CARD_ALLGEMEIN_ICON)

        tb.Button(
            allg_content, text=Cfg.Texts.BTN_HILFE,
            command=self.gui.show_help, bootstyle="secondary", padding=(4, 2)
        ).pack(fill=tk.X, pady=(BT_PAD.LARGE_PAD_Y, BT_PAD.PAD_Y), padx=6)

        ttk.Separator(allg_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=BT_PAD.PAD_Y, padx=BT_PAD.PAD_X)

        tb.Label(allg_content, text=Cfg.Texts.LBL_PFAD,
                 font=(Cfg.Fonts.FAMILY, Cfg.Fonts.MEDIUM, "bold")).pack(anchor="w", pady=(4, 2), padx=6)

        tb.Button(
            allg_content, text=Cfg.Texts.BTN_HERKUNFTSPFAD,
            command=lambda: self.gui.show_path_window(Cfg.Texts.BTN_HERKUNFTSPFAD),
            bootstyle="outline-secondary", padding=(4, 2)
        ).pack(fill=tk.X, pady=BT_PAD.SMALL_PAD_Y, padx=6)

        tb.Button(
            allg_content, text=Cfg.Texts.BTN_SPEICHERPFAD,
            command=lambda: self.gui.show_path_window(Cfg.Texts.BTN_SPEICHERPFAD),
            bootstyle="outline-secondary", padding=(4, 2)
        ).pack(fill=tk.X, pady=BT_PAD.SMALL_PAD_Y, padx=6)

        ttk.Separator(allg_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=BT_PAD.PAD_Y, padx=BT_PAD.PAD_X)

        tb.Label(allg_content, text=Cfg.Texts.LBL_RESET,
                 font=(Cfg.Fonts.FAMILY, Cfg.Fonts.MEDIUM, "bold")).pack(anchor="w", pady=(4, 2), padx=6)

        tb.Button(
            allg_content, text=f"{Cfg.Texts.BTN_RESET_KOMPLETT_ICON}{' ' * Cfg.Texts.CARD_ICON_SPACING}{Cfg.Texts.BTN_RESET_KOMPLETT_TEXT}",
            command=lambda: self.gui.on_reset_selected(Cfg.Texts.RESET_KOMPLETT_DESC),
            bootstyle="outline-warning", padding=(4, 2)
        ).pack(fill=tk.X, pady=BT_PAD.SMALL_PAD_Y, padx=6)

        tb.Button(
            allg_content, text=f"{Cfg.Texts.BTN_RESET_EINGABE_ICON}{' ' * Cfg.Texts.CARD_ICON_SPACING}{Cfg.Texts.BTN_RESET_EINGABE_TEXT}",
            command=lambda: self.gui.on_reset_selected(Cfg.Texts.RESET_EINGABE_DESC),
            bootstyle="outline-warning", padding=(4, 2)
        ).pack(fill=tk.X, pady=BT_PAD.SMALL_PAD_Y, padx=6)

    # --------------------------------------------------------
    #  INPUT / OUTPUT SEKTIONEN
    # --------------------------------------------------------

    def _create_input_section(self, parent):
        """Erstellt den Eingabe-Bereich."""
        card = tk.Frame(parent, bg=Cfg.Colors.TAB_INPUT, bd=0, relief="flat", highlightthickness=0)
        card.pack(fill=tk.X, pady=(0, Cfg.Layout.Sidebar.CARD_PAD_Y))

        tk.Label(
            card, text=Cfg.Texts.TAB_EINGABE, anchor="w",
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold"),
            fg="white", bg=Cfg.Colors.TAB_INPUT,
        ).pack(fill=tk.X, padx=Cfg.Layout.InputOutput.HEADER_PAD_X, pady=Cfg.Layout.InputOutput.HEADER_PAD_Y)

        section = ttk.Frame(card)
        section.pack(fill=tk.BOTH, expand=False,
                     padx=Cfg.Layout.InputOutput.SECTION_PAD_X, pady=Cfg.Layout.InputOutput.SECTION_PAD_Y)

        BG  = Cfg.Layout.BottomGrid
        PAD = Cfg.Layout.Buttons.SMALL_PAD_Y

        def _make_entry(placeholder, row, col, *, is_combo=False):
            if is_combo:
                widget = ttk.Combobox(section, values=Cfg.Defaults.FENSTER_TYPEN, state="disabled")
                widget.set(placeholder)
                widget.grid(row=row, column=col, pady=PAD, padx=BG.PADX_ENTRY, sticky=BG.STICKY)
                widget.bind('<<ComboboxSelected>>', self.gui.on_window_function_changed)
            else:
                widget = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
                widget.grid(row=row, column=col, pady=PAD, padx=BG.PADX_ENTRY, sticky=BG.STICKY)
                widget.insert(0, placeholder)
                widget._is_placeholder = True
                widget.config(state="disabled")
            return widget

        self.gui.entry1 = _make_entry(Cfg.Ph.START_REIHE,  row=0, col=BG.C1)
        self.gui.entry2 = _make_entry(Cfg.Ph.END_REIHE,    row=0, col=BG.C2)
        self.gui.entry3 = _make_entry(Cfg.Ph.START_SPALTE, row=1, col=BG.C1)
        self.gui.entry4 = _make_entry(Cfg.Ph.END_SPALTE,   row=1, col=BG.C2)
        self.gui.entry5 = _make_entry(Cfg.Ph.SAMPLERATE,   row=2, col=BG.C1)
        self.gui.entry6 = _make_entry(Cfg.Ph.FENSTERTYP,   row=2, col=BG.C2, is_combo=True)

        section.columnconfigure(BG.C1, weight=BG.WEIGHT_C1, uniform=BG.UNIFORM)
        section.columnconfigure(BG.C2, weight=BG.WEIGHT_C2, uniform=BG.UNIFORM)

    def _create_output_section(self, parent):
        """Erstellt den Ausgabe-Bereich."""
        card = tk.Frame(parent, bg=Cfg.Colors.TAB_OUTPUT, bd=0, relief="flat", highlightthickness=0)
        card.pack(fill=tk.X, pady=(0, Cfg.Layout.Sidebar.CARD_PAD_Y))

        tk.Label(
            card, text=Cfg.Texts.TAB_AUSGABE, anchor="w",
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE, "bold"),
            fg="white", bg=Cfg.Colors.TAB_OUTPUT,
        ).pack(fill=tk.X, padx=Cfg.Layout.InputOutput.HEADER_PAD_X, pady=Cfg.Layout.InputOutput.HEADER_PAD_Y)

        section = ttk.Frame(card)
        section.pack(fill=tk.BOTH, expand=False,
                     padx=Cfg.Layout.InputOutput.SECTION_PAD_X, pady=Cfg.Layout.InputOutput.SECTION_PAD_Y)

        BG  = Cfg.Layout.BottomGrid
        PAD = Cfg.Layout.Buttons.SMALL_PAD_Y

        def _make_output_entry(placeholder, row, col, columnspan=1):
            widget = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
            widget.grid(row=row, column=col, columnspan=columnspan, pady=PAD, padx=BG.PADX_ENTRY, sticky=BG.STICKY)
            widget.delete(0, tk.END)
            widget.insert(0, placeholder)
            widget.configure(style="EntryPlaceholder.TEntry", state="readonly")
            widget._is_placeholder = True
            return widget

        self.gui.entry9  = _make_output_entry(Cfg.Ph.SAMPLES,   row=0, col=BG.C1)
        self.gui.entry7  = _make_output_entry(Cfg.Ph.STARTZEIT,  row=0, col=BG.C2)
        self.gui.entry10 = _make_output_entry(Cfg.Ph.DT,         row=1, col=BG.C1)
        self.gui.entry8  = _make_output_entry(Cfg.Ph.ENDZEIT,    row=1, col=BG.C2)
        self.gui.entry11 = _make_output_entry(Cfg.Ph.DF,         row=2, col=BG.C1)

        section.columnconfigure(BG.C1, weight=BG.WEIGHT_C1, uniform=BG.UNIFORM)
        section.columnconfigure(BG.C2, weight=BG.WEIGHT_C2, uniform=BG.UNIFORM)

    # --------------------------------------------------------
    #  STATUS BAR & LOGO
    # --------------------------------------------------------

    def _create_status_bar(self, parent):
        """Erstellt die Statusleiste mit Label, Progressanzeige und Floodgauge."""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, padx=Cfg.Layout.Sidebar.PAD_X, pady=(Cfg.Layout.Buttons.SMALL_PAD_Y, 0))

        status_row = ttk.Frame(status_frame)
        status_row.pack(pady=(0, 5))

        self.gui.status_label = ttk.Label(
            status_row,
            text=Cfg.Texts.STATUS_BEREIT,
            style="Status.TLabel"
        )
        self.gui.status_label.pack(side=tk.LEFT, padx=(0, 10))

        self.gui.progress_label = ttk.Label(
            status_row, text="",
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.STATUS)
        )
        self.gui.progress_label.pack(side=tk.LEFT, padx=10)

        self.gui.flood_gauge = tb.Floodgauge(
            status_row,
            bootstyle="primary",
            text="Daten werden geladen...",
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL),
            length=200,
            mode="indeterminate",
        )
        self.gui.flood_gauge.pack(side=tk.LEFT, padx=10)
        self.gui.flood_gauge.pack_forget()

    def _create_logo_background(self, parent):
        """Stadler-Logo als Hintergrundbild in der Mid-Region."""
        try:
            bild_pfad = self.gui.get_resource_path("docs_bilder/stadler_blue_rgb.png")
            bild      = Image.open(bild_pfad)

            stadler_width  = Cfg.Layout.Global.LOGO_WIDTH
            stadler_height = int(stadler_width * Cfg.Layout.Global.LOGO_ASPECT)
            bild           = bild.resize((stadler_width, stadler_height), Image.Resampling.LANCZOS)

            self.gui.stadler_img = ImageTk.PhotoImage(bild)
            logo_label           = ttk.Label(parent, image=self.gui.stadler_img)
            logo_label.place(relx=Cfg.Layout.Logo.RELX, rely=Cfg.Layout.Logo.RELY, anchor="center")
            self.gui._logo_label = logo_label
        except Exception:
            logger.warning("Stadler-Logo konnte nicht geladen werden")

    # --------------------------------------------------------
    #  SPEZIALFENSTER LAYOUTS
    # --------------------------------------------------------

    def create_filter_characteristic_layout(self, filter_info):
        """Erstellt das Layout für die Filter-Charakteristik."""
        self.gui.characteristic_window = tb.Toplevel(self.gui.root)
        self.gui.characteristic_window.title(Cfg.Texts.FILTER_CHAR_WINDOW_TITLE)
        self.gui.apply_icon(self.gui.characteristic_window)

        main_frame = ttk.Frame(self.gui.characteristic_window)
        main_frame.pack(fill=tk.BOTH, expand=True,
                        padx=Cfg.Layout.Main.REGION_PAD[0], pady=Cfg.Layout.Main.REGION_PAD[1])

        # --- Filter-Parameter ---
        info_frame = ttk.LabelFrame(main_frame, text=Cfg.Texts.FILTER_PARAM_SECTION_TITLE,
                                    padding=Cfg.Layout.Filter.PAD_FRAME_WIDE)
        info_frame.pack(fill=tk.X, pady=(0, Cfg.Layout.Sidebar.CARD_PAD_Y))

        info_labels = [
            (Cfg.Texts.FILTER_PARAM_LABEL_TYPE,   filter_info.get('type',         'Unbekannt')),
            (Cfg.Texts.FILTER_PARAM_LABEL_CHAR,   filter_info.get('characteristic','Unbekannt')),
            (Cfg.Texts.FILTER_PARAM_LABEL_ORDER,  str(filter_info.get('order', '-'))),
            (Cfg.Texts.FILTER_PARAM_LABEL_FS,     f"{filter_info.get('sample_rate', '-')} Hz"),
            (Cfg.Texts.FILTER_PARAM_LABEL_CUTOFF1,f"{filter_info.get('cutoff', '-')} Hz"),
            (Cfg.Texts.FILTER_PARAM_LABEL_CUTOFF2,
             f"{filter_info.get('cutoff2', '-')} Hz" if filter_info.get('cutoff2') else "-"),
        ]
        for i, (label, value) in enumerate(info_labels):
            ttk.Label(info_frame, text=label,  font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE, "bold")).grid(
                row=0, column=i * 2,     sticky="e", padx=5, pady=Cfg.Layout.Buttons.SMALL_PAD_Y)
            ttk.Label(info_frame, text=value,  font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE)).grid(
                row=0, column=i * 2 + 1, sticky="w", padx=5, pady=Cfg.Layout.Buttons.SMALL_PAD_Y)

        # --- Inhaltsbereich: Plot + Koeffizienten ---
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=2)
        content_frame.rowconfigure(0, weight=1)

        plot_frame = ttk.LabelFrame(content_frame, text=Cfg.Texts.FREQ_RESPONSE_TITLE,
                                    padding=Cfg.Layout.Filter.PAD_FRAME)
        plot_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.gui.filter_fig    = plt.Figure(figsize=(7, 5))
        self.gui.filter_canvas = FigureCanvasTkAgg(self.gui.filter_fig, master=plot_frame)
        self.gui.filter_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        coef_frame = ttk.LabelFrame(content_frame, text=Cfg.Texts.FILTER_COEFS_TITLE,
                                    padding=Cfg.Layout.Filter.PAD_FRAME_WIDE)
        coef_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        text_scroll = ttk.Scrollbar(coef_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        info_text_widget = ttk.Treeview(
            coef_frame,
            columns=("line",),
            show="headings",
            selectmode="browse",
            yscrollcommand=text_scroll.set,
        )
        info_text_widget.heading("line", text=Cfg.Texts.TREE_INFO_HEADER)
        info_text_widget.column("line", anchor="w", stretch=True, width=520)
        info_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        text_scroll.config(command=info_text_widget.yview)

        return {
            "window":          self.gui.characteristic_window,
            "info_text_widget": info_text_widget,
        }

    def create_signal_selection_layout(self, on_window_close):
        """Erstellt das Layout des Signalauswahl-Bereichs in der Mid-Region."""
        for widget in self.gui.mid_region.winfo_children():
            if widget != getattr(self.gui, '_logo_label', None):
                widget.destroy()

        select_window = ttk.Frame(self.gui.mid_region)
        select_window.pack(fill=tk.BOTH, expand=True)

        # --- Header ---
        header_frame = ttk.Frame(select_window)
        header_frame.pack(fill=tk.X, padx=Cfg.Layout.Sidebar.PAD_X, pady=(Cfg.Layout.Buttons.SMALL_PAD_Y, 0))

        ttk.Label(
            header_frame, text=Cfg.Texts.SIGNAL_SELECT_HEADER,
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE)
        ).pack(side=tk.LEFT)

        # --- Suche ---
        search_var   = tk.StringVar()
        search_entry = ttk.Entry(select_window, textvariable=search_var, font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE))
        search_entry.pack(pady=Cfg.Layout.Buttons.SMALL_PAD_Y, padx=Cfg.Layout.Sidebar.PAD_X, fill=tk.X)

        # --- Ausgewählte Signale Anzeige ---
        selected_display_var = tk.StringVar(value=Cfg.Texts.NO_SIGNALS_SELECTED)
        selected_display_style = ttk.Style()
        selected_display_style.configure("SelectedDisplay.TEntry", foreground="blue")
        ttk.Entry(
            select_window, textvariable=selected_display_var,
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), state="readonly",
            style="SelectedDisplay.TEntry",
        ).pack(pady=Cfg.Layout.Buttons.SMALL_PAD_Y, padx=Cfg.Layout.Sidebar.PAD_X, fill=tk.X)

        # --- Aktionen (zuerst packen → immer am unteren Rand sichtbar) ---
        actions_frame = ttk.Frame(select_window)
        actions_frame.pack(side=tk.BOTTOM, pady=Cfg.Layout.Buttons.PAD_Y)

        # --- Optionen (zuerst packen → immer am unteren Rand sichtbar) ---
        opts_frame = ttk.LabelFrame(
            select_window, text=Cfg.Texts.LBL_OPTIONS,
            padding=Cfg.Layout.InputOutput.SECTION_PAD_Y
        )
        opts_frame.pack(side=tk.BOTTOM, padx=Cfg.Layout.Sidebar.PAD_X, pady=Cfg.Layout.Buttons.PAD_Y, fill=tk.X)

        # --- Paned Window für Listbox und Gruppen (mit Splitter) ---
        paned_window = ttk.PanedWindow(select_window, orient=tk.VERTICAL)
        paned_window.pack(pady=Cfg.Layout.Main.REGION_PAD[1], padx=Cfg.Layout.Main.REGION_PAD[0],
                         fill=tk.BOTH, expand=True)

        # --- Listbox ---
        list_frame = ttk.Frame(paned_window)
        paned_window.add(list_frame, weight=1)

        listbox = ttk.Treeview(list_frame, show="tree", selectmode="extended")
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Treeview Font konfigurieren ---
        select_style = ttk.Style(select_window)
        select_style.configure("Treeview", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.PLOT))

        list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=list_scrollbar.set)

        # --- Gruppen ---
        groups_frame = ttk.LabelFrame(
            paned_window, text=Cfg.Texts.LBL_GROUPS,
            padding=Cfg.Layout.InputOutput.SECTION_PAD_Y
        )
        paned_window.add(groups_frame, weight=0)

        group_buttons_frame = ttk.Frame(groups_frame)
        group_buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        groups_canvas    = tk.Canvas(groups_frame, highlightthickness=0, height=120)
        groups_scrollbar = ttk.Scrollbar(groups_frame, orient="vertical", command=groups_canvas.yview)
        groups_canvas.configure(yscrollcommand=groups_scrollbar.set)
        groups_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        groups_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        groups_container = ttk.Frame(groups_canvas)
        groups_canvas_window = groups_canvas.create_window((0, 0), window=groups_container, anchor="nw")

        def _on_groups_configure(event):
            groups_canvas.configure(scrollregion=groups_canvas.bbox("all"))

        def _on_groups_canvas_resize(event):
            groups_canvas.itemconfig(groups_canvas_window, width=event.width)

        groups_container.bind("<Configure>", _on_groups_configure)
        groups_canvas.bind("<Configure>",    _on_groups_canvas_resize)

        return {
            "select_window":       select_window,
            "search_var":          search_var,
            "search_entry":        search_entry,
            "selected_display_var": selected_display_var,
            "listbox":             listbox,
            "groups_container":    groups_container,
            "group_buttons_frame": group_buttons_frame,
            "opts_frame":          opts_frame,
            "actions_frame":       actions_frame,
        }

    def create_live_plot_layout(self, selected_signal):
        """Erstellt das reine Layout eines Live-Plot-Fensters."""
        LP = Cfg.Layout.LivePlot

        plot_window = tb.Toplevel(self.gui.root)
        self.gui.apply_icon(plot_window)

        # ---------- Kleinerer Font für Plotfenster (global) ----------
        plot_style = ttk.Style(plot_window)
        plot_style.configure("TNotebook.Tab", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.PLOT))
        plot_style.configure("TLabel", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.PLOT))
        plot_style.configure("TButton", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.PLOT))
        plot_style.configure("TEntry", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.PLOT))
        plot_style.configure("Treeview", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.PLOT))

        plot_window.title(f"Plot: {selected_signal}")

        plot_frame = ttk.Frame(plot_window)
        plot_frame.pack(fill=tk.BOTH, expand=True)

        fig    = plt.Figure(figsize=(16, 12))
        fig.set_tight_layout({'pad': 1.0, 'h_pad': 1.5, 'w_pad': 1.0})
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
            canvas.draw_idle()

        toolbar.home = home_with_reset

        toolbar.pack(side=tk.RIGHT)

        options_frame = ttk.LabelFrame(
            plot_frame, text=Cfg.Texts.LBL_ANZEIGE,
            padding=Cfg.Layout.InputOutput.SECTION_PAD_Y
        )
        options_frame.pack(side=tk.TOP, fill=tk.X, padx=LP.OPTIONS_PAD_X, pady=LP.OPTIONS_PAD_Y)

        analysis_frame = ttk.LabelFrame(
            plot_frame, text=Cfg.Texts.LBL_ANALYSE,
            padding=Cfg.Layout.InputOutput.SECTION_PAD_Y
        )
        analysis_frame.pack(side=tk.TOP, fill=tk.X, padx=LP.ANALYSE_PAD_X, pady=LP.ANALYSE_PAD_Y)

        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                          padx=LP.CANVAS_PAD_X, pady=LP.CANVAS_PAD_Y)

        _resize_job = [None]

        def on_canvas_resize(event=None):
            if event is None or event.width <= 10 or event.height <= 10:
                return
            if _resize_job[0] is not None:
                canvas_widget.after_cancel(_resize_job[0])
            captured_w = event.width
            captured_h = event.height
            def do_resize():
                try:
                    dpi = fig.get_dpi()
                    new_w = max(captured_w / dpi, 4)
                    new_h = max(captured_h / dpi, 3)
                    if (abs(fig.get_figwidth() - new_w) > 0.1
                            or abs(fig.get_figheight() - new_h) > 0.1):
                        fig.set_size_inches(new_w, new_h)
                    canvas.draw_idle()
                except Exception as e:
                    logger.debug("Figure-Resize (draw_idle) fehlgeschlagen: %s", e)
            _resize_job[0] = canvas_widget.after(100, do_resize)

        canvas_widget.bind("<Configure>", on_canvas_resize)

        def _initial_resize():
            try:
                cw = canvas_widget.winfo_width()
                ch = canvas_widget.winfo_height()
                if cw > 10 and ch > 10:
                    dpi = fig.get_dpi()
                    new_w = max(cw / dpi, 4)
                    new_h = max(ch / dpi, 3)
                    if (abs(fig.get_figwidth() - new_w) > 0.1
                            or abs(fig.get_figheight() - new_h) > 0.1):
                        fig.set_size_inches(new_w, new_h)
                    canvas.draw()
            except Exception as e:
                logger.debug("Figure-Resize (draw) fehlgeschlagen: %s", e)

        plot_window.after(200, _initial_resize)

        return {
            "window":         plot_window,
            "fig":            fig,
            "canvas":         canvas,
            "toolbar_frame":  toolbar_frame,
            "options_frame":  options_frame,
            "analysis_frame": analysis_frame,
        }