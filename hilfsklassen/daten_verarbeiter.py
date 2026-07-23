"""
Daten Verarbeiter - Signalverarbeitung
=======================================
Klasse für die Verarbeitung von Signaldaten:
- Zeitbereichsanalyse
- FFT-Berechnung
- Filteranwendung
- Statistische Kennwerte
- Datenexport
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
import logging

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq

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
class DatenVerarbeiter:
    """Klasse für Signalverarbeitung und Datenexport"""

    def __init__(self):

        # --- Verarbeitungsparameter ---
        self._window_type  = Cfg.Defaults.FFT_WINDOW_TYPE
        self._normalize    = Cfg.Defaults.FFT_NORMALIZE
        self._log_scale    = Cfg.Defaults.FFT_LOG_SCALE
        self._dt           = Cfg.FFT.DEFAULT_DT
        self._sample_rate  = Cfg.Defaults.SAMPLERATE

        # --- Filter-Parameter ---
        self._filter_type  = Cfg.Defaults.FILTER_CHARAKTERISTIK
        self._filter_order = Cfg.Defaults.FILTER_ORDER_INT
        self._cutoff_freq  = Cfg.Defaults.CUTOFF_FREQ

    # --------------------------------------------------------
    #  PROPERTIES
    # --------------------------------------------------------

    @property
    def window_type(self):
        """Fensterfunktion für FFT/Signalverarbeitung"""
        return self._window_type

    @window_type.setter
    def window_type(self, value):
        if value not in Cfg.FFT.WINDOW_TYPES:
            raise ValueError(Cfg.Errors.PROC_INVALID_WINDOW.format(value))
        self._window_type = value

    @property
    def normalize(self):
        """Normalisierung der FFT-Ergebnisse"""
        return self._normalize

    @normalize.setter
    def normalize(self, value):
        if not isinstance(value, bool):
            raise ValueError("Normalize muss boolean sein")
        self._normalize = value

    @property
    def log_scale(self):
        """Logarithmische Skalierung der FFT"""
        return self._log_scale

    @log_scale.setter
    def log_scale(self, value):
        if not isinstance(value, bool):
            raise ValueError("Log_scale muss boolean sein")
        self._log_scale = value

    @property
    def dt(self):
        """Zeitschritt zwischen Samples"""
        return self._dt

    @dt.setter
    def dt(self, value):
        if value <= 0:
            raise ValueError(Cfg.Errors.PROC_INVALID_SAMPLE_RATE.format(value))
        self._dt          = value
        self._sample_rate = 1.0 / value

    @property
    def sample_rate(self):
        """Samplerate in Hz"""
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value):
        if value <= 0:
            raise ValueError(Cfg.Errors.PROC_INVALID_SAMPLE_RATE.format(value))
        self._sample_rate = value
        self._dt          = 1.0 / value

    @property
    def filter_type(self):
        """Filtertyp (z.B. butterworth, bessel)"""
        return self._filter_type

    @filter_type.setter
    def filter_type(self, value):
        if value not in Cfg.Defaults.FILTER_CHARAKTERISTIKEN:
            raise ValueError(Cfg.Errors.PROC_INVALID_WINDOW.format(value))
        self._filter_type = value

    @property
    def filter_order(self):
        """Filterordnung"""
        return self._filter_order

    @filter_order.setter
    def filter_order(self, value):
        if not (Cfg.Limits.FILTER_ORDER_MIN <= value <= Cfg.Limits.FILTER_ORDER_MAX):
            raise ValueError(Cfg.Errors.FILTER_INVALID_ORDER.format(
                Cfg.Limits.FILTER_ORDER_MIN,
                Cfg.Limits.FILTER_ORDER_MAX
            ))
        self._filter_order = value

    @property
    def cutoff_freq(self):
        """Grenzfrequenz in Hz"""
        return self._cutoff_freq

    @cutoff_freq.setter
    def cutoff_freq(self, value):
        if not (Cfg.Limits.CUTOFF_FREQ_MIN <= value <= Cfg.Limits.CUTOFF_FREQ_MAX):
            raise ValueError(Cfg.Errors.FILTER_INVALID_CUTOFF.format(
                Cfg.Limits.CUTOFF_FREQ_MIN,
                Cfg.Limits.CUTOFF_FREQ_MAX
            ))
        self._cutoff_freq = value

    # --------------------------------------------------------
    #  VALIDIERUNG
    # --------------------------------------------------------

    def validate_signal_data(self, t, y, signal_name=""):
        """
        Validiert Zeit- und Signaldaten.
        Args:
            t:           Zeitarray
            y:           Signalarray
            signal_name: Name des Signals (für Logs)
        Returns:
            bool: True wenn gültig
        """
        if t is None or y is None:
            logger.error(Cfg.Errors.PROC_NO_SIGNAL_DATA)
            return False

        if len(t) != len(y):
            logger.error(Cfg.Errors.PROC_INCONSISTENT_LENGTHS.format(len(t), len(y)))
            return False

        if len(t) < 2:
            logger.error(Cfg.Errors.PROC_TOO_FEW_SAMPLES.format(2))
            return False

        if len(t) > Cfg.Limits.FFT_MAX_SAMPLES:
            logger.error(Cfg.Errors.PROC_TOO_MANY_SAMPLES.format(Cfg.Limits.FFT_MAX_SAMPLES))
            return False

        logger.info(Cfg.Logs.PROC_TIME_DATA.format(len(t), self.dt))
        logger.info(Cfg.Logs.PROC_SIGNAL_DATA.format(len(y), "N/A"))
        return True

    # --------------------------------------------------------
    #  FFT
    # --------------------------------------------------------

    def calculate_fft(self, y, t=None):
        """
        Berechnet FFT des Signals.
        Args:
            y: Signalarray
            t: Zeitarray (optional, für Samplerate)
        Returns:
            tuple: (frequencies, amplitude, phase)
        """
        if not self.validate_signal_data(t, y):
            return None, None, None

        if len(t) < Cfg.Limits.FFT_MIN_SAMPLES:
            logger.error(Cfg.Errors.PROC_TOO_FEW_SAMPLES.format(Cfg.Limits.FFT_MIN_SAMPLES))
            return None, None, None

        N = len(y)
        if t is not None:
            T                = t[-1] - t[0]
            self.sample_rate = N / T
            self.dt          = 1.0 / self.sample_rate

        window     = self._get_window(N)
        y_windowed = y * window
        logger.info(Cfg.Logs.PROC_WINDOW_APPLIED.format(self.window_type))

        fft_result  = fft(y_windowed)
        frequencies = fftfreq(N, self.dt)[:N//2]
        amplitude   = np.abs(fft_result[:N//2])
        phase       = np.angle(fft_result[:N//2])

        if self.normalize:
            amplitude /= N
            logger.info(Cfg.Logs.PROC_NORMALIZING.format(1.0 / N))

        logger.info(Cfg.Logs.PROC_CALC_FFT.format(N, self.window_type))
        return frequencies, amplitude, phase

    def _get_window(self, N):
        """Erzeugt Fensterfunktion."""
        if self.window_type == "hanning":
            return np.hanning(N)
        elif self.window_type == "hamming":
            return np.hamming(N)
        elif self.window_type == "blackman":
            return np.blackman(N)
        else:  # rectangular
            return np.ones(N)

    # --------------------------------------------------------
    #  STATISTISCHE KENNWERTE
    # --------------------------------------------------------

    def calculate_avg(self, y):
        """Berechnet Durchschnittswert."""
        if y is None or len(y) == 0:
            logger.error(Cfg.Errors.PROC_EMPTY_SIGNAL)
            return None
        return np.mean(y)

    def calculate_rms(self, y):
        """Berechnet Effektivwert (RMS)."""
        if y is None or len(y) == 0:
            logger.error(Cfg.Errors.PROC_EMPTY_SIGNAL)
            return None
        return np.sqrt(np.mean(y**2))

    def calculate_differential(self, y, t=None):
        """Berechnet Ableitung (dY/dt)."""
        if not self.validate_signal_data(t, y):
            return None
        dt = np.mean(np.diff(t)) if t is not None else self.dt
        return np.gradient(y, dt)

    def calculate_integral(self, y, t=None):
        """Berechnet Integral (∫Y dt)."""
        if not self.validate_signal_data(t, y):
            return None
        dt = np.mean(np.diff(t)) if t is not None else self.dt
        return np.cumsum(y) * dt

    def detrend_signal(self, y, t=None):
        """Entfernt Gleichanteil (Lineare Detrend)."""
        if not self.validate_signal_data(t, y):
            return None
        if len(y) < 2:
            return y.copy()
        x         = np.arange(len(y))
        coeffs    = np.polyfit(x, y, 1)
        trend     = np.polyval(coeffs, x)
        detrended = y - trend
        logger.info(Cfg.Logs.PROC_DETRENDING)
        return detrended

    def smooth_signal(self, y, window_len=11, window='hanning'):
        """
        Glättet Signal mit gleitendem Durchschnitt.
        Args:
            y:          Signalarray
            window_len: Fensterlänge (ungerade)
            window:     Fensterfunktion
        Returns:
            np.array: Geglättetes Signal
        """
        if y is None or len(y) < window_len:
            logger.error(Cfg.Errors.PROC_TOO_FEW_SAMPLES.format(window_len))
            return None
        if window_len < 3:
            return y.copy()
        if window not in Cfg.FFT.WINDOW_TYPES:
            window = 'hanning'

        s        = np.r_[y[window_len-1:0:-1], y, y[-2:-window_len-1:-1]]
        w        = self._get_window(window_len)
        smoothed = np.convolve(w / w.sum(), s, mode='valid')
        logger.info(Cfg.Logs.PROC_SMOOTHING.format(window))
        return smoothed[window_len//2:-window_len//2+1]

    # --------------------------------------------------------
    #  EXPORT
    # --------------------------------------------------------

    def export_signal_data(self, save_path, t, y, headers, units,
                           include_fft=False,
                           include_avg=False, include_rms=False,
                           include_diff=False, include_integral=False):
        """
        Exportiert Signaldaten in verschiedene Formate.
        Args:
            save_path:   Zieldateipfad (ohne Endung)
            t:           Zeitarray
            y:           Signalarray (oder Liste von Arrays)
            headers:     Signalnamen
            units:       Einheiten
            include_*:   Flags für zusätzliche Daten
        Returns:
            tuple: (success, message)
        """
        try:
            logger.info(Cfg.Logs.PROC_START.format(
                headers[0] if headers else "Unbekannt"
            ))

            if not isinstance(y, list):
                y       = [y]
                headers = [headers]
                units   = [units]

            data = {"Time [s]": t}

            for signal, header, unit in zip(y, headers, units):
                data[f"{header} [{unit}]"] = signal

                if include_avg and len(signal) > 0:
                    avg = self.calculate_avg(signal)
                    data[f"{header} AVG [{unit}]"] = [avg] * len(t)

                if include_rms and len(signal) > 0:
                    rms = self.calculate_rms(signal)
                    data[f"{header} RMS [{unit}]"] = [rms] * len(t)

                if include_diff:
                    diff = self.calculate_differential(signal, t)
                    if diff is not None:
                        data[f"d({header})/dt [{unit}/s]"] = diff

                if include_integral:
                    integral = self.calculate_integral(signal, t)
                    if integral is not None:
                        data[f"∫{header} dt [{unit}·s]"] = integral

            df = pd.DataFrame(data)

            for fmt, ext in Cfg.Export.IMAGE_FORMATS:
                try:
                    if fmt == "PNG":
                        self._export_to_image(save_path + ext, df, t, y, headers, units)
                    elif fmt == "PDF":
                        self._export_to_pdf(save_path + ext, df)
                    elif fmt == "SVG":
                        self._export_to_svg(save_path + ext, df)
                    logger.info(Cfg.Logs.PROC_EXPORTING.format(save_path + ext, fmt))
                except Exception as e:
                    logger.error(f"Export nach {fmt} fehlgeschlagen: {e}")

            return True, Cfg.Status.PROC_EXPORT_COMPLETED.format(save_path)

        except Exception as e:
            logger.error(Cfg.Errors.PROC_EXPORT_FAILED.format(e))
            return False, Cfg.Errors.PROC_EXPORT_FAILED.format(e)

    def _export_to_image(self, path, df, t, y, headers, units):
        """Exportiert Daten als Bild (Placeholder-Implementierung)."""
        logger.info(f"Exportiere Bild nach {path} (Daten: {len(t)} Samples)")

    def _export_to_pdf(self, path, df):
        """Exportiert DataFrame als PDF (Placeholder)."""
        logger.info(f"Exportiere PDF nach {path}")

    def _export_to_svg(self, path, df):
        """Exportiert DataFrame als SVG (Placeholder)."""
        logger.info(f"Exportiere SVG nach {path}")

    # --------------------------------------------------------
    #  HAUPTVERARBEITUNG
    # --------------------------------------------------------

    def process_signal(self, t, y, signal_name="Unbekannt",
                       calculate_fft=False,
                       calculate_avg=False, calculate_rms=False,
                       calculate_diff=False, calculate_integral=False):
        """
        Hauptmethode zur Signalverarbeitung.
        Args:
            t:                  Zeitarray
            y:                  Signalarray
            signal_name:        Name des Signals
            calculate_fft:      FFT berechnen
            calculate_avg:      Durchschnitt berechnen
            calculate_rms:      RMS berechnen
            calculate_diff:     Ableitung berechnen
            calculate_integral: Integral berechnen
        Returns:
            dict: Ergebnisse der Verarbeitung
        """
        results = {
            "signal_name": signal_name,
            "original":    y,
            "time":        t,
            "sample_rate": self.sample_rate,
            "dt":          self.dt,
            "status":      Cfg.Status.PROC_PROCESSING,
        }

        try:
            logger.info(Cfg.Logs.PROC_START.format(signal_name))

            if not self.validate_signal_data(t, y):
                results["status"] = Cfg.Errors.PROC_NO_SIGNAL_DATA
                return results

            if calculate_fft:
                freq, amp, phase = self.calculate_fft(y, t)
                if freq is not None:
                    results.update({"frequency": freq, "amplitude": amp, "phase": phase})
                    logger.info(Cfg.Status.PROC_FFT_CALCULATED.format(self.window_type))

            if calculate_avg:
                results["avg"] = self.calculate_avg(y)

            if calculate_rms:
                results["rms"] = self.calculate_rms(y)

            if calculate_diff:
                results["differential"] = self.calculate_differential(y, t)

            if calculate_integral:
                results["integral"] = self.calculate_integral(y, t)

            results["status"] = Cfg.Status.PROC_COMPLETED
            logger.info(Cfg.Status.PROC_COMPLETED)
            return results

        except Exception as e:
            results["status"] = Cfg.Errors.PROC_PROCESSING_FAILED.format(e)
            logger.error(results["status"])
            return results