# !/usr/local/bin/python3.6
# MIT licensed
# Copyright (c) 2018 White Russsian
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
'''Material Design GUI for PySpy. The results are rendered as HTML/CSS
inside an embedded WebView2 (Edge) browser control (see webui.py); all
scanning, caching and intel logic remains in Python. Menus and dialogs
are native wx for reliability.'''
# **********************************************************************
import datetime
import json
import logging
import os
import webbrowser

import wx
import wx.html2
import wx.lib.agw.persist as pm

import config
import db

import aboutdialog
import chatwatch
import highlightdialog
import ignoredialog
import statusmsg
import webui
# cSpell Checker - Correct Words****************************************
# // cSpell:words wrusssian, wxpython, zkill, blops, russsian, chkversion
# // cSpell:words posix, Gallente, Minmatar, Amarr, Caldari, ontop, hics
# // cSpell:words npsi, webui, evetech
# **********************************************************************
Logger = logging.getLogger(__name__)
# Example call: Logger.info("Something badhappened", exc_info=True) ****

# Grid column index -> stable key used in the HTML/JS layer. Aligned
# with self.columns and the `out` display array built in updateList().
COL_KEYS = [
    "id", "warning", "factionid", "name", "security", "corpid",
    "corporation", "allianceid", "alliance", "faction", "kills", "losses",
    "lastwk", "solo", "blops", "hics", "lastloss", "lastkill", "avgatt",
    "covcyno", "regcyno", "lastcov", "lastreg", "abyssal", "danger",
    "gang", "topship", "active"
    ]
# Grid column indices that are internal helpers, never shown as columns.
HIDDEN_COLS = {0, 2, 5, 7}
# Keys whose values sort numerically in the table.
NUMERIC_KEYS = {
    "security", "kills", "losses", "lastwk", "solo", "blops", "hics",
    "lastloss", "lastkill", "avgatt", "covcyno", "regcyno", "abyssal",
    "danger", "gang"
    }


class Frame(wx.Frame):
    def __init__(self, *args, **kwds):

        # Persistent Options
        self.options = config.OPTIONS_OBJECT

        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetName("Main Window")

        # Set stay on-top unless user deactivated it
        if self.options.Get("StayOnTop", True):
            self.ToggleWindowStyle(wx.STAY_ON_TOP)

        # Set parameters for columns
        self.columns = (
            # Index, Heading, Format, Default Width, Can Toggle, Default Show, Menu Name, Outlist Column
            [0, "ID", wx.ALIGN_LEFT, 0, False, False, "", 0],
            [1, "Warning", wx.ALIGN_LEFT, 80, True, True, "Warning\tCTRL+ALT+X"],
            [2, "Faction ID", wx.ALIGN_LEFT, 0, False, False, "", 1],
            [3, "Character", wx.ALIGN_LEFT, 160, False, True, "", 2],
            [4, "Security", wx.ALIGN_RIGHT, 50, True, False, "&Security\tCTRL+ALT+S", 15],
            [5, "CorpID", wx.ALIGN_LEFT, 0, False, False, "", 3],
            [6, "Corporation", wx.ALIGN_LEFT, 100, True, True, "Cor&poration\tCTRL+ALT+P", 4],
            [7, "AllianceID", wx.ALIGN_LEFT, 0, False, False, "-", 5],
            [8, "Alliance", wx.ALIGN_LEFT, 150, True, True, "All&iance\tCTRL+ALT+I", 6],
            [9, "Faction", wx.ALIGN_LEFT, 50, True, False, "&Faction\tCTRL+ALT+F", 7],
            [10, "Kills", wx.ALIGN_RIGHT, 50, True, True, "&Kills\tCTRL+ALT+K", 10],
            [11, "Losses", wx.ALIGN_RIGHT, 50, True, True, "&Losses\tCTRL+ALT+L", 13],
            [12, "Last Wk", wx.ALIGN_RIGHT, 50, True, True, "Last &Wk\tCTRL+ALT+W", 9],
            [13, "Solo", wx.ALIGN_RIGHT, 50, True, False, "S&olo\tCTRL+ALT+O", 14],
            [14, "BLOPS", wx.ALIGN_RIGHT, 50, True, False, "&BLOPS\tCTRL+ALT+B", 11],
            [15, "HICs", wx.ALIGN_RIGHT, 50, True, False, "&HICs\tCTRL+ALT+H", 12],
            [16, "Last Loss", wx.ALIGN_RIGHT, 60, True, True, "Days since last Loss\tCTRL+ALT+[", 16],
            [17, "Last Kill", wx.ALIGN_RIGHT, 60, True, True, "Days since last Kill\tCTRL+ALT+]", 17],
            [18, "Avg. Attackers", wx.ALIGN_RIGHT, 100, True, True, "&Average Attackers\tCTRL+ALT+A", 18],
            [19, "Covert Cyno", wx.ALIGN_RIGHT, 100, True, True, "&Covert Cyno Probability\tCTRL+ALT+C", 19],
            [20, "Regular Cyno", wx.ALIGN_RIGHT, 100, True, True, "&Regular Cyno Probability\tCTRL+ALT+R", 20],
            [21, "Last Covert Cyno", wx.ALIGN_RIGHT, 100, True, True, "&Last Covert Cyno Ship Loss\tCTRL+ALT+<", 21],
            [22, "Last Regular Cyno", wx.ALIGN_RIGHT, 110, True, True, "&Last Regular Cyno Ship Loss\tCTRL+ALT+>", 22],
            [23, "Abyssal Losses", wx.ALIGN_RIGHT, 100, True, False, "&Abyssal Losses\tCTRL+ALT+Y", 23],
            [24, "Danger", wx.ALIGN_RIGHT, 55, True, True, "&Danger Rating\tCTRL+ALT+D", 24],
            [25, "Gang", wx.ALIGN_RIGHT, 50, True, False, "&Gang Ratio\tCTRL+ALT+G", 25],
            [26, "Top Ship", wx.ALIGN_LEFT, 90, True, True, "&Top Ship (recent)\tCTRL+ALT+T", 26],
            [27, "Active (ET)", wx.ALIGN_RIGHT, 70, True, True, "Active Ho&urs (EVE Time)\tCTRL+ALT+U", 27],
            )

        # ---- Menus (native wx, shown via the header's menu button) ----
        self.main_menu = wx.Menu()

        self.file_menu = wx.Menu()
        self.file_about = self.file_menu.Append(wx.ID_ANY, '&About\tCTRL+A')
        self.file_menu.Bind(wx.EVT_MENU, self._openAboutDialog, self.file_about)
        self.file_quit = self.file_menu.Append(wx.ID_ANY, 'Quit PySpy')
        self.file_menu.Bind(wx.EVT_MENU, self.OnQuit, self.file_quit)

        # View menu is platform independent
        self.view_menu = wx.Menu()

        self._createShowColMenuItems()

        self.view_menu.AppendSeparator()

        # Ignore Factions submenu for view menu
        self.factions_sub = wx.Menu()
        self.view_menu.Append(wx.ID_ANY, "Ignore Factions", self.factions_sub)

        self.ignore_galmin = self.factions_sub.AppendRadioItem(wx.ID_ANY, "Gallente / Minmatar")
        self.factions_sub.Bind(wx.EVT_MENU, self._toggleIgnoreFactions, self.ignore_galmin)
        self.ignore_galmin.Check(self.options.Get("IgnoreGalMin", False))

        self.ignore_amacal = self.factions_sub.AppendRadioItem(wx.ID_ANY, "Amarr / Caldari")
        self.factions_sub.Bind(wx.EVT_MENU, self._toggleIgnoreFactions, self.ignore_amacal)
        self.ignore_amacal.Check(self.options.Get("IgnoreAmaCal", False))

        self.ignore_none = self.factions_sub.AppendRadioItem(wx.ID_ANY, "None")
        self.factions_sub.Bind(wx.EVT_MENU, self._toggleIgnoreFactions, self.ignore_none)
        self.ignore_none.Check(self.options.Get("IgnoreNone", True))

        # Higlighting submenu for view menu
        self.hl_sub = wx.Menu()
        self.view_menu.Append(wx.ID_ANY, "Highlighting", self.hl_sub)

        self.hl_blops = self.hl_sub.AppendCheckItem(wx.ID_ANY, "&BLOPS Kills\t(red)")
        self.hl_sub.Bind(wx.EVT_MENU, self._toggleHighlighting, self.hl_blops)
        self.hl_blops.Check(self.options.Get("HlBlops", True))

        self.hl_hic = self.hl_sub.AppendCheckItem(wx.ID_ANY, "&HIC Losses\t(red)")
        self.hl_sub.Bind(wx.EVT_MENU, self._toggleHighlighting, self.hl_hic)
        self.hl_hic.Check(self.options.Get("HlHic", True))

        self.hl_cyno = self.hl_sub.AppendCheckItem(
            wx.ID_ANY,
            "Cyno Characters (>" +
            "{:.0%}".format(config.CYNO_HL_PERCENTAGE) +
            " cyno losses)\t(blue)"
            )
        self.hl_sub.Bind(wx.EVT_MENU, self._toggleHighlighting, self.hl_cyno)
        self.hl_cyno.Check(self.options.Get("HlCyno", True))

        self.hl_list = self.hl_sub.AppendCheckItem(wx.ID_ANY, "&Highlighted Entities List\t(pink)")
        self.hl_sub.Bind(wx.EVT_MENU, self._toggleHighlighting, self.hl_list)
        self.hl_list.Check(self.options.Get("HlList", True))

        # Font submenu for font scale
        self.font_sub = wx.Menu()
        self.view_menu.Append(wx.ID_ANY, "Font Scale", self.font_sub)

        self._fontScaleMenu(config.FONT_SCALE_MIN, config.FONT_SCALE_MAX)

        self.view_menu.AppendSeparator()

        # Toggle Stay on-top
        self.stay_ontop = self.view_menu.AppendCheckItem(
            wx.ID_ANY, 'Stay on-&top\tCTRL+T'
            )
        self.view_menu.Bind(wx.EVT_MENU, self._toggleStayOnTop, self.stay_ontop)
        self.stay_ontop.Check(self.options.Get("StayOnTop", True))

        # Toggle Dark-Mode
        self.dark_mode = self.view_menu.AppendCheckItem(
            wx.ID_ANY, '&Dark Mode\tCTRL+D'
            )
        self.dark_mode.Check(self.options.Get("DarkMode", True))
        self.view_menu.Bind(wx.EVT_MENU, self._toggleDarkMode, self.dark_mode)
        self.use_dm = self.dark_mode.IsChecked()

        # Options Menu
        self.opt_menu = wx.Menu()

        self.review_ignore = self.opt_menu.Append(wx.ID_ANY, "&Review Ignored Entities\tCTRL+R")
        self.opt_menu.Bind(wx.EVT_MENU, self._openIgnoreDialog, self.review_ignore)

        self.review_highlight = self.opt_menu.Append(wx.ID_ANY, "&Review Highlighted Entities\tCTRL+H")
        self.opt_menu.Bind(wx.EVT_MENU, self._openHightlightDialog, self.review_highlight)

        self.opt_menu.AppendSeparator()

        self.ignore_all = self.opt_menu.Append(wx.ID_ANY, "&Set NPSI Ignore List\tCTRL+SHIFT+S")
        self.opt_menu.Bind(wx.EVT_MENU, self._showNpsiDialog, self.ignore_all)

        self.clear_ignore = self.opt_menu.Append(wx.ID_ANY, "&Clear NPSI Ignore List\tCTRL+SHIFT+C")
        self.opt_menu.Bind(wx.EVT_MENU, self._clearNpsiList, self.clear_ignore)

        self.opt_menu.AppendSeparator()

        # Toggle zKillboard linking mode
        self.zkill_mode = self.opt_menu.AppendCheckItem(
            wx.ID_ANY, '&zKillboard Advanced Linking\tCTRL+ALT+Z'
            )
        self.zkill_mode.Check(self.options.Get("ZkillMode", False))
        self.opt_menu.Bind(wx.EVT_MENU, self._toggleZkillMode, self.zkill_mode)
        self.use_adv_zkill = self.zkill_mode.IsChecked()

        self.opt_menu.AppendSeparator()

        # Automatic intel: chat log watching and live kill feed
        self.chat_watch = self.opt_menu.AppendCheckItem(
            wx.ID_ANY, '&Watch EVE Chat Logs (Intel + Location)'
            )
        self.chat_watch.Check(self.options.Get("ChatWatch", False))
        self.opt_menu.Bind(wx.EVT_MENU, self._toggleChatWatch, self.chat_watch)

        self.set_intel = self.opt_menu.Append(wx.ID_ANY, 'Set &Intel Channels...')
        self.opt_menu.Bind(wx.EVT_MENU, self._setIntelChannels, self.set_intel)

        self.kill_feed = self.opt_menu.AppendCheckItem(
            wx.ID_ANY, '&Live Kill Feed Alerts'
            )
        self.kill_feed.Check(self.options.Get("KillFeed", False))
        self.opt_menu.Bind(wx.EVT_MENU, self._toggleKillFeed, self.kill_feed)

        self.opt_menu.AppendSeparator()

        self.clear_cache = self.opt_menu.Append(wx.ID_ANY, '&Clear Character Cache')
        self.opt_menu.Bind(wx.EVT_MENU, self.clear_character_cache, self.clear_cache)

        # Assemble the popup menu shown by the header's menu button
        self.main_menu.AppendSubMenu(self.file_menu, "PySpy")
        self.main_menu.AppendSubMenu(self.view_menu, "View")
        self.main_menu.AppendSubMenu(self.opt_menu, "Options")

        # Keyboard shortcuts (previously provided by the menu bar)
        self.SetAcceleratorTable(wx.AcceleratorTable([
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("A"), self.file_about.GetId()),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("D"), self.dark_mode.GetId()),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("T"), self.stay_ontop.GetId()),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("R"), self.review_ignore.GetId()),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("H"), self.review_highlight.GetId()),
            ]))
        self.Bind(wx.EVT_MENU, self._openAboutDialog, id=self.file_about.GetId())
        self.Bind(wx.EVT_MENU, self._accelDarkMode, id=self.dark_mode.GetId())
        self.Bind(wx.EVT_MENU, self._accelStayOnTop, id=self.stay_ontop.GetId())
        self.Bind(wx.EVT_MENU, self._openIgnoreDialog, id=self.review_ignore.GetId())
        self.Bind(wx.EVT_MENU, self._openHightlightDialog, id=self.review_highlight.GetId())

        # ---- WebView (the Material Design UI itself) ----
        self._web_ready = False
        self._pending_js = []
        self._last_payload = None
        self.web = wx.html2.WebView.New(
            self, backend=wx.html2.WebViewBackendEdge
            )
        self.web.SetName("WebUI")
        # Suppress the browser's own context menu / accelerators
        try:
            self.web.EnableContextMenu(False)
            self.web.EnableAccessToDevTools(False)
        except Exception:
            pass
        self.web.AddScriptMessageHandler("pyspy")
        self.web.Bind(wx.html2.EVT_WEBVIEW_LOADED, self._onWebLoaded)
        self.web.Bind(
            wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self._onWebMessage
            )
        self.web.SetPage(webui.PAGE, "")

        # First set default window properties
        self.__set_properties()

        # Set up Persistence Manager (window position / size)
        self._persistMgr = pm.PersistenceManager.Get()
        self._persistMgr.SetPersistenceFile(config.GUI_CFG_FILE)
        self._persistMgr.RegisterAndRestoreAll(self)

        # Ensure that Persistence Manager saves window location on close
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.__do_layout()

    # ==================================================================
    #  Window setup
    # ==================================================================
    def __set_properties(self):
        self.SetTitle(config.GUI_TITLE)
        self.SetSize((940, 480))
        self.SetMinSize((520, 260))
        icon = wx.Icon()
        icon.CopyFromBitmap(wx.Bitmap(config.ICON_FILE, wx.BITMAP_TYPE_ANY))
        self.SetIcon(icon)
        self._applyFrameBg()
        self._applyTitleBarTheme()
        # Restore transparency
        alpha = self.options.Get("GuiAlpha", 250)
        self.SetTransparent(alpha)

    def _applyFrameBg(self):
        '''Paint the frame (and WebView) background to match the page so
        no light border shows around the embedded browser.'''
        if self.options.Get("DarkMode", True):
            bg = wx.Colour(31, 30, 29)  # --bg warm dark (matches webui.py)
        else:
            bg = wx.Colour(238, 236, 226)  # --bg warm paper
        self.SetBackgroundColour(bg)
        try:
            self.web.SetBackgroundColour(bg)
        except Exception:
            pass

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.web, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()

    # ==================================================================
    #  WebView plumbing
    # ==================================================================
    def _onWebLoaded(self, event=None):
        self._web_ready = True
        self._applyTheme()
        # Restore transparency slider position
        self._js("document.getElementById('alpha').value = " +
                 str(self.options.Get("GuiAlpha", 250)))
        for script in self._pending_js:
            self.web.RunScriptAsync(script)
        self._pending_js = []
        if self._last_payload is not None:
            self._pushPayload(self._last_payload)

    def _js(self, script):
        '''Run JS in the page, queuing until the page has loaded.'''
        if self._web_ready:
            try:
                self.web.RunScriptAsync(script)
            except Exception:
                pass
        else:
            self._pending_js.append(script)

    def _applyTheme(self):
        theme = "light" if not self.options.Get("DarkMode", True) else "dark"
        self._js("window.setTheme(" + json.dumps(theme) + ")")
        self._js("window.setScale(" +
                 str(self.options.Get("FontScale", 1)) + ")")
        self._applyFrameBg()
        self._applyTitleBarTheme()

    def _applyTitleBarTheme(self):
        '''Match the native window title bar to the colour scheme
        (Windows 10/11 immersive dark mode).'''
        if os.name != "nt":
            return
        dark = self.options.Get("DarkMode", True)
        try:
            import ctypes
            value = ctypes.c_int(1 if dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                int(self.GetHandle()), 20, ctypes.byref(value),
                ctypes.sizeof(value)
                )
        except Exception:
            pass
        self._enableDarkMenus(dark)

    def _enableDarkMenus(self, dark):
        '''Theme the native popup and context menus to match the app,
        using the Windows uxtheme "preferred app mode" API (Win 10 1809+).'''
        if os.name != "nt":
            return
        try:
            import ctypes
            uxtheme = ctypes.WinDLL("uxtheme")
            # Ordinal 135: SetPreferredAppMode (0=Default,1=AllowDark,
            # 2=ForceDark,3=ForceLight). Ordinal 136: FlushMenuThemes.
            set_mode = uxtheme[135]
            set_mode.argtypes = [ctypes.c_int]
            set_mode.restype = ctypes.c_int
            flush = uxtheme[136]
            flush.restype = None
            set_mode(2 if dark else 3)
            flush()
        except Exception:
            pass

    def _onWebMessage(self, event):
        try:
            msg = json.loads(event.GetString())
        except (ValueError, TypeError):
            return
        action = msg.get("action")
        if action == "menu":
            self.PopupMenu(self.main_menu)
        elif action == "alpha":
            self._setTransparency(msg.get("value", 250))
        elif action == "zkill":
            self._goToZKill(msg.get("idx"), msg.get("col", ""))
        elif action == "context":
            self._showContextMenu(msg.get("idx"))

    # ==================================================================
    #  Menu helpers
    # ==================================================================
    def _fontScaleMenu(self, lower, upper):
        for scale in range(lower, upper):
            scale = scale / 10
            self.font_sub.AppendRadioItem(wx.ID_ANY, "{:.0%}".format(scale))
            self.font_sub.Bind(
                wx.EVT_MENU,
                lambda evt, scale=scale: self._setFontScale(scale, evt),
                self.font_sub.MenuItems[-1]
                )
            if scale == self.options.Get("FontScale", 1):
                self.font_sub.MenuItems[-1].Check(True)

    def _setFontScale(self, scale, evt=None):
        self.options.Set("FontScale", scale)
        self._js("window.setScale(" + str(scale) + ")")

    def _createShowColMenuItems(self):
        '''Populate the View menu with a show/hide toggle for each
        toggleable column.'''
        self.col_menu_items = [[] for i in self.columns]
        for col in self.columns:
            if not col[4]:  # Not hideable
                continue
            index = col[0]
            options_key = "Show" + col[1]
            menu_name = "Show " + col[6]
            self.col_menu_items[index] = self.view_menu.AppendCheckItem(
                wx.ID_ANY, menu_name
                )
            checked = self.options.Get(options_key, self.columns[index][5])
            self.col_menu_items[index].Check(
                self.options.Get(options_key, checked)
                )
            self.view_menu.Bind(
                wx.EVT_MENU,
                lambda evt, index=index: self._toggleColumn(index, evt),
                self.col_menu_items[index]
                )

    def _toggleColumn(self, index, event=None):
        '''Show or hide a column, then re-render.'''
        self._pushPayload(self._last_payload)

    def _colVisible(self, index):
        '''Whether a data column is currently shown.'''
        item = self.col_menu_items[index]
        if item == []:  # Not toggleable (always shown, e.g. Character)
            return True
        return item.IsChecked()

    # ==================================================================
    #  Rendering
    # ==================================================================
    def appendString(self, org, app):
        if org == "-":
            return app
        else:
            return org + " + " + app

    def updateList(self, outlist, duration=None):
        '''
        Takes the output of `output_list()` in analyze.py (via
        `sortOutlist()`) and builds a payload for the WebView, applying
        ignore lists, faction ignoring and highlight rules.
        '''
        if not outlist:
            self._last_payload = None
            self._js("window.render(null)")
            return
        if len(outlist[0]) < 28:  # Older/incompatible persisted outlist
            return

        npsi_list = self.options.Get("NPSIList", default=[])
        ignored_list = self.options.Get("ignoredList", default=[])
        highlighted_list = self.options.Get("highlightedList", default=[])
        hl_blops = self.options.Get("HlBlops", True)
        hl_hic = self.options.Get("HlHic", True)
        hl_cyno = self.options.Get("HlCyno", True)
        hl_list = self.options.Get("HlList", True)
        hl_cyno_prob = config.CYNO_HL_PERCENTAGE
        ignore_count = 0

        rollup_affil = {}
        rollup_cyno = 0
        rollup_blops = 0

        rows = []
        for rowidx, r in enumerate(outlist):
            ignore = False
            for rec in ignored_list:
                if r[0] == rec[0] or r[3] == rec[0] or r[5] == rec[0]:
                    ignore = True
            for rec in npsi_list:
                if r[0] == rec[0]:
                    ignore = True
            if ignore:
                ignore_count += 1

            # Schema depending on output_list() in analyze.py
            id = r[0]
            faction_id = r[1]
            name = r[2]
            corp_name = r[4]
            alliance_name = r[6]
            faction = r[7] if r[7] is not None else "-"
            allies = "{:,}".format(int(r[8]))

            if alliance_name is not None:
                alliance_display = alliance_name + " (" + allies + ")"
            else:
                alliance_display = "-"

            week_kills = kills = blops_kills = hic_losses = "n.a."
            losses = solo_ratio = sec_status = "n.a."
            if r[13] is not None:
                week_kills = "{:,}".format(int(r[9])) if int(r[9]) > 0 else "-"
                kills = "{:,}".format(int(r[10]))
                blops_kills = "{:,}".format(int(r[11])) if int(r[11]) > 0 else "-"
                hic_losses = "{:,}".format(int(r[12])) if int(r[12]) > 0 else "-"
                losses = "{:,}".format(int(r[13]))
                solo_ratio = "{:.0%}".format(float(r[14]))
                sec_status = "{:.1f}".format(float(r[15]))

            last_loss = last_kill = covert_ship = normal_ship = "n.a."
            avg_attackers = covert_prob = normal_prob = abyssal_losses = "n.a."
            cov_prob_float = norm_prob_float = 0
            if r[16] is not None:
                if int(r[16]) > 0:
                    last_loss = str((
                        datetime.date.today() -
                        datetime.datetime.strptime(str(r[16]), '%Y%m%d').date()
                        ).days) + "d"
                else:
                    last_loss = "n.a."
                if int(r[17]) > 0:
                    last_kill = str((
                        datetime.date.today() -
                        datetime.datetime.strptime(str(r[17]), '%Y%m%d').date()
                        ).days) + "d"
                else:
                    last_kill = "n.a."
                avg_attackers = "{:.1f}".format(float(r[18]))
                cov_prob_float = r[19]
                covert_prob = "{:.0%}".format(cov_prob_float) if cov_prob_float > 0 else "-"
                norm_prob_float = r[20]
                normal_prob = "{:.0%}".format(norm_prob_float) if norm_prob_float > 0 else "-"
                covert_ship = r[21]
                normal_ship = r[22]
                abyssal_losses = r[23] if int(r[23]) > 0 else "-"

            danger = gang = top_ship = active_tz = "n.a."
            danger_val = None
            if r[24] is not None:
                danger_val = int(r[24])
                danger = "{}%".format(int(r[24])) if int(r[24]) > 0 else "-"
                gang = "{}%".format(int(r[25])) if int(r[25]) > 0 else "-"
                top_ship = r[26] if r[26] != "-" else "-"
                active_tz = r[27] if r[27] else "-"

            # Display values, aligned with grid column indices (COL_KEYS)
            out = [
                id, "-", faction_id, name, sec_status, r[3], corp_name,
                r[5], alliance_display, faction, kills, losses, week_kills,
                solo_ratio, blops_kills, hic_losses, last_loss, last_kill,
                avg_attackers, covert_prob, normal_prob, covert_ship,
                normal_ship, abyssal_losses, danger, gang, top_ship, active_tz
                ]

            # Warning flags
            warnings = []
            if hl_blops and r[9] is not None and r[11] > 0:
                warnings.append("BLOPS")
            if hl_hic and r[9] is not None and r[12] > 0:
                warnings.append("HIC")
            if hl_cyno and (
                    cov_prob_float >= hl_cyno_prob or norm_prob_float >= hl_cyno_prob):
                warnings.append("CYNO")

            # Highlight row colour class (precedence: list > cyno > blops/hic)
            cls = ""
            if (hl_blops and r[9] is not None and r[11] > 0) or \
               (hl_hic and r[9] is not None and r[12] > 0):
                cls = "hl1"
            if hl_cyno and (
                    cov_prob_float >= hl_cyno_prob or norm_prob_float >= hl_cyno_prob):
                cls = "hl2"
            if hl_list:
                for entry in highlighted_list:
                    if entry[1] == name or entry[1] == corp_name or \
                            (alliance_name and entry[1] == alliance_name):
                        cls = "hl3"
                        break

            # Faction ignoring hides the row
            hidden = ignore
            if faction_id != 0:
                if config.IGNORED_FACTIONS == 2 and faction_id % 2 == 0:
                    hidden = True
                if config.IGNORED_FACTIONS == 1 and faction_id % 2 != 0:
                    hidden = True

            # Fleet rollup (non-ignored characters only)
            if not ignore:
                affil = r[6] if r[6] is not None else (
                    r[4] if r[4] is not None else "No affiliation")
                rollup_affil[affil] = rollup_affil.get(affil, 0) + 1
                if cov_prob_float >= hl_cyno_prob or norm_prob_float >= hl_cyno_prob:
                    rollup_cyno += 1
                if r[9] is not None and r[11] > 0:
                    rollup_blops += 1

            # Build display + sort dicts keyed by column key
            d = {}
            s = {}
            for gi in range(len(COL_KEYS)):
                if gi in HIDDEN_COLS:
                    continue
                key = COL_KEYS[gi]
                d[key] = str(out[gi])
                s[key] = self._sortValue(gi, key, r, out[gi])

            rows.append({
                "idx": rowidx,
                "charId": id,
                "cls": cls,
                "hidden": hidden,
                "warnings": warnings,
                "dangerVal": danger_val,
                "d": d,
                "s": s,
                })

        pilots = len(outlist) - ignore_count
        top_affils = sorted(
            rollup_affil.items(), key=lambda kv: kv[1], reverse=True
            )
        summary = {
            "pilots": pilots,
            "ignored": ignore_count,
            "affils": top_affils[:3],
            "more": max(0, len(top_affils) - 3),
            "cyno": rollup_cyno,
            "blops": rollup_blops,
            }

        columns = []
        for col in self.columns:
            gi = col[0]
            if gi in HIDDEN_COLS:
                continue
            key = COL_KEYS[gi]
            columns.append({
                "key": key,
                "label": col[1],
                "num": col[2] == wx.ALIGN_RIGHT,
                "visible": self._colVisible(gi),
                })

        payload = {"columns": columns, "rows": rows, "summary": summary}
        self._pushPayload(payload)

        if duration is not None:
            statusmsg.push_status(
                str(pilots) + " characters analysed, in " + str(duration) +
                " seconds (" + str(ignore_count) + " ignored). Double click "
                "a pilot to open zKillboard."
                )
        else:
            statusmsg.push_status(
                str(pilots) + " characters analysed (" + str(ignore_count) +
                " ignored). Double click a pilot to open zKillboard."
                )

    def _sortValue(self, grid_idx, key, r, display):
        '''Compute a sortable value for a cell.'''
        if key == "danger":
            return r[24] if r[24] is not None else -1
        if key == "gang":
            return r[25] if r[25] is not None else -1
        if key == "lastloss" or key == "lastkill":
            raw = r[16] if key == "lastloss" else r[17]
            if raw is None or int(raw) <= 0:
                return -1
            return (
                datetime.date.today() -
                datetime.datetime.strptime(str(raw), '%Y%m%d').date()
                ).days
        if key in NUMERIC_KEYS:
            outidx = None
            for col in self.columns:
                if col[0] == grid_idx and len(col) > 7:
                    outidx = col[7]
                    break
            if outidx is not None and r[outidx] is not None:
                try:
                    return float(r[outidx])
                except (ValueError, TypeError):
                    return -1
            return -1
        return str(display).lower()

    def _pushPayload(self, payload):
        if payload is None:
            return
        self._last_payload = payload
        self._js("window.render(" + json.dumps(payload) + ")")

    def updateStatusbar(self, msg):
        if isinstance(msg, str):
            self._js("window.setStatus(" + json.dumps(msg) + ")")
            # Kill feed / watchlist alerts also raise a snackbar
            if msg.startswith("KILL IN ") or msg.startswith("WATCHLIST"):
                self._js("window.snackbar(" + json.dumps(msg) + ")")

    def updateLocation(self, system_name):
        try:
            self.SetTitle(config.GUI_TITLE + "  |  " + str(system_name))
            self._js("window.setLocation(" + json.dumps(str(system_name)) + ")")
        except RuntimeError:
            pass

    # ==================================================================
    #  Interactions from the WebView
    # ==================================================================
    def _setTransparency(self, value):
        alpha = int(value)
        self.SetTransparent(alpha)
        self.options.Set("GuiAlpha", alpha)

    def _goToZKill(self, rowidx, colkey=""):
        if rowidx is None:
            return
        outlist = self.options.Get("outlist")
        if not outlist or rowidx >= len(outlist):
            return
        row = outlist[rowidx]
        url = "https://zkillboard.com/"

        if self.options.Get("ZkillMode", False):
            if colkey == "corporation":
                url = url + "corporation/" + str(row[3]) + "/"
            elif colkey == "alliance":
                if row[5] is not None:
                    url = url + "alliance/" + str(row[5]) + "/"
            elif colkey == "faction":
                if row[1] is not None:
                    url = url + "faction/" + str(row[1]) + "/"
            elif colkey not in ("name", ""):
                url = url + "character/" + str(row[0]) + "/"
                modifiers = {
                    "kills": "kills/", "losses": "losses/", "solo": "solo/",
                    "blops": "group/898/", "hics": "group/894/",
                    "abyssal": "abyssal/",
                    }
                if colkey in modifiers:
                    url = url + modifiers[colkey]

        if url == "https://zkillboard.com/":
            url = url + "character/" + str(row[0]) + "/"
        webbrowser.open_new_tab(url)

    def _showContextMenu(self, rowidx):
        '''Right-click menu to ignore / highlight the pilot, corp or
        alliance in the given row.'''
        outlist = self.options.Get("outlist")
        if not outlist or rowidx is None or rowidx >= len(outlist):
            return
        r = outlist[rowidx]
        character_id, character_name = r[0], r[2]
        corp_id, corp_name = r[3], r[4]
        alliance_id, alliance_name = r[5], r[6]

        def OnIgnore(id, name, type, e=None):
            ignored_list = self.options.Get("ignoredList", default=[])
            ignored_list.append([id, name, type])
            self.options.Set("ignoredList", ignored_list)
            self.updateList(self.options.Get("outlist", None))

        def OnHighlight(id, name, type, e=None):
            highlighted_list = self.options.Get("highlightedList", default=[])
            if [id, name, type] not in highlighted_list:
                highlighted_list.append([id, name, type])
            self.options.Set("highlightedList", highlighted_list)
            self.updateList(self.options.Get("outlist", None))

        def OnDeHighlight(id, name, type, e=None):
            highlighted_list = self.options.Get("highlightedList", default=[])
            highlighted_list.remove([id, name, type])
            self.options.Set("highlightedList", highlighted_list)
            self.updateList(self.options.Get("outlist", None))

        highlighted_list = self.options.Get("highlightedList", default=[])
        menu = wx.Menu()

        item = menu.Append(wx.ID_ANY, "Ignore character '" + character_name + "'")
        menu.Bind(wx.EVT_MENU, lambda e, i=character_id, n=character_name: OnIgnore(i, n, "Character", e), item)
        item = menu.Append(wx.ID_ANY, "Ignore corporation: '" + corp_name + "'")
        menu.Bind(wx.EVT_MENU, lambda e, i=corp_id, n=corp_name: OnIgnore(i, n, "Corporation", e), item)
        if alliance_name is not None:
            item = menu.Append(wx.ID_ANY, "Ignore alliance: '" + alliance_name + "'")
            menu.Bind(wx.EVT_MENU, lambda e, i=alliance_id, n=alliance_name: OnIgnore(i, n, "Alliance", e), item)

        menu.AppendSeparator()

        hl_char = hl_corp = hl_alliance = False
        for entry in highlighted_list:
            if entry[1] == character_name:
                hl_char = True
            if entry[1] == corp_name:
                hl_corp = True
            if alliance_name is not None and entry[1] == alliance_name:
                hl_alliance = True

        if not hl_char:
            item = menu.Append(wx.ID_ANY, "Highlight character '" + character_name + "'")
            menu.Bind(wx.EVT_MENU, lambda e, i=character_id, n=character_name: OnHighlight(i, n, "Character", e), item)
        else:
            item = menu.Append(wx.ID_ANY, "Stop highlighting character '" + character_name + "'")
            menu.Bind(wx.EVT_MENU, lambda e, i=character_id, n=character_name: OnDeHighlight(i, n, "Character", e), item)

        if not hl_corp:
            item = menu.Append(wx.ID_ANY, "Highlight corporation '" + corp_name + "'")
            menu.Bind(wx.EVT_MENU, lambda e, i=corp_id, n=corp_name: OnHighlight(i, n, "Corporation", e), item)
        else:
            item = menu.Append(wx.ID_ANY, "Stop highlighting corporation '" + corp_name + "'")
            menu.Bind(wx.EVT_MENU, lambda e, i=corp_id, n=corp_name: OnDeHighlight(i, n, "Corporation", e), item)

        if alliance_name is not None:
            if not hl_alliance:
                item = menu.Append(wx.ID_ANY, "Highlight alliance: '" + alliance_name + "'")
                menu.Bind(wx.EVT_MENU, lambda e, i=alliance_id, n=alliance_name: OnHighlight(i, n, "Alliance", e), item)
            else:
                item = menu.Append(wx.ID_ANY, "Stop highlighting alliance: '" + alliance_name + "'")
                menu.Bind(wx.EVT_MENU, lambda e, i=alliance_id, n=alliance_name: OnDeHighlight(i, n, "Alliance", e), item)

        self.PopupMenu(menu)
        menu.Destroy()

    def sortOutlist(self, event=None, outlist=None, duration=None):
        '''Stores the outlist and renders it. Sorting itself now happens
        in the WebView; this keeps compatibility with callers.'''
        if outlist is None:
            outlist = self.options.Get("outlist", False)
        self.options.Set("outlist", outlist)
        self.updateList(outlist, duration=duration)

    def updateAlert(self, latest_ver, cur_ver):
        self.ToggleWindowStyle(wx.STAY_ON_TOP)
        msgbox = wx.MessageBox(
            "PySpy " + str(latest_ver) + " is now available. You are running " +
            str(cur_ver) + ". Would you like to update now?",
            'Update Available',
            wx.YES_NO | wx.YES_DEFAULT | wx.ICON_INFORMATION | wx.STAY_ON_TOP
            )
        if msgbox == wx.YES:
            webbrowser.open_new_tab(
                "https://github.com/Eve-PySpy/PySpy/releases/latest"
                )
        self.ToggleWindowStyle(wx.STAY_ON_TOP)

    # ==================================================================
    #  Option toggles / dialogs
    # ==================================================================
    def _toggleIgnoreFactions(self, e):
        if self.ignore_galmin.IsChecked():
            config.IGNORED_FACTIONS = 2
            self.options.Set("IgnoredFactions", 2)
        if self.ignore_amacal.IsChecked():
            config.IGNORED_FACTIONS = 1
            self.options.Set("IgnoredFactions", 1)
        if self.ignore_none.IsChecked():
            config.IGNORED_FACTIONS = None
            self.options.Set("IgnoredFactions", 0)
        self.updateList(self.options.Get("outlist", None))

    def _toggleHighlighting(self, e):
        self.options.Set("HlBlops", self.hl_blops.IsChecked())
        self.options.Set("HlCyno", self.hl_cyno.IsChecked())
        self.options.Set("HlHic", self.hl_hic.IsChecked())
        self.options.Set("HlList", self.hl_list.IsChecked())
        self.updateList(self.options.Get("outlist", None))

    def _toggleStayOnTop(self, evt=None):
        self.options.Set("StayOnTop", self.stay_ontop.IsChecked())
        self.ToggleWindowStyle(wx.STAY_ON_TOP)

    def _accelDarkMode(self, event=None):
        self.dark_mode.Check(not self.dark_mode.IsChecked())
        self._toggleDarkMode()

    def _accelStayOnTop(self, event=None):
        self.stay_ontop.Check(not self.stay_ontop.IsChecked())
        self._toggleStayOnTop()

    def _toggleDarkMode(self, evt=None):
        self.options.Set("DarkMode", self.dark_mode.IsChecked())
        self.use_dm = self.dark_mode.IsChecked()
        self._applyTheme()

    def _toggleChatWatch(self, event=None):
        checked = self.chat_watch.IsChecked()
        self.options.Set("ChatWatch", checked)
        if checked:
            if chatwatch.find_chatlog_dir() is None:
                wx.MessageBox(
                    'No EVE chat logs found. Please enable "Log Chat to '
                    'File" in the EVE client settings (Settings > Chat) '
                    'and restart the EVE client.\n\nPySpy will start '
                    'watching automatically once logs appear.',
                    'EVE Chat Logs Not Found',
                    wx.OK | wx.ICON_INFORMATION
                    )
            elif not self.options.Get("IntelChannels", ""):
                self._setIntelChannels()

    def _setIntelChannels(self, event=None):
        dlg = wx.TextEntryDialog(
            self,
            "Enter the names of the intel channels to watch,\n"
            "separated by commas (channel names as shown in EVE):",
            "Intel Channels",
            self.options.Get("IntelChannels", "")
            )
        if dlg.ShowModal() == wx.ID_OK:
            self.options.Set("IntelChannels", dlg.GetValue())
        dlg.Destroy()

    def _toggleKillFeed(self, event=None):
        self.options.Set("KillFeed", self.kill_feed.IsChecked())

    def _openAboutDialog(self, evt=None):
        for c in self.GetChildren():
            if c.GetName() == "AboutDialog":
                c.Raise()
                return
        aboutdialog.showAboutBox(self)

    def _openIgnoreDialog(self, evt=None):
        for c in self.GetChildren():
            if c.GetName() == "IgnoreDialog":
                c.Raise()
                return
        ignoredialog.showIgnoreDialog(self)

    def _openHightlightDialog(self, evt=None):
        for c in self.GetChildren():
            if c.GetName() == "HighlightDialog":
                c.Raise()
                return
        highlightdialog.showHighlightDialog(self)

    def _showNpsiDialog(self, evt=None):
        dialog = wx.MessageBox(
            "Do you want to ignore all currently shown characters? "
            "You can undo this under `Options > Clear NPSI Ignore List`.",
            "NPSI Ignore List",
            wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION
            )
        if dialog == 2:
            npsi_list = []
            outlist = self.options.Get("outlist", None)
            if outlist is None:
                return
            for r in outlist:
                npsi_list.append([r[0]])
            self.options.Set("NPSIList", npsi_list)
            self.updateList(outlist)

    def _clearNpsiList(self, evt=None):
        dialog = wx.MessageBox(
            "Would you like to clear the current NPSI fleet ignore list?",
            "NPSI Ignore List",
            wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION
            )
        if dialog == 2:
            self.options.Set("NPSIList", [])
            self.updateList(self.options.Get("outlist", None))

    def _toggleZkillMode(self, evt=None):
        self.options.Set("ZkillMode", self.zkill_mode.IsChecked())
        self.use_adv_zkill = self.zkill_mode.IsChecked()

    def OnClose(self, event=None):
        self._persistMgr.SaveAndUnregister()
        self.options.Set("HlBlops", self.hl_blops.IsChecked())
        self.options.Set("HlCyno", self.hl_cyno.IsChecked())
        self.options.Set("IgnoreGalMin", self.ignore_galmin.IsChecked())
        self.options.Set("IgnoreAmaCal", self.ignore_amacal.IsChecked())
        self.options.Set("IgnoreNone", self.ignore_none.IsChecked())
        self.options.Set("StayOnTop", self.stay_ontop.IsChecked())
        self.options.Set("DarkMode", self.dark_mode.IsChecked())
        # Save which columns are shown
        for col in self.columns:
            if col[4]:
                self.options.Set(
                    "Show" + col[1], self._colVisible(col[0])
                    )
        self.options.Set("outlist", None)
        self.options.Set("NPSIList", [])
        self.options.Save()
        event.Skip() if event else False

    def OnQuit(self, e):
        self.Close()

    def clear_character_cache(self, e):
        conn, cur = db.connect_persistent_db()
        cur.execute('''DELETE FROM characters''')
        conn.commit()
        conn.close()
        statusmsg.push_status("Cleared character cache")


class App(wx.App):
    def OnInit(self):
        self.PySpy = Frame(None, wx.ID_ANY, "")
        self.SetTopWindow(self.PySpy)
        self.PySpy.Show()
        return True
