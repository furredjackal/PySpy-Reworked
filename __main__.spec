# -*- mode: python ; coding: utf-8 -*-
'''PyInstaller spec for PySpy [Reworked]. Builds a single-file,
windowed executable with the icon and version resources bundled.'''
# cSpell Checker - Correct Words****************************************
# // cSpell:words pyinstaller, pyspy, posix, icns, datas, noconfirm
# **********************************************************************
import os

if os.name == "nt":
    ICON_FILE = os.path.join("assets", "pyspy.ico")
else:
    ICON_FILE = os.path.join("assets", "pyspy.png")

MAC_ICON = os.path.join("assets", "pyspy.icns")
ABOUT_ICON = os.path.join("assets", "pyspy_mid.png")

a = Analysis(
    ["__main__.py"],
    pathex=[],
    binaries=[],
    datas=[
        (ICON_FILE, "."),
        (ABOUT_ICON, "."),
        ("VERSION", "."),
        ("LICENSE.txt", "."),
        ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    )

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="PySpy",
    icon=ICON_FILE,
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    )

app = BUNDLE(
    exe,
    name="PySpy.app",
    icon=MAC_ICON,
    bundle_identifier=None,
    )
