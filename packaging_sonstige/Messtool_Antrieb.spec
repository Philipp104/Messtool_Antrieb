# -*- mode: python ; coding: utf-8 -*-
# Liegt in packaging_sonstige/, während main.py und projektbeschreibung_bilder im
# Projekt-Root liegen - SPECPATH (von PyInstaller automatisch bereitgestellt: Ordner
# dieser .spec-Datei) macht die Pfade unabhängig vom Ordner, aus dem pyinstaller
# aufgerufen wird.
import os
from PyInstaller.utils.hooks import collect_all

PROJECT_ROOT = os.path.join(SPECPATH, "..")

datas = [(os.path.join(PROJECT_ROOT, "projektbeschreibung_bilder"), "projektbeschreibung_bilder")]
binaries = []
hiddenimports = ['reportlab.graphics.barcode.code128', 'reportlab.graphics.barcode.code39', 'reportlab.graphics.barcode.code93', 'reportlab.graphics.barcode.eanbc', 'reportlab.graphics.barcode.qr', 'reportlab.graphics.barcode.usps', 'reportlab.graphics.barcode.usps4s', 'reportlab.graphics.barcode.dmtx', 'xhtml2pdf']
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    [os.path.join(PROJECT_ROOT, "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Messtool_Antrieb',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SPECPATH, "Giraffe.ico"),
    version=os.path.join(SPECPATH, "version_info.txt"),
)
