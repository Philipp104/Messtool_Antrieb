import unittest
import numpy as np
import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hilfsklassen.daten_validator import DataValidator
from hilfsklassen.filter_manager import FilterManager
from hilfsklassen.datei_handler import FileHandler
from hilfsklassen.daten_verarbeiter import DatenVerarbeiter

log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "test_results.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("test_messtool")


class TestDataValidatorExcelColumns(unittest.TestCase):

    def setUp(self):
        self.validator = DataValidator()

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


class TestDataValidatorProperties(unittest.TestCase):

    def setUp(self):
        self.validator = DataValidator()

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


class TestFileHandlerHeaderUnit(unittest.TestCase):

    def test_standard_format(self):
        header, unit = FileHandler.split_header_unit("Speed [km/h]")
        self.assertEqual(header, "Speed")
        self.assertEqual(unit, "km/h")

    def test_unit_prefix_format(self):
        header, unit = FileHandler.split_header_unit("Torque [unit: Nm]")
        self.assertEqual(header, "Torque")
        self.assertEqual(unit, "Nm")

    def test_no_unit(self):
        header, unit = FileHandler.split_header_unit("SignalName")
        self.assertEqual(header, "SignalName")
        self.assertEqual(unit, "")

    def test_empty_brackets(self):
        header, unit = FileHandler.split_header_unit("Signal []")
        self.assertEqual(header, "Signal")
        self.assertEqual(unit, "")

    def test_special_characters_in_unit(self):
        header, unit = FileHandler.split_header_unit("Pressure [N/m²]")
        self.assertEqual(header, "Pressure")
        self.assertEqual(unit, "N/m²")

    def test_spaces_around_unit(self):
        header, unit = FileHandler.split_header_unit("Temp [ °C ]")
        self.assertEqual(header, "Temp")
        self.assertEqual(unit, "°C")

    def test_multiple_brackets_takes_first(self):
        header, unit = FileHandler.split_header_unit("Signal [V] extra [ignored]")
        self.assertIn("V", unit)


class TestFileHandlerDelimiter(unittest.TestCase):

    def test_valid_delimiters_accepted(self):
        fh = FileHandler()
        for d in [';', ',', '\t', '|']:
            fh.delimiter = d
            self.assertEqual(fh._delimiter, d)

    def test_invalid_delimiter_raises(self):
        fh = FileHandler()
        with self.assertRaises(ValueError):
            fh.delimiter = '#'

    def test_valid_encodings_accepted(self):
        fh = FileHandler()
        for enc in ['utf-8', 'windows-1252', 'iso-8859-1']:
            fh.encoding = enc
            self.assertEqual(fh._encoding, enc)

    def test_invalid_encoding_raises(self):
        fh = FileHandler()
        with self.assertRaises(ValueError):
            fh.encoding = "ascii-fantasy"


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
        for char in ["butterworth", "bessel", "Chebyshev I", "elliptic"]:
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
        self.assertAlmostEqual(peak_amp, amplitude / 2, delta=0.1,
                               msg=f"FFT Peak-Amplitude {peak_amp} statt erwartet {amplitude / 2}")
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

        self.assertAlmostEqual(amp[idx_50], 1.0, delta=0.1,
                               msg="50 Hz Amplitude falsch")
        self.assertAlmostEqual(amp[idx_120], 0.5, delta=0.1,
                               msg="120 Hz Amplitude falsch")
        logger.info("FFT Zwei-Frequenzen-Test: 50 Hz=%.3f, 120 Hz=%.3f", amp[idx_50], amp[idx_120])

    def test_fft_leeres_signal(self):
        dv = DatenVerarbeiter()
        dv.dt = 0.001
        t = np.array([0.0, 0.001])
        f, amp, phase = dv.calculate_fft(np.array([1.0, 1.0]), t)
        self.assertIsNotNone(f)
        self.assertGreater(len(f), 0)

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


class TestRMSundAVG(unittest.TestCase):

    def test_rms_sinus(self):
        fs = 10000
        t = np.linspace(0, 1, fs, endpoint=False)
        amplitude = 5.0
        signal = amplitude * np.sin(2 * np.pi * 50 * t)

        rms = float(np.sqrt(np.nanmean(signal ** 2)))
        expected_rms = amplitude / np.sqrt(2)

        self.assertAlmostEqual(rms, expected_rms, delta=0.01,
                               msg=f"RMS {rms} statt erwartet {expected_rms}")
        logger.info("RMS-Test: %.4f (erwartet: %.4f)", rms, expected_rms)

    def test_avg_sinus_near_zero(self):
        fs = 10000
        t = np.linspace(0, 1, fs, endpoint=False)
        signal = 5.0 * np.sin(2 * np.pi * 50 * t)

        avg = float(np.nanmean(signal))

        self.assertAlmostEqual(avg, 0.0, delta=0.01,
                               msg=f"AVG eines Sinus sollte ~0 sein, ist aber {avg}")
        logger.info("AVG-Test: %.6f (erwartet: ~0.0)", avg)

    def test_rms_constant_signal(self):
        signal = np.ones(1000) * 3.0
        rms = float(np.sqrt(np.nanmean(signal ** 2)))
        self.assertAlmostEqual(rms, 3.0, delta=0.001)

    def test_avg_constant_signal(self):
        signal = np.ones(1000) * 7.5
        avg = float(np.nanmean(signal))
        self.assertAlmostEqual(avg, 7.5, delta=0.001)


class TestDifferentiationIntegration(unittest.TestCase):

    def test_differentiation_sin_to_cos(self):
        fs = 10000
        freq = 10.0
        t = np.linspace(0, 1, fs, endpoint=False)
        dt = 1.0 / fs
        signal = np.sin(2 * np.pi * freq * t)

        diff = np.gradient(signal, dt)
        expected = 2 * np.pi * freq * np.cos(2 * np.pi * freq * t)

        middle = slice(500, 9500)
        correlation = np.corrcoef(diff[middle], expected[middle])[0, 1]

        self.assertGreater(correlation, 0.99,
                           msg=f"Ableitung von sin sollte cos ergeben, Korrelation: {correlation}")
        logger.info("Differentiation-Test: Korrelation = %.6f", correlation)

    def test_integration_constant(self):
        fs = 1000
        dt = 1.0 / fs
        signal = np.ones(fs) * 2.0

        integral = np.cumsum(signal) * dt

        self.assertAlmostEqual(integral[-1], 2.0, delta=0.01,
                               msg="Integral einer Konstante 2.0 über 1s sollte 2.0 sein")
        logger.info("Integration-Test: Endwert = %.4f (erwartet: 2.0)", integral[-1])

    def test_integration_linear(self):
        fs = 1000
        dt = 1.0 / fs
        t = np.linspace(0, 1, fs, endpoint=False)
        signal = t

        integral = np.cumsum(signal) * dt

        self.assertAlmostEqual(integral[-1], 0.5, delta=0.05,
                               msg="Integral von t über [0,1] sollte ~0.5 sein")


class TestFensterfunktionen(unittest.TestCase):

    def test_hanning_fenster_laenge(self):
        nS = 1000
        window = np.hanning(nS)
        self.assertEqual(len(window), nS)

    def test_hanning_fenster_randwerte(self):
        nS = 1000
        window = np.hanning(nS)
        self.assertAlmostEqual(window[0], 0.0, delta=0.001,
                               msg="Hanning-Fenster sollte am Rand 0 sein")
        self.assertAlmostEqual(window[-1], 0.0, delta=0.001,
                               msg="Hanning-Fenster sollte am Rand 0 sein")

    def test_hanning_fenster_maximum(self):
        nS = 1000
        window = np.hanning(nS)
        self.assertAlmostEqual(np.max(window), 1.0, delta=0.01,
                               msg="Hanning-Fenster Maximum sollte ~1.0 sein")

    def test_hanning_anwendung_reduziert_amplitude(self):
        nS = 1000
        signal = np.ones(nS)
        window = np.hanning(nS)
        windowed = signal * window
        self.assertLess(np.mean(np.abs(windowed)), np.mean(np.abs(signal)),
                        "Gefenstertes Signal sollte geringere mittlere Amplitude haben")

    def test_rechteck_fenster_aendert_nichts(self):
        nS = 1000
        signal = np.sin(2 * np.pi * 50 * np.linspace(0, 1, nS))
        window = np.ones(nS)
        windowed = signal * window
        np.testing.assert_array_equal(windowed, signal)


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