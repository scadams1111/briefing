-- Minimal stand-ins for KOReader modules, enough to drive the plugin's screens off-device.
local Class = {}
function Class:extend(o) o = o or {}; setmetatable(o, { __index = self }); return o end
function Class:new(o) o = o or {}; setmetatable(o, { __index = self }); if o.key_events == nil then o.key_events = {} end
    if o.init then o:init() end; return o end
local function mod(name, v) package.preload[name] = function() return v end end
SHOWN = {}
local UIManager = {}
function UIManager:show(w) SHOWN[#SHOWN + 1] = w; if w._autook then w._autook() end end
function UIManager:close(w) for i = #SHOWN, 1, -1 do if SHOWN[i] == w then table.remove(SHOWN, i) end end end
function UIManager:setDirty() end
function UIManager:scheduleIn(_, f) f() end
mod("ui/uimanager", UIManager)
mod("ffi/blitbuffer", { COLOR_WHITE = 0, COLOR_BLACK = 1, COLOR_GRAY_E = 2, COLOR_LIGHT_GRAY = 3, COLOR_DARK_GRAY = 4, COLOR_GRAY_B = 5 })
local BT = Class:extend{}
function BT:init()
    for _, row in ipairs(self.buttons) do
        for _, b in ipairs(row) do
            assert(type(b.text) == "string", "button text must be a string, got " .. type(b.text))
            assert(type(b.callback) == "function", "button without callback: " .. tostring(b.text))
            assert(b.height == nil or (type(b.height) == "number" and b.height > 0), "bad height")
        end
    end
    assert(self.width and self.width > 0)
end
mod("ui/widget/buttontable", BT)
local BD = Class:extend{}
mod("ui/widget/buttondialog", BD)
local CB = Class:extend{}
function CB:init() self._autook = function() self.ok_callback() end end
mod("ui/widget/confirmbox", CB)
mod("datastorage", { getDataDir = function() return "/tmp/kodata" end, getSettingsDir = function() return "/tmp/kodata" end })
mod("device", { screen = { getWidth = function() return 1264 end, getHeight = function() return 1680 end }, hasKeys = function() return true end,
    input = { group = { Back = "Back" } } })
mod("ui/font", { getFace = function() return {} end })
mod("ui/widget/container/framecontainer", Class:extend{})
mod("ui/geometry", Class:extend{})
local IM = Class:extend{}
function IM:init() LAST_INFO = self.text end
mod("ui/widget/infomessage", IM)
mod("ui/widget/container/inputcontainer", Class:extend{})
local ID = Class:extend{}
function ID:getInputText() return NEXT_INPUT or "" end
function ID:onShowKeyboard() end
function ID:init() self._autook = function() for _, b in ipairs(self.buttons[1]) do if b.is_enter_default then b.callback() end end end end
mod("ui/widget/inputdialog", ID)
mod("json", { decode = function(t) return JSON_DECODE(t) end })
local LS = Class:extend{}
function LS:open() return LS:new{ data = {} } end
function LS:readSetting(k, d) if self.data[k] == nil then self.data[k] = d end return self.data[k] end
function LS:saveSetting(k, v) self.data[k] = v end
function LS:flush() FLUSHES = (FLUSHES or 0) + 1 end
mod("luasettings", LS)
mod("ui/network/manager", { runWhenOnline = function(_, f) f() end })
mod("ui/size", { span = { vertical_large = 10, vertical_default = 5 }, padding = { large = 10 } })
mod("ui/widget/textboxwidget", Class:extend{ init = function(self) assert(type(self.text) == "string") end })
local TV = Class:extend{}
function TV:init() assert(type(self.text) == "string" and type(self.title) == "string"); LAST_VIEW = self.text end
mod("ui/widget/textviewer", TV)
mod("ui/widget/titlebar", Class:extend{ init = function(self) assert(type(self.title) == "string"); assert(self.subtitle == nil or type(self.subtitle) == "string") end })
mod("ui/widget/verticalgroup", Class:extend{})
mod("ui/widget/verticalspan", Class:extend{})
mod("ui/widget/container/widgetcontainer", Class:extend{})
mod("socket.http", { request = function() return 1, 500 end })
mod("libs/libkoreader-lfs", { attributes = function() return "directory" end, mkdir = function() end })
mod("logger", { warn = function() end, dbg = function() end })
mod("ltn12", { sink = { table = function() end } })
mod("socket", { skip = function(_, ...) return select(1, ...) end })
mod("socketutil", { set_timeout = function() end, reset_timeout = function() end, LARGE_BLOCK_TIMEOUT = 1, LARGE_TOTAL_TIMEOUT = 1 })
mod("gettext", function(s) return s end)
