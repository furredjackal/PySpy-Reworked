# MIT licensed
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
''' Live killmail feed alerts, using zKillboard's R2Z2 ephemeral
killmail stream (https://github.com/zKillboard/zKillboard/wiki/API-(R2Z2),
the replacement for RedisQ, which was sunsetted in May 2026). A
background thread iterates the strictly-increasing killmail sequence
and raises an alert when:

* a kill happens in the player's current solar system (as tracked by
  chatwatch.py from the EVE Local chat log), or
* a pilot, corporation or alliance on PySpy's highlight list is
  involved in a kill anywhere in New Eden, as victim or attacker.

Alerts are pushed to the status bar and sound the system bell. The
thread idles when the "KillFeed" option is off.
'''
# **********************************************************************
import json
import logging
import threading
import time

import requests

import apis
import chatwatch
import config
# **********************************************************************
Logger = logging.getLogger(__name__)

R2Z2_BASE = "https://r2z2.zkillboard.com/ephemeral/"
CAUGHT_UP_SLEEP = 6  # Documented minimum wait after a 404 (no new kills)
KILL_SLEEP = 0.15  # Pause between sequence fetches (limit is 15 req/s)
RESYNC_AFTER_MISSES = 5  # Consecutive 404s before re-reading sequence.json

HEADERS = {
    "Accept-Encoding": "gzip",
    "User-Agent": "PySpy, https://github.com/Eve-PySpy/PySpy"
    }


class KillFeed(threading.Thread):
    '''
    Background thread iterating zKillboard's R2Z2 killmail stream.

    :param `alert_callback`: Called with a message string whenever an
    alert-worthy kill is seen.
    '''

    def __init__(self, alert_callback):
        super(KillFeed, self).__init__()
        self.daemon = True
        self._alert = alert_callback
        self._sequence = None
        self._misses = 0

    def run(self):
        while True:
            try:
                if not config.OPTIONS_OBJECT.Get("KillFeed", False):
                    time.sleep(5)
                    continue
                self._listen()
            except Exception:
                Logger.error("Kill feed error.", exc_info=True)
                time.sleep(10)

    def _get(self, url):
        return requests.get(url, headers=HEADERS, timeout=20)

    def _resync(self):
        '''
        Reads the current sequence number from sequence.json. Also used
        to catch up when our sequence has expired from the ephemeral
        bucket (e.g. after the feed was disabled for a while).
        '''
        r = self._get(R2Z2_BASE + "sequence.json")
        if r.status_code != 200:
            Logger.info("R2Z2 sequence.json returned " + str(r.status_code))
            return None
        return r.json().get("sequence")

    def _listen(self):
        try:
            if self._sequence is None:
                self._sequence = self._resync()
                if self._sequence is None:
                    time.sleep(10)
                    return
                Logger.info("Kill feed started at sequence " + str(self._sequence))
            r = self._get(R2Z2_BASE + str(self._sequence) + ".json")
        except requests.exceptions.RequestException:
            Logger.info("Kill feed connection problem.", exc_info=True)
            time.sleep(10)
            return
        if r.status_code == 200:
            self._misses = 0
            try:
                self._process(r.json())
            except ValueError:
                pass
            self._sequence += 1
            time.sleep(KILL_SLEEP)
        elif r.status_code == 404:
            # Caught up with the feed - wait politely as documented
            self._misses += 1
            if self._misses >= RESYNC_AFTER_MISSES:
                # Guard against our sequence having expired from the bucket
                self._misses = 0
                latest = self._resync()
                if latest is not None and latest > self._sequence:
                    self._sequence = latest
            time.sleep(CAUGHT_UP_SLEEP)
        elif r.status_code == 403:
            Logger.warning(
                "R2Z2 returned 403 (rate limited or blocked). Backing off."
                )
            time.sleep(60)
        else:
            time.sleep(10)

    def _process(self, package):
        killmail = package.get("esi")
        if not killmail:
            return
        system_id = killmail.get("solar_system_id")
        victim = killmail.get("victim", {})
        attackers = killmail.get("attackers", [])

        # Kill in the player's current system?
        location_name, location_id = chatwatch.get_location()
        if location_id is not None and system_id == location_id:
            self._alert_local_kill(killmail, victim, attackers, location_name)
            return

        # Anyone from the highlight list involved?
        watch = self._watchlist()
        if not watch:
            return
        involved = set()
        for party in [victim] + attackers:
            for key in ("character_id", "corporation_id", "alliance_id"):
                if party.get(key):
                    involved.add(party[key])
        matches = watch.keys() & involved
        if matches:
            self._alert_watchlist_kill(killmail, victim, matches, watch)

    def _watchlist(self):
        '''
        :return: Dictionary mapping the ids of all highlighted entities
        (characters, corporations, alliances) to their names.
        '''
        entities = config.OPTIONS_OBJECT.Get("highlightedList", [])
        watch = {}
        for entry in entities:
            try:
                watch[int(entry[0])] = str(entry[1])
            except (ValueError, TypeError, IndexError):
                continue
        return watch

    def _alert_local_kill(self, killmail, victim, attackers, system_name):
        names = self._resolve_names(
            [victim.get("character_id"), victim.get("ship_type_id")]
            )
        victim_name = names.get(victim.get("character_id"), "Unknown")
        ship_name = names.get(victim.get("ship_type_id"), "ship")
        msg = (
            "KILL IN " + str(system_name).upper() + ": " + victim_name +
            " (" + ship_name + ") killed by " + str(len(attackers)) +
            " attacker(s). https://zkillboard.com/kill/" +
            str(killmail.get("killmail_id", "")) + "/"
            )
        Logger.info(msg)
        self._alert(msg)

    def _alert_watchlist_kill(self, killmail, victim, matches, watch):
        matched_names = ", ".join(sorted(watch[i] for i in matches))
        victim_ids = {
            victim.get("character_id"), victim.get("corporation_id"),
            victim.get("alliance_id")
            }
        role = "died" if matches & victim_ids else "got a kill"
        names = self._resolve_names([killmail.get("solar_system_id")])
        system_name = names.get(killmail.get("solar_system_id"), "?")
        msg = (
            "WATCHLIST: " + matched_names + " " + role + " in " +
            system_name + ". https://zkillboard.com/kill/" +
            str(killmail.get("killmail_id", "")) + "/"
            )
        Logger.info(msg)
        self._alert(msg)

    def _resolve_names(self, ids):
        '''
        Resolves a list of EVE ids to names via ESI. Only called when
        an alert actually fires. Returns {} on failure.

        :return: Dictionary mapping each resolvable id to its name.
        '''
        ids = [i for i in ids if i]
        if not ids:
            return {}
        try:
            r = apis.post_req_ccp("universe/names/", json.dumps(ids))
            return {e["id"]: e["name"] for e in r}
        except Exception:
            Logger.info("Could not resolve names for kill alert.", exc_info=True)
            return {}
