# !/usr/local/bin/python3.6
# MIT licensed
# Copyright (c) 2018 White Russsian
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
'''The About Dialog for PySpy's GUI. OnAboutBox() gets called by the GUI
module.'''
# **********************************************************************
import logging
import time

import wx
import wx.adv

import __main__
import config
# cSpell Checker - Correct Words****************************************
# // cSpell:words russsian, wxpython, ccp's
# // cSpell:words
# **********************************************************************
Logger = logging.getLogger(__name__)
# Example call: Logger.info("Something badhappened", exc_info=True) ****


def showAboutBox(parent, event=None):
    # __main__.app.PySpy.ToggleWindowStyle(wx.STAY_ON_TOP)

    description = """
    PySpy [Reworked] is an EVE Online character intel tool
    using CCP's ESI API, zKillboard's API and full-history
    killboard statistics served by the community-run
    PySpy-backend (with automatic local fallback).

    This edition revives the original, no longer maintained
    PySpy and expands it with asynchronous scanning, threat
    ratings, fleet rollups, chat log intel, location tracking
    and live killmail alerts.

    Standing on the shoulders of:

    White Russsian - author of the original PySpy (2018).
    If you enjoy PySpy, ISK donations in-game to
    White Russsian (with 3 "s") honour the original work.

    jhmartin (Justin Martin) - resurrected the project and
    rebuilt & hosts the killboard statistics backend from
    the complete killmail archive since 2007.
    https://github.com/jhmartin/PySpy-backend

    furredjackal - the [Reworked] edition: repairs,
    modernisation and the expanded capabilities above."""

    try:
        with open(config.resource_path('LICENSE.txt'), 'r') as lic_file:
            license = lic_file.read()
    except:
        license = "PySpy is licensed under the MIT License."

    info = wx.adv.AboutDialogInfo()

    info.SetIcon(wx.Icon(config.ABOUT_ICON, wx.BITMAP_TYPE_PNG))
    info.SetName("PySpy [Reworked]")
    info.SetVersion(config.CURRENT_VER)
    info.SetDescription(description)
    info.SetCopyright(
        '(C) 2018 White Russsian (original) - '
        '(C) 2026 furredjackal (Reworked edition)'
        )
    info.SetWebSite('https://github.com/Eve-PySpy/PySpy')
    info.AddDeveloper('White Russsian - original PySpy')
    info.AddDeveloper('jhmartin - resurrected fork & community stats backend')
    info.AddDeveloper('furredjackal - [Reworked] edition & expanded capabilities')
    info.SetLicence(license)

    wx.adv.AboutBox(info)
