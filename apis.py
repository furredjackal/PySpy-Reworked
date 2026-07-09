# !/usr/local/bin/python3.6
# MIT licensed
# Copyright (c) 2018 White Russsian
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
''' This module provides connectivity to CCP's ESI API, to zKillboard's
API and to PySpy's own proprietary RESTful API.
'''
# **********************************************************************
import json
import logging
import time

import requests

import config
import statusmsg
# cSpell Checker - Correct Words****************************************
# // cSpell:words wrusssian, ZKILL, gmail, blops, toon, HICs, russsian,
# // cSpell:words ccp's, activepvp
# **********************************************************************
Logger = logging.getLogger(__name__)
# Example call: Logger.info("Something badhappened", exc_info=True) ****


# ESI Status
# https://esi.evetech.net/ui/?version=meta#/Meta/get_status

def server_error_msg(r):
    '''Extract the error message from an API response, tolerating
    non-JSON bodies (e.g. HTML error pages).'''
    try:
        return json.loads(r.text)["error"]
    except (ValueError, KeyError, TypeError):
        return "N/A"


def post_req_ccp(esi_path, json_data):
    url = "https://esi.evetech.net/latest/" + esi_path + \
        "?datasource=tranquility"
    try:
        r = requests.post(url, json_data, timeout=10)
    except requests.exceptions.RequestException:
        Logger.info("No network connection.", exc_info=True)
        statusmsg.push_status(
            "NETWORK ERROR: Check your internet connection and firewall settings."
            )
        time.sleep(5)
        return "network_error"
    if r.status_code != 200:
        server_msg = server_error_msg(r)
        Logger.info(
            "CCP Servers at (" + esi_path + ") returned error code: " +
            str(r.status_code) + ", saying: " + server_msg, exc_info=True
            )
        statusmsg.push_status(
            "CCP SERVER ERROR: " + str(r.status_code) + " (" + server_msg + ")"
            )
        return "server_error"
    return r.json()


def get_ship_data():
    '''
    Produces a list of ship id and ship name pairs for each ship in EVE
    Online, using ESI's universe/names endpoint.

    :return: List of lists containing ship ids and related ship names.
    '''
    all_ship_ids = get_all_ship_ids()
    if not isinstance(all_ship_ids, (list, tuple)) or len(all_ship_ids) < 1:
        Logger.error("[get_ship_data] No valid ship ids provided.", exc_info=True)
        return

    url = "https://esi.evetech.net/v2/universe/names/?datasource=tranquility"
    json_data = json.dumps(all_ship_ids)
    try:
        r = requests.post(url, json_data, timeout=10)
    except requests.exceptions.RequestException:
        Logger.error("[get_ship_data] No network connection.", exc_info=True)
        return "network_error"
    if r.status_code != 200:
        server_msg = server_error_msg(r)
        Logger.error(
            "[get_ship_data] CCP Servers returned error code: " +
            str(r.status_code) + ", saying: " + server_msg, exc_info=True
            )
        return "server_error"
    ship_data = list(map(lambda r: [r['id'], r['name']], r.json()))
    return ship_data


def get_all_ship_ids():
    '''
    Uses ESI's insurance/prices endpoint to get all available ship ids.

    :return: List of ship ids as integers.
    '''
    url = "https://esi.evetech.net/v1/insurance/prices/?datasource=tranquility"

    try:
        r = requests.get(url, timeout=10)
    except requests.exceptions.RequestException:
        Logger.error("[get_ship_ids] No network connection.", exc_info=True)
        return "network_error"
    if r.status_code != 200:
        server_msg = server_error_msg(r)
        Logger.error(
            "[get_ship_ids] CCP Servers at returned error code: " +
            str(r.status_code) + ", saying: " + server_msg, exc_info=True
            )
        return "server_error"

    ship_ids = list(map(lambda r: str(r['type_id']), r.json()))
    Logger.info("[get_ship_ids] Number of ship ids found: " + str(len(ship_ids)))
    return ship_ids