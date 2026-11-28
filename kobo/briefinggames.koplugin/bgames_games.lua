--[[ The twelve puzzles as screens. Each maker returns a table:
  title, status() -> subtitle, info() -> text above the grid, rows(width) -> ButtonTable rows,
  controls() -> ButtonTable rows. H (helpers) and S (this puzzle's saved state) come from main.lua. ]]
local L = require("bgames_logic")
local key = L.key

local M = {}

local function letters(s)
    local t = {}
    for i = 1, #s do t[#t + 1] = s:sub(i, i) end
    return t
end

local function join(t, sep)
    local out = {}
    for _, v in ipairs(t) do out[#out + 1] = tostring(v) end
    return table.concat(out, sep or " ")
end

-- ── crossword ──
function M.crossword(x, S, H)
    S.cells = S.cells or {}
    local g = { title = "Crossword" }
    local function clue_list()
        local a, d = { "ACROSS" }, { "", "DOWN" }
        for _, en in ipairs(x.entries) do
            local line = en.n .. ". " .. en.clue .. " (" .. #en.answer .. ")"
            if en.d == "A" then a[#a + 1] = line else d[#d + 1] = line end
        end
        for _, l in ipairs(d) do a[#a + 1] = l end
        return table.concat(a, "\n")
    end
    local function answer(i)
        local en = x.entries[i]
        H.input((en.d == "A" and "Across " or "Down ") .. en.n, en.clue .. " (" .. #en.answer .. ")\n" ..
            L.xw_pattern(x, S.cells, i), "", function(text)
                L.xw_fill(x, S.cells, i, text)
                g.refresh()
            end)
    end
    function g.status()
        if L.xw_solved(x, S.cells) then H.won("crossword"); return "Solved!" end
        return (x.theme or "") .. " · tap a square to answer"
    end
    function g.rows(width)
        local nums = {}
        for _, en in ipairs(x.entries) do nums[key(en.r, en.c)] = en.n end
        local cw = math.floor(width / x.cols)
        local rows = {}
        for r = 0, x.rows - 1 do
            local row = {}
            for c = 0, x.cols - 1 do
                if L.xw_sol(x, r, c) == "." then
                    row[#row + 1] = H.cell(" ", nil, { height = cw, background = H.colors.dark })
                else
                    local v = S.cells[key(r, c)]
                    row[#row + 1] = H.cell(v or (nums[key(r, c)] and tostring(nums[key(r, c)]) or " "), function()
                        local here = L.xw_at(x, r, c)
                        if #here == 1 then return answer(here[1]) end
                        local opts = {}
                        for _, i in ipairs(here) do
                            local en = x.entries[i]
                            opts[#opts + 1] = { text = (en.d == "A" and "Across " or "Down ") .. en.n .. ": " .. en.clue,
                                                callback = function() answer(i) end }
                        end
                        H.choose("Which clue?", opts)
                    end, { height = cw, font_size = v and 22 or 11, font_bold = v ~= nil })
                end
            end
            rows[#rows + 1] = row
        end
        return rows
    end
    function g.controls()
        return { {
            H.cell("Clues", function() H.view("Clues", clue_list()) end),
            H.cell("Check", function() local n = L.xw_wrong(x, S.cells); H.info(n > 0 and (n .. " wrong letters cleared.") or "No mistakes so far."); g.refresh() end),
            H.cell("Reveal", function() H.confirm("Reveal the whole crossword?", function()
                for i, en in ipairs(x.entries) do L.xw_fill(x, S.cells, i, en.answer) end; g.refresh() end) end),
            H.cell("Clear", function() H.confirm("Clear the grid?", function() S.cells = {}; g.refresh() end) end),
        } }
    end
    return g
end

-- ── sudoku ──
function M.sudoku(s, S, H)
    S.v = S.v or {}
    local g = { title = "Sudoku", sel = nil }
    function g.status()
        if L.sd_solved(s, S.v) then H.won("sudoku"); return "Solved!" end
        return s.givens .. " clues · tap a square, then a number"
    end
    function g.rows(width)
        local cw = math.floor(width / 9 * 0.88)
        local rows = {}
        for r = 0, 8 do
            local row = {}
            for c = 0, 8 do
                local i = r * 9 + c + 1
                local v, given = L.sd_val(s, S.v, i)
                local shade = ((math.floor(r / 3) + math.floor(c / 3)) % 2 == 1) and H.colors.light or nil
                if g.sel == i then shade = H.colors.mid end
                row[#row + 1] = H.cell(v ~= "" and v or " ", not given and function() g.sel = i; g.refresh() end or nil,
                    { height = cw, font_size = 22, font_bold = given, background = shade })
            end
            rows[#rows + 1] = row
        end
        return rows
    end
    function g.controls()
        local function put(v) return function()
            if g.sel then S.v[tostring(g.sel)] = v; g.refresh() end end end
        local a, b = {}, {}
        for d = 1, 5 do a[#a + 1] = H.cell(tostring(d), put(tostring(d))) end
        for d = 6, 9 do b[#b + 1] = H.cell(tostring(d), put(tostring(d))) end
        b[#b + 1] = H.cell("Erase", put(nil))
        return { a, b, {
            H.cell("Check", function() local n = L.sd_wrong(s, S.v); H.info(n > 0 and (n .. " wrong numbers cleared.") or "No mistakes so far."); g.refresh() end),
            H.cell("Reveal", function() H.confirm("Reveal the solution?", function()
                for i = 1, 81 do if s.puzzle:sub(i, i) == "0" then S.v[tostring(i)] = s.solution:sub(i, i) end end; g.refresh() end) end),
            H.cell("Clear", function() H.confirm("Clear the grid?", function() S.v = {}; g.refresh() end) end),
        } }
    end
    return g
end

-- ── futoshiki ──
function M.futoshiki(f, S, H)
    S.v = S.v or {}
    local g = { title = "Futoshiki", sel = nil }
    local giv = L.ft_givens(f)
    local hs, vs = L.ft_signs(f)
    function g.status()
        if L.ft_solved(f, S.v) then H.won("futoshiki"); return "Solved!" end
        return "Fill rows and columns with 1–" .. f.n .. "; signs show the bigger number"
    end
    function g.rows(width)
        local n = f.n
        local cw = math.floor(width / (2 * n - 1))
        local rows = {}
        for R = 0, 2 * n - 2 do
            local row = {}
            for C = 0, 2 * n - 2 do
                local r, c = math.floor(R / 2), math.floor(C / 2)
                if R % 2 == 0 and C % 2 == 0 then
                    local k = key(r, c)
                    local v = giv[k] or S.v[k]
                    row[#row + 1] = H.cell(v or " ", not giv[k] and function() g.sel = k; g.refresh() end or nil,
                        { height = cw, font_size = 22, font_bold = giv[k] ~= nil,
                          background = (g.sel == k) and H.colors.mid or H.colors.light })
                elseif R % 2 == 0 then
                    row[#row + 1] = H.cell(hs[key(r, c)] or " ", nil, { height = cw, font_size = 18 })
                elseif C % 2 == 0 then
                    row[#row + 1] = H.cell(vs[key(r, c)] or " ", nil, { height = math.floor(cw / 2), font_size = 16 })
                else
                    row[#row + 1] = H.cell(" ", nil, { height = math.floor(cw / 2) })
                end
            end
            rows[#rows + 1] = row
        end
        return rows
    end
    function g.controls()
        local pad = {}
        for d = 1, f.n do pad[#pad + 1] = H.cell(tostring(d), function() if g.sel then S.v[g.sel] = tostring(d); g.refresh() end end) end
        pad[#pad + 1] = H.cell("Erase", function() if g.sel then S.v[g.sel] = nil; g.refresh() end end)
        return { pad, {
            H.cell("Check", function() local n = L.ft_wrong(f, S.v); H.info(n > 0 and (n .. " wrong numbers cleared.") or "No mistakes so far."); g.refresh() end),
            H.cell("Reveal", function() H.confirm("Reveal the solution?", function()
                for r = 0, f.n - 1 do for c = 0, f.n - 1 do S.v[key(r, c)] = f.solution[r + 1]:sub(c + 1, c + 1) end end; g.refresh() end) end),
            H.cell("Clear", function() H.confirm("Clear the grid?", function() S.v = {}; g.refresh() end) end),
        } }
    end
    return g
end

-- ── queens ──
function M.queens(q, S, H)
    S.v = S.v or {}
    local g = { title = "Queens" }
    local AB = "ABCDEFGHIJ"
    function g.status()
        if L.qn_solved(q, S.v) then H.won("queens"); return "Solved!" end
        local bad = L.qn_conflicts(q, S.v)
        if next(bad) then return "Two crowns clash (marked !)" end
        return "One Q per row, column and lettered region; none touching"
    end
    function g.rows(width)
        local bad = L.qn_conflicts(q, S.v)
        local cw = math.floor(width / q.n)
        local rows = {}
        for r = 0, q.n - 1 do
            local row = {}
            for c = 0, q.n - 1 do
                local k = key(r, c)
                local reg = q.regions[r + 1][c + 1]
                local v = S.v[k]
                local text = v == "q" and ((bad[k] and "!Q") or "Q") or (v == "x" and "×" or AB:sub(reg + 1, reg + 1):lower())
                row[#row + 1] = H.cell(text, function()
                    S.v[k] = (not v) and "x" or (v == "x" and "q" or nil); g.refresh()
                end, { height = cw, font_size = v and 24 or 13, font_bold = v == "q", background = H.shade(reg) })
            end
            rows[#rows + 1] = row
        end
        return rows
    end
    function g.controls()
        return { {
            H.cell("Help", function() H.view("Queens", "Place one crown (Q) in each row, each column and each lettered region. No two crowns may touch, even diagonally.\n\nTap a square once to mark it × (ruled out), twice for a crown, a third time to clear.") end),
            H.cell("Reveal", function() H.confirm("Reveal the solution?", function()
                S.v = {}; for r = 0, q.n - 1 do S.v[key(r, q.solution[r + 1])] = "q" end; g.refresh() end) end),
            H.cell("Clear", function() H.confirm("Clear the board?", function() S.v = {}; g.refresh() end) end),
        } }
    end
    return g
end

-- ── nonogram ──
function M.nonogram(n, S, H)
    if not S.v then S.v = {}; L.ng_apply_givens(n, S.v) end
    S.mode = S.mode or "f"
    local g = { title = "Nonogram" }
    local R, C = #n.rows, #n.cols
    function g.status()
        if L.ng_solved(n, S.v) then H.won("nonogram"); return "Solved! It's " .. n.picture .. "." end
        return "Numbers are the runs of filled squares, in order"
    end
    function g.rows(width)
        local cw = math.floor(width / (C + 1))
        local rows = { { H.cell(" ", nil, { height = cw }) } }
        for c = 1, C do rows[1][#rows[1] + 1] = H.cell(join(n.cols[c], " "), nil, { height = cw, font_size = 11 }) end
        for r = 0, R - 1 do
            local row = { H.cell(join(n.rows[r + 1], " "), nil, { height = cw, font_size = 11 }) }
            for c = 0, C - 1 do
                local k = key(r, c)
                local v = S.v[k]
                row[#row + 1] = H.cell(v == "x" and "×" or " ", function()
                    S.v[k] = (S.v[k] == S.mode) and nil or S.mode; g.refresh()
                end, { height = cw, font_size = 16, background = v == "f" and H.colors.dark or nil })
            end
            rows[#rows + 1] = row
        end
        return rows
    end
    function g.controls()
        return { {
            H.cell((S.mode == "f" and "● " or "") .. "Fill", function() S.mode = "f"; g.refresh() end),
            H.cell((S.mode == "x" and "● " or "") .. "Mark ×", function() S.mode = "x"; g.refresh() end),
        }, {
            H.cell("Check", function() local w = L.ng_wrong(n, S.v); H.info(w > 0 and (w .. " squares are wrong.") or "No mistakes so far.") end),
            H.cell("Reveal", function() H.confirm("Reveal the picture?", function()
                S.v = {}; for r = 0, R - 1 do for c = 0, C - 1 do if n.solution[r + 1]:sub(c + 1, c + 1) == "1" then S.v[key(r, c)] = "f" end end end; g.refresh() end) end),
            H.cell("Clear", function() H.confirm("Clear the grid?", function() S.v = {}; L.ng_apply_givens(n, S.v); g.refresh() end) end),
        } }
    end
    return g
end

-- ── whodunit ──
function M.whodunit(w, S, H)
    S.v = S.v or {}
    local g = { title = "Whodunit" }
    local n = w.size
    local function first(name) return name:match("^(%S+)") end
    local function short(s) local t = s:match("(%S+)$") or s; return t:sub(1, 1):upper() .. t:sub(2, 6) end
    function g.status()
        if S.won then return "Case closed!" end
        return "Tap boxes: × then ● · Clues and Accuse below"
    end
    function g.info()
        local wl, pl = {}, {}
        for i, x in ipairs(w.weapons) do wl[#wl + 1] = i .. " " .. x end
        for i, x in ipairs(w.places) do pl[#pl + 1] = i .. " " .. x end
        return "Weapons: " .. table.concat(wl, ", ") .. "\nPlaces: " .. table.concat(pl, ", ")
    end
    local function box(k, cw)
        local v = S.v[k]
        return H.cell(v == "o" and "●" or (v == "x" and "×" or " "), function()
            S.v[k] = (not v) and "x" or (v == "x" and "o" or nil); g.refresh()
        end, { height = cw, font_size = 18 })
    end
    function g.rows(width)
        local cw = math.floor(width / (2 * n + 2))
        local head = { H.cell(" ", nil, { height = cw }) }
        for i = 1, n do head[#head + 1] = H.cell("W" .. i, nil, { height = cw, font_size = 13 }) end
        for i = 1, n do head[#head + 1] = H.cell("P" .. i, nil, { height = cw, font_size = 13, background = H.colors.light }) end
        local rows = { head }
        for s = 0, n - 1 do
            local row = { H.cell(first(w.suspects[s + 1].name), nil, { height = cw, font_size = 12 }) }
            for j = 0, n - 1 do row[#row + 1] = box("sw:" .. s .. ":" .. j, cw) end
            for j = 0, n - 1 do row[#row + 1] = box("sl:" .. s .. ":" .. j, cw) end
            rows[#rows + 1] = row
        end
        for p = 0, n - 1 do
            local row = { H.cell("P" .. (p + 1), nil, { height = cw, font_size = 13, background = H.colors.light }) }
            for j = 0, n - 1 do row[#row + 1] = box("pw:" .. p .. ":" .. j, cw) end
            for _ = 1, n do row[#row + 1] = H.cell(" ", nil, { height = cw, background = H.colors.light }) end
            rows[#rows + 1] = row
        end
        return rows
    end
    local function accuse()
        local opts = {}
        for i, s in ipairs(w.suspects) do
            opts[#opts + 1] = { text = s.name, callback = function()
                local o2 = {}
                for j, x in ipairs(w.weapons) do
                    o2[#o2 + 1] = { text = x, callback = function()
                        local o3 = {}
                        for k, y in ipairs(w.places) do
                            o3[#o3 + 1] = { text = y, callback = function()
                                local ok, right_who = L.wd_accuse(w, i - 1, j - 1, k - 1)
                                if ok then S.won = true; H.won("whodunit")
                                    H.info("Case closed: " .. s.name .. ", with the " .. x .. ", in the " .. y .. ".")
                                else H.info(right_who and "Right suspect, but the details are off." or "Not quite. Check your grid against the clues.") end
                                g.refresh()
                            end }
                        end
                        H.choose("Where?", o3)
                    end }
                end
                H.choose("With what?", o2)
            end }
        end
        H.choose("Who did it?", opts)
    end
    function g.controls()
        return { {
            H.cell("Case file", function()
                local t = { w.intro, "" }
                for _, s in ipairs(w.suspects) do t[#t + 1] = s.name .. ", " .. s.about end
                t[#t + 1] = ""
                for i, c in ipairs(w.clues) do t[#t + 1] = i .. ". " .. c end
                H.view("Case file", table.concat(t, "\n"))
            end),
            H.cell("Accuse", accuse),
        }, {
            H.cell("Reveal", function() H.confirm("Reveal the answer?", function()
                local k = w.solution.killer
                H.info("It was " .. w.suspects[k + 1].name .. ", with the " .. w.weapons[w.solution.weapon[k + 1] + 1] ..
                    ", in the " .. w.places[w.crime_place + 1] .. ".") end) end),
            H.cell("Clear grid", function() H.confirm("Clear the grid?", function() S.v = {}; g.refresh() end) end),
        } }
    end
    return g
end

-- ── murder map ──
function M.murdermap(m, S, H)
    S.v = S.v or {}
    local g = { title = "Murder map" }
    local fur = L.mm_furniture(m)
    local sym = { plant = "♣", table = "▬", rug = "≈" }
    function g.status()
        if S.won then return "Solved!" end
        return "One person per row and column · tap a square to place"
    end
    function g.info()
        local rl, pl = {}, {}
        for _, r in ipairs(m.rooms) do rl[#rl + 1] = r:sub(1, 1) .. " " .. r end
        for _, p in ipairs(m.people) do pl[#pl + 1] = p.initial .. " " .. p.name end
        return "Rooms: " .. table.concat(rl, ", ") .. "\nPeople: " .. table.concat(pl, ", ") ..
            "\n♣ plant, ▬ table (no standing) · ≈ rug (fine)"
    end
    function g.rows(width)
        local cw = math.floor(width / m.n)
        local rows = {}
        for r = 0, m.n - 1 do
            local row = {}
            for c = 0, m.n - 1 do
                local k = key(r, c)
                local reg = m.room[r + 1][c + 1]
                local f = fur[k]
                local v = S.v[k]
                local text = m.rooms[reg + 1]:sub(1, 1):lower() .. (f and (" " .. sym[f]) or "")
                if v then text = (v == "x" and "×" or v) .. "  " .. m.rooms[reg + 1]:sub(1, 1):lower() end
                row[#row + 1] = H.cell(text, (f ~= "plant" and f ~= "table") and function()
                    local opts = {}
                    for _, p in ipairs(m.people) do
                        opts[#opts + 1] = { text = p.initial .. " · " .. p.name, callback = function() L.mm_place(S.v, k, p.initial); g.refresh() end }
                    end
                    opts[#opts + 1] = { text = "× Rule out", callback = function() L.mm_place(S.v, k, "x"); g.refresh() end }
                    opts[#opts + 1] = { text = "Clear", callback = function() L.mm_place(S.v, k, "clear"); g.refresh() end }
                    H.choose("Who stood here?", opts)
                end or nil, { height = cw, font_size = v and 24 or 14, font_bold = v ~= nil, background = H.shade(reg) })
            end
            rows[#rows + 1] = row
        end
        return rows
    end
    function g.controls()
        return { {
            H.cell("Clues", function()
                local t = { "Each row and column holds exactly one person. Nobody stands on a plant or table; rugs are fine. The murderer is the only person alone in a room with the victim.", "" }
                for _, p in ipairs(m.people) do t[#t + 1] = p.initial .. ": " .. p.name .. ", " .. p.about end
                t[#t + 1] = ""
                for i, c in ipairs(m.clues) do t[#t + 1] = i .. ". " .. c end
                H.view("Clues", table.concat(t, "\n"))
            end),
            H.cell("Check", function()
                local wrong, missing = L.mm_check(m, S.v)
                if wrong == 0 and missing == 0 then
                    S.won = true; H.won("murdermap")
                    H.info("Solved! " .. m.people[m.solution.killer + 1].name .. " was alone with the victim.")
                else H.info(wrong > 0 and (wrong .. " people are in the wrong spot.") or (missing .. " still to place.")) end
                g.refresh()
            end),
        }, {
            H.cell("Reveal", function() H.confirm("Reveal the answer?", function()
                S.v = {}; for i, p in ipairs(m.people) do local pos = m.solution.pos[i]; S.v[key(pos[1], pos[2])] = p.initial end
                g.refresh(); H.info(m.people[m.solution.killer + 1].name .. " did it.") end) end),
            H.cell("Clear", function() H.confirm("Clear the map?", function() S.v = {}; S.won = nil; g.refresh() end) end),
        } }
    end
    return g
end

-- ── news quiz ──
function M.quiz(q, S, H)
    S.a = S.a or {}
    S.i = S.i or 1
    local g = { title = "News quiz" }
    function g.status()
        local s, n = L.qz_score(q, S.a)
        if n == #q.questions then H.won("quiz"); return "You scored " .. s .. " of " .. n end
        return "Question " .. S.i .. " of " .. #q.questions .. " · " .. s .. " right so far"
    end
    function g.info()
        local qq = q.questions[S.i]
        local a = S.a[tostring(S.i)]
        local t = qq.q
        if a then
            t = t .. "\n\n" .. ((a == qq.answer + 1) and "Correct!" or ("The answer: " .. qq.options[qq.answer + 1])) ..
                ((qq.why and qq.why ~= "") and ("\n" .. qq.why) or "")
        end
        return t
    end
    function g.rows()
        local qq = q.questions[S.i]
        local a = S.a[tostring(S.i)]
        local rows = {}
        for j, o in ipairs(qq.options) do
            local mark = ""
            if a then mark = (j == qq.answer + 1) and "✓ " or ((j == a) and "✗ " or "") end
            rows[#rows + 1] = { H.cell(mark .. o, not a and function() S.a[tostring(S.i)] = j; g.refresh() end or nil,
                { align = "left", font_size = 18, font_bold = false }) }
        end
        return rows
    end
    function g.controls()
        return { {
            H.cell("‹ Previous", function() if S.i > 1 then S.i = S.i - 1; g.refresh() end end),
            H.cell("Next ›", function() if S.i < #q.questions then S.i = S.i + 1; g.refresh() end end),
        }, { H.cell("Start over", function() H.confirm("Clear your answers?", function() S.a = {}; S.i = 1; g.refresh() end) end) } }
    end
    return g
end

-- ── groups ──
function M.groups(gr, S, H)
    S.found = S.found or {}
    S.miss = S.miss or 0
    local g = { title = "Groups", sel = {} }
    local function is_found(w)
        for _, i in ipairs(S.found) do for _, x in ipairs(gr.groups[i].words) do if x == w then return true end end end
    end
    function g.status()
        if #S.found == 4 then H.won("groups"); return S.miss == 0 and "Perfect! No mistakes." or ("Solved with " .. S.miss .. " mistakes") end
        return "Pick four that belong together · mistakes: " .. S.miss
    end
    function g.info()
        local t = {}
        for _, i in ipairs(S.found) do t[#t + 1] = gr.groups[i].name:upper() .. ": " .. table.concat(gr.groups[i].words, ", ") end
        return table.concat(t, "\n")
    end
    function g.rows(width)
        local left = {}
        for _, grp in ipairs(gr.groups) do for _, w in ipairs(grp.words) do if not is_found(w) then left[#left + 1] = w end end end
        table.sort(left)
        local rows, row = {}, {}
        for _, w in ipairs(left) do
            local on = false
            for _, x in ipairs(g.sel) do if x == w then on = true end end
            row[#row + 1] = H.cell(w, function()
                if on then for i, x in ipairs(g.sel) do if x == w then table.remove(g.sel, i) end end
                elseif #g.sel < 4 then g.sel[#g.sel + 1] = w end
                g.refresh()
            end, { height = math.floor(width / 6), font_size = 15, background = on and H.colors.mid or nil })
            if #row == 4 then rows[#rows + 1] = row; row = {} end
        end
        return rows
    end
    function g.controls()
        return { {
            H.cell("Deselect", function() g.sel = {}; g.refresh() end),
            H.cell("Submit", function()
                local r = L.gr_submit(gr, S, g.sel)
                if r == "ok" then g.sel = {} end
                if r == "pick" then H.info("Pick four words.") elseif r == "one" then H.info("One away…")
                elseif r == "no" then H.info("Not a group.") end
                g.refresh()
            end),
        }, {
            H.cell("Reveal", function() H.confirm("Reveal all groups?", function()
                for i = 1, 4 do local have = false; for _, f in ipairs(S.found) do if f == i then have = true end end
                    if not have then S.found[#S.found + 1] = i end end; g.refresh() end) end),
            H.cell("Start over", function() H.confirm("Start over?", function() S.found = {}; S.miss = 0; g.sel = {}; g.refresh() end) end),
        } }
    end
    return g
end

-- ── letter hive ──
function M.hive(h, S, H)
    S.f = S.f or {}
    local g = { title = "Letter hive", cur = "" }
    function g.status()
        local rk = L.hv_rank(h, S)
        if #S.f == #h.answers then H.won("hive") end
        if L.hv_score(h, S) / h.max >= .45 then H.won("hive") end
        return rk .. " · " .. L.hv_score(h, S) .. " points · " .. #S.f .. " of " .. #h.answers .. " words"
    end
    function g.info()
        return "Words of 4+ letters, always using " .. h.center .. ". Letters can repeat.\n\n" ..
            "Word: " .. (g.cur ~= "" and g.cur or "…")
    end
    function g.rows(width)
        local cw = math.floor(width / 4)
        local o = h.outer
        local function b(l, center)
            return H.cell(l, function() g.cur = g.cur .. l; g.refresh() end,
                { height = cw, font_size = 30, background = center and H.colors.mid or nil })
        end
        local blank = H.cell(" ", nil, { height = cw })
        return { { b(o[1]), b(o[2]), b(o[3]) }, { b(o[4]), b(h.center, true), b(o[5]) }, { blank, b(o[6]), H.cell(" ", nil, { height = cw }) } }
    end
    local function enter(word)
        local m = L.hv_enter(h, S, word)
        g.cur = ""
        H.info(m)
        g.refresh()
    end
    function g.controls()
        return { {
            H.cell("Delete", function() g.cur = g.cur:sub(1, -2); g.refresh() end),
            H.cell("Enter", function() enter(g.cur) end),
            H.cell("Type…", function() H.input("Letter hive", "Type a word", "", enter) end),
        }, {
            H.cell("Found words", function()
                local t = {}
                for _, w in ipairs(S.f) do t[#t + 1] = w end
                table.sort(t)
                H.view("Found words", #t > 0 and table.concat(t, ", ") or "None yet.")
            end),
            H.cell("Reveal", function() H.confirm("Show every answer?", function()
                H.view("All words", table.concat(h.answers, ", ") .. "\n\nPangrams: " .. table.concat(h.pangrams, ", ")) end) end),
        } }
    end
    return g
end

-- ── cryptogram ──
function M.cryptogram(c, S, H)
    S.v = S.v or {}
    local g = { title = "Cryptogram" }
    function g.status()
        if L.cg_solved(c, S.v) then H.won("cryptogram"); return "Decoded!" end
        return (c.source or "") .. " · tap a code letter to guess it"
    end
    function g.info()
        local plain = L.cg_text(c, S.v)
        return plain .. "\n\nCode: " .. c.cipher
    end
    function g.rows(width)
        local ls = L.cg_letters(c)
        local rows, row = {}, {}
        for _, x in ipairs(ls) do
            local hint = c.hints[x]
            row[#row + 1] = H.cell(x .. "=" .. (hint or S.v[x] or "?"), not hint and function()
                H.input("Code letter " .. x, "What does " .. x .. " stand for?", S.v[x] or "", function(t)
                    L.cg_set(S.v, x, t); g.refresh() end)
            end or nil, { font_size = 17, font_bold = hint ~= nil or S.v[x] ~= nil, height = math.floor(width / 8) })
            if #row == 6 then rows[#rows + 1] = row; row = {} end
        end
        if #row > 0 then while #row < 6 do row[#row + 1] = H.cell(" ", nil) end; rows[#rows + 1] = row end
        return rows
    end
    function g.controls()
        return { {
            H.cell("Check", function()
                local n = 0
                for i = 1, #c.cipher do
                    local x = c.cipher:sub(i, i)
                    if S.v[x] and S.v[x] ~= c.plain:sub(i, i) then S.v[x] = nil; n = n + 1 end
                end
                H.info(n > 0 and (n .. " wrong letters cleared.") or "All correct so far."); g.refresh()
            end),
            H.cell("Reveal", function() H.confirm("Reveal the message?", function()
                for i = 1, #c.cipher do local x = c.cipher:sub(i, i); if x:match("%u") then S.v[x] = c.plain:sub(i, i) end end
                g.refresh() end) end),
            H.cell("Clear", function() H.confirm("Clear your guesses?", function() S.v = {}; g.refresh() end) end),
        } }
    end
    return g
end

-- ── word ladder ──
function M.ladder(l, S, H)
    S.v = S.v or {}
    local g = { title = "Word ladder" }
    function g.status()
        local ok = L.ld_check(l, S.v)
        if ok then H.won("ladder"); return "Solved!" end
        return "Change one letter at a time; every rung is a real word"
    end
    function g.rows(width)
        local _, marks = L.ld_check(l, S.v)
        local h = math.floor(width / 9)
        local rows = { { H.cell(l.start, nil, { font_size = 26, height = h, background = H.colors.light }) } }
        for i = 1, #l.solution - 2 do
            local w = S.v[tostring(i)]
            local mark = marks[i] == "bad" and "  ✗" or ""
            rows[#rows + 1] = { H.cell((w and w ~= "") and (w .. mark) or "_ _ _ _", function()
                H.input("Rung " .. i, "A four-letter word, one letter different from the word above", w or "", function(t)
                    S.v[tostring(i)] = t:upper():gsub("[^A-Z]", ""):sub(1, 4); g.refresh() end)
            end, { font_size = 26, height = h }) }
        end
        rows[#rows + 1] = { H.cell(l["end"], nil, { font_size = 26, height = h, background = H.colors.light }) }
        return rows
    end
    function g.controls()
        return { {
            H.cell("Reveal", function() H.confirm("Reveal a solution?", function()
                for i = 2, #l.solution - 1 do S.v[tostring(i - 1)] = l.solution[i] end; g.refresh() end) end),
            H.cell("Clear", function() H.confirm("Clear the ladder?", function() S.v = {}; g.refresh() end) end),
        } }
    end
    return g
end

M.order = {
    { "quiz", "News quiz" }, { "groups", "Groups" }, { "crossword", "Crossword" }, { "hive", "Letter hive" },
    { "whodunit", "Whodunit" }, { "murdermap", "Murder map" }, { "cryptogram", "Cryptogram" }, { "ladder", "Word ladder" },
    { "sudoku", "Sudoku" }, { "futoshiki", "Futoshiki" }, { "queens", "Queens" }, { "nonogram", "Nonogram" },
}

return M
