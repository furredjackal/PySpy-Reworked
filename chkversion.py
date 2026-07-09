# !/usr/local/bin/python3.6
# MIT licensed
# Copyright (c) 2018 White Russsian
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
''' Checks if there is a later version of PySpy available on GitHub.'''
# **********************************************************************
import logging.config
import logging
import os
import sys
import datetime

import requests
import wx

import __main__
import config
# cSpell Checker - Correct Words****************************************
# // cSpell:words russsian
# **********************************************************************
Logger = logging.getLogger(__name__)
# Example call: Logger.info("Something badhappened", exc_info=True) ****
CURRENT_VER = config.CURRENT_VER


def chk_github_update():
    last_check = config.OPTIONS_OBJECT.Get("last_update_check", 0)
    if last_check == 0 or last_check < datetime.date.today():
        # Get latest version available on GitHub
        GIT_URL = "https://api.github.com/repos/Eve-PySpy/PySpy/releases/latest"
        try:
            latest_ver = requests.get(GIT_URL, timeout=10).json()["tag_name"]
            Logger.info(
                "You are running PySpy [Reworked] " + CURRENT_VER + ". The " +
                "original (unmaintained) project's latest release on GitHub "
                "is " + latest_ver + "."
                )
            config.OPTIONS_OBJECT.Set("last_update_check", datetime.date.today())
            # Update alert disabled: this reworked fork is ahead of the
            # unmaintained upstream project, so alerting on a version
            # mismatch would wrongly suggest "updating" to older code.
        except:
            Logger.info("Could not check GitHub for potential available updates.")


