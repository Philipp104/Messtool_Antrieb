"""
Setup – Zentraler Styleguide & Konfiguration
=============================================

STRUKTUR ÜBERSICHT:
───────────────────────────────────────────────────────────────────────
  Cfg.Fonts          → Schriftarten & Größen          (UI-weit)
  Cfg.Colors         → Farben & Plot-Stile             (UI-weit)
  Cfg.Layout         → Abstände, Fenster, Figure       (UI-weit)
  Cfg.Texts          → Alle UI-Texte & Labels          (UI-weit)
  Cfg.Defaults       → Standardwerte                   (UI-weit)
  Cfg.Limits         → Validierungsgrenzen             (UI-weit)
  Cfg.Errors         → Alle Fehlermeldungen            (UI-weit)
  Cfg.Status         → Alle Statusmeldungen            (UI-weit)
  Cfg.Logs           → Alle Log-Nachrichten            (UI-weit)
  Cfg.Filter         → Filter-Konfiguration            → filter_manager.py
  Cfg.FFT            → FFT-Konfiguration               → data_processor.py
  Cfg.Export         → Export-Optionen & Pfade         → file_handler.py
  Cfg.Signal         → Signalauswahl & Gruppen         → signal_auswahl_manager.py
  Cfg.Analysis       → Analyse-Typen & Plot-Zuordnung  → analyse_*.py
  Cfg.AxisLabels     → Achsenbeschriftungen            → plot_manager.py
  Cfg.Data           → Spalten-Ausschlüsse             → data_validator.py
───────────────────────────────────────────────────────────────────────

→ Zugriff immer über: Cfg.<Bereich>.<KONSTANTE>
→ Dieses File ist der EINZIGE Ort für Konfigurationsänderungen.
"""


# ============================================================
#  FONTS – Schriften                            (alle UI-Files)
# ============================================================

class Fonts:
    FAMILY  = "Arial"

    # Allgemeine UI‑Schriften
    SMALL   = 12
    MEDIUM  = 12
    LARGE   = 12
    HEADER  = 12
    TABS    = 12

    # Spezialschriften
    STATUS  = 12          # Statuslabel
    PLOT    = 8         # Plotfenster-Widgets (kleiner!)

    # ---- Zentrale Schriftgrößen für matplotlib-Plots ----
    class Plots:
        """Zentrale Schriftgrößen für alle Plot-Elemente (matplotlib)."""
        TICK_LABELS = 10      # Achsen-Tick-Labels (x/y)
        AXIS_LABELS = 11      # Achsenbeschriftung (xlabel/ylabel)
        AXIS_TITLE  = 12      # Unterpunkt-Titel (ax.set_title)
        PLOT_TITLE  = 14      # Oberster Plot-Titel (fig.suptitle)
        LEGEND      = 10      # Legenden


# ============================================================
#  COLORS – Farben & Plot-Stile                (alle UI-Files)
# ============================================================

class Colors:
    """Farbschema des gesamten UI und aller Plots."""

    # --- Branding & Basis ---
    WINE      = "#a0616c"
    PRIMARY   = "#0d6efd"
    SUCCESS   = "#198754"
    WARNING   = "#fd7e14"
    SECONDARY = "#6c757d"
    DANGER    = "#dc3545"

    CARD_MAP = {
        "danger":    DANGER,
        "primary":   PRIMARY,
        "success":   SUCCESS,
        "warning":   WARNING,
        "secondary": SECONDARY,
        "wine":      WINE,
    }

    # --- Sidebar ---
    SIDEBAR_HEADER_BG = "#3a3a3a"
    SIDEBAR_INNER_BG  = "#2b2b2b"
    SIDEBAR_TEXT_BG   = "#4a4a4a"

    # --- Sidebar Karten (dezent) ---
    CARD_IMPORT  = "#8b4a52"   # Weinrot (gedämpft)
    CARD_PROCESS = "#4a7ab5"   # Hellblau (gedämpft)
    CARD_SIGNAL  = "#4a8a5c"   # Grün (gedämpft)

    # --- Tabs ---
    TAB_INPUT        = PRIMARY
    TAB_OUTPUT       = SUCCESS
    TAB_INACTIVE     = "#e9ecef"
    TAB_TEXT_ACTIVE  = "white"
    TAB_TEXT_INACTIVE = "#333333"

    # --- Gruppen-Hervorhebung (signal_auswahl_manager.py) ---
    GROUP_SELECTED_BG = "#d9edf7"
    GROUP_LABEL       = "blue"

    # --- Einheiten-Palette für Plots (plot_manager.py) ---
    UNIT_PALETTE = [
        "#e6f3ff", "#e6ffe6", "#fff3e6", "#ffe6e6", "#f3e6ff",
        "#e6ffff", "#fff9e6", "#ffe6f3", "#e6ffe9", "#f0e6ff",
    ]

    # --- Signalfarben (plot_manager.py) ---
    SIGNAL_ORIGINAL  = "#2c7fb8"
    SIGNAL_FILTERED  = "#d62728"
    SIGNAL_DIFF      = "#a51c30"
    SIGNAL_INT       = "#1b6e1b"
    SIGNAL_AVG       = "#ff8c00"
    SIGNAL_RMS       = "#6f42c1"
    LINEWIDTH_ORIGINAL = 1.5

    # --- Linienstile (plot_manager.py) ---
    LINESTYLE_DIFF = "--"
    LINESTYLE_INT  = ":"
    LINESTYLE_AVG  = "-"
    LINESTYLE_RMS  = "--"

    # --- Cursor & Auswahl (plot_manager.py) ---
    CURSOR_PRIMARY_COLOR   = "#dc3545"
    CURSOR_SECONDARY_COLOR = "#0d6efd"
    CURSOR_LINESTYLE       = "--"
    CURSOR_LINEWIDTH       = 1
    CURSOR_ALPHA           = 0.7
    SELECTION_LINESTYLE    = ":"
    SELECTION_LINEWIDTH    = 1

    # --- Annotation / Tooltip (plot_manager.py) ---
    ANNOTATION_BG          = "#ffffff"
    ANNOTATION_FG          = "#000000"
    ANNOTATION_ALPHA       = 0.85
    ANNOTATION_BORDER      = "#999999"
    ANNOTATION_ARROW_STYLE = "->"
    ANNOTATION_BOX_ALPHA   = 0.8

    # --- Grid (alle Plots) ---
    GRID_COLOR     = "#bfbfbf"
    GRID_ALPHA     = 0.5
    GRID_LINESTYLE = "--"

    # --- Overlay & Filter (plot_manager.py) ---
    OVERLAY_CMAP             = "Set1"
    FILTER_CUTOFF_LINESTYLE  = ":"


# ============================================================
#  STYLES – Custom TTK-Button-Styles            (gui_layout_manager.py)
# ============================================================

class Styles:
    WINE_BTN   = "WineBtn.TButton"
    BLUE_BTN   = "BlueBtn.TButton"
    GREEN_BTN  = "GreenBtn.TButton"
    WINE_FRAME  = "WineCard.TFrame"
    BLUE_FRAME  = "BlueCard.TFrame"
    GREEN_FRAME = "GreenCard.TFrame"
    WINE_LABEL  = "WineCard.TLabel"
    BLUE_LABEL  = "BlueCard.TLabel"
    GREEN_LABEL = "GreenCard.TLabel"

    @staticmethod
    def register():
        from tkinter import ttk
        _s = ttk.Style()

        # Buttons
        for name, color, active in [
                (Styles.WINE_BTN,  Colors.CARD_IMPORT,  "#7a3e46"),  # Weinrot
                (Styles.BLUE_BTN,  Colors.CARD_PROCESS, "#3d6699"),  # Hellblau
                (Styles.GREEN_BTN, Colors.CARD_SIGNAL,  "#3d7a4e"),  # Grün
            ]:
                _s.configure(
                    name,
                    font=(Fonts.FAMILY, 12),
                    background=color,
                    foreground="white",
                    bordercolor=color,
                    darkcolor=color,
                    lightcolor=color,
                    relief="flat",
                    padding=(8, 4),
                )

                # Disabled-Zustand: Grau und nicht klickbar
                _s.map(
                    name,
                    background=[
                        ("active",   active),                # Hintergrund bei Klick
                        ("disabled", "#cccccc"),             # Grau, wenn deaktiviert
                        ("!disabled", color),                # Standard-Hintergrund
                    ],
                    foreground=[
                        ("disabled", "#666666"),              # Dunkleres Grau für Text
                        ("!disabled", "white"),              # Standard-Textfarbe
                    ],
                    relief=[
                        ("disabled", "sunken"),              # Optisch "eingedrückt"
                        ("!disabled", "flat"),
                    ],
                )

        # Card Frames + Labels
        for name, color in [
            (Styles.WINE_FRAME,  Colors.CARD_IMPORT),
            (Styles.BLUE_FRAME,  Colors.CARD_PROCESS),
            (Styles.GREEN_FRAME, Colors.CARD_SIGNAL),
        ]:
            _s.configure(name, background=color)
        for name, color in [
            (Styles.WINE_LABEL,  Colors.CARD_IMPORT),
            (Styles.BLUE_LABEL,  Colors.CARD_PROCESS),
            (Styles.GREEN_LABEL, Colors.CARD_SIGNAL),
        ]:
            _s.configure(name, background=color, foreground="white", anchor = "w")

    @staticmethod
    def force_apply(widget, style_name):
        widget.tk.call(widget._w, 'configure', '-style', style_name)

# ============================================================
#  LAYOUT – Abstände, Fenster, Figure          (alle UI-Files)
# ============================================================

class Layout:
    """Alle Layout-Parameter: Padding, Fenstergrößen, Figure-Maße."""

    # --- Global ---
    class Global:
        PAD_X        = 10
        PAD_Y        = 8
        SIDEBAR_WIDTH = 700
        LOGO_WIDTH   = 400
        LOGO_ASPECT  = 80 / 500
        CARD_PAD_X   = 6
        CARD_PAD_Y   = 4

    # --- Matplotlib Figure (plot_manager.py, analyse_*.py) ---
    class Figure:
        BASE_WIDTH      = 14
        MIN_HEIGHT      = 8
        SUBPLOT_HEIGHT  = 2
        AXIS_MARGIN_PERCENT = 5
        HSPACE          = 0.35
        WSPACE          = 0.20
        TOP_ADJUST      = 0.95
        FIG_SIZE_SINGLE   = (12, 6)
        FIG_SIZE_DOUBLE   = (12, 8)
        FIG_SIZE_OVERVIEW = (14, 16)
        FIG_SIZE_FILTER   = (12, 6)
        # Fehlertext
        ERROR_TEXT_POS   = (0.5, 0.5)
        ERROR_TEXT_ALIGN = ("center", "center")
        ERROR_TEXT_FONT  = (Fonts.FAMILY, Fonts.MEDIUM)
        ERROR_TEXT_COLOR = Colors.DANGER
        # Grid (übernimmt von Colors)
        GRID_LINESTYLE = Colors.GRID_LINESTYLE
        GRID_ALPHA     = Colors.GRID_ALPHA
        GRID_COLOR     = Colors.GRID_COLOR

    # --- Fenstergrößen ---
    # --- Control-Leiste (synchroner Zoom) ---
    class Control:
        PAD_X       = 5
        PAD_Y       = 5
        FONT        = (Fonts.FAMILY, Fonts.SMALL, "bold")
        LABEL_WIDTH = 120

    class Checkbutton:
        PAD_X = 5
        PAD_Y = 2

    class Reset:
        PAD_X        = 5
        PAD_Y_TOP    = 0
        PAD_Y_BOTTOM = 5

    class Canvas:
        PAD_X = 0
        PAD_Y = 0

    class Toolbar:
        PAD_X = 0
        PAD_Y = 0

    class Sidebar:
        PAD_X         = 10
        PAD_Y         = 10
        HEADER_HEIGHT = 70
        CARD_PAD_X    = 8
        CARD_PAD_Y    = 10

    class Main:
        REGION_PAD       = (8, 8)
        INNER_REGION_PAD = (4, 4)

    class InputOutput:
        HEADER_PAD_X  = 8
        HEADER_PAD_Y  = (6, 4)
        SECTION_PAD_X = 8
        SECTION_PAD_Y = (0, 6)

    class Buttons:
        PAD_X       = 6
        PAD_Y       = 4
        SMALL_PAD_Y = 2
        LARGE_PAD_Y = 8

    class Notebook:
        TAB_PAD = (12, 4)

    class Scrollbar:
        SCROLL_PAD_Y = 10

    class Logo:
        RELX = 0.5
        RELY = 0.5

    class Filter:
        PAD_FRAME      = (5, 5)
        PAD_FRAME_WIDE = (10, 5)

    # --- Live-Plot-Fenster (live_plot.py) ---
    class LivePlot:
        OPTIONS_PAD_X      = 8
        OPTIONS_PAD_Y      = 6
        OPTIONS_ITEM_PAD_X = 6
        ANALYSE_PAD_X      = 8
        ANALYSE_PAD_Y      = 6
        ANALYSE_ITEM_PAD_X = 6
        TOOLBAR_PAD_X      = 8
        TOOLBAR_PAD_Y      = 4
        TOOLBAR_BUTTON_PAD_X = 8
        CANVAS_PAD_X       = 0
        CANVAS_PAD_Y       = 0

    # --- Grid-Regeln ---
    class BottomGrid:
        C1       = 0
        C2       = 1
        FULLSPAN = 2
        STICKY   = "ew"
        PADX_ENTRY = 8
        WEIGHT_C1  = 1
        WEIGHT_C2  = 1
        UNIFORM    = "form"

    class SidebarGrid:
        SINGLE_COL = 0
        STICKY     = "ew"
        PADX       = 8
        WEIGHT     = 1
        UNIFORM    = "sidebar"


# ============================================================
#  TEXTS – UI-Texte & Labels                   (alle UI-Files)
# ============================================================

class Texts:
    """Alle sichtbaren UI-Texte, Buttons, Labels und Dialoge."""

    # --- App / Fenster ---
    WINDOW_TITLE = "Signal-Analyse Tool"
    DASHBOARD    = "Dashboard"
    HINT         = "Hinweis"
    ERROR        = "Fehler"

    # --- Tabs ---
    TAB_EINGABE  = "📥 Eingabedaten"
    TAB_AUSGABE  = "📤 Ausgabedaten"

    # --- Sidebar-Karten ---
    CARD_IMPORT_TITLE      = "Datenimport"
    CARD_IMPORT_ICON       = "📥"
    CARD_VERARBEITUNG_TITLE = "Datenverarbeitung"
    CARD_VERARBEITUNG_ICON  = "🛠"
    CARD_SIGNAL_TITLE      = "Signalverarbeitung"
    CARD_SIGNAL_ICON       = "📈"
    CARD_ALLGEMEIN_TITLE   = "Allgemeines"
    CARD_ALLGEMEIN_ICON    = "ℹ"
    CARD_ICON_SPACING      = 1  # Leerzeichen nach dem Icon

    # --- Buttons (main_ui.py) ---
    BTN_IMPORT          = "Messdaten Import"
    BTN_VERARBEITUNG    = "Datenverarbeitung"
    BTN_SIGNALE         = "Signalverarbeitung"
    BTN_RESET_KOMPLETT_ICON = "🗑"
    BTN_RESET_KOMPLETT_TEXT = "Komplett"
    BTN_RESET_EINGABE_ICON = "🧽"
    BTN_RESET_EINGABE_TEXT = "Eingaben"
    BTN_HILFE           = "Hilfe"
    BTN_HERKUNFTSPFAD   = "Datei-Herkunftspfad"
    BTN_SPEICHERPFAD    = "Spektrum-Speicherpfad"
    BTN_CLOSE           = "✕"
    BTN_OK              = "OK"
    BTN_CANCEL          = "Abbrechen"

    # --- Radio Buttons ---
    RB_PLOTS_SPEKTRUM = "Plots und Spektrum speichern"
    RB_PLOTS          = "Plots speichern"
    RB_SPEKTRUM       = "Spektrum speichern"
    RB_NICHTS         = "Nichts speichern"

    # --- Import ---
    CB_CSV_DEFAULT = "CSV"

    # --- Reset ---
    RESET_KOMPLETT_DESC = "Komplett zurücksetzen"
    RESET_EINGABE_DESC  = "Nur Eingabefelder zurücksetzen"

    # --- Status ---
    STATUS_BEREIT      = "Bereit"
    STATUS_VERARBEITUNG = "Verarbeitung läuft..."
    STATUS_NEUE_DATEI  = "Neue Datei bereit"
    STATUS_NEUE_EINGABEN = "Neue Eingaben bereit"

    # --- Analyse-Titel (analyse_*.py) ---
    DIFFERENTIAL_ANALYSE_TITLE       = "Differential Analyse"
    DIFFERENTIAL_ANALYSE_MULTI_TITLE = "Differential Analyse (Multi)"
    AVG_ANALYSE_TITLE                = "AVG Analyse"
    AVG_ANALYSE_MULTI_TITLE          = "AVG Analyse (Multi)"
    RMS_ANALYSE_TITLE                = "RMS Analyse"
    RMS_ANALYSE_MULTI_TITLE          = "RMS Analyse (Multi)"
    FFT_ANALYSE_TITLE                = "FFT Analyse"
    FFT_ANALYSE_MULTI_TITLE          = "FFT Analyse (Multi)"
    INTEGRAL_ANALYSE_TITLE           = "Integral Analyse"
    INTEGRAL_ANALYSE_MULTI_TITLE     = "Integral Analyse (Multi)"
    VARIANZ_ANALYSE_TITLE            = "Varianz/Autokorrelation Analyse"
    VARIANZ_ANALYSE_MULTI_TITLE      = "Varianz/Autokorrelation Analyse (Multi)"
    ANALYSE_ERGEBNISSE_TITLE         = "Analyse-Ergebnisse"
    ZEITBEREICH_DIALOG_TITLE         = "Zeitbereich wählen - {0}"
    MULTI_SIGNAL_SUFFIX              = "(+{0} weitere)"
    SYNC_ZOOM_LABEL                  = "Synchroner Zoom:"

    # --- Signalauswahl (signal_auswahl_manager.py) ---
    SIGNAL_SELECT_HEADER       = "Wähle die Signale aus, die angezeigt werden sollen:"
    NO_SIGNALS_SELECTED        = "Keine Signale ausgewählt"
    LBL_GROUPS                 = "Signal-Gruppen"
    LBL_OPTIONS                = "Optionen"
    BTN_GRUPPE_ERSTELLEN       = "Gruppe erstellen"
    BTN_GRUPPE_LOESCHEN        = "Gruppe(n) löschen"
    STATUS_KEIN_SIGNAL         = "Keine Signale ausgewählt"
    GRUPPE_ERSTELLEN_HINWEIS   = "Bitte wählen Sie die Signale für die Gruppe aus.\nHinweis: Am besten ähnliche Signale für eine übersichtliche Gruppe."
    GRUPPE_ZU_WENIG_SIGNALE    = "Bitte mindestens 1 Signal auswählen, um eine Gruppe zu erstellen."
    GRUPPE_MAX_ERREICHT        = "Es können maximal {0} Gruppen erstellt werden."
    GRUPPE_ERSTELLT            = "Gruppe {0} wurde erstellt mit {1} Signal(en)."
    GRUPPE_LOESCHEN_BESTAETIGUNG = "Möchten Sie wirklich {0} Gruppe(n) löschen?"
    EXPORT_ABGEBROCHEN         = "Export abgebrochen."
    EXPORT_KEINE_DATEN         = "Keine verarbeiteten Daten vorhanden."
    BTN_PLOT                   = "Signale plotten"
    BTN_EXPORT                 = "Exportieren"
    BTN_CLEAR                  = "Auswahl löschen"

    # --- Filter-Dialog (filter_manager.py, signal_auswahl_manager.py) ---
    BTN_FILTER                 = "Filter einstellen"
    FILTER_CHAR_WINDOW_TITLE   = "Filter-Charakteristik"
    FILTER_DIALOG_TITEL        = "Filter einstellen"
    FILTER_PARAM_SECTION_TITLE = "Filter-Parameter"
    FILTER_PARAM_LABEL_TYPE    = "Filtertyp:"
    FILTER_PARAM_LABEL_CHAR    = "Charakteristik:"
    FILTER_PARAM_LABEL_ORDER   = "Ordnung:"
    FILTER_PARAM_LABEL_FS      = "Abtastrate:"
    FILTER_PARAM_LABEL_CUTOFF1 = "Grenzfrequenz 1:"
    FILTER_PARAM_LABEL_CUTOFF2 = "Grenzfrequenz 2:"
    FREQ_RESPONSE_TITLE        = "Frequenzgang"
    FILTER_COEFS_TITLE         = "Filter-Koeffizienten"
    TREE_INFO_HEADER           = "Information"
    FILTER_FEHLER_GRENZFREQUENZ = "Bandpass-Filter benötigt BEIDE Grenzfrequenzen!\n\nBitte geben Sie sowohl die untere als auch die obere Grenzfrequenz ein."
    FILTER_FEHLER_EINGABE      = "Beide Grenzfrequenzen müssen gültige Zahlen sein!"
    FILTER_FEHLER_REIHENFOLGE  = "Die untere Grenzfrequenz ({0} Hz) muss kleiner sein\nals die obere Grenzfrequenz ({1} Hz)!"

    # --- Live-Plot (live_plot.py) ---
    LBL_ANZEIGE       = "Anzeige"
    LBL_ANALYSE       = "Analyse"
    LP_ORIGINAL       = "Original"
    LP_FILTERED       = "Gefiltert"
    LP_FFT_MASTER     = "FFT anzeigen"
    LP_FFT_AMP        = "Amplitude (FFT)"
    LP_FFT_PHASE      = "Phase (FFT)"
    LP_AVG            = "AVG"
    LP_RMS            = "RMS"
    LP_DIFFERENTIAL   = "Differential"
    LP_INTEGRAL       = "Integral"
    LP_EXPORT         = "Exportieren"
    LP_FILTER_NOT_READY = "Filter nicht konfiguriert"
    LP_FILTER_SELECT  = "Bitte Filter wählen/einstellen"
    LP_DIALOG_FFT     = "FFT - Zeitbereich auswählen"
    LP_DIALOG_AVG     = "AVG - Zeitbereich auswählen"
    LP_DIALOG_RMS     = "RMS - Zeitbereich auswählen"

    # --- Zeitbereich-Dialog (dialog_zeitbereich.py) ---
    DLG_TIME_RANGE_GENERIC      = "Zeitbereich auswählen"
    DLG_SELECTED_SIGNAL_PREFIX  = "Ausgewähltes Signal:"
    DLG_UNFILTERED              = "Ungefiltert"
    DLG_FILTER_INFO             = "Gefiltert: {type}, Ordnung: {order}, Charakteristik: {characteristic}"
    TIME_RANGE_ADD              = "+ Zeitbereich hinzufügen"
    TIME_RANGE_N                = "Zeitbereich {0}:"
    UNIT_S                      = "[s]"

    # --- Overlay / Übersicht (plot_manager.py) ---
    OVERLAY_TITLE    = "Überlagerte Signale [Einheiten: gemischt]"
    OVERVIEW_SUPTITLE = "Übersicht aller Signale ({0} Kanäle) [Einheiten gemischt]"
    STARTTIME_LABEL  = "Startzeit"
    DIFF_INT_TITLE   = "Differential / Integral (ausgewählt) [Einheiten: gemischt]"

    # --- Pfad-Fenster (main_ui.py) ---
    LBL_PFAD              = "Speicherpfade"
    LBL_RESET             = "Zurücksetzen"
    PFAD_HERKUNFT_TITLE   = "Datei Herkunftspfad"
    PFAD_HERKUNFT_EMPTY   = "Keine Datei geladen"
    PFAD_SPEICHER_TITLE   = "Spektrum Speicherpfad"
    PFAD_SPEICHER_EMPTY   = "Kein Speicherpfad festgelegt"

    # --- Allgemeine Fehlertexte im UI ---
    NO_DATA               = "Keine verarbeiteten Daten vorhanden."
    SELECT_SIGNAL         = "Signal auswählen:"
    SELECT_SIGNAL_FIRST   = "Bitte zuerst ein Signal in der Liste auswählen."
    SIGNAL_NOT_FOUND      = "Signal '{0}' wurde nicht gefunden."
    NO_DT                 = "Keine gültige Abtastzeit (dt) vorhanden."
    PLOT_ERROR            = "Fehler bei der Darstellung:\n{0}"
    SIGNAL_FALLBACK       = "Signal {0}"
    NO_TIME_CURVE_SELECTED = "Keine Zeitkurve ausgewählt"
    ERROR_SHEET_LOAD      = "Fehler beim Laden des Sheets:"

    # --- Plot-Titel (gui_config → plot_manager.py) ---
    OVERVIEW_WINDOW_TITLE        = "Signalübersicht"
    OVERVIEW_PLOT_TITLE          = "Signalübersicht ({} Kanäle)"
    FILTER_PLOT_TITLE            = "Signal: {} (mit Filter)"
    FILTER_PLOT_ORIGINAL_TITLE   = "{} - Original"
    FILTER_PLOT_FILTERED_TITLE   = "gefiltert ({})"
    FILTER_PLOT_FILTERED_TITLE_FULL = "{} - Gefiltert ({})"
    LIVE_PLOT_TITLE              = "Live-Plot: {}"

    # --- Messages (plot_manager.py) ---
    PLOT_EMPTY     = "Kein gültiger Filter\noder\nParameter nicht gesetzt"
    NO_SIGNALS     = "Keine gültigen Signale ausgewählt"
    NO_RANGE       = "Kein Signal im gewählten Zeitbereich"
    FILTER_FORMAT  = " (Gefiltert: {type}, {order}, {characteristic})"

    # --- Verarbeitungsoptionen (data_processor.py) ---
    PROCESS_ORIGINAL = "Original"
    PROCESS_FILTERED = "Gefiltert"
    PROCESS_AVG      = "Durchschnitt (AVG)"
    PROCESS_RMS      = "Effektivwert (RMS)"
    PROCESS_DIFF     = "Ableitung"
    PROCESS_INTEGRAL = "Integral"
    PROCESS_FFT      = "FFT"


# ============================================================
#  DEFAULTS – Standardwerte                    (alle Files)
# ============================================================

class Defaults:
    """Standardwerte für Eingabefelder, Filter, FFT und Fenster."""

    # --- Eingabefelder (main_ui.py, data_validator.py) ---
    START_REIHE    = 1
    END_REIHE      = 10000
    START_SPALTE   = 1
    END_SPALTE     = 100
    SAMPLERATE     = 20
    FENSTERTYP     = "Rechteck"
    START_ROW_PREFILL = 2

    VALUES_CONFIG = [
        (1,         "Start Reihe --> 1"),
        (10000,     "End Reihe --> 10000"),
        (1,         "Start Spalte --> 1"),
        (100,       "End Spalte --> 100"),
        (20,        "Samplefrequenz FS --> 20"),
        ("Rechteck","Fenster --> Rechteck"),
    ]

    # --- Filter (filter_manager.py, signal_auswahl_manager.py) ---
    FILTER_TYP            = "Kein Filter"
    FILTER_CHARAKTERISTIK = "butterworth"
    FILTER_ORDNUNG        = "1.Ordnung"
    GRENZFREQUENZ_1       = 2
    GRENZFREQUENZ_2       = 6
    FILTER_TYPEN          = ["Kein Filter", "Tiefpass", "Hochpass", "Bandpass"]
    FILTER_CHARAKTERISTIKEN = ["butterworth", "bessel", "Chebyshev I", "Elliptic"]
    FILTER_ORDNUNGEN      = ["1.Ordnung", "2.Ordnung", "3.Ordnung", "4.Ordnung"]
    FILTER_ORDER_INT      = 1
    CUTOFF_FREQ           = 5.0     # Hz
    SAMPLE_RATE           = 20.0    # Hz

    # --- FFT (data_processor.py, plot_manager.py) ---
    FFT_WINDOW_TYPE    = "hanning"
    FFT_NORMALIZE      = True
    FFT_LOG_SCALE      = True
    FENSTER_TYPEN      = ["Fenstertyp wählen:", "Rechteck", "Hanning"]

    # --- Plot-Stile (plot_manager.py) ---
    FILTER_RESPONSE_LINESTYLE = "-"
    FILTER_RESPONSE_LINEWIDTH = 2

    # --- Signalgruppen (signal_auswahl_manager.py) ---
    MAX_GROUPS  = 999
    MAX_SIGNALS = 999


# ============================================================
#  LIMITS – Validierungsgrenzen                (alle Files)
# ============================================================

class Limits:
    """Min/Max-Grenzen für alle Eingaben – genutzt in filter_manager.py, data_validator.py, data_processor.py."""

    # --- Filterordnung ---
    FILTER_ORDER_MIN = 1
    FILTER_ORDER_MAX = 10

    # --- Grenzfrequenz ---
    CUTOFF_FREQ_MIN  = 0.1       # Hz
    CUTOFF_FREQ_MAX  = 10000.0   # Hz

    # --- Samplerate ---
    SAMPLE_RATE_MIN  = 1.0       # Hz
    SAMPLE_RATE_MAX  = 10000.0   # Hz

    # --- Zeilen/Spalten (data_validator.py) ---
    MIN_ROW          = 1
    MIN_COL          = 0
    DEFAULT_END_ROW  = 10000
    DEFAULT_END_COL  = 100

    # --- FFT (data_processor.py) ---
    FFT_MIN_SAMPLES  = 64
    FFT_MAX_SAMPLES  = 1024 * 1024

    # --- SOS-Filter (filter_manager.py) ---
    SOS_NUM_POINTS   = 1024
    MAX_SOS_ORDER    = 20
    DEFAULT_RIPPLE_DB = 1.0      # Chebyshev-Welligkeit
    DEFAULT_STOP_DB  = 40.0      # Elliptic-Dämpfung

    # --- Signalgruppen (signal_auswahl_manager.py) ---
    MAX_GROUPS             = 999
    MAX_SIGNALS_PER_GROUP  = 999
    MIN_SIGNALS_FOR_GROUP  = 1

    # --- Formatierung ---
    COEFFICIENT_PRECISION = 6
    FREQUENCY_PRECISION   = 2

    # --- Schätzungen (data_validator.py) ---
    SAMPLES_PER_SECOND = 1000


# ============================================================
#  ERRORS – Fehlermeldungen                    (alle Files)
# ============================================================

class Errors:
    """Alle Fehlermeldungen, alphabetisch nach Thema."""

    # --- Filter (filter_manager.py) ---
    FILTER_INVALID_TYPE        = "Ungültiger Filtertyp: {0}"
    FILTER_INVALID_CHAR        = "Ungültige Filtercharakteristik: {0}"
    FILTER_INVALID_ORDER       = "Filterordnung muss zwischen {0} und {1} liegen"
    FILTER_INVALID_CUTOFF      = "Grenzfrequenz muss zwischen {0}Hz und {1}Hz liegen"
    FILTER_INVALID_SAMPLE_RATE = "Samplerate muss zwischen {0}Hz und {1}Hz liegen"
    FILTER_BANDPASS_TWO_FREQS  = "Bandpass-Filter benötigt zwei Grenzfrequenzen"
    FILTER_LOW_HIGH_ORDER      = "Unterer Cutoff ({0}Hz) muss kleiner als oberer Cutoff ({1}Hz) sein"
    FILTER_APPLICATION         = "Fehler beim Anwenden des Filters: {0}"
    FILTER_COEFFICIENT_CALC    = "Fehler bei Filterkoeffizienten-Berechnung: {0}"
    FILTER_FREQUENCY_RESPONSE  = "Fehler bei Frequenzgang-Berechnung: {0}"
    FILTER_NAN_IN_SIGNAL       = "Signal enthält NaN/Inf-Werte; Filterung überspringen"
    FILTER_CUTOFF_TOO_HIGH     = "Grenzfrequenz {0}Hz zu hoch für Nyquist-Frequenz {1}Hz"

    # --- Datenverarbeitung (data_processor.py) ---
    PROC_EMPTY_SIGNAL          = "Kein gültiges Signal ausgewählt"
    PROC_INVALID_WINDOW        = "Ungültige Fensterfunktion: {0}"
    PROC_FFT_FAILED            = "FFT-Berechnung fehlgeschlagen: {0}"
    PROC_FILTER_FAILED         = "Filteranwendung fehlgeschlagen: {0}"
    PROC_EXPORT_FAILED         = "Export fehlgeschlagen: {0}"
    PROC_NO_TIME_DATA          = "Keine Zeitdaten verfügbar"
    PROC_NO_SIGNAL_DATA        = "Keine Signaldaten verfügbar"
    PROC_INCONSISTENT_LENGTHS  = "Inkonsistente Datenlängen: Zeit ({0}) vs. Signal ({1})"
    PROC_INVALID_SAMPLE_RATE   = "Ungültige Samplerate: {0} (muss > 0)"
    PROC_TOO_FEW_SAMPLES       = "Zu wenige Samples für FFT (Minimum: {0})"
    PROC_TOO_MANY_SAMPLES      = "Zu viele Samples (Maximum: {0})"
    PROC_PROCESSING_FAILED = "Verarbeitung fehlgeschlagen: {0}"

    # --- Validierung (data_validator.py) ---
    VAL_NEGATIVE_ROW           = "Start-Zeile darf nicht negativ sein"
    VAL_ROW_ORDER              = "Start-Zeile muss kleiner als End-Zeile sein"
    VAL_NEGATIVE_COL           = "Start-Spalte darf nicht negativ sein"
    VAL_COL_ORDER              = "Start-Spalte muss kleiner als End-Spalte sein"
    VAL_INVALID_SAMPLERATE     = "Samplerate muss positiv sein"
    VAL_NO_DATAFRAME           = "Kein gültiger DataFrame verfügbar"
    VAL_EMPTY_DATAFRAME        = "DataFrame ist leer"
    VAL_INVALID_RANGE          = "Ungültiger Bereich: {0}"
    VAL_NO_NUMERIC_DATA        = "Keine numerischen Daten gefunden"
    VAL_INCONSISTENT_DIMS      = "Inkonsistente Dimensionen der extrahierten Daten"
    VAL_COLUMN_NOT_FOUND       = "Spalte '{0}' nicht gefunden"
    VAL_TIMESTAMP_CONVERSION   = "Fehler bei Zeitstempel-Konvertierung: {0}"
    VAL_PROCESSING_FAILED      = "Verarbeitung fehlgeschlagen: {0}"

    # --- Mehrfachdatei-Import (mehrfachdatei_manager.py) ---
    VAL_MULTIFILE_NOT_LOADED     = "Datei '{0}' konnte nicht geladen werden"
    VAL_MULTIFILE_FILE_FAILED    = "Verarbeitung von '{0}' fehlgeschlagen: {1}"

    # --- Datei-Handler (file_handler.py) ---
    FILE_EMPTY                 = "Fehler: Datei ist leer"
    FILE_NO_TIMESTAMP          = "Fehler: Zeitstempel-Spalte nicht gefunden"
    FILE_INVALID_TIMESTAMP     = "Fehler: Ungültige Zeitstempel gefunden"
    FILE_NOT_FOUND             = "Fehler: Datei nicht gefunden"
    FILE_NOT_EXCEL             = "Fehler: Keine Excel-Datei"
    FILE_NOT_CSV               = "Fehler: Keine CSV-Datei"
    FILE_NO_COLUMNS            = "Fehler: keine gültigen Daten vorhanden"
    FILE_EXPORT_FAILED         = "Fehler beim Export: {0}"
    FILE_NO_NUMERIC_COLUMNS    = "Keine numerischen Spalten erkannt"
    FILE_EXCEL_SHEET_NOT_FOUND = "Fehler: Sheet '{0}' nicht gefunden"
    FILE_EXCEL_INVALID_HEADER  = "Fehler: Ungültiger Header in Excel-Datei"
    FILE_CSV_EMPTY_AFTER_CLEAN = "CSV-Datei ist nach Bereinigung leer"
    FILE_UNSUPPORTED_FORMAT    = "Nicht unterstütztes Dateiformat: {}"
    FILE_INVALID_ENCODING = "Fehler: Ungültiges Encoding: {0} (unterstützt: {1})"
    FILE_INVALID_DELIMITER = "Fehler: Ungültiges Trennzeichen: {0} (unterstützt: {1})"

    # --- GUI (main_ui.py) ---
    GUI_SELECT_SIGNAL          = "Bitte zuerst ein Signal auswählen"
    GUI_INVALID_SIGNAL         = "Ungültige Signalauswahl"


# ============================================================
#  STATUS – Statusmeldungen                    (alle Files)
# ============================================================

class Status:
    """Alle Statusmeldungen, nach Kontext gruppiert."""

    # --- Filter (filter_manager.py) ---
    FILTER_APPLIED             = "Filter angewendet: {0} (Ordnung {1})"
    FILTER_RESET               = "Filter wurde zurückgesetzt"
    FILTER_COEFFICIENTS_CALC   = "Filterkoeffizienten berechnet"
    FILTER_FREQ_RESPONSE_CALC  = "Frequenzgang berechnet"
    FILTER_NO_ACTIVE           = "Kein aktiver Filter"
    FILTER_INACTIVE            = "Filter deaktiviert"
    FILTER_PLOT_CREATED        = "Filter-Plot erstellt"
    FILTER_PLOT_UPDATED        = "Filter-Plot aktualisiert"
    FILTER_CALC_FAILED         = "Filterberechnung fehlgeschlagen"
    FILTER_NO_ACTIVE            = "Kein aktiver Filter" 

    # --- Datenverarbeitung (data_processor.py) ---
    PROC_PROCESSING            = "Daten werden verarbeitet..."
    PROC_COMPLETED             = "Verarbeitung abgeschlossen"
    PROC_EXPORTING             = "Exportiere Daten..."
    PROC_EXPORT_COMPLETED      = "Export abgeschlossen: {0}"
    PROC_FILTER_APPLIED        = "Filter angewendet: {0}"
    PROC_FFT_CALCULATED        = "FFT berechnet (Fenster: {0})"
    PROC_NO_DATA               = "Keine Daten zum Verarbeiten verfügbar"

    # --- Validierung (data_validator.py) ---
    VAL_READY                  = "Bereit für Verarbeitung"
    VAL_FAILED                 = "Validierung fehlgeschlagen - prüfen Sie Ihre Eingaben"
    VAL_DATA_LOADED            = "Daten erfolgreich geladen"
    VAL_DWS_PROCESSED          = "DWS-Datei erfolgreich verarbeitet"
    VAL_TOP_PROCESSED          = "TOP-Datei erfolgreich verarbeitet"
    VAL_NO_DATA                = "Keine gültigen Daten geladen"
    VAL_INVALID_FORMAT         = "Falsches Datenformat für {0}"
    VAL_RANGE_ADJUSTED         = "Bereich angepasst: {0} auf {1}"

    # --- Datei-Handler (file_handler.py) ---
    FILE_LOADED                = "Datei erfolgreich geladen - Eingaben vornehmen"
    FILE_EXPORT_SUCCESS        = "Export abgeschlossen: {0}"
    FILE_NO_NUMERIC_COLUMNS    = "Keine numerischen Spalten erkannt"
    FILE_EXPORT_FALLBACK_CSV = "Fallback: CSV-Export erstellt: {0}"

    # --- GUI (main_ui.py) ---
    GUI_READY                  = "Bereit"
    GUI_LOADING                = "Lade Daten..."
    GUI_PROCESSING_START       = "Verarbeitung gestartet..."
    GUI_PROCESSING_SUCCESS     = "Verarbeitung erfolgreich: {} Signale, {} Header"
    GUI_PROCESSING_PARTIAL     = "Verarbeitung teilweise erfolgreich"
    GUI_PROCESSING_FAILED      = "Fehler: Validierung fehlgeschlagen"
    GUI_NO_DATA                = "Keine Daten verfügbar"
    GUI_CSV_LOADED             = "CSV-Datei erfolgreich geladen"
    GUI_FILE_SELECTED          = "Datei: {}"
    GUI_IMPORT_CANCELLED       = "Import abgebrochen"
    GUI_SELECT_SHEET           = "Bitte Sheet auswählen"
    GUI_SHEET_PROCESSING       = "Lade Sheet: {}..."
    GUI_SHEET_LOADED           = "Sheet {} erfolgreich geladen"
    GUI_SHEET_LOAD_ERROR       = "Fehler beim Laden des Sheets"
    GUI_NO_SHEET_SELECTED      = "Kein Sheet ausgewählt"
    GUI_OVERVIEW_CREATED       = "Übersichtsplot erstellt"
    GUI_NO_FILTER_PLOT         = "Kein Filter-Plot verfügbar"
    GUI_LOAD_ERROR             = "Fehler beim Laden der Daten"
    GUI_LOADING_ERROR           = "Fehler beim Laden: {}"

# ============================================================
#  LOGS – Log-Nachrichten                      (alle Files)
# ============================================================

class Logs:
    """Alle internen Log-Nachrichten für Debugging und Info."""

    # --- Filter (filter_manager.py) ---
    FILTER_APPLYING            = "Wende {0}-Filter an (Ordnung {1}, Cutoff {2}Hz)"
    FILTER_CALC_COEFFICIENTS   = "Berechne Filterkoeffizienten ({0}, Ordnung {1})"
    FILTER_CALC_FREQ_RESPONSE  = "Berechne Frequenzgang mit {0} Punkten"
    FILTER_RESET               = "Filterparameter zurückgesetzt"
    FILTER_NAN_IN_SIGNAL       = "Signal enthält NaN/Inf-Werte; Filterung überspringen"
    FILTER_CUTOFF_TOO_HIGH     = "Grenzfrequenz {0}Hz zu hoch für Nyquist {1}Hz - Filterung überspringen"
    FILTER_BANDPASS_WARNING    = "Bandpass: Untere Grenzfrequenz {0}Hz ≥ obere {1}Hz - Filterung abgebrochen"
    FILTER_USING_SOS           = "Verwende SOS-Implementierung für bessere numerische Stabilität"
    FILTER_INFO                = "Filter-Info: {0} (Charakteristik: {1}, Ordnung: {2})"
    FILTER_RESET                = "Filterparameter zurückgesetzt"

    # --- Datenverarbeitung (data_processor.py) ---
    PROC_START                 = "Starte Datenverarbeitung (Signal: {0})"
    PROC_TIME_DATA             = "Zeitdaten: {0} Samples, dt={1}s"
    PROC_SIGNAL_DATA           = "Signaldaten: {0} Samples, Einheit={1}"
    PROC_APPLYING_FILTER       = "Wende Filter an: {0} (Ordnung {1}, Grenzfrequenz {2}Hz)"
    PROC_CALC_FFT              = "Berechne FFT mit {0} Samples (Fenster: {1})"
    PROC_EXPORTING             = "Exportiere nach {0} (Format: {1})"
    PROC_NORMALIZING           = "Normalisiere Daten (Skalierungsfaktor: {0})"
    PROC_WINDOW_APPLIED        = "Fensterfunktion angewendet: {0}"
    PROC_DETRENDING            = "Entferne Gleichanteil (Detrend)"
    PROC_SMOOTHING             = "Glätte Signal (Fenster: {0})"

    # --- Validierung (data_validator.py) ---
    VAL_START                  = "=== {0} Verarbeitung gestartet ==="
    VAL_DATAFRAME_TYPE         = "DataFrame Type: {0}"
    VAL_DATAFRAME_EMPTY        = "DataFrame Status: Ungültig - Kein DataFrame-Objekt"
    VAL_RANGE_VALIDATION       = "Bereichsvalidierung: Zeilen {0}-{1}, Spalten {0}-{1}"
    VAL_RANGE_ADJUSTED         = "Bereich angepasst: {0} von {1} auf {2}"
    VAL_DATA_EXTRACTED         = "{0}-Daten erfolgreich extrahiert: {1} Spalten"
    VAL_NO_NUMERIC_COLUMNS     = "Keine numerischen Spalten erkannt"
    VAL_PROCESSING_TIME        = "Geschätzte Verarbeitungszeit: {0}"
    VAL_TIMESTAMP_CONVERTED    = "Zeitstempel konvertiert (Format: {0})"
    VAL_FALLBACK_TO_TEMP       = "DataFrame aus temp_df wiederhergestellt"
    VAL_EXCEL_COLUMN_DETECTED  = "Excel-Spalte {0} entspricht Nummer {1}"
    VAL_CSV_PARSED             = "CSV-Datei mit {0} Zeilen geladen"

    # --- Datei-Handler (file_handler.py) ---
    FILE_LOADED                = "Datei geladen: {0}"
    FILE_EXCEL_SHEET_EMPTY     = "Warnung: Excel-Sheet ist leer"
    FILE_CSV_PARSED            = "CSV-Datei mit {0} Zeilen geladen"
    FILE_TIMESTAMP_CONVERTED   = "Zeitstempel konvertiert (Format: {0})"
    FILE_NO_TIMESTAMP          = "Keine Zeitstempel-Spalte erkannt - verwende Fallback"
    FILE_NUMERIC_COLUMNS       = "Numerische Spalten: {0} (erste 8: {1})"
    FILE_DELIMITER_DETECTED    = "Erkanntes Trennzeichen: '{0}' (Anzahl: {1})"
    FILE_ENCODING_DETECTED     = "Erkanntes Encoding: {0}"
    FILE_FALLBACK_DELIMITER    = "Kein Trennzeichen erkannt, verwende '{0}' als Standard"
    FILE_EXPORT_FALLBACK_CSV   = "Fallback: CSV-Export erstellt: {0}"
    FILE_ENGINE_MISSING        = "Excel-Engine nicht verfügbar ({0})."
    FILE_NO_DATA_START = "Kein Datenbeginn gefunden"

    # --- GUI (main_ui.py) ---
    GUI_IMPORT_CLICK           = "Datenimport gestartet"
    GUI_IMPORT_CANCELLED       = "Datenimport abgebrochen"
    GUI_FILE_SELECTED          = "Datei ausgewählt: {}"
    GUI_EXCEL_RAW_DATA         = "Excel-Rohdaten geladen: {} Bytes"
    GUI_EXCEL_LOADED           = "Excel-Datei geladen: {} | Sheets: {}"
    GUI_CSV_LOADED             = "CSV geladen: {}"
    GUI_SHEET_SELECTED         = "Sheet ausgewählt: {}"
    GUI_SHEET_LOAD_ERROR       = "Fehler beim Laden des Sheets: {}"
    GUI_LOADING_ERROR          = "Ladefehler: {}"
    GUI_PROCESSING_START       = "Verarbeitung gestartet: Zeilen={}-{}, Spalten={}-{}, FS={}, Fenster={}"
    GUI_PROCESSING_DATA        = "Verarbeite Daten mit Form: {}"
    GUI_PROCESSING_FAILED      = "Datenvalidierung fehlgeschlagen"
    GUI_PROCESSING_DONE        = "Verarbeitung abgeschlossen: Signale={}, Header={}, Einheiten={}"
    GUI_FILTER_DEACTIVATED     = "Filter deaktiviert"
    GUI_OVERVIEW_OPEN          = "Übersichtsfenster geöffnet: Daten verfügbar={}"
    GUI_OVERVIEW_CREATED       = "Übersichtsplot erstellt: {} Signale"


# ============================================================
#  FILTER – Filter-Konfiguration        → filter_manager.py
# ============================================================

class Filter:
    """Spezifische Konfiguration für den FilterManager."""

    SUPPORTED_TYPES           = ["Kein Filter", "Tiefpass", "Hochpass", "Bandpass"]
    SUPPORTED_CHARACTERISTICS = ["butterworth", "bessel", "Chebyshev I", "elliptic"]

    # Zugriff auf Defaults und Limits via Cfg:
    # Defaults.FILTER_TYP, Defaults.FILTER_CHARAKTERISTIK, Defaults.FILTER_ORDER_INT
    # Defaults.CUTOFF_FREQ, Defaults.SAMPLE_RATE
    # Limits.FILTER_ORDER_MIN / MAX, Limits.CUTOFF_FREQ_MIN / MAX, ...


# ============================================================
#  FFT – FFT-Konfiguration              → data_processor.py
# ============================================================

class FFT:
    """Spezifische Konfiguration für FFT-Verarbeitung."""

    WINDOW_TYPES = ["hanning", "hamming", "blackman", "rectangular"]
    DEFAULT_DT   = 0.05     # Standard-Zeitschritt (50ms)

    # Zugriff auf Defaults und Limits via Cfg:
    # Defaults.FFT_WINDOW_TYPE, Defaults.FFT_NORMALIZE, Defaults.FFT_LOG_SCALE
    # Limits.FFT_MIN_SAMPLES, Limits.FFT_MAX_SAMPLES


# ============================================================
#  EXPORT – Export-Optionen              → file_handler.py
# ============================================================

class Export:
    """Export-Konfiguration und Dateiformate."""

    # --- Dateinamen-Vorlagen ---
    TIME_FMT  = "signal_{header}_time.png"
    FREQ_FMT  = "signal_{header}_freq.png"
    OVERVIEW  = "overview.png"
    MULTI_SIGNALS = "MultiSignals_Export.xlsx"

    # --- Unterstützte Formate ---
    IMAGE_FORMATS    = [("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")]
    EXCEL_FILETYPES  = [("Excel files", "*.xlsx")]
    SUPPORTED_FILETYPES = [
        ("CSV-Dateien",   "*.csv"),
        ("Excel-Dateien", "*.xlsx;*.xls"),
        ("Alle Dateien",  "*.*"),
    ]

    # --- Engines ---
    EXCEL_ENGINES = ["openpyxl", "xlsxwriter"]

    # --- Encodings & Trennzeichen (file_handler.py) ---
    SUPPORTED_ENCODINGS  = ['utf-8', 'windows-1250', 'windows-1252', 'iso-8859-1', 'cp1252']
    SUPPORTED_DELIMITERS = [';', ',', '\t', '|']
    DEFAULT_ENCODING     = 'utf-8'
    DEFAULT_DELIMITER    = ';'

    # --- Standardpfade ---
    DEFAULT_SPECTRUM_PATH = "spektren/"
    DEFAULT_EXPORT_PATH   = "exports/"
    DEFAULT_LOG_PATH      = "logs/"

    # --- Excel-spezifisch (data_validator.py) ---
    EXCEL_HEADER_ROWS  = [0, 1]
    EXCEL_TIME_COLUMN  = ("Time", "s")

    # --- CSV-spezifisch (data_validator.py, file_handler.py) ---
    CSV_SKIP_ROWS      = 0
    CSV_DATA_MARKER    = "Nb"
    CSV_FALLBACK_COLUMN = 0

    # --- Verarbeitungsoptionen (data_validator.py) ---
    PROCESS_DWS      = "DWS/Excel (MultiIndex)"
    PROCESS_TOP      = "TOP/CSV (Simple Index)"
    PROCESS_FALLBACK = "Fallback-Verarbeitung"


# ============================================================
#  SIGNAL – Signalauswahl            → signal_auswahl_manager.py
# ============================================================

class Signal:
    """Konfiguration für Signalauswahl und Gruppenmanagement."""

    # Zugriff auf Limits: Limits.MAX_GROUPS, Limits.MAX_SIGNALS_PER_GROUP
    LISTBOX_HEIGHT    = 15
    SEARCH_ENTRY_WIDTH = 30
    GROUP_FRAME_PADX  = 5
    GROUP_FRAME_PADY  = 2
    GROUP_LABEL_FONT  = (Fonts.FAMILY, Fonts.SMALL, "bold")
    GROUP_SELECTED_BG = Colors.GROUP_SELECTED_BG
    GROUP_LABEL_COLOR = Colors.GROUP_LABEL
    FILTER_ENTRY_WIDTH = 15


# ============================================================
#  ANALYSIS – Analyse-Typen               → analyse_*.py
# ============================================================

class Analysis:
    """Zuordnung Analyse-Typ → Plotarten und Titel."""

    TYPES = {
        "Signal":       ["Original"],
        "AVG":          ["Original", "AVG"],
        "RMS":          ["Original", "RMS"],
        "Differential": ["Original", "Ableitung"],
        "Integral":     ["Original", "Integral"],
        "FFT":          ["Original", "Amplitude", "Phase"],
        "Statistik":    ["Original", "Statistik"],
    }

    TITLES = {
        "Original":  "Original",
        "Gefiltert": "Gefiltert",
        "AVG":       "Durchschnitt (AVG)",
        "RMS":       "Effektivwert (RMS)",
        "Ableitung": "Ableitung",
        "Integral":  "Integral",
        "Amplitude": "Amplitudenspektrum",
        "Phase":     "Phasenspektrum",
        "Statistik": "Statistik",
    }

    NAMES = {
        "DIFFERENTIAL": "Differential",
        "AVG":          "AVG",
        "RMS":          "RMS",
        "FFT":          "FFT",
        "INTEGRAL":     "Integral",
        "STATISTIK":    "Statistik",
    }

    TIME_RANGE_SUPPORTED = ["AVG", "RMS", "FFT"]


# ============================================================
#  AXIS LABELS – Achsenbeschriftungen         → plot_manager.py
# ============================================================

class AxisLabels:
    TIME         = "Zeit [s]"
    FREQ         = "Frequenz [Hz]"
    AMP          = "Amplitude"
    PHASE        = "Phase [Grad]"
    MAGNITUDE_DB = "Magnitude [dB]"
    VALUE        = "Wert"

    @staticmethod
    def diff(unit: str) -> str:
        return f"{unit}/s" if unit else "1/s"

    @staticmethod
    def integral(unit: str) -> str:
        return f"{unit}·s" if unit else "unit·s"


# ============================================================
#  PLOT STYLE – Matplotlib/Seaborn           → plot_manager.py
# ============================================================

class PlotStyle:
    STYLE   = "whitegrid"
    CONTEXT = "notebook"
    PALETTE = "husl"

    MPL_RCPARAMS = {
        "axes.titlesize":  Fonts.Plots.AXIS_TITLE,
        "axes.labelsize":  Fonts.Plots.AXIS_LABELS,
        "xtick.labelsize": Fonts.Plots.TICK_LABELS,
        "ytick.labelsize": Fonts.Plots.TICK_LABELS,
        "legend.fontsize": Fonts.Plots.LEGEND,
        "grid.color":      Colors.GRID_COLOR,
        "grid.linestyle":  Colors.GRID_LINESTYLE,
        "grid.alpha":      Colors.GRID_ALPHA,
        "axes.grid":       True,
    }

    # Plot-Parameter (gui_config.py)
    DEFAULT_DPI         = 100
    DEFAULT_LINE_WIDTH  = 1.5
    DEFAULT_MARKER_SIZE = 6

    # Timeouts (main_ui.py)
    BUTTON_BLINK_DURATION  = 300    # ms
    BUTTON_BLINK_TIMES     = 25
    LOADING_SPINNER_TIMEOUT = 5000  # ms
    PLOT_UPDATE_INTERVAL   = 100    # ms


# ============================================================
#  PLACEHOLDERS – Eingabefeld-Platzhalter     → main_ui.py
# ============================================================

class Placeholders:
    START_REIHE  = "Start Reihe z.B. 1"
    END_REIHE    = "End Reihe z.B. 10000"
    START_SPALTE = "Start Spalte z.B. 1 / A"
    END_SPALTE   = "End Spalte z.B. 100 / CC"
    SAMPLERATE   = "Samplefrequenz z.B. 20"
    FENSTERTYP   = "Fenstertyp wählen:"

    EINGABE = [START_REIHE, END_REIHE, START_SPALTE, END_SPALTE, SAMPLERATE]

    STARTZEIT = "Startzeit"
    ENDZEIT   = "Endzeit"
    SAMPLES   = "Samples (n)"
    DT        = "Zeitabstände (dt)"
    DF        = "Frequenzabstände (df)"

    AUSGABE = [STARTZEIT, ENDZEIT, SAMPLES, DT, DF]


# ============================================================
#  DATA – Spalten-Ausschlüsse             → data_validator.py
# ============================================================

class Data:
    EXCLUDE_COLUMNS = ['SECTION', 'LOGDATA', 'Nb', 'Type', 'Date', 'Time']


# ============================================================
#  CFG – Master-Zugriffsobjekt
# ============================================================

class Cfg:
    """
    Einziger Einstiegspunkt für die gesamte Konfiguration.

    VERWENDUNG IN ANDEREN FILES:
    ────────────────────────────
    from konfiguration import Cfg

    Cfg.Fonts.FAMILY              → Schriftart
    Cfg.Colors.PRIMARY            → Hauptfarbe
Cfg.Texts.BTN_IMPORT          → Button-Text
    Cfg.Defaults.SAMPLERATE       → Standardwert
    Cfg.Limits.FILTER_ORDER_MAX   → Validierungsgrenze
    Cfg.Errors.FILTER_NAN_IN_SIGNAL → Fehlermeldung
    Cfg.Status.GUI_READY          → Statusmeldung
    Cfg.Logs.PROC_START           → Log-Nachricht
    Cfg.Filter.SUPPORTED_TYPES    → filter_manager.py
    Cfg.FFT.WINDOW_TYPES          → data_processor.py
    Cfg.Export.DEFAULT_DELIMITER  → file_handler.py
    Cfg.Signal.LISTBOX_HEIGHT     → signal_auswahl_manager.py
    Cfg.Analysis.TYPES            → analyse_*.py
    Cfg.AxisLabels.TIME           → plot_manager.py
    Cfg.PlotStyle.DEFAULT_DPI     → plot_manager.py
    Cfg.Data.EXCLUDE_COLUMNS      → data_validator.py
    """

    Fonts       = Fonts
    Colors      = Colors
    Styles      = Styles
    Layout      = Layout
    Texts       = Texts
    Defaults    = Defaults
    Limits      = Limits
    Errors      = Errors
    Status      = Status
    Logs        = Logs
    Filter      = Filter
    FFT         = FFT
    Export      = Export
    Signal      = Signal
    Analysis    = Analysis
    AxisLabels  = AxisLabels
    PlotStyle   = PlotStyle
    Ph          = Placeholders
    Data        = Data