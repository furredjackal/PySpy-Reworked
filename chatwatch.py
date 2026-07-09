# MIT licensed
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
''' Watches EVE Online's chat log files for two purposes:

* Location tracking: the Local channel log records a system-change
  message every time the player jumps, letting PySpy always know what
  system the player is in (used for kill feed proximity alerts and
  shown in the window title).
* Intel channels: any channel named in the "IntelChannels" option is
  monitored and pilot names mentioned in new messages are automatically
  run through PySpy's analysis pipeline - no copy & paste required.

This only reads the log files EVE itself writes to disk when
"Log Chat to File" is enabled in the EVE client settings (fully
EULA-compliant, same approach as tools like Spyglass/Vintel). Log
files are UTF-16 LE encoded and named `<Channel>_<date>_<time>.txt`.
'''
# **********************************************************************
import json
import logging
import os
import re
import threading
import time

import apis
import config
import statusmsg
# **********************************************************************
Logger = logging.getLogger(__name__)

POLL_INTERVAL = 2  # Seconds between chat log polls
MESSAGE_DEDUPE_SECS = 300  # Ignore identical intel messages for this long
SPEAKER_DEDUPE_SECS = 600  # Re-scan a Local speaker at most this often
MAX_CANDIDATES = 60  # Max pilot name candidates extracted per message

# "[ 2026.07.08 17:55:12 ] Author Name > message text"
LINE_RE = re.compile(r"^\[ [\d\.]+ [\d:]+ \] (.*?) > (.*)$")
# "<Channel>_<YYYYMMDD>_<HHMMSS>_<listenerCharID>.txt" - the character
# id suffix was added by newer EVE clients and is optional here to
# also support older log files. Channel names may contain underscores.
FILENAME_RE = re.compile(r"^(.+)_(\d{8})_(\d{6})(?:_(\d+))?\.txt$")
LOCAL_CHANGE_RE = re.compile(r"Channel changed to Local\s*:\s*(.+?)\s*$")
NAME_CHAR_RE = re.compile(r"[^ 'a-zA-Z0-9-]")

# Common intel channel jargon that is never a pilot name. Lower case.
INTEL_STOPWORDS = frozenset((
    "clr", "clear", "clr?", "status", "stat", "red", "reds", "neut",
    "neuts", "hostile", "hostiles", "blue", "blues", "gate", "station",
    "dock", "docked", "spike", "spiked", "local", "jumped", "jump",
    "in", "on", "at", "to", "from", "with", "and", "or", "the", "a",
    "is", "are", "was", "gone", "left", "camp", "camped", "bubble",
    "cyno", "covert", "blops", "caps", "capital", "super", "titan",
    "fleet", "gang", "solo", "afk", "pod", "podded", "safe", "nv",
    "no", "yes", "visual", "eyes", "wh", "hole", "anyone", "anybody"
    ))

# Current player location, shared with killfeed.py
_location_lock = threading.Lock()
_location = {"name": None, "id": None}


def get_location():
    '''
    :return: Tuple (system_name, system_id) of the player's current
    system, each None if unknown.
    '''
    with _location_lock:
        return _location["name"], _location["id"]


def find_chatlog_dir():
    '''
    Returns the EVE chat log directory, honouring the "ChatlogDir"
    option and falling back to the usual Documents locations
    (including OneDrive-redirected Documents). None if not found.
    '''
    candidates = []
    custom = config.OPTIONS_OBJECT.Get("ChatlogDir", "")
    if custom:
        candidates.append(custom)
    home = os.path.expanduser("~")
    candidates.append(os.path.join(home, "Documents", "EVE", "logs", "Chatlogs"))
    candidates.append(os.path.join(home, "OneDrive", "Documents", "EVE", "logs", "Chatlogs"))
    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


class ChatWatcher(threading.Thread):
    '''
    Background thread polling the newest log file of each watched
    channel for new lines. Idles when the "ChatWatch" option is off.

    :param `analyze_callback`: Called with a list of potential pilot
    names extracted from intel channel messages.
    :param `location_callback`: Called with the system name whenever
    the player's location changes.
    '''

    def __init__(self, analyze_callback, location_callback=None):
        super(ChatWatcher, self).__init__()
        self.daemon = True
        self._analyze = analyze_callback
        self._location_cb = location_callback
        self._offsets = {}  # file path -> byte offset already read
        self._recent_msgs = {}  # message text -> timestamp (dedupe)
        self._recent_speakers = {}  # Local speaker name -> timestamp (dedupe)
        self._warned_no_dir = False

    def run(self):
        while True:
            try:
                if config.OPTIONS_OBJECT.Get("ChatWatch", False):
                    self._poll()
            except Exception:
                Logger.error("Chat log watcher error.", exc_info=True)
            time.sleep(POLL_INTERVAL)

    def _poll(self):
        logdir = find_chatlog_dir()
        if logdir is None:
            if not self._warned_no_dir:
                self._warned_no_dir = True
                Logger.warning("No EVE chat log directory found.")
                statusmsg.push_status(
                    "Chat log watch: no EVE chat logs found. Enable "
                    '"Log Chat to File" in the EVE client settings.'
                    )
            return

        intel_channels = [
            c.strip().lower() for c in
            config.OPTIONS_OBJECT.Get("IntelChannels", "").split(",")
            if c.strip()
            ]
        watched = set(intel_channels) | {"local"}

        for channel, path in self._newest_files(logdir, watched).items():
            first_seen = path not in self._offsets
            lines = self._read_new_lines(path, channel, first_seen)
            for line in lines:
                self._process_line(channel, line)

    def _newest_files(self, logdir, watched):
        '''
        Maps each watched channel name (lower case) to its most recent
        log file. EVE starts a new file per session, named
        `<Channel>_<YYYYMMDD>_<HHMMSS>.txt`, so the lexically greatest
        file name is the newest.
        '''
        newest = {}
        try:
            filenames = os.listdir(logdir)
        except OSError:
            return {}
        for fname in filenames:
            m = FILENAME_RE.match(fname)
            if m is None:
                continue
            channel = m.group(1).lower()
            if channel not in watched:
                continue
            # Sort key: session date + time, so the newest session wins
            sort_key = m.group(2) + m.group(3)
            if channel not in newest or sort_key > newest[channel][0]:
                newest[channel] = (sort_key, os.path.join(logdir, fname))
        return {chan: entry[1] for chan, entry in newest.items()}

    def _read_new_lines(self, path, channel, first_seen):
        '''
        Returns decoded new lines of `path` since the last poll. On
        first sight of a file the backlog is skipped (except for the
        Local channel, whose backlog is scanned once for the most
        recent system-change line so the location is known
        immediately).
        '''
        try:
            size = os.path.getsize(path)
        except OSError:
            return []
        if first_seen:
            if channel == "local":
                self._scan_local_backlog(path)
            self._offsets[path] = size
            return []
        offset = self._offsets.get(path, 0)
        if size <= offset:
            return []
        try:
            with open(path, "rb") as f:
                f.seek(offset)
                data = f.read()
        except OSError:
            return []
        self._offsets[path] = offset + len(data)
        text = data.decode("utf-16-le", errors="ignore")
        return [l.strip("\r﻿ ") for l in text.split("\n") if l.strip()]

    def _scan_local_backlog(self, path):
        '''
        Reads an entire Local log file once and applies the last
        system-change line found, so PySpy knows the player's location
        without waiting for the next jump.
        '''
        try:
            with open(path, "rb") as f:
                text = f.read().decode("utf-16-le", errors="ignore")
        except OSError:
            return
        last_system = None
        for line in text.split("\n"):
            m = LOCAL_CHANGE_RE.search(line)
            if m:
                last_system = m.group(1)
        if last_system:
            self._set_location(last_system)

    def _process_line(self, channel, line):
        m = LINE_RE.match(line)
        if m is None:
            return
        author, text = m.group(1), m.group(2)
        if author == "EVE System":
            if channel == "local":
                m = LOCAL_CHANGE_RE.search(text)
                if m:
                    self._set_location(m.group(1))
            return
        if channel == "local":
            # Anyone speaking in Local is a confirmed pilot in system -
            # their author name is exact, so scan them directly. (The
            # silent member list is not written to the chat logs.)
            now = time.time()
            self._recent_speakers = {
                name: ts for name, ts in self._recent_speakers.items()
                if now - ts < SPEAKER_DEDUPE_SECS
                }
            if author in self._recent_speakers:
                return
            self._recent_speakers[author] = now
            Logger.info("Pilot spotted talking in Local: " + author)
            statusmsg.push_status(
                "Pilot talking in Local: " + author + ", analysing..."
                )
            self._analyze([author])
            return
        # Intel channel message: extract and analyze potential names
        now = time.time()
        self._recent_msgs = {
            msg: ts for msg, ts in self._recent_msgs.items()
            if now - ts < MESSAGE_DEDUPE_SECS
            }
        if text in self._recent_msgs:
            return
        self._recent_msgs[text] = now
        candidates = extract_name_candidates(text)
        if candidates:
            Logger.info(
                "Intel report in '" + channel + "' by " + author + ": " + text
                )
            statusmsg.push_status(
                "Intel report in '" + channel + "', analysing..."
                )
            self._analyze(candidates)

    def _set_location(self, system_name):
        with _location_lock:
            if _location["name"] == system_name:
                return
            _location["name"] = system_name
            _location["id"] = None
        Logger.info("Location changed to " + system_name)
        # Resolve the system id for kill feed proximity matching
        try:
            r = apis.post_req_ccp("universe/ids/", json.dumps([system_name]))
            system_id = r["systems"][0]["id"]
            with _location_lock:
                _location["id"] = system_id
        except Exception:
            Logger.info(
                "Could not resolve system id for " + system_name, exc_info=True
                )
        if self._location_cb is not None:
            self._location_cb(system_name)


def extract_name_candidates(text):
    '''
    Extracts potential pilot names from an intel message. Generates
    1-3 word combinations of consecutive words, filtered for EVE
    character name validity and common intel jargon. Junk candidates
    are harmless: ESI's name-to-id resolution only matches exact
    character names, so anything else simply drops out.

    :param `text`: Chat message text.
    :return: List of candidate name strings.
    '''
    candidates = []
    # Split into segments on characters never part of a name, so
    # n-grams do not span commas, links etc.
    segments = re.split(r"[^ 'a-zA-Z0-9-]", text)
    for segment in segments:
        words = [w for w in segment.split() if w]
        for size in (1, 2, 3):
            for i in range(len(words) - size + 1):
                candidate = " ".join(words[i:i + size])
                if len(candidate) < 3 or len(candidate) > 37:
                    continue
                if NAME_CHAR_RE.search(candidate):
                    continue
                if size == 1 and candidate.lower() in INTEL_STOPWORDS:
                    continue
                if candidate not in candidates:
                    candidates.append(candidate)
                if len(candidates) >= MAX_CANDIDATES:
                    return candidates
    return candidates
