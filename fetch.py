# MIT licensed
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
''' Asynchronous zKillboard fetch layer. For each character this module
concurrently retrieves three resources and condenses them into one flat
record per character:

* `stats` - lifetime and recent killboard statistics, including the
  danger and gang ratios, the most flown ship of the last 90 days and
  an hourly activity histogram used to estimate a pilot's prime time.
* killmail-derived intel - last kill/loss dates, average gang size,
  cyno probabilities, last cyno ship and abyssal losses. Primarily
  retrieved from the community-run intel backend (jhmartin's
  resurrection of PySpy's original statistics server, computed from
  the full killmail history since 2007). If that backend is
  unreachable, the same statistics are computed locally from the
  character's recent `kills` / `losses` killmails as a fallback.

Requests run concurrently up to `config.ZKILL_CONCURRENCY`, which
replaces the old one-request-per-second thread pool and makes a scan of
a full local chat take seconds rather than minutes.
'''
# **********************************************************************
import asyncio
import logging

import aiohttp

import config
# **********************************************************************
Logger = logging.getLogger(__name__)

STATS_URL = "https://zkillboard.com/api/stats/characterID/{}/"
KILLS_URL = "https://zkillboard.com/api/kills/characterID/{}/"
LOSSES_URL = "https://zkillboard.com/api/losses/characterID/{}/"
# Community-run resurrection of PySpy's original statistics server, by
# jhmartin (https://github.com/jhmartin/PySpy-backend). Computes intel
# from the complete killmail archive since 2007. Used as the primary
# intel source; if unreachable, PySpy falls back to computing the same
# statistics locally from each pilot's recent killmails.
INTEL_URL = "https://pyspy.toger.us/v2/character_intel?character_id={}"

HEADERS = {
    "Accept-Encoding": "gzip",
    "User-Agent": "PySpy, https://github.com/Eve-PySpy/PySpy"
    }

COVERT_CYNO_IDS = (28646,)  # Covert Cynosural Field Generator I
NORMAL_CYNO_IDS = (21096, 52694)  # Standard & Industrial Cynosural Field Generator
ABYSSAL_MIN_SYSTEM_ID = 32000000  # Abyssal Deadspace solar system ids
LOSSES_SAMPLE = 25  # Number of recent losses used for cyno / abyssal stats
KILLS_SAMPLE = 25  # Number of recent kills used for avg. attacker count
PRIME_TIME_WINDOW = 4  # Width in hours of the reported prime-time window


def characters(char_ids):
    '''
    Fetches zKillboard statistics and killmail-derived intel for a list
    of character ids. Blocking entry point, intended to be called from
    PySpy's analysis thread. Only the first `config.ZKILL_CALLS`
    characters are processed.

    :param `char_ids`: List or tuple of character ids as integers.
    :return: List of dictionaries, one per character for which at least
    one zKillboard resource could be retrieved.
    '''
    char_ids = list(char_ids)[:config.ZKILL_CALLS]
    if not char_ids:
        return []
    try:
        return asyncio.run(_gather_characters(char_ids))
    except Exception:
        Logger.error("Async zKillboard fetch failed.", exc_info=True)
        return []


async def _gather_characters(char_ids):
    sem = asyncio.Semaphore(config.ZKILL_CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=config.ZKILL_CONCURRENCY)
    async with aiohttp.ClientSession(
            headers=HEADERS, timeout=timeout, connector=connector) as session:
        results = await asyncio.gather(
            *[_character(session, sem, char_id) for char_id in char_ids]
            )
    return [r for r in results if r is not None]


# Intel fields derived from a character's kills / losses respectively.
# The community backend stores the two sides separately and only
# returns the sides a character has records for.
KILL_SIDE_KEYS = ("last_kill_date", "avg_attackers")
LOSS_SIDE_KEYS = (
    "last_loss_date", "covert_prob", "normal_prob",
    "last_cov_ship", "last_norm_ship", "abyssal_losses"
    )


async def _character(session, sem, char_id):
    '''
    Fetches and parses all resources for one character: zKillboard
    stats plus killmail-derived intel. Intel comes preferably from the
    community intel backend (full history since 2007); any side (kills
    / losses) the backend does not provide - or all of it, if the
    backend is unreachable - is computed locally from the character's
    recent killmails instead.
    '''
    stats, backend = await asyncio.gather(
        _get_json(session, sem, STATS_URL.format(char_id)),
        _get_json(session, sem, INTEL_URL.format(char_id))
        )
    if not isinstance(backend, dict):
        backend = None
    # One character with unexpected data must not sink the whole batch
    try:
        has_kill_side = backend is not None and "last_kill_date" in backend
        has_loss_side = backend is not None and "last_loss_date" in backend

        kills = losses = None
        if not has_kill_side and not has_loss_side:
            kills, losses = await asyncio.gather(
                _get_json(session, sem, KILLS_URL.format(char_id)),
                _get_json(session, sem, LOSSES_URL.format(char_id))
                )
        elif not has_kill_side:
            kills = await _get_json(session, sem, KILLS_URL.format(char_id))
        elif not has_loss_side:
            losses = await _get_json(session, sem, LOSSES_URL.format(char_id))

        if stats is None and backend is None and kills is None and losses is None:
            # Nothing worked - stay uncached and retry on the next scan.
            return None

        intel = _parse_killmails(
            kills if isinstance(kills, list) else [],
            losses if isinstance(losses, list) else []
            )
        if backend is not None:
            backend_intel = _parse_backend_intel(backend)
            for key in (KILL_SIDE_KEYS if has_kill_side else ()):
                intel[key] = backend_intel[key]
            for key in (LOSS_SIDE_KEYS if has_loss_side else ()):
                intel[key] = backend_intel[key]

        record = {"char_id": char_id}
        record.update(_parse_stats(stats if isinstance(stats, dict) else {}))
        record.update(intel)
        return record
    except Exception:
        Logger.error(
            "Failed to parse killboard data for character " + str(char_id),
            exc_info=True
            )
        return None


def _parse_backend_intel(data):
    '''
    Maps a response of the community intel backend to PySpy's intel
    fields. Missing fields and null values map to 0.
    '''
    def num(key):
        value = data.get(key)
        return value if isinstance(value, (int, float)) else 0

    return {
        "last_loss_date": num("last_loss_date"),
        "last_kill_date": num("last_kill_date"),
        "avg_attackers": num("avg_attackers"),
        "covert_prob": num("covert_prob"),
        "normal_prob": num("normal_prob"),
        "last_cov_ship": num("last_cov_ship"),
        "last_norm_ship": num("last_norm_ship"),
        "abyssal_losses": num("abyssal_losses")
        }


async def _get_json(session, sem, url):
    '''
    GET a JSON resource, retrying once on rate limiting or server
    errors. Returns the decoded payload or None on failure.
    '''
    async with sem:
        for attempt in range(3):
            try:
                async with session.get(url) as r:
                    if r.status == 429 or r.status >= 500:
                        Logger.info(
                            "zKillboard returned " + str(r.status) +
                            " for " + url + ", retrying..."
                            )
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    if r.status != 200:
                        Logger.info(
                            "zKillboard returned error code " +
                            str(r.status) + " for " + url
                            )
                        return None
                    return await r.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                Logger.info("Failed to fetch " + url, exc_info=True)
                return None
    return None


def _parse_stats(stats):
    '''
    Extracts the classic PySpy statistics plus the enriched columns
    (danger and gang ratio, most flown recent ship, prime time) from a
    zKillboard stats payload. Missing values default to 0 / empty.
    '''
    def get(func, default=0):
        try:
            value = func()
            return value if value is not None else default
        except (KeyError, TypeError, IndexError, ZeroDivisionError):
            return default

    return {
        "kills": get(lambda: stats["shipsDestroyed"]),
        "blops_kills": get(lambda: stats["groups"]["898"]["shipsDestroyed"]),
        "hic_losses": get(lambda: stats["groups"]["894"]["shipsLost"]),
        "week_kills": get(lambda: stats["activepvp"]["kills"]["count"]),
        "losses": get(lambda: stats["shipsLost"]),
        "solo_ratio": get(lambda: int(stats["soloKills"]) / int(stats["shipsDestroyed"])),
        "sec_status": get(lambda: stats["info"]["secStatus"]),
        "danger": get(lambda: stats["dangerRatio"]),
        "gang_ratio": get(lambda: stats["gangRatio"]),
        "top_ship": _top_ship(stats),
        "prime_tz": _prime_time(stats)
        }


def _top_ship(stats):
    '''
    Returns the type id of the ship the character has used most over
    zKillboard's recent (90 day) window, or 0 if unknown.
    '''
    try:
        for top_list in stats["topLists"]:
            if top_list.get("type") != "shipType":
                continue
            for entry in top_list.get("values", []):
                ship_id = entry.get("shipTypeID")
                ship_name = entry.get("shipName", "")
                # Skip capsules, they say nothing about what a pilot flies
                if ship_id and not ship_name.startswith("Capsule"):
                    return ship_id
    except (KeyError, TypeError):
        pass
    return 0


def _prime_time(stats):
    '''
    Estimates a character's prime time from zKillboard's recent
    activity histogram, as the contiguous window of
    `PRIME_TIME_WINDOW` hours (EVE time) with the most kill activity.

    :return: String such as "18-22" (EVE/UTC hours), or "" if the
    character has no recent activity.
    '''
    hours = [0] * 24
    try:
        activity = stats["activity"]
        for day in [str(d) for d in range(7)]:
            day_data = activity.get(day)
            # zKillboard returns each day as a dict of hour -> kills,
            # or as a plain list indexed by hour for some characters.
            if isinstance(day_data, dict):
                items = day_data.items()
            elif isinstance(day_data, list):
                items = enumerate(day_data)
            else:
                continue
            for hour, count in items:
                hours[int(hour)] += int(count or 0)
    except Exception:
        return ""
    if sum(hours) == 0:
        return ""
    best_start, best_sum = 0, -1
    for start in range(24):
        window = sum(hours[(start + i) % 24] for i in range(PRIME_TIME_WINDOW))
        if window > best_sum:
            best_start, best_sum = start, window
    return "{:02d}-{:02d}".format(
        best_start, (best_start + PRIME_TIME_WINDOW) % 24
        )


def _killmail_date(killmail):
    '''
    Returns the killmail date as YYYYMMDD integer, or 0 if unavailable.
    Killmail times look like "2026-07-07T23:27:58Z".
    '''
    try:
        return int(killmail["killmail_time"][:10].replace("-", ""))
    except (KeyError, TypeError, ValueError):
        return 0


def _fitted_cyno(killmail):
    '''
    Checks the victim's fitted items for cyno field generators.

    :return: "covert", "normal" or None.
    '''
    items = killmail.get("victim", {}).get("items", [])
    for item in items:
        type_id = item.get("item_type_id")
        if type_id in COVERT_CYNO_IDS:
            return "covert"
        if type_id in NORMAL_CYNO_IDS:
            return "normal"
    return None


def _parse_killmails(kills, losses):
    '''
    Computes the killmail-derived intel statistics from a character's
    most recent kills and losses (newest first, as zKillboard returns
    them). Replaces PySpy's retired proprietary statistics server.
    Probabilities are based on the last `LOSSES_SAMPLE` losses rather
    than the character's full history.
    '''
    last_loss_date = last_kill_date = 0
    avg_attackers = covert_prob = normal_prob = 0
    last_cov_ship = last_norm_ship = 0
    abyssal_losses = 0

    if kills:
        last_kill_date = _killmail_date(kills[0])
        sample = kills[:KILLS_SAMPLE]
        attacker_counts = [len(k.get("attackers", [])) for k in sample]
        if attacker_counts:
            avg_attackers = sum(attacker_counts) / len(attacker_counts)

    if losses:
        last_loss_date = _killmail_date(losses[0])
        sample = losses[:LOSSES_SAMPLE]
        covert_count = normal_count = 0
        for loss in sample:
            cyno = _fitted_cyno(loss)
            if cyno == "covert":
                covert_count += 1
                if last_cov_ship == 0:
                    last_cov_ship = loss.get("victim", {}).get("ship_type_id", 0)
            elif cyno == "normal":
                normal_count += 1
                if last_norm_ship == 0:
                    last_norm_ship = loss.get("victim", {}).get("ship_type_id", 0)
            if loss.get("solar_system_id", 0) >= ABYSSAL_MIN_SYSTEM_ID:
                abyssal_losses += 1
        covert_prob = covert_count / len(sample)
        normal_prob = normal_count / len(sample)

    return {
        "last_loss_date": last_loss_date,
        "last_kill_date": last_kill_date,
        "avg_attackers": avg_attackers,
        "covert_prob": covert_prob,
        "normal_prob": normal_prob,
        "last_cov_ship": last_cov_ship,
        "last_norm_ship": last_norm_ship,
        "abyssal_losses": abyssal_losses
        }
