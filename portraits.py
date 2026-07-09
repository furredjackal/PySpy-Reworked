# MIT licensed
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
''' Downloads and caches EVE Online character portraits from CCP's
image server for display in the results grid. Portraits are cached on
disk indefinitely (they rarely change) and in memory as wx.Bitmap
objects for fast cell rendering.
'''
# **********************************************************************
import logging
import os
import threading

import requests
import wx

import config
# **********************************************************************
Logger = logging.getLogger(__name__)

SIZE = 32  # Requested portrait size (EVE image server: 32/64/128...)
URL = "https://images.evetech.net/characters/{}/portrait?size=" + str(SIZE)
CACHE_DIR = os.path.join(config.PREF_PATH, "portraits")

_bitmaps = {}  # char_id -> wx.Bitmap (display size)
_lock = threading.Lock()
_display_size = 24  # Bitmap edge length in px, set via set_display_size()


def set_display_size(pixels):
    '''Sets the edge length used for grid bitmaps (based on row height).'''
    global _display_size
    _display_size = max(16, int(pixels))


def get(char_id):
    '''
    :return: Cached wx.Bitmap for the character, or None if the
    portrait has not been loaded (yet).
    '''
    with _lock:
        return _bitmaps.get(char_id)


def prefetch(char_ids, done_callback=None):
    '''
    Ensures portraits for the given character ids are downloaded and
    loaded into the bitmap cache, in a background thread.

    :param `char_ids`: Iterable of character ids as integers.
    :param `done_callback`: Called via wx.CallAfter once any new
    portraits have been loaded (e.g. to refresh the grid).
    '''
    with _lock:
        missing = [c for c in set(char_ids) if c and c not in _bitmaps]
    if not missing:
        return
    t = threading.Thread(
        target=_fetch_files, args=(missing, done_callback), daemon=True
        )
    t.start()


def _fetch_files(char_ids, done_callback):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except OSError:
        return
    fetched = []
    for char_id in char_ids:
        path = os.path.join(CACHE_DIR, str(char_id) + ".jpg")
        if not os.path.isfile(path):
            try:
                r = requests.get(URL.format(char_id), timeout=10)
                if r.status_code != 200:
                    continue
                with open(path, "wb") as f:
                    f.write(r.content)
            except (requests.exceptions.RequestException, OSError):
                continue
        fetched.append((char_id, path))
    if fetched:
        # Create wx objects on the GUI thread
        wx.CallAfter(_load_bitmaps, fetched, done_callback)


def _load_bitmaps(fetched, done_callback):
    for char_id, path in fetched:
        try:
            image = wx.Image(path, wx.BITMAP_TYPE_ANY)
            if not image.IsOk():
                continue
            image = image.Scale(
                _display_size, _display_size, wx.IMAGE_QUALITY_HIGH
                )
            with _lock:
                _bitmaps[char_id] = wx.Bitmap(image)
        except Exception:
            Logger.info(
                "Could not load portrait for " + str(char_id), exc_info=True
                )
    if done_callback is not None:
        done_callback()
