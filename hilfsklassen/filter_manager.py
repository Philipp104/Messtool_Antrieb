"""
Filter Manager - Signalfilterung
=================================
Klasse für digitale Signalfilter: Tiefpass, Hochpass,
Bandpass mit verschiedenen Charakteristiken (Butterworth,
Chebyshev, Bessel) und konfigurierbarer Ordnung.
"""

# ============================================================
#  IMPORTS – Standardbibliotheken
# ============================================================
import logging

# ============================================================
#  IMPORTS – Drittanbieter
# ============================================================
import numpy as np
from scipy import signal as scipy_signal

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
class FilterManager:
    """Klasse für verschiedene Signalfilter mit Parameter-Container"""

    def __init__(self):

        # --- Filter-Parameter ---
        self.filter_type       = Cfg.Defaults.FILTER_TYP
        self.characteristic    = Cfg.Defaults.FILTER_CHARAKTERISTIK
        self.order             = Cfg.Defaults.FILTER_ORDER_INT
        self.sample_rate       = Cfg.Defaults.SAMPLE_RATE
        self.cutoff_frequency  = None
        self.cutoff_frequency2 = None

        # --- Koeffizienten ---
        self.b_coeffs   = None
        self.a_coeffs   = None
        self.sos_coeffs = None

        # --- Warn-Flags (einmalige Warnungen) ---
        self._warned_nan_inf        = False
        self._warned_cutoff         = False
        self._warned_cutoff2        = False
        self._warned_bandpass_range = False

    # --------------------------------------------------------
    #  PARAMETER SETZEN
    # --------------------------------------------------------

    def set_filter_parameters(self, filter_type, cutoff_frequency, sample_rate, cutoff_frequency2=None):
        """
        Setzt Filter-Parameter aus GUI mit Validierung.
        Args:
            filter_type:        Filtertyp (Tiefpass/Hochpass/Bandpass)
            cutoff_frequency:   Grenzfrequenz in Hz
            sample_rate:        Samplerate in Hz
            cutoff_frequency2:  Zweite Grenzfrequenz für Bandpass
        """
        if filter_type not in Cfg.Filter.SUPPORTED_TYPES:
            raise ValueError(Cfg.Errors.FILTER_INVALID_TYPE.format(filter_type))

        if not (Cfg.Limits.SAMPLE_RATE_MIN <= sample_rate <= Cfg.Limits.SAMPLE_RATE_MAX):
            raise ValueError(Cfg.Errors.FILTER_INVALID_SAMPLE_RATE.format(
                Cfg.Limits.SAMPLE_RATE_MIN,
                Cfg.Limits.SAMPLE_RATE_MAX
            ))

        if cutoff_frequency is not None and not (Cfg.Limits.CUTOFF_FREQ_MIN <= cutoff_frequency <= Cfg.Limits.CUTOFF_FREQ_MAX):
            raise ValueError(Cfg.Errors.FILTER_INVALID_CUTOFF.format(
                Cfg.Limits.CUTOFF_FREQ_MIN,
                Cfg.Limits.CUTOFF_FREQ_MAX
            ))

        if filter_type == "Bandpass" and cutoff_frequency2 is None:
            raise ValueError(Cfg.Errors.FILTER_BANDPASS_TWO_FREQS)

        self.filter_type       = filter_type
        self.cutoff_frequency  = cutoff_frequency
        self.cutoff_frequency2 = cutoff_frequency2
        self.sample_rate       = sample_rate

        logger.info(Cfg.Logs.FILTER_INFO.format(filter_type, self.characteristic, self.order))

    def set_filter_characteristics(self, characteristic, order):
        """
        Setzt Filter-Charakteristik und Ordnung mit Validierung.
        Args:
            characteristic: Filtercharakteristik (butterworth/bessel/etc.)
            order:          Filterordnung
        """
        if characteristic not in Cfg.Filter.SUPPORTED_CHARACTERISTICS:
            raise ValueError(Cfg.Errors.FILTER_INVALID_CHAR.format(characteristic))

        if not (Cfg.Limits.FILTER_ORDER_MIN <= order <= Cfg.Limits.FILTER_ORDER_MAX):
            raise ValueError(Cfg.Errors.FILTER_INVALID_ORDER.format(
                Cfg.Limits.FILTER_ORDER_MIN,
                Cfg.Limits.FILTER_ORDER_MAX
            ))

        self.characteristic = characteristic
        self.order          = order

        logger.info(Cfg.Logs.FILTER_INFO.format(self.filter_type, characteristic, order))

    # --------------------------------------------------------
    #  FILTER ANWENDEN
    # --------------------------------------------------------

    def apply_filter(self, input_signal):
        """
        Wendet den gewählten Filter auf das Signal an mit vollständiger Validierung.
        Args:
            input_signal: Eingabesignal (numpy array)
        Returns:
            numpy.array: Gefiltertes Signal oder Originalsignal bei Fehlern
        """
        if (self.filter_type == Cfg.Defaults.FILTER_TYP or
                self.cutoff_frequency is None or
                self.sample_rate is None):
            logger.info(Cfg.Status.FILTER_NO_ACTIVE)
            return input_signal

        if not np.all(np.isfinite(input_signal)):
            if not self._warned_nan_inf:
                logger.warning(Cfg.Logs.FILTER_NAN_IN_SIGNAL)
                self._warned_nan_inf = True
            return input_signal

        try:
            nyquist           = self.sample_rate / 2
            normalized_cutoff = self.cutoff_frequency / nyquist

            if normalized_cutoff >= 1.0:
                if not self._warned_cutoff:
                    logger.warning(Cfg.Logs.FILTER_CUTOFF_TOO_HIGH.format(
                        self.cutoff_frequency, nyquist
                    ))
                    self._warned_cutoff = True
                return input_signal

            logger.info(Cfg.Logs.FILTER_APPLYING.format(
                self.filter_type, self.order, self.cutoff_frequency
            ))

            if self.filter_type == "Tiefpass":
                return self._apply_lowpass_filter(input_signal, normalized_cutoff)
            elif self.filter_type == "Hochpass":
                return self._apply_highpass_filter(input_signal, normalized_cutoff)
            elif self.filter_type == "Bandpass":
                return self._apply_bandpass_filter(input_signal)
            else:
                return input_signal

        except ValueError:
            raise
        except Exception as e:
            logger.exception(Cfg.Errors.FILTER_APPLICATION.format(str(e)))
            return input_signal

    def _apply_lowpass_filter(self, input_signal, normalized_cutoff):
        """Tiefpass-Filter mit SOS-Implementierung."""
        logger.info(Cfg.Logs.FILTER_USING_SOS)
        try:
            sos             = self._build_sos(normalized_cutoff, btype='low')
            filtered_signal = scipy_signal.sosfiltfilt(sos, input_signal)
            logger.info(Cfg.Status.FILTER_APPLIED.format("Tiefpass", self.order))
            return filtered_signal
        except Exception as e:
            logger.exception(Cfg.Errors.FILTER_APPLICATION.format(str(e)))
            return input_signal

    def _apply_highpass_filter(self, input_signal, normalized_cutoff):
        """Hochpass-Filter mit SOS-Implementierung."""
        logger.info(Cfg.Logs.FILTER_USING_SOS)
        try:
            sos             = self._build_sos(normalized_cutoff, btype='high')
            filtered_signal = scipy_signal.sosfiltfilt(sos, input_signal)
            logger.info(Cfg.Status.FILTER_APPLIED.format("Hochpass", self.order))
            return filtered_signal
        except Exception as e:
            logger.exception(Cfg.Errors.FILTER_APPLICATION.format(str(e)))
            return input_signal

    def _apply_bandpass_filter(self, input_signal):
        """Bandpass-Filter mit vollständiger Validierung."""
        if self.cutoff_frequency2 is None:
            raise ValueError(Cfg.Errors.FILTER_BANDPASS_TWO_FREQS)

        nyquist               = self.sample_rate / 2
        normalized_cutoff_low  = self.cutoff_frequency / nyquist
        normalized_cutoff_high = self.cutoff_frequency2 / nyquist

        if normalized_cutoff_low >= normalized_cutoff_high:
            if not self._warned_bandpass_range:
                logger.warning(Cfg.Logs.FILTER_BANDPASS_WARNING.format(
                    self.cutoff_frequency, self.cutoff_frequency2
                ))
                self._warned_bandpass_range = True
            raise ValueError(Cfg.Errors.FILTER_LOW_HIGH_ORDER.format(
                self.cutoff_frequency, self.cutoff_frequency2
            ))

        try:
            logger.info(Cfg.Logs.FILTER_USING_SOS)
            sos             = self._build_sos([normalized_cutoff_low, normalized_cutoff_high], btype='band')
            filtered_signal = scipy_signal.sosfiltfilt(sos, input_signal)
            logger.info(Cfg.Status.FILTER_APPLIED.format("Bandpass", self.order))
            return filtered_signal

        except Exception as e:
            logger.exception(Cfg.Errors.FILTER_APPLICATION.format(str(e)))
            return input_signal

    # --------------------------------------------------------
    #  KOEFFIZIENTEN
    # --------------------------------------------------------

    def get_filter_coefficients(self):
        """
        Berechnet und speichert die Filter-Koeffizienten mit Validierung.
        Returns:
            tuple: (b_coeffs, a_coeffs, sos_coeffs) oder (None, None, None) bei Fehlern
        """
        if (self.filter_type == Cfg.Defaults.FILTER_TYP or
                self.cutoff_frequency is None or
                self.sample_rate is None):
            self._reset_coefficients()
            return None, None, None

        try:
            logger.info(Cfg.Logs.FILTER_CALC_COEFFICIENTS.format(self.filter_type, self.order))

            nyquist           = self.sample_rate / 2
            normalized_cutoff = self.cutoff_frequency / nyquist

            if normalized_cutoff >= 1.0:
                self._reset_coefficients()
                logger.warning(Cfg.Errors.FILTER_CUTOFF_TOO_HIGH.format(self.cutoff_frequency, nyquist))
                return None, None, None

            if self.filter_type == "Tiefpass":
                self.sos_coeffs = self._calculate_sos_coefficients(normalized_cutoff, btype='low')
            elif self.filter_type == "Hochpass":
                self.sos_coeffs = self._calculate_sos_coefficients(normalized_cutoff, btype='high')
            elif self.filter_type == "Bandpass":
                if self.cutoff_frequency2 is not None:
                    normalized_cutoff2 = self.cutoff_frequency2 / nyquist
                    if normalized_cutoff2 >= 1.0:
                        self._reset_coefficients()
                        logger.warning(Cfg.Errors.FILTER_CUTOFF_TOO_HIGH.format(self.cutoff_frequency2, nyquist))
                        return None, None, None
                    self.sos_coeffs = self._calculate_sos_coefficients(
                        [normalized_cutoff, normalized_cutoff2], btype='band'
                    )
                else:
                    self._reset_coefficients()
                    return None, None, None

            if self.sos_coeffs is not None:
                self.b_coeffs, self.a_coeffs = scipy_signal.sos2tf(self.sos_coeffs)
                logger.info(Cfg.Status.FILTER_COEFFICIENTS_CALC)
            else:
                self._reset_coefficients()

            return self.b_coeffs, self.a_coeffs, self.sos_coeffs

        except Exception as e:
            logger.exception(Cfg.Errors.FILTER_COEFFICIENT_CALC.format(str(e)))
            self._reset_coefficients()
            return None, None, None

    def _build_sos(self, cutoff, btype='low'):
        """
        Zentrale SOS-Berechnung für alle Filtertypen und Charakteristiken.
        Args:
            cutoff: Normalisierte Grenzfrequenz(en)
            btype:  Filtertyp (low/high/band)
        Returns:
            numpy.array: SOS-Koeffizienten
        """
        if self.characteristic == "bessel":
            return scipy_signal.bessel(
                self.order, cutoff, btype=btype, analog=False, output='sos'
            )
        elif self.characteristic == "Chebyshev I":
            return scipy_signal.cheby1(
                self.order, Cfg.Limits.DEFAULT_RIPPLE_DB,
                cutoff, btype=btype, analog=False, output='sos'
            )
        elif self.characteristic == "Elliptic":
            return scipy_signal.ellip(
                self.order, Cfg.Limits.DEFAULT_RIPPLE_DB, Cfg.Limits.DEFAULT_STOP_DB,
                cutoff, btype=btype, analog=False, output='sos'
            )
        else:  # butterworth
            return scipy_signal.butter(
                self.order, cutoff, btype=btype, analog=False, output='sos'
            )

    def _calculate_sos_coefficients(self, cutoff, btype='low'):
        """
        Wrapper um _build_sos mit Fehlerbehandlung für get_filter_coefficients.
        Args:
            cutoff: Normalisierte Grenzfrequenz(en)
            btype:  Filtertyp (low/high/band)
        Returns:
            numpy.array: SOS-Koeffizienten oder None bei Fehlern
        """
        try:
            return self._build_sos(cutoff, btype)
        except Exception as e:
            logger.exception(Cfg.Errors.FILTER_COEFFICIENT_CALC.format(str(e)))
            return None

    def _reset_coefficients(self):
        """Setzt alle Koeffizienten zurück."""
        self.b_coeffs   = None
        self.a_coeffs   = None
        self.sos_coeffs = None

    # --------------------------------------------------------
    #  FREQUENZGANG
    # --------------------------------------------------------

    def get_frequency_response(self, num_points=None):
        """
        Berechnet den Frequenzgang des Filters.
        Args:
            num_points: Anzahl Punkte für Frequenzgang (Standard: 1024)
        Returns:
            tuple: (frequencies, magnitude_db, phase_deg) oder (None, None, None) bei Fehlern
        """
        if num_points is None:
            num_points = Cfg.Limits.SOS_NUM_POINTS

        if (self.b_coeffs is None or
                self.a_coeffs is None or
                self.sample_rate is None):
            logger.warning(Cfg.Status.FILTER_NO_ACTIVE)
            return None, None, None

        try:
            logger.info(Cfg.Logs.FILTER_CALC_FREQ_RESPONSE.format(num_points))

            w, h = scipy_signal.freqz(
                self.b_coeffs, self.a_coeffs,
                worN=num_points, fs=self.sample_rate
            )

            magnitude_db = 20 * np.log10(np.abs(h) + 1e-10)
            phase_deg    = np.angle(h, deg=True)

            logger.info(Cfg.Status.FILTER_FREQ_RESPONSE_CALC)
            return w, magnitude_db, phase_deg

        except Exception as e:
            logger.exception(Cfg.Errors.FILTER_FREQUENCY_RESPONSE.format(str(e)))
            return None, None, None

    # --------------------------------------------------------
    #  INFO & RESET
    # --------------------------------------------------------

    def get_filter_info(self):
        """Gibt ein Dictionary mit allen Filter-Parametern zurück."""
        return {
            'type':           self.filter_type,
            'characteristic': self.characteristic,
            'order':          self.order,
            'sample_rate':    self.sample_rate,
            'cutoff':         self.cutoff_frequency,
            'cutoff2':        self.cutoff_frequency2,
            'b_coeffs':       self.b_coeffs,
            'a_coeffs':       self.a_coeffs,
            'sos_coeffs':     self.sos_coeffs,
        }

    def format_filter_info_text(self):
        """
        Generiert den formatierten Info-Text für Filter-Parameter.
        Returns:
            str: Formatierter Info-Text
        """
        info  = self.get_filter_info()
        prec  = Cfg.Limits.COEFFICIENT_PRECISION
        fprec = Cfg.Limits.FREQUENCY_PRECISION

        info_text = f"""FILTER-PARAMETER:
========================
Filtertyp: {info['type'] or Cfg.Defaults.FILTER_TYP}
Charakteristik: {info['characteristic'] or Cfg.Defaults.FILTER_CHARAKTERISTIK}
Ordnung: {info['order'] or Cfg.Defaults.FILTER_ORDER_INT}
Grenzfrequenz 1: {info['cutoff'] or 'Nicht gesetzt'} Hz
Grenzfrequenz 2: {info['cutoff2'] or 'Nicht gesetzt'} Hz
Samplerate: {info['sample_rate'] or 'Nicht gesetzt'} Hz
"""

        if info['b_coeffs'] is not None and info['a_coeffs'] is not None:
            info_text += f"""
TRANSFER FUNKTION (ba)
========================
WICHTIG: Diese ba-Koeffizienten dienen nur zur mathematischen
Beschreibung und können bei höheren Ordnungen numerische
Rundungsfehler aufweisen!

• b (Zähler):
{np.array2string(
    info['b_coeffs'],
    precision=prec, separator=', ', max_line_width=50,
    formatter={'float_kind': lambda x: f'{x:.{prec}e}'}
)}

• a (Nenner):
{np.array2string(
    info['a_coeffs'],
    precision=prec, separator=', ', max_line_width=50,
    formatter={'float_kind': lambda x: f'{x:.{prec}e}'}
)}
"""

        if info['sos_coeffs'] is not None:
            info_text += f"""
SECOND-ORDER SECTIONS (sos)
=============================
DIESE WERTE WERDEN FÜR DIE TATSÄCHLICHE FILTERUNG VERWENDET!

SOS Matrix ({info['sos_coeffs'].shape[0]} Sektionen):
{np.array2string(info['sos_coeffs'], precision=prec, separator=', ', max_line_width=50)}

ORDNUNGS-ZUSAMMENHANG BEI SOS:
=============================
Gewählte Sektionen/Ordnung: {info['order']}
Anzahl SOS-Sektionen: {info['sos_coeffs'].shape[0]}
Effektive Gesamtordnung: {info['sos_coeffs'].shape[0] * 2}
"""

        if info['sample_rate'] and info['cutoff'] and info['cutoff'] != "Nicht gesetzt":
            nyquist           = info['sample_rate'] / 2
            normalized_cutoff = info['cutoff'] / nyquist
            info_text += f"""
FREQUENZ-INFORMATIONEN:
========================
Nyquist-Frequenz: {nyquist:.{fprec}f} Hz
Normalisierte Grenzfrequenz: {normalized_cutoff:.4f}
Grenzfrequenz (physikalisch): {info['cutoff']:.{fprec}f} Hz
"""

        if (info['type'] == "Bandpass" and info['cutoff2'] and
                info['cutoff2'] != "Nicht gesetzt" and info['cutoff'] != "Nicht gesetzt"):
            try:
                bandwidth = float(info['cutoff2']) - float(info['cutoff'])
                info_text += f"""
BANDPASS-PARAMETER:
====================
Untere Grenzfrequenz: {info['cutoff']:.{fprec}f} Hz
Obere Grenzfrequenz: {info['cutoff2']:.{fprec}f} Hz
Bandbreite: {bandwidth:.{fprec}f} Hz
"""
            except Exception:
                logger.debug("Bandpass-Parameter konnten nicht formatiert werden")

        return info_text

    def reset_filter(self):
        """Setzt alle Filter-Parameter auf Standardwerte zurück."""
        self.filter_type       = Cfg.Defaults.FILTER_TYP
        self.characteristic    = Cfg.Defaults.FILTER_CHARAKTERISTIK
        self.order             = None
        self.sample_rate       = Cfg.Defaults.SAMPLE_RATE
        self.cutoff_frequency  = None
        self.cutoff_frequency2 = None
        self._reset_coefficients()
        self._warned_nan_inf        = False
        self._warned_cutoff         = False
        self._warned_cutoff2        = False
        self._warned_bandpass_range = False

        logger.info(Cfg.Logs.FILTER_RESET)