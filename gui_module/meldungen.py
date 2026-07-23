"""
Meldungen nicht-blockierende Popup-Benachrichtigungen
============================================================
Bietet showinfo/showwarning/showerror mit derselben Signatur wie
tkinter.messagebox, zeigt die Meldung aber als nicht-blockierendes Toast
(verschwindet automatisch nach kurzer Zeit, per Klick auch sofort schließbar)
statt als Dialog, der erst mit "OK" bestätigt werden muss.

Bestätigungsdialoge (askyesno, askokcancel, ...) bleiben bewusst blockierend
und werden unverändert vom echten tkinter.messagebox durchgereicht, da hier
eine echte Entscheidung des Nutzers abgewartet werden muss.

Verwendung: Importiere dieses Modul anstelle von tkinter.messagebox
(z.B. `from gui_module import meldungen as messagebox`) - bestehender Code,
der messagebox.showinfo/showwarning/showerror/askyesno aufruft, funktioniert
unverändert weiter.
"""
import logging
import tkinter as _tk
from tkinter import messagebox as _tk_messagebox
from ttkbootstrap.toast import ToastNotification

logger = logging.getLogger(__name__)

MELDUNG_DAUER_MS = 7000
MARGIN_X         = 20
MARGIN_Y         = 40
STACK_ABSTAND    = 10

_BOOTSTYLE = {
    "info":    "info",
    "warning": "warning",
    "error":   "danger",
}

# Aktuell sichtbare Meldungen je Anker-Fenster, damit mehrere gleichzeitige
# Meldungen untereinander gestapelt statt übereinander angezeigt werden.
_aktive_meldungen = {}


def _resolve_anker(parent):
    """Liefert das Fenster, an dem die Meldung ausgerichtet wird
    (Fallback: Hauptfenster der Anwendung, falls kein parent übergeben wurde)."""
    return parent if parent is not None else _tk._default_root


def _basis_position(anker):
    """Position oben rechts über dem Anker-Fenster (ohne Stapel-Versatz).

    ttkbootstrap erwartet bei Anchor "ne" den X-Wert als Abstand vom RECHTEN
    Bildschirmrand (nicht als absolute Koordinate) und den Y-Wert als Abstand
    vom OBEREN Bildschirmrand.
    """
    if anker is None:
        return None
    try:
        screen_w       = anker.winfo_screenwidth()
        fenster_rechts = anker.winfo_rootx() + anker.winfo_width()
        x_von_rechts   = max(screen_w - fenster_rechts + MARGIN_X, 0)
        y_von_oben     = anker.winfo_rooty() + MARGIN_Y
        return (x_von_rechts, y_von_oben, "ne")
    except Exception:
        return None


def _stack_versatz(key):
    """Summierte Höhe der aktuell sichtbaren Meldungen an diesem Anker."""
    versatz = 0
    for toplevel in _aktive_meldungen.get(key, []):
        try:
            versatz += toplevel.winfo_height() + STACK_ABSTAND
        except Exception as e:
            logger.debug("Höhe einer Meldung im Stapel konnte nicht ermittelt werden: %s", e)
    return versatz


def _stack_registrieren(key, toplevel):
    _aktive_meldungen.setdefault(key, []).append(toplevel)

    def _entfernen(_event, key=key, toplevel=toplevel):
        stack = _aktive_meldungen.get(key)
        if stack and toplevel in stack:
            stack.remove(toplevel)

    toplevel.bind("<Destroy>", _entfernen)


def _show(kind, title, message, parent=None):
    anker = _resolve_anker(parent)
    basis = _basis_position(anker)

    position = None
    if basis is not None:
        x, y, anchor = basis
        position = (x, y + _stack_versatz(id(anker)), anchor)

    meldung = ToastNotification(
        title=title,
        message=message,
        duration=MELDUNG_DAUER_MS,
        bootstyle=_BOOTSTYLE[kind],
        position=position,
        topmost=True,
    )
    meldung.show_toast()
    _stack_registrieren(id(anker), meldung.toplevel)


def showinfo(title, message, parent=None, **kwargs):
    _show("info", title, message, parent)


def showwarning(title, message, parent=None, **kwargs):
    _show("warning", title, message, parent)


def showerror(title, message, parent=None, **kwargs):
    _show("error", title, message, parent)


# Bestätigungsdialoge bleiben echte, blockierende tkinter-Dialoge.
askyesno       = _tk_messagebox.askyesno
askokcancel    = _tk_messagebox.askokcancel
askretrycancel = _tk_messagebox.askretrycancel
askquestion    = _tk_messagebox.askquestion
