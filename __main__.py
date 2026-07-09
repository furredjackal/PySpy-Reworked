# !/usr/local/bin/python3.6
# MIT licensed
# Copyright (c) 2018 White Russsian
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
''' This is the primary module responsible for launching a background
thread that watches for changes in the clipboard and if it detects a
list of strings that could be EVE Online character strings, sends them
to the analyze.py module to gather specific information from CCP's ESI
API and zKIllboard's API. This information then gets sent to the GUI for
output.
'''
# **********************************************************************
import logging
import os
import re
import threading
import time

# Crisp rendering on high-DPI displays (must run before wx starts)
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

import wx
import pyperclip

import analyze
import chatwatch
import chkversion
import config
import gui
import killfeed
import reportstats
import statusmsg
import db
# cSpell Checker - Correct Words****************************************
# // cSpell:words russsian, ccp's, pyperclip, chkversion, clpbd, gui
# **********************************************************************
Logger = logging.getLogger(__name__)
# Example call: Logger.info("Something badhappened", exc_info=True) ****


def watch_clpbd():
    valid = False
    recent_value = None
    while True:
        clipboard = pyperclip.paste()
        if clipboard != recent_value:
            char_names = clipboard.splitlines()
            for name in char_names:
                valid = check_name_validity(name)
                if valid is False:
                    break
            if valid:
                statusmsg.push_status("Clipboard change detected...")
                recent_value = clipboard
                analyze_chars(clipboard.splitlines())
        time.sleep(0.5)  # Short sleep between loops to reduce CPU load


def check_name_validity(char_name):
    if len(char_name) < 3:
        return False
    regex = r"[^ 'a-zA-Z0-9-]"  # Valid EVE Online character names
    if re.search(regex, char_name):
        return False
    return True


# Serializes scans regardless of origin (clipboard, intel channels)
scan_lock = threading.Lock()


def safe_call_after(*args, **kwargs):
    '''
    wx.CallAfter that tolerates the GUI going away - background threads
    (clipboard, chat logs, kill feed) must never crash on shutdown.
    '''
    try:
        if wx.GetApp() is not None:
            wx.CallAfter(*args, **kwargs)
    except Exception:
        pass


def analyze_chars(char_names, quiet=False):
    with scan_lock:
        conn_mem, cur_mem = db.connect_memory_db()
        conn_dsk, cur_dsk = db.connect_persistent_db()
        start_time = time.time()
        try:
            outlist = analyze.main(char_names, conn_mem, cur_mem, conn_dsk, cur_dsk)
            duration = round(time.time() - start_time, 1)
            if outlist is not None:
                # Need to use keyword args as sortOutlist can also get called
                # by event handler which would pass event object as first argument.
                safe_call_after(
                    app.PySpy.sortOutlist,
                    outlist=outlist,
                    duration=duration
                    )
            elif not quiet:
                # Suppressed for automatic scans, where chat messages
                # without pilot names are perfectly normal.
                statusmsg.push_status(
                    "No valid character names found. Please try again..."
                    )
        except Exception:
            Logger.error(
                "Failed to collect character information. Scanned "
                "names were: " + str(char_names), exc_info=True
            )


def intel_scan(char_names):
    '''Called by the chat log watcher for names seen in intel channels.'''
    analyze_chars(char_names, quiet=True)


def kill_alert(msg):
    '''Called by the kill feed when an alert-worthy kill is seen.'''
    statusmsg.push_status(msg)
    safe_call_after(wx.Bell)


def location_update(system_name):
    '''Called by the chat log watcher when the player changes system.'''
    safe_call_after(app.PySpy.updateLocation, system_name)


app = gui.App(0)  # Has to be defined before background thread starts.

background_thread = threading.Thread(
    target=watch_clpbd,
    daemon=True
    )
background_thread.start()

update_checker = threading.Thread(
    target=chkversion.chk_github_update,
    daemon=True
    )
update_checker.start()

# Chat log watcher (intel channels + location) and live kill feed.
# Both threads idle unless enabled in the Options menu.
chat_watcher = chatwatch.ChatWatcher(
    analyze_callback=intel_scan,
    location_callback=location_update
    )
chat_watcher.start()

kill_feed = killfeed.KillFeed(alert_callback=kill_alert)
kill_feed.start()

app.MainLoop()

# Hard exit: daemon threads (clipboard, chat logs, kill feed) must not
# touch wx objects while the interpreter tears down, which segfaults.
os._exit(0)
