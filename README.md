<!--- // cSpell:words killboard, blops, hics, killboard's, cynos, ccp's, pyspy, psf's, pyperclip, pyinstaller, executables, jojo, unported, killmails, aiohttp --->

# PySpy [Reworked] - EVE Online character intel tool

**Version v1.0.0** - a revived, repaired and modernised fork of the original
[PySpy](https://github.com/Eve-PySpy/PySpy) by White Russsian, which is
unmaintained and no longer functional. This rework restores every original
feature and adds automatic intel gathering for today's game environment.

## What is PySpy?

PySpy is a fast and simple character intel tool for
[EVE Online](https://www.eveonline.com/). Copy a list of character names from
the in-game *local chat* member list and, within a couple of seconds, PySpy
shows you who you are dealing with: killboard activity, threat ratings, cyno
probabilities, likely ships, active timezones and more.

PySpy connects to [CCP's ESI API](https://esi.evetech.net/ui/) and the
[zKillboard API](https://github.com/zKillboard/zKillboard/wiki) and runs on
Windows, macOS and Linux.

## What the Rework changed

* **It works again.** Fixed the startup crash on modern wxPython, broken
  API error handling and several threading bugs in the original code.
* **Proprietary stats server replaced - twice over.** The original PySpy
  depended on a private statistics server that no longer exists. Its
  statistics (cyno probabilities, last kill/loss dates, average gang size,
  abyssal losses) now come primarily from the community-run
  [PySpy-backend](https://github.com/jhmartin/PySpy-backend) by jhmartin,
  which rebuilt the database from the complete killmail archive since 2007.
  If that backend is ever unreachable, PySpy transparently computes the same
  statistics locally from each pilot's recent zKillboard killmail history -
  the feature can never fully die again. Results are cached for 12 hours.
* **Much faster scans.** The one-request-per-second query loop was replaced
  with an asynchronous fetch layer - a fresh scan of a handful of pilots
  takes ~2 seconds instead of minutes for a full local.
* **New intel columns.** Danger rating, gang ratio, most-flown recent ship
  ("likely flying") and active hours (EVE time) for every pilot.
* **Fleet rollup.** A summary line above the results: pilot count, largest
  alliances, cyno risks and BLOPS-active pilots at a glance.
* **Automatic intel.** Chat log watching (intel channels, Local speakers,
  location tracking) and live killmail alerts - see below.
* **Usage statistics reporting removed.** The original phoned home to its
  (now dead) server; the reworked version reports nothing.

## How to use PySpy

1. Open PySpy.
2. In your EVE client, select the characters in your local chat member list
   (click one, `CTRL+A`) and copy them to the clipboard (`CTRL+C` on Windows
   *or* `⌘+C` on macOS).
3. PySpy detects the clipboard change and analyses everyone automatically.
4. Double-click a result row to open the matching zKillboard page in your
   browser (character, corporation, alliance or faction depending on the
   column, if advanced zKillboard linking is enabled).

**Note**: PySpy saves its window location, size, column layout, sorting order,
transparency (slider at the bottom right) and all other settings automatically
and restores them on the next launch. If selected in the _View_ menu, PySpy
stays on top of the EVE client so long as the game runs in *window mode*.

## Automatic Intel (optional)

Beyond clipboard scanning, PySpy can gather intel hands-free. Both features
are off by default and can be enabled in the _Options_ menu:

* **Watch EVE Chat Logs (Intel + Location)** - requires "Log Chat to File" to
  be enabled in the EVE client settings (Settings > Chat). PySpy then:
  * **Tracks your location**: your current solar system is read from the
    Local channel log and shown in the window title, updating as you jump.
    Works in wormhole space too.
  * **Scans pilots who talk in Local**: anyone who types in your local chat
    is a confirmed pilot in your system and gets analysed automatically the
    moment their message appears.
  * **Watches your intel channels**: set your channels via _Options > Set
    Intel Channels_ and any pilot names mentioned in them (e.g. by your
    alliance's scouts) are analysed automatically.
* **Live Kill Feed Alerts** - subscribes to zKillboard's live killmail
  stream (R2Z2) and alerts you via the status bar and a bell sound whenever:
  * a kill happens **in your current system** (needs chat log watching for
    the location), or
  * any pilot, corporation or alliance on your **highlight list** appears on
    a killmail anywhere in New Eden - your highlight list doubles as a
    watchlist.

**A note on limits**: the *silent* local member list is not written to any
log file and CCP deliberately provides no API for it, so reading it
automatically is impossible for any EULA-compliant tool. The one manual step
that remains is the `CTRL+A`, `CTRL+C` copy - PySpy automates everything
around it.

## Information Provided by PySpy

* **Warning**: Why a character is highlighted (CYNO, BLOPS, HIC).
* **Character**: Character name.
* **Security**: CONCORD security status.
* **Corporation / Alliance / Faction**: Affiliations (alliance shows member
  count of that alliance within your scan).
* **Kills / Losses**: Total kills and losses.
* **Last Wk**: Kills over the past 7 days.
* **Solo**: Ratio of solo kills to total kills.
* **BLOPS**: Black Ops battleships killed.
* **HICs**: Heavy Interdiction Cruisers lost.
* **Last Loss / Last Kill**: Days since last loss / kill.
* **Avg. Attackers**: Average gang size on their recent kills.
* **Covert / Regular Cyno**: Share of recent losses with a covert / regular
  (incl. industrial) cyno fitted.
* **Last Covert / Regular Cyno**: Ship type of the most recent such loss.
* **Abyssal Losses**: Recent losses in Abyssal space.
* **Danger**: zKillboard danger rating (0-100%).
* **Gang**: Share of their kills made with a gang (high = rarely alone).
* **Top Ship**: Most flown ship over the last 90 days - what they are
  likely flying right now.
* **Active (ET)**: The 4-hour window (EVE time) in which they are most
  active - are they in their prime time right now?

Columns can be shown or hidden individually via the _View_ menu, and sorted
by clicking their headers.

**Current limitations**: to stay polite with zKillboard's API, the killboard
statistics are gathered for the first 100 characters per scan (names beyond
that are still resolved and listed). Cyno and abyssal statistics are based on
each pilot's most recent killmails rather than their full history since 2007,
so values can differ slightly from the original server-based PySpy.

## Ignore Certain Entities

PySpy allows you to specify a list of ignored characters, corporations and
alliances. To add entities to that list, right click on a search result. You
can remove entities from this list under _Options_ > _Review Ignored
Entities_.

## Ignore all Members of your NPSI Fleet

For anyone using PySpy in not-purple-shoot-it (NPSI) fleets, you can tell
PySpy to temporarily ignore your fleet mates by first running PySpy on all
characters in your fleet chat and then selecting _Options_ > _Set NPSI Ignore
List_. Once the fleet is over, clear the list under _Options_ > _Clear NPSI
Ignore List_. Your custom ignore list is not affected by this.

## Highlighting & Watchlist

PySpy allows you to specify a list of highlighted characters, corporations
and alliances, shown in a distinct colour. Right click a search result to add
or remove entities; review the list under _Options_ > _Review Highlighted
Entities_. PySpy also highlights characters that use Black Ops or Heavy
Interdiction Cruisers, or frequently have a cyno fitted.

With **Live Kill Feed Alerts** enabled, highlighted entities also act as a
watchlist: PySpy alerts you whenever any of them appears on a killmail.

## Installation

Run from source (Python 3.8 or newer):

```
git clone <this repository>
cd PySpy
pip install -r requirements.txt
python __main__.py
```

If you want to build a single-file executable, a
[pyinstaller](https://www.pyinstaller.org/) spec file (`__main__.spec`) is
provided.

## Uninstalling PySpy

Delete the PySpy folder and remove the settings/log files:

* **Running from source**: settings, cache and logs live in the `tmp` folder
  inside the PySpy directory (Linux: `~/.config/pyspy`).
* **Windows executable**: a folder called `PySpy` under `%LocalAppData%`.
* **macOS executable**: `pyspy.log` under `~/Library/Logs`, and `pyspy.cfg` /
  `pyspy.pickle` under `~/Library/Preferences`.

## Dependencies & Acknowledgements

* Original PySpy by [White Russsian / Eve-PySpy](https://github.com/Eve-PySpy/PySpy),
  licensed under the MIT License. If you enjoy PySpy, the original author
  accepted ISK in-game to *White Russsian* (with 3 's').
* Full-history intel statistics are served by the community-run
  [PySpy-backend](https://github.com/jhmartin/PySpy-backend), built and
  hosted by [jhmartin](https://github.com/jhmartin), who also maintains his
  own [resurrected PySpy client](https://github.com/jhmartin/PySpy).
* PySpy is written in [Python 3](https://www.python.org/), licensed under
  [PSF's License Agreement](https://docs.python.org/3/license.html#psf-license-agreement-for-python-release).
* API connectivity relies on [Requests](https://docs.python-requests.org/)
  (Apache 2.0) and [aiohttp](https://docs.aiohttp.org/) (Apache 2.0).
* Clipboard monitoring uses [pyperclip](https://github.com/asweigart/pyperclip)
  (3-Clause BSD).
* The GUI is powered by [wxPython](https://www.wxpython.org/)
  ([wxWindows Library Licence](https://wxpython.org/pages/license/index.html)).
* Killmail data and statistics by [zKillboard](https://zkillboard.com/);
  game data by [CCP's ESI API](https://esi.evetech.net/ui/).
* PySpy's icon was created by Jojo Mendoza, licensed under
  [CC BY-NC 3.0](https://creativecommons.org/licenses/by-nc/3.0/), available
  on [IconFinder](https://www.iconfinder.com/icons/1218719/cyber_hat_spy_undercover_user_icon).

## License

PySpy is licensed under the [MIT](LICENSE.txt) License.

## CCP Copyright Notice

EVE Online and the EVE logo are the registered trademarks of CCP hf. All
rights are reserved worldwide. All other trademarks are the property of their
respective owners. EVE Online, the EVE logo, EVE and all associated logos and
designs are the intellectual property of CCP hf. All artwork, screenshots,
characters, vehicles, storylines, world facts or other recognizable features
of the intellectual property relating to these trademarks are likewise the
intellectual property of CCP hf. CCP is in no way responsible for the content
on or functioning of this tool, nor can it be liable for any damage arising
from the use of this tool.
