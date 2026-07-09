# !/usr/local/bin/python3.6
# MIT licensed
# Copyright (c) 2018 White Russsian
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
''' The primary function is main(), which takes a set of EVE Online
character names and gathers useful information from CCP's ESI API and
zKIllboard's API, to be stored in a temporary in-memory SQLite3 database.
'''
# **********************************************************************
import logging
import json
import datetime

import apis
import config
import db
import fetch
import statusmsg
# cSpell Checker - Correct Words****************************************
# // cSpell:words affil, zkill, blops, qsize, numid, russsian, ccp's
# // cSpell:words records_added
# **********************************************************************
Logger = logging.getLogger(__name__)
# Example call: Logger.info("Something badhappened", exc_info=True) ****


# All per-character columns retrieved from zKillboard, in the order
# used by the update and cache queries in main() below. Must match the
# record keys produced by fetch.characters().
ZKILL_COLUMNS = (
    "kills", "blops_kills", "hic_losses", "week_kills", "losses",
    "solo_ratio", "sec_status", "danger", "gang_ratio", "top_ship",
    "prime_tz", "last_loss_date", "last_kill_date", "avg_attackers",
    "covert_prob", "normal_prob", "last_cov_ship", "last_norm_ship",
    "abyssal_losses"
    )


def main(char_names, conn_mem, cur_mem, conn_dsk, cur_dsk):
    chars_found = get_char_ids(conn_mem, cur_mem, char_names)
    if chars_found == 0:
        return

    char_ids_mem = cur_mem.execute(
        "SELECT char_id, char_name FROM characters ORDER BY char_name"
        ).fetchall()

    cache_max_age = datetime.datetime.now() - datetime.timedelta(seconds=config.CACHE_TIME)
    char_ids_dsk = cur_dsk.execute(
        "SELECT char_id FROM characters WHERE last_update > ?", (cache_max_age,)
        ).fetchall()

    ids_mem = set(r[0] for r in char_ids_mem)
    ids_dsk = set(r[0] for r in char_ids_dsk)

    cache_hits = ids_mem & ids_dsk # Intersection of what we want and what we already have
    cache_miss = ids_mem - cache_hits

    Logger.debug("Cache Hits - {}".format(len(cache_hits)))
    Logger.debug("Cache Miss - {}".format(len(cache_miss)))

    get_char_affiliations(conn_mem, cur_mem)
    get_affil_names(conn_mem, cur_mem)

    update_query = (
        "UPDATE characters SET " +
        ", ".join(c + "=?" for c in ZKILL_COLUMNS) +
        ", last_update=? WHERE char_id=?"
        )
    select_query = (
        "SELECT " + ", ".join(ZKILL_COLUMNS) +
        ", last_update, char_id FROM characters WHERE char_id = ?"
        )

    if cache_miss:
        statusmsg.push_status(
            "Retrieving zKillboard data for " + str(len(cache_miss)) +
            " character(s)..."
            )
        records = fetch.characters(sorted(cache_miss))
        update_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fresh_rows = tuple(
            tuple(rec[c] for c in ZKILL_COLUMNS) + (update_datetime, rec["char_id"])
            for rec in records
            )
        db.write_many_to_db(conn_mem, cur_mem, update_query, fresh_rows)
        # Persist to the disk cache, making sure the character rows exist
        name_rows = [r for r in char_ids_mem if r[0] in cache_miss]
        db.write_many_to_db(
            conn_dsk, cur_dsk,
            "INSERT OR REPLACE INTO characters (char_id, char_name) VALUES (?, ?)",
            name_rows
            )
        db.write_many_to_db(conn_dsk, cur_dsk, update_query, fresh_rows)

    # Copy cached characters from the disk cache into the in-memory db
    cached_rows = []
    for char_id in cache_hits:
        row = cur_dsk.execute(select_query, (char_id,)).fetchone()
        if row is not None:
            cached_rows.append(tuple(row))
    db.write_many_to_db(conn_mem, cur_mem, update_query, cached_rows)

    output = output_list(cur_mem)
    conn_mem.close()
    return output


def get_char_ids(conn, cur, char_names):
    char_names = json.dumps(char_names[0:config.MAX_NAMES])  # apis max char is 1000
    statusmsg.push_status("Resolving character names to IDs...")
    try:
        characters = apis.post_req_ccp("universe/ids/", char_names)
        characters = characters['characters']
    except:
        return 0
    records = ()
    for r in characters:
        records = records + ((r["id"], r["name"]),)
    query_string = (
        '''INSERT OR REPLACE INTO characters (char_id, char_name) VALUES (?, ?)'''
        )
    records_added = db.write_many_to_db(conn, cur, query_string, records)
    return records_added


def get_char_affiliations(conn, cur):
    char_ids = cur.execute("SELECT char_id FROM characters").fetchall()
    char_ids = json.dumps(tuple([r[0] for r in char_ids]))
    statusmsg.push_status("Retrieving character affiliation IDs...")
    try:
        affiliations = apis.post_req_ccp("characters/affiliation/", char_ids)
    except:
        Logger.info("Failed to obtain character affiliations.", exc_info=True)
        raise Exception

    records = ()
    for r in affiliations:
        corp_id = r["corporation_id"]
        alliance_id = r["alliance_id"] if "alliance_id" in r else 0
        faction_id = r["faction_id"] if "faction_id" in r else 0
        char_id = r["character_id"]
        records = records + ((corp_id, alliance_id, faction_id, char_id), )

    query_string = (
        '''UPDATE characters SET corp_id=?, alliance_id=?, faction_id=?
        WHERE char_id=?'''
        )
    db.write_many_to_db(conn, cur, query_string, records)


def get_affil_names(conn, cur):
    # use select distinct to get corp and alliance ids and reslove them
    alliance_ids = cur.execute(
        '''SELECT DISTINCT alliance_id FROM characters
        WHERE alliance_id IS NOT 0'''
        ).fetchall()
    corp_ids = cur.execute(
        "SELECT DISTINCT corp_id FROM characters WHERE corp_id IS NOT 0"
        ).fetchall()

    ids = alliance_ids + corp_ids
    ids = json.dumps(tuple([r[0] for r in ids]))

    statusmsg.push_status("Obtaining corporation and alliance names and zKillboard data...")
    try:
        names = apis.post_req_ccp("universe/names/", ids)
    except:
        Logger.info("Failed request corporation and alliance names.",
                    exc_info=True)
        raise Exception

    alliances, corporations = (), ()
    for r in names:
        if r["category"] == "alliance":
            alliances = alliances + ((r["id"], r["name"]),)
        elif r["category"] == "corporation":
            corporations = corporations + ((r["id"], r["name"]),)
    if alliances:
        query_string = ('''INSERT INTO alliances (id, name) VALUES (?, ?)''')
        db.write_many_to_db(conn, cur, query_string, alliances)
    if corporations:
        query_string = ('''INSERT INTO corporations (id, name) VALUES (?, ?)''')
        db.write_many_to_db(conn, cur, query_string, corporations)


def output_list(cur):
    query_string = (
        '''SELECT
        ch.char_id, ch.faction_id, ch.char_name, co.id, co.name, al.id,
        al.name, fa.name, ac.numid, ch.week_kills, ch.kills, ch.blops_kills,
        ch.hic_losses, ch.losses, ch.solo_ratio, ch.sec_status,
        ch.last_loss_date, ch.last_kill_date,
        ch.avg_attackers, ch.covert_prob, ch.normal_prob,
        IFNULL(cs.name,'-'), IFNULL(ns.name,'-'), ch.abyssal_losses,
        ch.danger, ch.gang_ratio, IFNULL(ts.name,'-'), ch.prime_tz
        FROM characters AS ch
        LEFT JOIN alliances AS al ON ch.alliance_id = al.id
        LEFT JOIN corporations AS co ON ch.corp_id = co.id
        LEFT JOIN factions AS fa ON ch.faction_id = fa.id
        LEFT JOIN (SELECT alliance_id, COUNT(alliance_id) AS numid FROM characters GROUP BY alliance_id)
            AS ac ON ch.alliance_id = ac.alliance_id
        LEFT JOIN ships AS cs ON ch.last_cov_ship = cs.id
        LEFT JOIN ships AS ns ON ch.last_norm_ship = ns.id
        LEFT JOIN ships AS ts ON ch.top_ship = ts.id
        ORDER BY ch.char_name'''
        )
    return cur.execute(query_string).fetchall()
