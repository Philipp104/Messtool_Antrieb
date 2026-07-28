"""
GUI-Hilfsfunktionen
====================
Allgemeine GUI-Helfer ohne Abhängigkeit auf GuiManager, damit auch
Module ohne GuiManager-Referenz (z.B. PlotManager mit seinen statischen
Methoden) sie nutzen können, ohne einen Import-Zyklus mit gui_manager.py
zu erzeugen.
"""


import os
import logging
import sys

logger = logging.getLogger(__name__)


def force_icon_refresh(window):
    """Zwingt Windows dazu, das Titelleisten-/Taskleisten-Icon eines bereits
    sichtbaren Fensters neu zu zeichnen (WM_SETICON + SWP_FRAMECHANGED).

    Nur ein Neuzeichnen-Anstoß für das aktuell auf Klassen-Ebene gesetzte
    Icon (z.B. nach iconbitmap()/iconphoto()) - lädt oder ändert selbst
    kein Icon. Kein Fehler, wenn nicht unter Windows oder wenn irgendwas
    schiefgeht - das Fenster bleibt dann einfach wie es ist.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.GetClassLongPtrW.restype = ctypes.c_void_p
        user32.GetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SendMessageW.restype = wintypes.LPARAM
        user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, wintypes.UINT,
        ]

        hwnd = window.winfo_id()
        GCL_HICON, GCL_HICONSM = -14, -34
        hicon_big   = user32.GetClassLongPtrW(hwnd, GCL_HICON)
        hicon_small = user32.GetClassLongPtrW(hwnd, GCL_HICONSM)

        WM_SETICON = 0x0080
        ICON_SMALL, ICON_BIG = 0, 1
        if hicon_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
        if hicon_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)

        SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, SWP_FRAMECHANGED = 0x0002, 0x0001, 0x0004, 0x0020
        user32.SetWindowPos(
            hwnd, None, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
        )
    except Exception as e:
        logger.debug("Icon-Refresh (WM_SETICON) fehlgeschlagen: %s", e)


# Segoe MDL2 Assets: seit Windows 10 vorinstallierte Icon-Schrift mit flachen,
# einfarbigen Glyphen (Symbol-Codepoints in der Private-Use-Area) - liefert
# "echte" Icons statt bunter, theme-fremder Emoji-Zeichen und braucht keine
# zusätzliche Abhängigkeit/Asset-Datei.
_ICON_FONT_PATH = r"C:\Windows\Fonts\segmdl2.ttf"
_icon_cache = {}


def get_icon_image(char, size=16, color="#000000"):
    """Rendert ein Segoe-MDL2-Assets-Icon-Zeichen zu einem gecachten
    Tk-PhotoImage (RGBA, transparenter Hintergrund) für image=/compound=
    an Label/Button-Widgets. Ergebnisse werden intern gecacht, d.h. der
    Aufrufer muss sich keine eigene Referenz halten.

    Gibt None zurück, wenn die Icon-Schrift nicht geladen werden kann
    (z.B. auf einem System ohne Windows) - Aufrufer sollten in dem Fall
    auf reinen Text zurückfallen.
    """
    key = (char, size, color)
    if key in _icon_cache:
        return _icon_cache[key]

    try:
        from PIL import Image, ImageDraw, ImageFont, ImageTk

        if not os.path.exists(_ICON_FONT_PATH):
            return None

        font   = ImageFont.truetype(_ICON_FONT_PATH, size)
        canvas = size + 8
        img    = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
        draw   = ImageDraw.Draw(img)

        bbox = draw.textbbox((0, 0), char, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x    = (canvas - w) / 2 - bbox[0]
        y    = (canvas - h) / 2 - bbox[1]
        draw.text((x, y), char, font=font, fill=color)

        photo = ImageTk.PhotoImage(img)
    except Exception as e:
        logger.debug("Icon '%s' konnte nicht gerendert werden: %s", char, e)
        return None

    _icon_cache[key] = photo
    return photo


def center_window(window, width=None, height=None):
    """Zentriert ein Toplevel-Fenster auf dem Bildschirm.

    Ohne width/height wird die natürliche Größe aus den bereits gepackten
    Widgets ermittelt (window.update_idletasks() + winfo_reqwidth/height).
    Mit width/height wird stattdessen diese feste Größe zentriert, z.B.
    wenn das Fenster bewusst eine fixe geometry() haben soll.
    """
    window.update_idletasks()
    if width is None:
        width = window.winfo_reqwidth()
    if height is None:
        height = window.winfo_reqheight()
    x = (window.winfo_screenwidth() - width) // 2
    y = (window.winfo_screenheight() - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")
