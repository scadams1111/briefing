"""Drive the KOReader plugin with stand-in modules: tap every button of every puzzle, then reveal/solve each."""
import json, os, sys, datetime
from lupa import luajit21 as lj
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lua = lj.LuaRuntime(unpack_returned_tuples=True)

def tl(x):
    if isinstance(x, dict): return lua.table_from({k: tl(v) for k, v in x.items()})
    if isinstance(x, list): return lua.table_from([tl(v) for v in x])
    return x
lua.globals().JSON_DECODE = lambda t: tl(json.loads(t))
lua.execute(f"package.path = '{ROOT}/briefinggames.koplugin/?.lua;{ROOT}/tests/?.lua;' .. package.path")
lua.execute(open(f"{ROOT}/tests/stubs.lua").read())
data = json.load(open(sys.argv[1]))
data["date"] = lua.eval('os.date("%Y-%m-%d")')
os.makedirs("/tmp/kodata/briefinggames", exist_ok=True)
json.dump(data, open("/tmp/kodata/briefinggames/today.json", "w"))

driver = lua.execute(r"""
local P = require("main")
local inst = P:new{ ui = { menu = { registerToMainMenu = function() end } } }
local function top() return SHOWN[#SHOWN] end
local function tables(b)
  local out = {}
  for _, w in ipairs(b[1][1]) do if w.buttons then out[#out + 1] = w end end
  return out
end
local function settle(depth)
  depth = depth or 0
  local t = top()
  if t and t.buttons and t.title and not t.game and depth < 6 then -- a ButtonDialog: pick the first option
    t.buttons[1][1].callback(); settle(depth + 1)
  end
end
local function all_buttons(b)
  local out = {}
  for _, bt in ipairs(tables(b)) do for _, row in ipairs(bt.buttons) do for _, btn in ipairs(row) do out[#out + 1] = btn end end end
  return out
end
local function press(b, text)
  for _, btn in ipairs(all_buttons(b)) do if btn.text:find(text, 1, true) then btn.callback(); settle(); return true end end
  error("no button " .. text)
end
return function()
  inst:open()
  local menu = top()
  local results = {}
  local items = all_buttons(menu)
  for _, item in ipairs(items) do
    if item.text ~= " " and not item.text:find("Check for new") then
      item.callback()
      local b = top()
      assert(b.game, "game screen didn't open for " .. item.text)
      -- tap everything twice over
      for pass = 1, 2 do
        local n = #all_buttons(b)
        for i = 1, n do
          local btns = all_buttons(top())
          local btn = btns[i]
          if btn and not btn.text:find("Reveal") and not btn.text:find("Start over") and not btn.text:find("Clear") then
            NEXT_INPUT = "A"
            btn.callback(); settle()
            while top() ~= b and not top().game do UIManager_close_top() end
          end
        end
      end
      -- reveal / solve
      local ok = pcall(press, b, "Reveal")
      results[#results + 1] = item.text .. " | " .. tostring(b.game.status()) .. (ok and "" or " (no reveal)")
      b:onClose()
    end
  end
  return results, inst
end
""")
lua.globals().UIManager_close_top = lambda: lua.execute("table.remove(SHOWN)")
res, inst = driver()
for r in res.values(): print(r)
print("solved flags:", sorted(dict(inst.settings.data.days[data["date"]].solved).keys()))
