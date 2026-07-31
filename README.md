# Messtool – Messdaten-Analyse-Tool

**Version**: 25
**Entwickler**: Stadler Rail – E-Engineering
**Sprache**: Python 3.13
**GUI-Framework**: ttkBootstrap (Tkinter)

---

## 📋 Projektübersicht

**Messtool** ist eine spezialisierte Python-Anwendung zur Verarbeitung, Filterung und Analyse von Messdaten aus verschiedenen Dateiformaten (Excel, CSV, DWS). Das Tool ermöglicht interaktive Visualisierung, Frequenzanalyse und erweiterte Signalverarbeitung für Engineering-Anwendungen.

**Besonders geeignet für:**
- Antriebssystem-Analyse
- Schwingungsanalyse und Diagnose
- Zeit-Frequenz-Analyse
- Filterung und Signalkonditionierung
- Statistische Messbewertung
- Techische PDF-Reports

---

## 🏗️ Architektur & Design-Patterns

Das Projekt folgt dem **MVC-Pattern** mit spezialiserten Manager-Klassen für Separation of Concerns:

```
┌───────────────────────────────────────────────────────────────────┐
│                             main.py                                │
│                      (Entry Point & Logging)                       │
└──────────────────────────────┬──────────────────────────────────────┘
                                │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     hauptfenster_manager.py                         │
│               (Central Application Controller)                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Koordiniert alle Sub-Manager und App-State                 │    │
│  │ • DateiHandler (Import)         • FilterManager             │    │
│  │ • DatenValidator (Validierung)  • DatenVerarbeiter           │    │
│  │ • PlotManager (Visualisierung)  • AnalyseManager             │    │
│  └────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────┘
        │              │                  │              │
        ▼              ▼                  ▼              ▼
   GUI LAYOUT    DATA PROCESSING       PLOTTING       ANALYSIS
   ┌────────┐   ┌────────────────┐   ┌────────┐    ┌────────┐
   │ Layout │   │ DateiHandler    │   │ Plots  │    │Analyse │
   │Manager │   │                 │   │Manager │    │Manager │
   └────────┘   │ DatenValidator  │   └────────┘    └────────┘
                │                 │
                │ FilterManager   │
                │                 │
                │ DatenVerarbeiter│
                │                 │
                └─────────────────┘
```

### Daten-Verarbeitungspipeline

```
📁 Datei-Import
    ↓ (DateiHandler)
🔍 Validierung
    ↓ (DatenValidator)
⚙️ Datenverarbeitung
    ↓ (DatenVerarbeiter)
🔧 Filterung
    ↓ (FilterManager)
📊 Visualisierung
    ↓ (PlotManager / AnalysePlotter)
✅ Display / Export
```

---

## 📂 Dateistruktur & Funktionen

### Haupteintrag & Konfiguration

| Datei | Größe | Funktion |
|-------|-------|----------|
| **main.py** | 2.6 KB | Einstiegspunkt • Logging-Setup • Session-Tracking • Fehlerbehandlung |
| **hauptfenster_manager.py** | 34.4 KB | Zentrale GUI-Kontrolle • State-Management • Sub-Manager-Koordination |
| **konfiguration.py** | 46.2 KB | Zentrale Konfiguration für Farben, Fonts, Layouts, Texte, Limits |
| **conftest.py** | – | Zentralisiert `.pyc`-Caches nach `.pycache/` auch für `pytest`-Läufe (siehe main.py-Mechanismus unten) |

---

### 🎨 GUI-Module (`gui_module/`)

| Datei | Größe | Verantwortung |
|-------|-------|---|
| **oberflaechen_layout_manager.py** | 37.8 KB | Layout-Konstruktion • Frame/Widget-Management • Button- und Input-Anordnung |
| **oberflaechen_steuerung.py** | 21.3 KB | UI-State-Management • Event-Handling • Enable/Disable-Logik • Dialog-Verwaltung |
| **plot_manager.py** | 40.1 KB | Kern-Plotting-Funktionen • Zeit-/Frequenzdarstellung • Interaktive Cursor • FFT-Visualization |
| **plot_fenster_manager.py** | 9.2 KB | Plot-Fenster-Lifecycle • Window-Management • Koordinator-Pattern |
| **live_plot_fenster_manager.py** | 26.9 KB | Interaktive Plot-Fenster • Live-Updates • Multi-Signal-Overlay • Real-Time-Refresh |
| **analyse_manager.py** | 19.1 KB | Signal-Analyse (AVG, RMS, Differential, Integral) • Variance, Autocorrelation • Ergebnis-Fenster |
| **analyse_plotter.py** | 27.5 KB | Analyse-Visualisierung • Multi-Subplot-Layout • Statistische Annotationen • Export-Button pro Tab |
| **signal_auswahlmanager.py** | 37.5 KB | Signal-Auswahl-Fenster • Gruppen-Management • Signal-Listbox • Filter-Visualisierung |
| **mehrfachdatei_manager.py** | – | Mehrfachdatei-Import • Batch-Verarbeitung (jede Datei unabhängig) • Signal-Pool-Aufbau • Rückkehr zu Schritt 1 |
| **meldungen.py** | – | Nicht-blockierende Toast-Benachrichtigungen (Ersatz für `tkinter.messagebox`) • gleiche API wie `messagebox` |

---

### 🔧 Hilfsfunktionen (`hilfsklassen/`)

| Datei | Größe | Verantwortung |
|-------|-------|---|
| **datei_handler.py** | 24.1 KB | Datei-I/O • Excel/CSV/DWS-Lesing • Encoding-Erkennung • Daten-Export • Validierung |
| **daten_validator.py** | 17.0 KB | Input-Validierung • Excel-Spalten-Konvertierung (A→1, AA→27) • Range-Validierung • DataFrame-Extraktion |
| **daten_verarbeiter.py** | 17.6 KB | Signalverarbeitung • FFT-Berechnung • Fensterung (Hann, Hamming) • AVG/RMS • Differential/Integral |
| **filter_manager.py** | 19.5 KB | Digitale Filter-Desing • Butterworth/Chebyshev/Bessel • Low-/High-/Bandpass • Frequenzgang-Berechnung |
| **zentrales_logging.py** | 4.4 KB | Zentrales Logging-Setup • Rotating File Handler • Session-Tracking • Protokoll-Logger |

---

### 🧪 Tests (`tests/`)

| Datei | Größe | Funktion |
|-------|-------|----------|
| **test_messtool.py** | 21.4 KB | Unit-Tests für Excel-Spalten-Konvertierung, Filter, Datenverarbeitung • Unittest-Framework |

---

## 🔄 Detaillierte Funktionsbeschreibungen

### 1. **main.py** – Anwendungs-Einstiegspunkt

```python
# Workflow:
1. setup_logging() - Logging-System initialisieren
2. _install_exception_hooks() - Globale Fehlerbehandlung
3. get_resource_path() - Pfade für Dev und PyInstaller
4. HauptfensterManager.create_gui() - GUI starten
5. log_session_end() - Session dokumentieren
```

**Besonderheit:** `get_resource_path()` funktioniert sowohl im Dev-Modus als auch im PyInstaller-Executable (nutzt `sys._MEIPASS`).

**`.pyc`-Caches zentral statt verstreut:** `main.py` setzt ganz am Anfang
`sys.pycache_prefix`, damit alle Bytecode-Caches gebündelt in `.pycache/`
landen statt als `__pycache__/`-Ordner neben jeder einzelnen Datei. Das gilt
nur für den Prozess, der tatsächlich über `main.py` startet – deshalb gibt
es dieselbe Zeile auch in `conftest.py` (für `pytest`-Läufe, die die Module
direkt importieren). Ad-hoc-Skripte, die Projekt-Module ohne einen dieser
beiden Einstiegspunkte importieren, umgehen die Umleitung und erzeugen
wieder verstreute `__pycache__/`-Ordner.

---

### 2. **hauptfenster_manager.py** – Zentrale Kontrolle

**Kernfunktionen:**
- `load_file()` - Datei importieren mit Validierung
- `process_data()` - Daten verarbeiten (FFT, Zeit-Achse, Frequenz-Achse)
- `show_single_signal()` - Einzelnes Signal anzeigen
- `show_multiple_signals()` - Mehrere Signale vergleichen (max. 3)
- `apply_filter()` - Filter anwenden & validieren
- `export_data()` - Ergebnisse exportieren
- `show_help()` - HTML→PDF konvertieren und öffnen

**State-Variablen:**
```python
self.data_loaded = False           # Daten importiert?
self.data_processed = False        # Daten verarbeitet?
self.filter_enabled = False        # Filter aktiv?
self.selected_signals = []         # Ausgewählte Signale
```

---

### 3. **konfiguration.py** – Zentrale Konfiguration

**Klassen-Struktur:**
```python
Cfg.Fonts          # Font-Familie & -Größen für UI und Plots
Cfg.Colors         # Farb-Schemata
Cfg.Layout         # Spacing, Window-Größen, Figure-Sizes
Cfg.Texts          # Alle UI-Labels (deutsch)
Cfg.Defaults       # Standard-Werte (FS=1000, Fenster=Hanning)
Cfg.Limits         # Validierungs-Grenzen
Cfg.Errors         # Fehlermeldungen
Cfg.Filter         # Filter-Konfiguration
Cfg.FFT            # FFT-Parameter
Cfg.Analysis       # Analyse-Typen & Plot-Mapping
```

**Vorteil:** Single Source of Truth – keine Magic Numbers/Strings im Code.

---

### 4. **datei_handler.py** – Datei-Ein-/Ausgabe

**Unterstützte Formate:**

| Format | Erkennung | Handling |
|--------|-----------|----------|
| **Excel (.xlsx/.xls)** | via openpyxl/xlrd | Sheet-Enumeration, MultiIndex-Header |
| **CSV** | Auto-Erkennung | Delimiter (,/;/Tab/Space), Encoding |
| **DWS** | Proprietary | Custom Format-Parser |

**Workflow:**
```python
load_file(filepath)
├─ Encoding-Erkennung (charset_normalizer)
├─ Format-Detektion
├─ DataFrame laden
└─ Metadaten-Spalten ignorieren (SECTION, LOGDATA, Type, Date, Time)

export_data(dataframe, format='xlsx')
├─ Excel-Workbook: Metadaten + Daten-Sheets
├─ CSV: Komma-getrennte Spalten
└─ Optional: PNG-Plots speichern
```

---

### 5. **daten_validator.py** – Input-Validierung

**Key-Funktionen:**

```python
excel_column_to_number("A")      # → 1
excel_column_to_number("AA")     # → 27
excel_column_to_number("AAA")    # → 703

validate_range(start_row, end_row, max_rows)
# Validiert Zeilenbereich

extract_dataframe(dataframe, row_range, col_range)
# Extrahiert Subset aus DataFrame
```

**Validierungsregeln:**
- Start Row < End Row
- Spalten: A-Z oder 1-26 (Auto-Konvertierung)
- Samplerate > 0 Hz
- Row/Col müssen vorhanden sein

---

### 6. **daten_verarbeiter.py** – Signalverarbeitung

**Kernberechnung:**

```python
compute_fft(signal, sample_rate, window_type='hann')
├─ Fenster-Funktion anwenden
├─ scipy.fft.fft() berechnen
├─ Normalisierung (Peak oder RMS)
└─ Rückgabe: (frequency_axis, magnitude, phase)

compute_avg(signal)        # Mittelwert
compute_rms(signal)        # Effektivwert (√(1/n Σx²))
compute_differential(signal)     # dU/dt (Ableitung)
compute_integral(signal, dt)     # ∫U dt (Fläche)
```

**Fensterung-Optionen:**
- Rechteck (Standard, aber höhere Leckage)
- Hanning (reduzierte Spektral-Leckage)
- Hamming, Blackman (weitere Optionen)

**FFT-Eigenschaften:**
- Nyquist-Grenze: f_nyquist = FS/2
- Frequenzauflösung: df = FS/n
- Zeit-Schritt: dt = 1/FS

---

### 7. **filter_manager.py** – Digitale Filterung

**Unterstützte Filter:**

| Typ | Charakteristik | Anwendung | Eigenschaft |
|-----|---|---|---|
| **Butterworth** | Flach, sanft | Allgemein | Minimal Welligkeit |
| **Chebyshev I** | Steil | Hohe Trennung | Leichte Welligkeit |
| **Bessel** | Phasenflach | Zeitsignale | Phase erhalten |
| **Elliptic** | Steilster | Extrem | Höchste Welligkeit |

**Filter-Typen:**
- Tiefpass: f_cutoff < FS/2 (Rauschen entfernen)
- Hochpass: f_cutoff < FS/2 (DC-Offset entfernen)
- Bandpass: f1 < f2 < FS/2 (Frequenzband isolieren)

**Validierung:**
```python
# Vor Anwendung prüfen:
✓ f_cutoff < Nyquist (FS/2)
✓ Filterordnung > 0
✓ Bei Bandpass: f1 < f2
✓ Alle Werte numerisch valid
```

---

### 8. **plot_manager.py** – Visualisierung

**Kern-Plot-Funktionen:**

```python
plot_time_domain(signal, time_axis, title)
# Zeigt Signal über Zeit mit interaktiven Cursoren

plot_fft(signal, freq_axis, magnitude, phase)
# Frequenzspektrum (Amplitude + Phase)

plot_filter_characteristic(b, a, worN, fs)
# Frequenzgang des Filters (Magnitude & Phase)

plot_overlay(signal1, signal2, signal3, time_axis)
# Mehrere Signale überlagert mit verschiedenen Farben
```

**Interaktivität:**
- Zoom & Pan mit Maus
- Toolbar für Speichern/Navigation

**Styling:**
- Farben aus `Cfg.Colors`
- Fonts aus `Cfg.Fonts`
- Line Styles aus `Cfg.Layout`

---

### 9. **oberflaechen_steuerung.py** – GUI-State-Management

**Kernfunktionen:**

```python
reset_all()
# Alle Eingaben, Analysen, Filter zurücksetzen

enable_after_import()
# Nach Datei-Import: Verarbeitung & Export freigeben

update_filter_status(is_enabled)
# UI-Element Enable/Disable je nach Filter-Status

show_filter_dialog()
# Popup für Filter-Parameter-Eingabe

show_path_window()
# Fenster mit Import/Export/Plot-Pfaden anzeigen
```

**State-Tracking:**
- Welche UI-Elemente sind aktiv?
- Abhängigkeitsketten (z.B. Range-Input nur nach Import)
- Protokollierung aller Benutzer-Aktionen

---

### 10. **oberflaechen_layout_manager.py** – UI-Konstruktion

**Aufbau:**

```
┌─────────────────────────────────────┐
│   Eingabe-Bereich (Input Frame)    │
│   ├─ Start/End Reihe               │
│   ├─ Start/End Spalte              │
│   ├─ Samplefrequenz (FS)           │
│   └─ Fenstertyp (Rechteck/Hanning) │
├─────────────────────────────────────┤
│   Buttons (Button Frame)            │
│   ├─ Datei laden                   │
│   ├─ Verarbeitung starten          │
│   ├─ Exportieren                   │
│   ├─ Pfad anzeigen                 │
│   ├─ Reset                         │
│   └─ Hilfe                         │
├─────────────────────────────────────┤
│   Ausgabe-Bereich (Output Frame)   │
│   ├─ Startzeit / Endzeit           │
│   ├─ Samples (n)                   │
│   ├─ dt [s]                        │
│   └─ df [Hz]                       │
├─────────────────────────────────────┤
│   Signalliste (List Frame)         │
│   └─ Checkbox-Liste mit Signals    │
├─────────────────────────────────────┤
│   Tabs (Tabs Frame)                │
│   ├─ Datenverarbeitung (Filter)    │
│   ├─ Analyse                       │
│   └─ Info                          │
├─────────────────────────────────────┤
│   Status-Bereich (Status Bar)      │
│   └─ Fortschritt & Meldungen       │
└─────────────────────────────────────┘
```

**Framework:** ttkBootstrap (modernes Tkinter-Theming)

---

### 11. **analyse_manager.py** – Signalanalyse

**Analyse-Typen:**

```python
AVG    # Durchschnittswert (Mean)
RMS    # Effektivwert (√(1/n Σx²))
Differential  # Ableitung (dU/dt)
Integral      # Integration (∫U dt)
Variance      # Varianz
Autocorrelation  # Periodizität
```

**Workflow:**
```python
analyze_signal(signal, signal_name)
├─ Berechne AVG, RMS, Varianz
├─ Berechne Differential & Integral
├─ Erstelle Ergebnis-Fenster
└─ Zeige Statistiken im Dialog
```

---

### 12. **zentrales_logging.py** – Logging-System

**Logger-Typen:**

```python
# Application Logger (System-Events)
logging.getLogger(__name__)
├─ Fehler
├─ Warnungen
├─ Debug-Infos
└─ Exceptions

# Protocol Logger (Benutzer-Aktionen)
protocol_logger = get_protocol_logger()
├─ DATEI_IMPORT
├─ FILTER_APPLY
├─ EXPORT
├─ SIGNAL_SELECT
└─ SESSION_START/END
```

**Dateiablage:**
```
logs/
├─ messtool.log          # Application Log (rotating, max 5 MB)
├─ protocol.log          # Protocol Log (rotating)
└─ test_results.log      # Test-Ergebnisse
```

**Features:**
- Automatische Rotation bei Größenlimit
- Session-Tracking mit Timestamp, Python-Version, PID
- Thread-sichere Logging via `logging`-Modul

---

## 🚀 Verwendung & Workflow

### 1. Programm-Start
```bash
python main.py
# oder
Messtool.exe  (nach PyInstaller-Build)
```

### 2. Datei-Import
1. Button "Datei laden" klicken
2. Excel/CSV/DWS wählen
3. Start-/End-Reihe & Spalte angeben
4. FS (Samplerate) eingeben
5. Fenstertyp wählen

### 3. Datenverarbeitung
1. Button "Verarbeitung starten"
2. FFT, Zeit-/Frequenz-Achsen berechnet
3. Ausgabefelder gefüllt (dt, df, Samples, Zeit)

### 4. Visualisierung
1. Signal aus Liste wählen
2. Plot-Fenster öffnet automatisch
3. Zeit-Plot, FFT-Amplitude, FFT-Phase, Overlays

### 5. Filterung (optional)
1. Checkbox "Gefiltert verwenden" aktivieren
2. Filter-Dialog: Typ, Charakteristik, Grenzfrequenz wählen
3. Filter anwenden
4. Gefilterte Daten im Plot (rot) vs. Original (blau)

### 6. Analyse (optional)
1. Tab "Analyse" klicken
2. Analyse-Typ wählen (AVG, RMS, etc.)
3. Ergebnis-Fenster mit Statistiken

### 7. Export
1. Im Analyse-Ergebnisse-Fenster (nach Signalauswahl → Plot) auf "Export" klicken
2. Zielordner wählen – pro angezeigtem Signal wird eine eigene Excel-Datei geschrieben
3. Enthält Zeit-/Frequenzdaten, AVG/RMS/Differential/Integral und Filter-Metadaten

---

## 📁 Mehrfachdatei-Import (Batch) & Signal-Pool

Werden beim Import mehrere Dateien ausgewählt, öffnet sich statt der normalen
Eingabedaten-Ansicht ein zweistufiges Panel:

1. **Schritt 1 – Globale Einstellungen:** Samplefrequenz und Fenstertyp gelten für alle Dateien gemeinsam.
2. **Schritt 2 – Datei-Tabs:** jede Datei bekommt einen eigenen Tab mit eigenem Zeilen-/Spaltenbereich; nach der Verarbeitung stehen dort auch die Ausgabewerte (Startzeit, Endzeit, Samples, dt, df) **pro Datei**.

Beim Verarbeiten läuft jede Datei **unabhängig** durch dieselbe Pipeline wie ein
Einzelimport – unterschiedliche Spaltenanzahl oder Dauer zwischen den Dateien ist
kein Problem, da nichts zeitlich zusammengeführt wird. Ist eine Speicher-Option
aktiv, werden Plots/Spektren automatisch pro Datei nach `spektren/<Dateiname>/`
geschrieben.

Anschließend öffnet sich **ein** Signalauswahl-Fenster mit den Signalen **aller**
Dateien zusammen (Signal-Pool). Jedes Signal behält seine eigene Zeit- bzw.
Uhrzeit-Achse; bei gleichnamigen Signalen aus verschiedenen Dateien wird der
Dateiname automatisch zur Unterscheidung angehängt (`Kanal1 (Datei2)`). Schließen
des Signalauswahl-Fensters oder "Eingaben zurücksetzen" führt zurück zu Schritt 1,
ohne die geladenen Dateien zu verwerfen – "Komplett zurücksetzen" beendet den
Mehrfachdatei-Modus vollständig.

Technisch wird das über `PlotManager.t_for_idx()` gelöst: `gui.t`/`gui.timestamps`
sind im Signal-Pool-Fall Listen (ein Zeitarray pro Signal) statt eines einzelnen
gemeinsamen Arrays; alle Analyse-/Export-/Plot-Funktionen lösen die passende
Zeitachse pro Signal-Index auf.

---

## 🔔 Meldungen (Toast-Benachrichtigungen)

Alle Info-/Warn-/Fehlermeldungen im Programm laufen über `gui_module/meldungen.py`
statt über den klassischen, blockierenden `tkinter.messagebox`-Dialog (mit
"OK"-Button). Stattdessen erscheint ein nicht-blockierendes Toast
(`ttkbootstrap.ToastNotification`):

- Erscheint oben rechts über dem jeweiligen Fenster (Fallback: Hauptfenster)
- Verschwindet automatisch nach ~7 Sekunden, per Klick auch sofort schließbar
- Mehrere gleichzeitige Meldungen stapeln sich untereinander statt sich zu überlappen
- Bleibt `topmost`, auch wenn direkt danach andere Fenster in den Vordergrund geholt werden

Bestätigungsdialoge, bei denen tatsächlich auf eine Ja/Nein-Entscheidung gewartet
werden muss (z. B. `askyesno` beim Löschen einer Signalgruppe), bleiben bewusst
echte blockierende Dialoge und werden unverändert durchgereicht.

**Verwendung:** Andere Module importieren `messagebox` einfach als Alias auf dieses
Modul (`from gui_module import meldungen as messagebox`) – bestehender Code, der
`messagebox.showinfo/showwarning/showerror/askyesno` aufruft, funktioniert dadurch
unverändert weiter.

---

## 🔌 Abhängigkeiten

### Externe Libraries
```
tkinter / ttkbootstrap  - GUI-Framework
matplotlib              - Plotting & Visualization
numpy / scipy           - Numerische Berechnungen (FFT, Filter)
pandas                  - DataFrames & Datenverarbeitung
openpyxl / xlrd         - Excel-Lesing (.xlsx / .xls)
xlsxwriter              - Excel-Export (Fallback-Engine, falls openpyxl fehlschlägt)
xhtml2pdf               - HTML → PDF Konvertierung
PIL                     - Bild-Handling
seaborn                 - Statistische Visualisierung
charset_normalizer      - Encoding-Erkennung
```

### Standard Library
```
logging                 - Logging
threading               - Background-Tasks
pathlib / os            - Dateisystem
csv                     - CSV-Parsing
datetime                - Zeitstempel
tempfile                - Temp-Dateien
```

### Installation
```bash
pip install -r requirements.txt
# oder einzeln:
pip install ttkbootstrap matplotlib numpy scipy pandas openpyxl xlsxwriter xlrd xhtml2pdf pillow seaborn charset_normalizer
```

---

## 🧪 Testing

```bash
python -m pytest tests/test_messtool.py -v
```

`pytest` ist Teil von `requirements.txt` (nur für Tests benötigt, nicht für den
normalen App-Betrieb).

**Test-Coverage:**
- Excel-Spalten-Konvertierung (A→1, AA→27)
- Filter-Erstellung (Butterworth, Chebyshev, Bessel)
- Datei-Operationen (Excel, CSV)
- Daten-Verarbeitung (FFT, AVG, RMS)

---

## 📦 PyInstaller Build

Build-Konfiguration liegt in `packaging_sonstige/`:

| Datei | Funktion |
|-------|----------|
| **packaging_sonstige/Messtool_Antrieb.spec** | Gepflegte PyInstaller-Spec (Datas, Hidden-Imports für reportlab/xhtml2pdf). Pfade sind über `SPECPATH` relativ zum Projekt-Root aufgelöst, funktioniert unabhängig vom Aufruf-Ordner. |
| **packaging_sonstige/Executable_Erstellung** | Alternativer Aufruf als reiner CLI-Befehl (ohne Spec-Datei) – muss aus dem Projekt-Root ausgeführt werden. |

```bash
pip install pyinstaller

# Empfohlen: über die gepflegte Spec-Datei (von überall aufrufbar)
python -m PyInstaller packaging_sonstige/Messtool_Antrieb.spec

# Alternativ: reiner CLI-Befehl aus packaging_sonstige/Executable_Erstellung
# (dafür ins Projekt-Root wechseln, siehe Kommentar in der Datei)

# Ergebnis
dist/Messtool_Antrieb/
```

---

## 📝 Logging & Debugging

**Log-Dateien:**
```
logs/messtool.log       # Application-Log
logs/protocol.log       # Benutzer-Aktionen
logs/test_results.log   # Test-Ergebnisse
```

**Log-Level:**
```python
# in main.py:
setup_logging(logging.INFO)  # Production
setup_logging(logging.DEBUG) # Development
```

**Beispiel Log-Einträge:**
```
[2024-01-30 14:23:45] INFO: Session started (PID: 12345)
[2024-01-30 14:23:50] PROTOCOL: DATEI_IMPORT path=data.xlsx
[2024-01-30 14:23:51] INFO: Daten geladen: 1000 Samples, 10 Kanäle
[2024-01-30 14:23:52] PROTOCOL: FILTER_APPLY type=Tiefpass fc=100Hz
[2024-01-30 14:24:01] PROTOCOL: EXPORT path=export_20240130_142401.xlsx
```

---

## 🤝 Code-Style & Conventions

**Naming:**
- `snake_case` für Variablen & Funktionen
- `PascalCase` für Klassen
- `UPPER_CASE` für Konstanten (Cfg.**)

**Dokumentation:**
- Docstrings für alle Funktionen/Klassen
- Deutsche Kommentare für komplexe Logik
- Type Hints (Optional)

**Error Handling:**
```python
try:
    # Kernaktion
except SpecificException as e:
    logger.exception("Aussagekräftige Fehlermeldung")
    messagebox.showerror("Fehler", str(e))
```

---

## 📄 Lizenz

© 2026 Stadler Rail – E-Engineering
Alle Rechte vorbehalten.

---

## 📞 Kontakt & Support

**Fragen zur Bedienungsanleitung:**
→ Siehe `projektbeschreibung_bilder/Bedienungsanleitung_Messtool.pdf`

**Fragen zur Architektur:**
→ Siehe dieses README

**Bug-Reports / Fehler:**
→ Log-Dateien in `logs/` prüfen
