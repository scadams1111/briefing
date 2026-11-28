--[[ Briefing puzzles for KOReader.
Downloads today's puzzles from your Briefing site and lets you solve them by tapping.
Tools menu → Briefing puzzles. Progress is saved on the device. ]]
local Blitbuffer = require("ffi/blitbuffer")
local ButtonDialog = require("ui/widget/buttondialog")
local ButtonTable = require("ui/widget/buttontable")
local ConfirmBox = require("ui/widget/confirmbox")
local DataStorage = require("datastorage")
local Device = require("device")
local Font = require("ui/font")
local FrameContainer = require("ui/widget/container/framecontainer")
local Geom = require("ui/geometry")
local InfoMessage = require("ui/widget/infomessage")
local InputContainer = require("ui/widget/container/inputcontainer")
local InputDialog = require("ui/widget/inputdialog")
local JSON = require("json")
local LuaSettings = require("luasettings")
local NetworkMgr = require("ui/network/manager")
local Size = require("ui/size")
local TextBoxWidget = require("ui/widget/textboxwidget")
local TextViewer = require("ui/widget/textviewer")
local TitleBar = require("ui/widget/titlebar")
local UIManager = require("ui/uimanager")
local VerticalGroup = require("ui/widget/verticalgroup")
local VerticalSpan = require("ui/widget/verticalspan")
local WidgetContainer = require("ui/widget/container/widgetcontainer")
local http = require("socket.http")
local lfs = require("libs/libkoreader-lfs")
local logger = require("logger")
local ltn12 = require("ltn12")
local socket = require("socket")
local socketutil = require("socketutil")
local _ = require("gettext")
local Screen = Device.screen

local Games = require("bgames_games")

local SOURCE = "https://scadams1111.github.io/briefing/games/today.json"
local DIR = DataStorage:getDataDir() .. "/briefinggames"
local CACHE = DIR .. "/today.json"

local COLORS = {
    light = Blitbuffer.COLOR_GRAY_E,
    mid = Blitbuffer.COLOR_LIGHT_GRAY,
    dark = Blitbuffer.COLOR_DARK_GRAY,
}
local SHADES = { nil, Blitbuffer.COLOR_GRAY_E, Blitbuffer.COLOR_LIGHT_GRAY, Blitbuffer.COLOR_GRAY_B }

-- ── a full-screen page: title, optional text, a grid of buttons, a row of controls ──
local Board = InputContainer:extend{
    game = nil,
    on_close = nil,
}

function Board:init()
    self.dimen = Geom:new{ x = 0, y = 0, w = Screen:getWidth(), h = Screen:getHeight() }
    if Device:hasKeys() then
        self.key_events.Close = { { Device.input.group.Back } }
    end
    self.covers_fullscreen = true
    self.game.refresh = function() self:refresh() end
    self:build()
end

function Board:build()
    local w = Screen:getWidth()
    local g = self.game
    local inner = math.floor(w * 0.94)
    local vg = VerticalGroup:new{ align = "center" }
    table.insert(vg, TitleBar:new{
        width = w,
        fullscreen = true,
        title = g.title,
        subtitle = g.status and g.status() or nil,
        subtitle_multilines = true,
        with_bottom_line = true,
        close_callback = function() self:onClose() end,
        show_parent = self,
    })
    local info = g.info and g.info()
    if info and info ~= "" then
        table.insert(vg, VerticalSpan:new{ width = Size.span.vertical_large })
        table.insert(vg, TextBoxWidget:new{
            text = info,
            face = Font:getFace("x_smallinfofont"),
            width = inner,
        })
    end
    local rows = g.rows and g.rows(inner)
    if rows and #rows > 0 then
        table.insert(vg, VerticalSpan:new{ width = Size.span.vertical_large })
        table.insert(vg, ButtonTable:new{ width = inner, buttons = rows, zero_sep = true, show_parent = self })
    end
    local ctl = g.controls and g.controls()
    if ctl and #ctl > 0 then
        table.insert(vg, VerticalSpan:new{ width = Size.span.vertical_large * 2 })
        table.insert(vg, ButtonTable:new{ width = inner, buttons = ctl, show_parent = self })
    end
    self[1] = FrameContainer:new{
        width = w,
        height = Screen:getHeight(),
        background = Blitbuffer.COLOR_WHITE,
        bordersize = 0,
        padding = 0,
        vg,
    }
end

function Board:refresh()
    if self.on_change then self.on_change() end
    self:build()
    UIManager:setDirty(self, "ui")
end

function Board:onClose()
    if self.on_change then self.on_change() end
    UIManager:close(self, "flashui")
    if self.on_close then self.on_close() end
    return true
end

-- ── the plugin ──
local BriefingGames = WidgetContainer:extend{
    name = "briefinggames",
    is_doc_only = false,
}

function BriefingGames:init()
    self.settings = LuaSettings:open(DataStorage:getSettingsDir() .. "/briefinggames.lua")
    self.ui.menu:registerToMainMenu(self)
end

function BriefingGames:addToMainMenu(menu_items)
    menu_items.briefing_puzzles = {
        text = _("Briefing puzzles"),
        sorting_hint = "tools",
        callback = function() self:open() end,
    }
end

function BriefingGames:loadCached()
    local f = io.open(CACHE, "r")
    if not f then return nil end
    local text = f:read("*a")
    f:close()
    local ok, data = pcall(JSON.decode, text)
    if ok and type(data) == "table" and data.date then return data end
    return nil
end

function BriefingGames:download()
    if lfs.attributes(DIR, "mode") ~= "directory" then lfs.mkdir(DIR) end
    local sink = {}
    socketutil:set_timeout(socketutil.LARGE_BLOCK_TIMEOUT, socketutil.LARGE_TOTAL_TIMEOUT)
    local code = socket.skip(1, http.request{
        url = SOURCE .. "?t=" .. os.time(),
        method = "GET",
        sink = ltn12.sink.table(sink),
    })
    socketutil:reset_timeout()
    if code ~= 200 then
        logger.warn("BriefingGames: download failed", code)
        return false
    end
    local text = table.concat(sink)
    local ok, data = pcall(JSON.decode, text)
    if not ok or type(data) ~= "table" or not data.date then return false end
    local f = io.open(CACHE, "w")
    if f then f:write(text); f:close() end
    return true
end

function BriefingGames:open()
    local data = self:loadCached()
    local today = os.date("%Y-%m-%d")
    if data and data.date == today then return self:showMenu(data) end
    NetworkMgr:runWhenOnline(function()
        UIManager:show(InfoMessage:new{ text = _("Getting today's puzzles…"), timeout = 1 })
        UIManager:scheduleIn(0.3, function()
            local got = self:download()
            local fresh = self:loadCached()
            if fresh then
                if not got then
                    UIManager:show(InfoMessage:new{ text = _("Couldn't download new puzzles. Showing the last ones saved."), timeout = 3 })
                end
                self:showMenu(fresh)
            else
                UIManager:show(InfoMessage:new{ text = _("Couldn't download the puzzles. Check Wi-Fi and try again.") })
            end
        end)
    end)
end

function BriefingGames:stateFor(date)
    local all = self.settings:readSetting("days", {})
    if not all[date] then
        all[date] = { solved = {} }
        -- keep two weeks of progress
        local dates = {}
        for d in pairs(all) do dates[#dates + 1] = d end
        table.sort(dates)
        for i = 1, #dates - 14 do all[dates[i]] = nil end
        self.settings:saveSetting("days", all)
    end
    return all[date]
end

function BriefingGames:helpers(day)
    local H = { colors = COLORS }
    function H.cell(text, cb, o)
        o = o or {}
        return {
            text = text,
            callback = cb or function() end,
            height = o.height,
            font_size = o.font_size or 20,
            font_bold = o.font_bold ~= false,
            background = o.background,
            align = o.align,
        }
    end
    function H.shade(i) return SHADES[(i % #SHADES) + 1] end
    function H.info(text) UIManager:show(InfoMessage:new{ text = text, timeout = 3 }) end
    function H.view(title, text) UIManager:show(TextViewer:new{ title = title, text = text }) end
    function H.confirm(text, cb) UIManager:show(ConfirmBox:new{ text = text, ok_text = _("Yes"), ok_callback = cb }) end
    function H.choose(title, opts)
        local dlg
        local buttons = {}
        for _, o in ipairs(opts) do
            buttons[#buttons + 1] = { { text = o.text, align = "left", callback = function()
                UIManager:close(dlg)
                o.callback()
            end } }
        end
        buttons[#buttons + 1] = { { text = _("Cancel"), callback = function() UIManager:close(dlg) end } }
        dlg = ButtonDialog:new{ title = title, buttons = buttons }
        UIManager:show(dlg)
    end
    function H.input(title, description, initial, cb)
        local dlg
        dlg = InputDialog:new{
            title = title,
            description = description,
            input = initial or "",
            buttons = { {
                { text = _("Cancel"), id = "close", callback = function() UIManager:close(dlg) end },
                { text = _("OK"), is_enter_default = true, callback = function()
                    local t = dlg:getInputText()
                    UIManager:close(dlg)
                    cb(t)
                end },
            } },
        }
        UIManager:show(dlg)
        dlg:onShowKeyboard()
    end
    function H.won(name)
        if not day.solved[name] then
            day.solved[name] = true
            self.settings:flush()
        end
    end
    return H
end

function BriefingGames:showMenu(data)
    local day = self:stateFor(data.date)
    local H = self:helpers(day)
    local menu = { title = _("Briefing puzzles") }
    local board
    function menu.status()
        local n, total = 0, 0
        for _, it in ipairs(Games.order) do
            if data[it[1]] then
                total = total + 1
                if day.solved[it[1]] then n = n + 1 end
            end
        end
        return data.date .. " · " .. n .. " of " .. total .. " solved"
    end
    function menu.rows(width)
        local rows, row = {}, {}
        for _, it in ipairs(Games.order) do
            local name, label = it[1], it[2]
            if data[name] and Games[name] then
                row[#row + 1] = H.cell((day.solved[name] and "✓ " or "") .. label, function()
                    day[name] = day[name] or {}
                    local game = Games[name](data[name], day[name], H)
                    local b = Board:new{ game = game }
                    b.on_change = function() self.settings:flush() end
                    b.on_close = function() menu.refresh() end
                    UIManager:show(b)
                end, { height = math.floor(width / 7), font_size = 20 })
                if #row == 2 then rows[#rows + 1] = row; row = {} end
            end
        end
        if #row > 0 then row[#row + 1] = H.cell(" ", nil); rows[#rows + 1] = row end
        return rows
    end
    function menu.controls()
        return { { H.cell(_("Check for new puzzles"), function()
            UIManager:close(board)
            NetworkMgr:runWhenOnline(function()
                if self:download() then self:showMenu(self:loadCached())
                else UIManager:show(InfoMessage:new{ text = _("Couldn't download the puzzles.") }) end
            end)
        end, { font_bold = false, font_size = 16 }) } }
    end
    board = Board:new{ game = menu }
    board.on_change = function() self.settings:flush() end
    UIManager:show(board)
end

function BriefingGames:onFlushSettings()
    if self.settings then self.settings:flush() end
end

return BriefingGames
