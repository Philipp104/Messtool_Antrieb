import unittest
import numpy as np
import pandas as pd
import sys
import os
import tempfile
import logging
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hilfsklassen.daten_validator import DatenValidator
from hilfsklassen.filter_manager import FilterManager
from hilfsklassen.datei_handler import DateiHandler
from hilfsklassen.daten_verarbeiter import DatenVerarbeiter
from gui_module.analyse_plotter import AnalysePlotter
from konfiguration import Cfg


class DummyLabel:
    """Duck-Typing-Ersatz für ein Tkinter-Label - Produktivcode ruft nur .config()
    auf, ein echtes Tk-Widget/-Root wird für die Datei-Parsing-Tests nicht gebraucht."""

    def config(self, **kwargs):
        pass

log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "test_results.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("test_messtool")


class TestDatenValidatorExcelColumns(unittest.TestCase):

    def setUp(self):
        self.validator = DatenValidator()

    def test_single_letter_A(self):
        self.assertEqual(self.validator.excel_column_to_number("A"), 1)

    def test_single_letter_Z(self):
        self.assertEqual(self.validator.excel_column_to_number("Z"), 26)

    def test_double_letter_AA(self):
        self.assertEqual(self.validator.excel_column_to_number("AA"), 27)

    def test_double_letter_AZ(self):
        self.assertEqual(self.validator.excel_column_to_number("AZ"), 52)

    def test_double_letter_BA(self):
        self.assertEqual(self.validator.excel_column_to_number("BA"), 53)

    def test_lowercase_converts(self):
        self.assertEqual(self.validator.excel_column_to_number("a"), 1)
        self.assertEqual(self.validator.excel_column_to_number("aa"), 27)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            self.validator.excel_column_to_number("")

    def test_none_raises(self):
        with self.assertRaises(ValueError):
            self.validator.excel_column_to_number(None)


class TestDatenValidatorProperties(unittest.TestCase):

    def setUp(self):
        self.validator = DatenValidator()

    def test_negative_start_row_raises(self):
        with self.assertRaises(ValueError):
            self.validator.start_row = -1

    def test_negative_end_row_raises(self):
        with self.assertRaises(ValueError):
            self.validator.end_row = -1

    def test_negative_start_col_raises(self):
        with self.assertRaises(ValueError):
            self.validator.start_col = -1

    def test_negative_end_col_raises(self):
        with self.assertRaises(ValueError):
            self.validator.end_col = -1

    def test_start_row_greater_than_end_row_raises(self):
        self.validator.end_row = 10
        with self.assertRaises(ValueError):
            self.validator.start_row = 20

    def test_end_row_less_than_start_row_raises(self):
        self.validator.start_row = 10
        with self.assertRaises(ValueError):
            self.validator.end_row = 5

    def test_start_col_greater_than_end_col_raises(self):
        self.validator.end_col = 5
        with self.assertRaises(ValueError):
            self.validator.start_col = 10

    def test_end_col_less_than_start_col_raises(self):
        self.validator.start_col = 5
        with self.assertRaises(ValueError):
            self.validator.end_col = 2

    def test_samplerate_zero_raises(self):
        with self.assertRaises(ValueError):
            self.validator.samplerate_fs = 0

    def test_samplerate_negative_raises(self):
        with self.assertRaises(ValueError):
            self.validator.samplerate_fs = -100

    def test_valid_range_true(self):
        self.validator._start_row = 1
        self.validator._end_row = 100
        self.validator._start_col = 0
        self.validator._end_col = 5
        self.assertTrue(self.validator.is_valid_range)

    def test_valid_range_false_when_incomplete(self):
        self.validator._start_row = 1
        self.assertFalse(self.validator.is_valid_range)

    def test_total_samples(self):
        self.validator._start_row = 1
        self.validator._end_row = 10
        self.validator._start_col = 0
        self.validator._end_col = 4
        expected = (10 - 1 + 1) * (4 - 0 + 1)
        self.assertEqual(self.validator.total_samples, expected)

    def test_total_samples_zero_when_invalid(self):
        self.assertEqual(self.validator.total_samples, 0)


class TestDateiHandlerHeaderUnit(unittest.TestCase):

    def test_standard_format(self):
        header, unit = DateiHandler.split_header_unit("Speed [km/h]")
        self.assertEqual(header, "Speed")
        self.assertEqual(unit, "km/h")

    def test_unit_prefix_format(self):
        header, unit = DateiHandler.split_header_unit("Torque [unit: Nm]")
        self.assertEqual(header, "Torque")
        self.assertEqual(unit, "Nm")

    def test_no_unit(self):
        header, unit = DateiHandler.split_header_unit("SignalName")
        self.assertEqual(header, "SignalName")
        self.assertEqual(unit, "")

    def test_empty_brackets(self):
        header, unit = DateiHandler.split_header_unit("Signal []")
        self.assertEqual(header, "Signal")
        self.assertEqual(unit, "")

    def test_special_characters_in_unit(self):
        header, unit = DateiHandler.split_header_unit("Pressure [N/m²]")
        self.assertEqual(header, "Pressure")
        self.assertEqual(unit, "N/m²")

    def test_spaces_around_unit(self):
        header, unit = DateiHandler.split_header_unit("Temp [ °C ]")
        self.assertEqual(header, "Temp")
        self.assertEqual(unit, "°C")

    def test_multiple_brackets_takes_first(self):
        header, unit = DateiHandler.split_header_unit("Signal [V] extra [ignored]")
        self.assertIn("V", unit)


class TestDateiHandlerDelimiter(unittest.TestCase):

    def test_valid_delimiters_accepted(self):
        fh = DateiHandler()
        for d in [';', ',', '\t', '|']:
            fh.delimiter = d
            self.assertEqual(fh._delimiter, d)

    def test_invalid_delimiter_raises(self):
        fh = DateiHandler()
        with self.assertRaises(ValueError):
            fh.delimiter = '#'

    def test_valid_encodings_accepted(self):
        fh = DateiHandler()
        for enc in ['utf-8', 'windows-1252', 'iso-8859-1']:
            fh.encoding = enc
            self.assertEqual(fh._encoding, enc)

    def test_invalid_encoding_raises(self):
        fh = DateiHandler()
        with self.assertRaises(ValueError):
            fh.encoding = "ascii-fantasy"


class TestDateiHandlerReadTop(unittest.TestCase):
    """Testet DateiHandler.read_top() mit echten, synthetischen CSV/TOP-Dateien -
    vorher komplett ungetestete Datei-Einlese-Pipeline (Encoding-/Delimiter-Erkennung,
    LOGITEM-Einheiten, 'Nb'-Datenstart-Erkennung, Zeitstempel-Parsing)."""

    def setUp(self):
        self.tmp_path = None

    def tearDown(self):
        if self.tmp_path and os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def _write_csv(self, content, encoding="utf-8"):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", encoding=encoding, newline="") as f:
            f.write(content)
        self.tmp_path = path
        return path

    def test_parses_columns_units_and_data(self):
        content = (
            "Nb;Date;Time;Signal1 [V];Signal2 [A]\n"
            "1;01.03.2025;10:00:00,000;1.0;2.0\n"
            "2;01.03.2025;10:00:00,010;1.5;2.5\n"
            "3;01.03.2025;10:00:00,020;2.0;3.0\n"
        )
        path = self._write_csv(content)

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_top(DummyLabel(), DummyLabel())

        self.assertIsNotNone(df)
        # Nb/Date/Time sind Metadaten-Spalten und werden aus headers/units gefiltert
        self.assertEqual(headers, ["Signal1", "Signal2"])
        self.assertEqual(units, ["V", "A"])
        self.assertEqual(df.shape, (3, 5))
        np.testing.assert_allclose(df["Signal1"].to_numpy(dtype=float), [1.0, 1.5, 2.0])

    def test_parses_echte_zeitstempel(self):
        content = (
            "Nb;Date;Time;Signal1 [V]\n"
            "1;01.03.2025;10:00:00,000;1.0\n"
            "2;01.03.2025;10:00:00,010;1.5\n"
        )
        path = self._write_csv(content)

        fh = DateiHandler()
        fh.file_path = path
        fh.read_top(DummyLabel(), DummyLabel())

        self.assertIsNotNone(fh.zeitstempel)
        self.assertEqual(len(fh.zeitstempel), 2)
        delta_ms = (fh.zeitstempel.iloc[1] - fh.zeitstempel.iloc[0]).total_seconds() * 1000
        self.assertAlmostEqual(delta_ms, 10.0, delta=0.1)

    def test_logitem_einheiten_werden_erkannt(self):
        content = (
            "LOGITEM;Signal1;info;[unit: bar];x;Res\n"
            "Nb;Date;Time;Signal1\n"
            "1;01.03.2025;10:00:00,000;5.0\n"
            "2;01.03.2025;10:00:00,010;5.5\n"
        )
        path = self._write_csv(content)

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_top(DummyLabel(), DummyLabel())

        self.assertEqual(headers, ["Signal1"])
        self.assertEqual(units, ["bar"])

    def test_ohne_nb_marker_wird_erste_zeile_als_header_genutzt(self):
        """Fehlt die 'Nb'-Zeile, greift der Fallback: Daten beginnen ab Zeile 0."""
        content = (
            "Time;Signal1 [V]\n"
            "10:00:00,000;1.0\n"
            "10:00:00,010;1.5\n"
        )
        path = self._write_csv(content)

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_top(DummyLabel(), DummyLabel())

        self.assertIsNotNone(df)
        self.assertEqual(headers, ["Signal1"])
        self.assertEqual(df.shape[0], 2)

    def test_rejects_non_csv_file(self):
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        with open(path, "wb") as f:
            f.write(b"not really an excel file")
        self.tmp_path = path

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_top(DummyLabel(), DummyLabel())

        self.assertIsNone(df)
        self.assertIsNone(headers)
        self.assertIsNone(units)


class TestDateiHandlerReadDwsExcel(unittest.TestCase):
    """Testet DateiHandler.read_dws_excel() mit einer echten, synthetischen
    DWS-Excel-Datei (MultiIndex-Header: Signalname + Einheit)."""

    def setUp(self):
        self.tmp_path = None

    def tearDown(self):
        if self.tmp_path and os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def _write_dws_excel(self, header_row=("Time", "Signal1", "Signal2"),
                          unit_row=("s", "V", "A"), n=5):
        import openpyxl
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(list(header_row))
        ws.append(list(unit_row))
        times = pd.date_range("2025-03-01 10:00:00", periods=n, freq="10ms")
        for i, t in enumerate(times):
            ws.append([t.strftime("%d.%m.%Y %H:%M:%S.%f")[:-3], float(i), float(i) + 2])
        wb.save(path)
        self.tmp_path = path
        return path

    def test_parses_multiindex_header_und_daten(self):
        path = self._write_dws_excel()

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_dws_excel(sheet_name=0, status_label=DummyLabel(), progress_label=DummyLabel())

        self.assertIsNotNone(df)
        self.assertEqual(headers, ["Time", "Signal1", "Signal2"])
        self.assertEqual(units, ["s", "V", "A"])
        self.assertEqual(df.shape, (5, 3))

    def test_parses_echte_zeitstempel(self):
        path = self._write_dws_excel()

        fh = DateiHandler()
        fh.file_path = path
        fh.read_dws_excel(sheet_name=0, status_label=DummyLabel(), progress_label=DummyLabel())

        self.assertIsNotNone(fh.zeitstempel)
        delta_ms = (fh.zeitstempel.iloc[1] - fh.zeitstempel.iloc[0]).total_seconds() * 1000
        self.assertAlmostEqual(delta_ms, 10.0, delta=0.1)

    def test_fehlende_zeitspalte_wird_abgelehnt(self):
        path = self._write_dws_excel(header_row=("Foo", "Signal1", "Signal2"),
                                     unit_row=("x", "V", "A"))

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_dws_excel(sheet_name=0, status_label=DummyLabel(), progress_label=DummyLabel())

        self.assertIsNone(df)

    def test_rejects_non_excel_file(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w") as f:
            f.write("a;b;c\n1;2;3\n")
        self.tmp_path = path

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_dws_excel(sheet_name=0, status_label=DummyLabel(), progress_label=DummyLabel())

        self.assertIsNone(df)


class TestDatenValidatorFilePipeline(unittest.TestCase):
    """End-to-End: Datei einlesen (DateiHandler) -> gewählten Zahlenbereich extrahieren
    (DatenValidator). Deckt den kompletten Weg ab, den eine echte Messdatei im Tool geht,
    ohne echte Tkinter-Entry-Widgets zu brauchen (Bereich wird direkt gesetzt statt über
    set_entries_from_gui)."""

    def setUp(self):
        self.tmp_path = None

    def tearDown(self):
        if self.tmp_path and os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_top_pipeline_end_to_end(self):
        content = (
            "Nb;Date;Time;Signal1 [V];Signal2 [A]\n"
            "1;01.03.2025;10:00:00,000;1.0;2.0\n"
            "2;01.03.2025;10:00:00,010;1.5;2.5\n"
            "3;01.03.2025;10:00:00,020;2.0;3.0\n"
        )
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.tmp_path = path

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_top(DummyLabel(), DummyLabel())

        dv = DatenValidator()
        dv.df           = df
        dv.headers      = headers
        dv.units        = units
        dv.temp_headers = headers
        dv.temp_units   = units
        dv._start_row     = 1
        dv._end_row       = 3
        dv._start_col     = 3  # Signal1 (Position in df.columns: Nb,Date,Time,Signal1,Signal2)
        dv._end_col       = 4  # Signal2
        dv._samplerate_fs = 100.0

        self.assertEqual(dv.dataframe_type, Cfg.Export.PROCESS_TOP)
        self.assertTrue(dv.can_process)

        samplerate, factor, value, out_headers, out_units = dv.validate_and_process_top(DummyLabel())

        self.assertEqual(samplerate, 100.0)
        self.assertEqual(out_headers, ["Signal1", "Signal2"])
        self.assertEqual(out_units, ["V", "A"])
        np.testing.assert_allclose(value, [[1.0, 2.0], [1.5, 2.5], [2.0, 3.0]])

    def test_dws_pipeline_end_to_end(self):
        import openpyxl
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Time", "Signal1", "Signal2"])
        ws.append(["s", "V", "A"])
        times = pd.date_range("2025-03-01 10:00:00", periods=5, freq="10ms")
        for i, t in enumerate(times):
            ws.append([t.strftime("%d.%m.%Y %H:%M:%S.%f")[:-3], float(i), float(i) + 2])
        wb.save(path)
        self.tmp_path = path

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_dws_excel(sheet_name=0, status_label=DummyLabel(), progress_label=DummyLabel())

        dv = DatenValidator()
        dv.df           = df
        dv.headers      = headers
        dv.units        = units
        dv.temp_headers = headers
        dv.temp_units   = units
        dv._start_row     = 1
        dv._end_row       = 5
        dv._start_col     = 1  # Signal1 (0=Time)
        dv._end_col       = 2  # Signal2
        dv._samplerate_fs = 100.0

        self.assertEqual(dv.dataframe_type, Cfg.Export.PROCESS_DWS)

        samplerate, factor, value, out_headers, out_units = dv.validate_and_process_dws(DummyLabel())

        self.assertEqual(out_headers, ["Signal1", "Signal2"])
        self.assertEqual(out_units, ["V", "A"])
        np.testing.assert_allclose(value, [[0, 2], [1, 3], [2, 4], [3, 5], [4, 6]])

    def test_end_row_ausserhalb_bereich_wird_geklemmt(self):
        """Regressionstest für _adjust_row_range: Eine End-Zeile jenseits der
        Datenmenge muss automatisch auf die letzte verfügbare Zeile geklemmt werden,
        statt mit einem Index-Fehler abzustürzen."""
        content = (
            "Nb;Date;Time;Signal1 [V];Signal2 [A]\n"
            "1;01.03.2025;10:00:00,000;1.0;2.0\n"
            "2;01.03.2025;10:00:00,010;1.5;2.5\n"
            "3;01.03.2025;10:00:00,020;2.0;3.0\n"
        )
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.tmp_path = path

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_top(DummyLabel(), DummyLabel())

        dv = DatenValidator()
        dv.df           = df
        dv.headers      = headers
        dv.units        = units
        dv.temp_headers = headers
        dv.temp_units   = units
        dv._start_row     = 1
        dv._end_row       = 100  # weit ausserhalb der 3 vorhandenen Zeilen
        dv._start_col     = 3    # Signal1
        dv._end_col       = 4    # Signal2
        dv._samplerate_fs = 100.0

        with mock.patch("gui_module.meldungen.showinfo") as mock_showinfo:
            samplerate, factor, value, out_headers, out_units = dv.validate_and_process_top(DummyLabel())

        self.assertTrue(mock_showinfo.called, "Nutzer sollte über die Anpassung informiert werden")
        self.assertEqual(dv.end_row, 3, "end_row sollte auf die letzte verfügbare Zeile geklemmt worden sein")
        self.assertEqual(len(value), 3)

    def test_start_row_ausserhalb_bereich_gibt_fehler(self):
        content = (
            "Nb;Date;Time;Signal1 [V];Signal2 [A]\n"
            "1;01.03.2025;10:00:00,000;1.0;2.0\n"
            "2;01.03.2025;10:00:00,010;1.5;2.5\n"
        )
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.tmp_path = path

        fh = DateiHandler()
        fh.file_path = path
        df, headers, units = fh.read_top(DummyLabel(), DummyLabel())

        dv = DatenValidator()
        dv.df           = df
        dv.headers      = headers
        dv.units        = units
        dv.temp_headers = headers
        dv.temp_units   = units
        dv._start_row     = 500  # weit ausserhalb
        dv._end_row       = 501
        dv._start_col     = 3
        dv._end_col       = 4
        dv._samplerate_fs = 100.0

        with mock.patch("gui_module.meldungen.showerror") as mock_showerror:
            result = dv.validate_and_process_top(DummyLabel())

        self.assertTrue(mock_showerror.called)
        self.assertEqual(result, (None, None, None, None, None))


class TestFilterManagerValidation(unittest.TestCase):

    def setUp(self):
        self.fm = FilterManager()
        self.fm.sample_rate = 1000
        self.fm.order = 4
        self.fm.characteristic = "butterworth"

    def test_order_less_than_one_raises(self):
        with self.assertRaises(ValueError):
            self.fm.set_filter_characteristics("butterworth", 0)

    def test_no_filter_returns_original(self):
        signal = np.sin(2 * np.pi * 50 * np.linspace(0, 1, 1000))
        self.fm.filter_type = "Kein Filter"
        result = self.fm.apply_filter(signal)
        np.testing.assert_array_equal(result, signal)

    def test_nan_signal_returns_original(self):
        signal = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 100
        result = self.fm.apply_filter(signal)
        np.testing.assert_array_equal(result, signal)

    def test_inf_signal_returns_original(self):
        signal = np.array([1.0, np.inf, 3.0, 4.0, 5.0])
        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 100
        result = self.fm.apply_filter(signal)
        np.testing.assert_array_equal(result, signal)

    def test_cutoff_above_nyquist_returns_original(self):
        signal = np.sin(2 * np.pi * 50 * np.linspace(0, 1, 1000))
        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 600
        result = self.fm.apply_filter(signal)
        np.testing.assert_array_equal(result, signal)

    def test_bandpass_low_greater_high_raises(self):
        signal = np.sin(2 * np.pi * 50 * np.linspace(0, 1, 1000))
        self.fm.filter_type = "Bandpass"
        self.fm.cutoff_frequency = 0.5
        self.fm.cutoff_frequency2 = 0.2  # Falsche Reihenfolge: low > high
        with self.assertRaises(ValueError):
            self.fm.apply_filter(signal)


class TestFilterDaempfung(unittest.TestCase):

    def setUp(self):
        self.fs = 1000
        self.t = np.linspace(0, 1, self.fs, endpoint=False)
        self.fm = FilterManager()
        self.fm.sample_rate = self.fs
        self.fm.order = 4
        self.fm.characteristic = "butterworth"

    def test_tiefpass_daempft_hohe_frequenz(self):
        signal_low = np.sin(2 * np.pi * 5 * self.t)
        signal_high = np.sin(2 * np.pi * 200 * self.t)
        signal = signal_low + signal_high

        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 20
        result = self.fm.apply_filter(signal)

        power_high_before = np.mean(signal_high ** 2)
        residual_high = result - signal_low
        power_high_after = np.mean(residual_high[100:-100] ** 2)

        self.assertLess(power_high_after, power_high_before * 0.01,
                        "Tiefpass hat hohe Frequenz nicht ausreichend gedämpft")
        logger.info("Tiefpass-Test bestanden: Dämpfung = %.2f dB",
                     10 * np.log10(power_high_after / power_high_before))

    def test_hochpass_daempft_niedrige_frequenz(self):
        signal_low = np.sin(2 * np.pi * 5 * self.t)
        signal_high = np.sin(2 * np.pi * 200 * self.t)
        signal = signal_low + signal_high

        self.fm.filter_type = "Hochpass"
        self.fm.cutoff_frequency = 100
        result = self.fm.apply_filter(signal)

        power_low_before = np.mean(signal_low ** 2)
        residual_low = result - signal_high
        power_low_after = np.mean(residual_low[100:-100] ** 2)

        self.assertLess(power_low_after, power_low_before * 0.01,
                        "Hochpass hat niedrige Frequenz nicht ausreichend gedämpft")
        logger.info("Hochpass-Test bestanden: Dämpfung = %.2f dB",
                     10 * np.log10(power_low_after / power_low_before))

    def test_bandpass_laesst_zielfrequenz_durch(self):
        signal_low = np.sin(2 * np.pi * 5 * self.t)
        signal_mid = np.sin(2 * np.pi * 100 * self.t)
        signal_high = np.sin(2 * np.pi * 400 * self.t)
        signal = signal_low + signal_mid + signal_high

        self.fm.filter_type = "Bandpass"
        self.fm.cutoff_frequency = 50
        self.fm.cutoff_frequency2 = 150
        result = self.fm.apply_filter(signal)

        power_mid_before = np.mean(signal_mid ** 2)
        power_mid_after = np.mean(result[100:-100] ** 2)

        self.assertGreater(power_mid_after, power_mid_before * 0.5,
                           "Bandpass hat Zielfrequenz zu stark gedämpft")
        logger.info("Bandpass-Test bestanden: Zielfrequenz-Erhaltung = %.1f%%",
                     (power_mid_after / power_mid_before) * 100)

    def test_tiefpass_kurzes_signal(self):
        short_signal = np.sin(2 * np.pi * 5 * np.linspace(0, 0.1, 50))
        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 20
        result = self.fm.apply_filter(short_signal)
        self.assertEqual(len(result), len(short_signal))

    def test_hohe_filterordnung_stabil(self):
        signal = np.sin(2 * np.pi * 50 * self.t)
        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 100
        self.fm.order = 10
        result = self.fm.apply_filter(signal)
        self.assertTrue(np.all(np.isfinite(result)),
                        "Hohe Filterordnung erzeugt NaN/Inf")

    def test_alle_charakteristiken(self):
        signal = np.sin(2 * np.pi * 50 * self.t)
        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 100
        for char in ["butterworth", "bessel", "Chebyshev I", "Elliptic"]:
            self.fm.characteristic = char
            self.fm.order = 4
            result = self.fm.apply_filter(signal)
            self.assertTrue(np.all(np.isfinite(result)),
                            f"Charakteristik {char} erzeugt NaN/Inf")
            logger.info("Filter-Charakteristik %s: bestanden", char)


class TestFFTBerechnung(unittest.TestCase):

    def test_fft_sinus_10hz(self):
        fs = 1000
        t = np.linspace(0, 1, fs, endpoint=False)
        amplitude = 3.0
        freq = 10.0
        signal = amplitude * np.sin(2 * np.pi * freq * t)

        dv = DatenVerarbeiter()
        dv.dt = 1.0 / fs
        dv.window_type = "rectangular"
        f_axis, amp, phase = dv.calculate_fft(signal, t)

        peak_idx = np.argmax(amp)
        peak_freq = f_axis[peak_idx]
        peak_amp = amp[peak_idx]

        self.assertAlmostEqual(peak_freq, freq, delta=2.0,
                               msg=f"FFT Peak-Frequenz {peak_freq} Hz statt erwartet {freq} Hz")
        self.assertAlmostEqual(peak_amp, amplitude, delta=0.1,
                               msg=f"FFT Peak-Amplitude {peak_amp} statt erwartet {amplitude} "
                                   f"(physikalisch korrekte Amplitude, nicht halbiert)")
        logger.info("FFT-Test: Peak bei %.1f Hz mit Amplitude %.3f (erwartet: %.1f Hz, %.1f)",
                     peak_freq, peak_amp, freq, amplitude)

    def test_fft_zwei_frequenzen(self):
        fs = 1000
        t = np.linspace(0, 1, fs, endpoint=False)
        signal = 2.0 * np.sin(2 * np.pi * 50 * t) + 1.0 * np.sin(2 * np.pi * 120 * t)

        dv = DatenVerarbeiter()
        dv.dt = 1.0 / fs
        dv.window_type = "rectangular"
        f_axis, amp, phase = dv.calculate_fft(signal, t)

        idx_50 = np.argmin(np.abs(f_axis - 50))
        idx_120 = np.argmin(np.abs(f_axis - 120))

        self.assertAlmostEqual(amp[idx_50], 2.0, delta=0.1,
                               msg="50 Hz Amplitude falsch")
        self.assertAlmostEqual(amp[idx_120], 1.0, delta=0.1,
                               msg="120 Hz Amplitude falsch")
        logger.info("FFT Zwei-Frequenzen-Test: 50 Hz=%.3f, 120 Hz=%.3f", amp[idx_50], amp[idx_120])

    def test_fft_zu_wenige_samples(self):
        """FFT mit weniger als FFT_MIN_SAMPLES muss fehlschlagen (kein sinnvolles Spektrum)."""
        dv = DatenVerarbeiter()
        dv.dt = 0.001
        t = np.array([0.0, 0.001])
        f, amp, phase = dv.calculate_fft(np.array([1.0, 1.0]), t)
        self.assertIsNone(f)
        self.assertIsNone(amp)
        self.assertIsNone(phase)

    def test_fft_genau_min_samples(self):
        """FFT mit genau FFT_MIN_SAMPLES Samples muss erfolgreich sein."""
        n = Cfg.Limits.FFT_MIN_SAMPLES
        fs = 1000
        t = np.linspace(0, n / fs, n, endpoint=False)
        signal = np.sin(2 * np.pi * 10 * t)

        dv = DatenVerarbeiter()
        dv.dt = 1.0 / fs
        dv.window_type = "rectangular"
        f, amp, phase = dv.calculate_fft(signal, t)
        self.assertIsNotNone(f)
        self.assertEqual(len(amp), n // 2)

    def test_fft_zu_viele_samples(self):
        """Signal über FFT_MAX_SAMPLES muss von validate_signal_data abgelehnt werden."""
        dv = DatenVerarbeiter()
        dv.dt = 0.001
        n = Cfg.Limits.FFT_MAX_SAMPLES + 1
        t = np.zeros(n)
        y = np.zeros(n)
        self.assertFalse(dv.validate_signal_data(t, y))

    def test_fft_dc_signal(self):
        fs = 1000
        t = np.linspace(0, 1, fs, endpoint=False)
        signal = np.ones(fs) * 5.0
        dv = DatenVerarbeiter()
        dv.dt = 1.0 / fs
        dv.window_type = "rectangular"
        f_axis, amp, phase = dv.calculate_fft(signal, t)
        self.assertAlmostEqual(amp[0], 5.0, delta=0.1,
                               msg="DC-Anteil nicht korrekt erkannt")

    def test_fft_window_type_aendert_amplitude_bei_leckage(self):
        """Regressionstest für den analyse_plotter.py-Bug: window_type wurde
        durchgereicht, aber nie angewendet - jedes Fenster lieferte dasselbe
        (rechteckige) Ergebnis. Bei einer nicht-periodischen Signallänge (Leckage)
        muss ein echtes Fenster das Spektrum spürbar verändern."""
        fs = 1000
        t = np.linspace(0, 1, fs, endpoint=False)
        # 10.3 Hz bei 1s Signallänge -> kein ganzzahliges Vielfaches -> Leckage
        signal = np.sin(2 * np.pi * 10.3 * t)

        dv = DatenVerarbeiter()
        dv.dt = 1.0 / fs

        dv.window_type = "rectangular"
        _, amp_rect, _ = dv.calculate_fft(signal.copy(), t)

        dv.window_type = "hanning"
        _, amp_hann, _ = dv.calculate_fft(signal.copy(), t)

        self.assertFalse(
            np.allclose(amp_rect, amp_hann),
            "Rechteck- und Hanning-Fenster liefern identisches Spektrum - "
            "window_type wird nicht angewendet"
        )


class TestAnalysePlotterFFT(unittest.TestCase):
    """Testet AnalysePlotter._fft_amplitude() - die FFT, die tatsächlich für die
    live angezeigten Amplitude/Phase-Tabs verwendet wird (separate Implementierung
    von DatenVerarbeiter.calculate_fft, die für den Bild-Export genutzt wird).
    Beide Implementierungen existierten unabhängig voneinander und liefen
    auseinander (fehlende Fensterfunktion + fehlerhafte DC-Normierung in
    analyse_plotter.py) - diese Klasse deckt jetzt beide Pfade ab."""

    def test_amplitude_korrekt_ohne_fenster(self):
        fs = 1000.0
        dt = 1.0 / fs
        t = np.arange(0, 2, dt)
        amplitude = 3.0
        y = amplitude * np.sin(2 * np.pi * 50 * t)

        freq, amp, _ = AnalysePlotter._fft_amplitude(y, dt, None)
        peak_idx = np.argmax(amp[1:]) + 1

        self.assertAlmostEqual(freq[peak_idx], 50.0, delta=1.0)
        self.assertAlmostEqual(amp[peak_idx], amplitude, delta=0.01)

    def test_amplitude_korrekt_mit_allen_fenstertypen(self):
        """Amplitude muss trotz Fensterung physikalisch korrekt bleiben
        (Normierung auf window.sum() statt N)."""
        fs = 1000.0
        dt = 1.0 / fs
        t = np.arange(0, 2, dt)
        amplitude = 3.0
        y = amplitude * np.sin(2 * np.pi * 50 * t)

        for window_type in ["hanning", "hamming", "blackman", "rectangular", None]:
            freq, amp, _ = AnalysePlotter._fft_amplitude(y, dt, window_type)
            peak_idx = np.argmax(amp[1:]) + 1
            self.assertAlmostEqual(
                amp[peak_idx], amplitude, delta=0.05,
                msg=f"Fenster '{window_type}': Peak-Amplitude {amp[peak_idx]} statt {amplitude}"
            )

    def test_dc_anteil_nicht_verdoppelt(self):
        fs = 1000.0
        dt = 1.0 / fs
        t = np.arange(0, 1, dt)
        offset = 2.5
        y = np.ones_like(t) * offset

        _, amp, _ = AnalysePlotter._fft_amplitude(y, dt, None)
        self.assertAlmostEqual(amp[0], offset, delta=0.01,
                               msg="DC-Anteil sollte nicht verdoppelt werden")

    def test_fenster_veraendert_spektrum_bei_leckage(self):
        """Gleicher Regressionstest wie bei DatenVerarbeiter: window_type muss
        eine sichtbare Wirkung auf das Spektrum haben."""
        fs = 1000.0
        dt = 1.0 / fs
        t = np.arange(0, 1, dt)
        y = np.sin(2 * np.pi * 10.3 * t)  # nicht-periodisch -> Leckage

        _, amp_rect, _ = AnalysePlotter._fft_amplitude(y, dt, None)
        _, amp_hann, _ = AnalysePlotter._fft_amplitude(y, dt, "hanning")

        self.assertFalse(
            np.allclose(amp_rect, amp_hann),
            "Rechteck- und Hanning-Fenster liefern identisches Spektrum - "
            "window_type wird nicht angewendet"
        )

    def test_konsistenz_mit_daten_verarbeiter(self):
        """Die beiden unabhängigen FFT-Implementierungen (Live-Plot vs.
        Bild-Export) müssen für dasselbe Signal dieselbe Amplitude liefern.
        Verhindert, dass die beiden Implementierungen künftig wieder auseinanderlaufen."""
        fs = 1000.0
        dt = 1.0 / fs
        t = np.arange(0, 2, dt)
        y = 3.0 * np.sin(2 * np.pi * 50 * t) + 0.5

        for window_type in ["hanning", "hamming", "blackman", "rectangular"]:
            dv = DatenVerarbeiter()
            dv.dt = dt
            dv.window_type = window_type
            freq_dv, amp_dv, _ = dv.calculate_fft(y.copy(), t)

            freq_ap, amp_ap, _ = AnalysePlotter._fft_amplitude(y.copy(), dt, window_type)

            # daten_verarbeiter liefert N//2 Bins (kein Nyquist-Bin), analyse_plotter
            # (rfft) liefert N//2+1 Bins (inkl. Nyquist) - nur den gemeinsamen Bereich vergleichen.
            n_common = len(amp_dv)
            np.testing.assert_allclose(
                amp_dv, amp_ap[:n_common], atol=0.02,
                err_msg=f"FFT-Implementierungen weichen bei window_type='{window_type}' voneinander ab"
            )


class TestRMSundAVG(unittest.TestCase):
    """Ruft DatenVerarbeiter.calculate_rms/calculate_avg auf (nicht np.mean/np.sqrt
    direkt nachgebaut) - sonst testet der Test nie den tatsächlichen Produktivcode."""

    def setUp(self):
        self.dv = DatenVerarbeiter()

    def test_rms_sinus(self):
        fs = 10000
        t = np.linspace(0, 1, fs, endpoint=False)
        amplitude = 5.0
        signal = amplitude * np.sin(2 * np.pi * 50 * t)

        rms = self.dv.calculate_rms(signal)
        expected_rms = amplitude / np.sqrt(2)

        self.assertAlmostEqual(rms, expected_rms, delta=0.01,
                               msg=f"RMS {rms} statt erwartet {expected_rms}")
        logger.info("RMS-Test: %.4f (erwartet: %.4f)", rms, expected_rms)

    def test_avg_sinus_near_zero(self):
        fs = 10000
        t = np.linspace(0, 1, fs, endpoint=False)
        signal = 5.0 * np.sin(2 * np.pi * 50 * t)

        avg = self.dv.calculate_avg(signal)

        self.assertAlmostEqual(avg, 0.0, delta=0.01,
                               msg=f"AVG eines Sinus sollte ~0 sein, ist aber {avg}")
        logger.info("AVG-Test: %.6f (erwartet: ~0.0)", avg)

    def test_rms_constant_signal(self):
        signal = np.ones(1000) * 3.0
        rms = self.dv.calculate_rms(signal)
        self.assertAlmostEqual(rms, 3.0, delta=0.001)

    def test_avg_constant_signal(self):
        signal = np.ones(1000) * 7.5
        avg = self.dv.calculate_avg(signal)
        self.assertAlmostEqual(avg, 7.5, delta=0.001)

    def test_rms_empty_signal_returns_none(self):
        self.assertIsNone(self.dv.calculate_rms(np.array([])))

    def test_avg_empty_signal_returns_none(self):
        self.assertIsNone(self.dv.calculate_avg(np.array([])))


class TestDifferentiationIntegration(unittest.TestCase):
    """Ruft DatenVerarbeiter.calculate_differential/calculate_integral auf
    (nicht np.gradient/np.cumsum direkt nachgebaut)."""

    def setUp(self):
        self.dv = DatenVerarbeiter()

    def test_differentiation_sin_to_cos(self):
        fs = 10000
        freq = 10.0
        t = np.linspace(0, 1, fs, endpoint=False)
        signal = np.sin(2 * np.pi * freq * t)

        diff = self.dv.calculate_differential(signal, t)
        expected = 2 * np.pi * freq * np.cos(2 * np.pi * freq * t)

        middle = slice(500, 9500)
        correlation = np.corrcoef(diff[middle], expected[middle])[0, 1]

        self.assertGreater(correlation, 0.99,
                           msg=f"Ableitung von sin sollte cos ergeben, Korrelation: {correlation}")
        logger.info("Differentiation-Test: Korrelation = %.6f", correlation)

    def test_integration_constant(self):
        fs = 1000
        t = np.linspace(0, 1, fs, endpoint=False)
        signal = np.ones(fs) * 2.0

        integral = self.dv.calculate_integral(signal, t)

        self.assertAlmostEqual(integral[-1], 2.0, delta=0.01,
                               msg="Integral einer Konstante 2.0 über 1s sollte 2.0 sein")
        logger.info("Integration-Test: Endwert = %.4f (erwartet: 2.0)", integral[-1])

    def test_integration_linear(self):
        fs = 1000
        t = np.linspace(0, 1, fs, endpoint=False)
        signal = t

        integral = self.dv.calculate_integral(signal, t)

        self.assertAlmostEqual(integral[-1], 0.5, delta=0.05,
                               msg="Integral von t über [0,1] sollte ~0.5 sein")

    def test_differential_invalid_data_returns_none(self):
        self.assertIsNone(self.dv.calculate_differential(np.array([1.0]), None))


class TestDetrendSignal(unittest.TestCase):
    """Testet DatenVerarbeiter.detrend_signal (lineare Trendbereinigung)."""

    def setUp(self):
        self.dv = DatenVerarbeiter()

    def test_removes_linear_trend(self):
        n = 1000
        t = np.linspace(0, 1, n, endpoint=False)
        trend = 3.0 * t + 10.0
        signal = trend + 0.1 * np.sin(2 * np.pi * 50 * t)

        detrended = self.dv.detrend_signal(signal, t)

        # Nach der Entfernung des linearen Trends darf kein signifikanter
        # linearer Anteil mehr übrig sein.
        slope_after = np.polyfit(np.arange(n), detrended, 1)[0]
        self.assertAlmostEqual(slope_after, 0.0, delta=1e-6,
                               msg=f"Nach Detrend sollte keine Steigung mehr da sein, ist aber {slope_after}")
        logger.info("Detrend-Test: Steigung nach Entfernung = %.8f (erwartet: ~0)", slope_after)

    def test_constant_signal_becomes_zero(self):
        n = 500
        t = np.linspace(0, 1, n, endpoint=False)
        signal = np.ones(n) * 42.0

        detrended = self.dv.detrend_signal(signal, t)

        np.testing.assert_allclose(detrended, 0.0, atol=1e-9,
                                   err_msg="Eine Konstante ist ihr eigener Trend - nach Detrend sollte ~0 übrig bleiben")

    def test_preserves_length(self):
        n = 300
        t = np.linspace(0, 1, n, endpoint=False)
        signal = np.random.default_rng(0).normal(size=n)

        detrended = self.dv.detrend_signal(signal, t)

        self.assertEqual(len(detrended), n)

    def test_invalid_data_returns_none(self):
        # t und y unterschiedlich lang -> validate_signal_data schlägt fehl
        self.assertIsNone(self.dv.detrend_signal(np.array([1.0, 2.0, 3.0]), np.array([0.0, 1.0])))


class TestFensterfunktionen(unittest.TestCase):
    """Ruft DatenVerarbeiter._get_window() auf (nicht np.hanning direkt) - so wird
    auch geprüft, dass window_type tatsächlich die zurückgegebene Fensterfunktion
    steuert (genau das war beim FFT-Bug in analyse_plotter.py nicht der Fall:
    die UI-Auswahl wurde durchgereicht, aber nie angewendet)."""

    def setUp(self):
        self.dv = DatenVerarbeiter()

    def test_hanning_fenster_laenge(self):
        nS = 1000
        self.dv.window_type = "hanning"
        window = self.dv._get_window(nS)
        self.assertEqual(len(window), nS)

    def test_hanning_fenster_randwerte(self):
        nS = 1000
        self.dv.window_type = "hanning"
        window = self.dv._get_window(nS)
        self.assertAlmostEqual(window[0], 0.0, delta=0.001,
                               msg="Hanning-Fenster sollte am Rand 0 sein")
        self.assertAlmostEqual(window[-1], 0.0, delta=0.001,
                               msg="Hanning-Fenster sollte am Rand 0 sein")

    def test_hanning_fenster_maximum(self):
        nS = 1000
        self.dv.window_type = "hanning"
        window = self.dv._get_window(nS)
        self.assertAlmostEqual(np.max(window), 1.0, delta=0.01,
                               msg="Hanning-Fenster Maximum sollte ~1.0 sein")

    def test_hanning_anwendung_reduziert_amplitude(self):
        nS = 1000
        signal = np.ones(nS)
        self.dv.window_type = "hanning"
        window = self.dv._get_window(nS)
        windowed = signal * window
        self.assertLess(np.mean(np.abs(windowed)), np.mean(np.abs(signal)),
                        "Gefenstertes Signal sollte geringere mittlere Amplitude haben")

    def test_rechteck_fenster_aendert_nichts(self):
        nS = 1000
        signal = np.sin(2 * np.pi * 50 * np.linspace(0, 1, nS))
        self.dv.window_type = "rectangular"
        window = self.dv._get_window(nS)
        windowed = signal * window
        np.testing.assert_array_equal(windowed, signal)

    def test_window_type_aendert_tatsaechlich_das_fenster(self):
        """Regressionstest für genau die Bug-Klasse aus analyse_plotter.py:
        Ein window_type-Parameter/Property muss auch tatsächlich ein anderes
        Fenster liefern - sonst ist die UI-Auswahl wirkungslos."""
        nS = 500
        fenster = {}
        for wt in Cfg.FFT.WINDOW_TYPES:
            self.dv.window_type = wt
            fenster[wt] = self.dv._get_window(nS)

        # rectangular muss sich von allen echten Fensterfunktionen unterscheiden
        for wt in Cfg.FFT.WINDOW_TYPES:
            if wt == "rectangular":
                continue
            self.assertFalse(
                np.array_equal(fenster["rectangular"], fenster[wt]),
                f"Fenster 'rectangular' und '{wt}' sind identisch - "
                f"window_type hat keine Wirkung"
            )


class TestFilterKoeffizienten(unittest.TestCase):

    def setUp(self):
        self.fm = FilterManager()
        self.fm.sample_rate = 1000
        self.fm.order = 4
        self.fm.characteristic = "butterworth"

    def test_tiefpass_koeffizienten_existieren(self):
        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 100
        b, a, sos = self.fm.get_filter_coefficients()
        self.assertIsNotNone(b)
        self.assertIsNotNone(a)
        self.assertIsNotNone(sos)
        logger.info("Tiefpass-Koeffizienten: b=%d Werte, a=%d Werte, sos=%s",
                     len(b), len(a), sos.shape)

    def test_kein_filter_gibt_none(self):
        self.fm.filter_type = "Kein Filter"
        b, a, sos = self.fm.get_filter_coefficients()
        self.assertIsNone(b)
        self.assertIsNone(a)
        self.assertIsNone(sos)

    def test_filter_info_dict(self):
        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 100
        info = self.fm.get_filter_info()
        self.assertEqual(info['type'], "Tiefpass")
        self.assertEqual(info['characteristic'], "butterworth")
        self.assertEqual(info['order'], 4)
        self.assertEqual(info['cutoff'], 100)

    def test_filter_reset(self):
        self.fm.filter_type = "Tiefpass"
        self.fm.cutoff_frequency = 100
        self.fm.reset_filter()
        self.assertEqual(self.fm.filter_type, "Kein Filter")
        self.assertIsNone(self.fm.cutoff_frequency)
        self.assertIsNone(self.fm.order)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MESSTOOL UNIT-TESTS GESTARTET")
    logger.info("=" * 60)

    result = unittest.main(verbosity=2, exit=False)

    if result.result.wasSuccessful():
        logger.info("ALLE TESTS BESTANDEN")
    else:
        for test, traceback in result.result.failures + result.result.errors:
            logger.error("FEHLGESCHLAGEN: %s\n%s", test, traceback)

    logger.info("=" * 60)
    logger.info("MESSTOOL UNIT-TESTS BEENDET")
    logger.info("=" * 60)