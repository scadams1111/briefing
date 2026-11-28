--[[ Puzzle rules for Briefing puzzles. Pure Lua (no KOReader modules) so it can be tested off-device.
Row/column numbers coming from the JSON are 0-based (as published); cell keys are "r,c" strings. ]]
local L = {}

local function key(r, c) return r .. "," .. c end
L.key = key

local function ch(s, i) return s:sub(i, i) end -- 1-based

-- ── crossword ──
function L.xw_cells(en)
    local out = {}
    for k = 0, #en.answer - 1 do
        if en.d == "A" then out[#out + 1] = key(en.r, en.c + k) else out[#out + 1] = key(en.r + k, en.c) end
    end
    return out
end

function L.xw_sol(x, r, c) return ch(x.solution[r + 1], c + 1) end

function L.xw_fill(x, st, i, word)
    local en = x.entries[i]
    word = (word or ""):upper():gsub("[^A-Z]", "")
    for k, kk in ipairs(L.xw_cells(en)) do
        local letter = ch(word, k)
        if letter ~= "" then st[kk] = letter end
    end
end

function L.xw_pattern(x, st, i)
    local t = {}
    for _, kk in ipairs(L.xw_cells(x.entries[i])) do t[#t + 1] = st[kk] or "_" end
    return table.concat(t, " ")
end

function L.xw_solved(x, st)
    for r = 0, x.rows - 1 do
        for c = 0, x.cols - 1 do
            local s = L.xw_sol(x, r, c)
            if s ~= "." and st[key(r, c)] ~= s then return false end
        end
    end
    return true
end

function L.xw_wrong(x, st)
    local n = 0
    for kk, v in pairs(st) do
        local r, c = kk:match("(%d+),(%d+)")
        if v ~= L.xw_sol(x, tonumber(r), tonumber(c)) then st[kk] = nil; n = n + 1 end
    end
    return n
end

-- entries (indexes) through a cell
function L.xw_at(x, r, c)
    local out = {}
    for i, en in ipairs(x.entries) do
        for _, kk in ipairs(L.xw_cells(en)) do
            if kk == key(r, c) then out[#out + 1] = i end
        end
    end
    return out
end

-- ── sudoku (st.v[i] with i = 1..81) ──
function L.sd_val(s, st, i)
    local g = ch(s.puzzle, i)
    if g ~= "0" then return g, true end
    return st[tostring(i)] or "", false
end

function L.sd_solved(s, st)
    for i = 1, 81 do if L.sd_val(s, st, i) ~= ch(s.solution, i) then return false end end
    return true
end

function L.sd_wrong(s, st)
    local n = 0
    for k, v in pairs(st) do
        if v ~= ch(s.solution, tonumber(k)) then st[k] = nil; n = n + 1 end
    end
    return n
end

-- ── futoshiki ──
function L.ft_givens(f)
    local g = {}
    for _, t in ipairs(f.givens) do g[key(t[1], t[2])] = tostring(t[3]) end
    return g
end

function L.ft_signs(f)
    local h, v = {}, {}
    for _, t in ipairs(f.less) do
        local a, b, c, d = t[1], t[2], t[3], t[4] -- value(a,b) < value(c,d)
        if a == c then h[key(a, math.min(b, d))] = (b < d) and "<" or ">"
        else v[key(math.min(a, c), b)] = (a < c) and "^" or "v" end
    end
    return h, v
end

function L.ft_solved(f, st)
    local g = L.ft_givens(f)
    for r = 0, f.n - 1 do
        for c = 0, f.n - 1 do
            if (g[key(r, c)] or st[key(r, c)]) ~= ch(f.solution[r + 1], c + 1) then return false end
        end
    end
    return true
end

function L.ft_wrong(f, st)
    local n = 0
    for kk, v in pairs(st) do
        local r, c = kk:match("(%d+),(%d+)")
        if v ~= ch(f.solution[tonumber(r) + 1], tonumber(c) + 1) then st[kk] = nil; n = n + 1 end
    end
    return n
end

-- ── queens (st[key] = "q" | "x") ──
function L.qn_conflicts(q, st)
    local qs, bad = {}, {}
    for kk, v in pairs(st) do
        if v == "q" then
            local r, c = kk:match("(%d+),(%d+)")
            qs[#qs + 1] = { tonumber(r), tonumber(c), kk }
        end
    end
    for i = 1, #qs do
        for j = i + 1, #qs do
            local a, b = qs[i], qs[j]
            if a[1] == b[1] or a[2] == b[2] or q.regions[a[1] + 1][a[2] + 1] == q.regions[b[1] + 1][b[2] + 1]
                or (math.abs(a[1] - b[1]) <= 1 and math.abs(a[2] - b[2]) <= 1) then
                bad[a[3]] = true; bad[b[3]] = true
            end
        end
    end
    return bad, #qs
end

function L.qn_solved(q, st)
    local bad, n = L.qn_conflicts(q, st)
    return n == q.n and next(bad) == nil
end

-- ── nonogram (st[key] = "f" | "x") ──
function L.ng_solved(g, st)
    for r = 0, #g.rows - 1 do
        for c = 0, #g.cols - 1 do
            if (st[key(r, c)] == "f") ~= (ch(g.solution[r + 1], c + 1) == "1") then return false end
        end
    end
    return true
end

function L.ng_wrong(g, st)
    local n = 0
    for kk, v in pairs(st) do
        local r, c = kk:match("(%d+),(%d+)")
        if (v == "f") ~= (ch(g.solution[tonumber(r) + 1], tonumber(c) + 1) == "1") then n = n + 1 end
    end
    return n
end

function L.ng_apply_givens(g, st)
    for _, t in ipairs(g.givens) do st[key(t[1], t[2])] = (t[3] == 1) and "f" or "x" end
end

-- ── whodunit ──
function L.wd_accuse(w, who, what, where) -- 0-based picks
    local s = w.solution
    local k = s.killer
    return who == k and what == s.weapon[k + 1] and where == w.crime_place, who == k
end

-- ── murder map (st[key] = initial or "x") ──
function L.mm_check(m, st)
    local wrong, missing = 0, 0
    for i, p in ipairs(m.people) do
        local at
        for kk, v in pairs(st) do if v == p.initial then at = kk end end
        local pos = m.solution.pos[i]
        if not at then missing = missing + 1 elseif at ~= key(pos[1], pos[2]) then wrong = wrong + 1 end
    end
    return wrong, missing
end

function L.mm_place(st, kk, tok)
    if tok == "clear" then st[kk] = nil return end
    if tok ~= "x" then for k2, v in pairs(st) do if v == tok then st[k2] = nil end end end
    st[kk] = tok
end

function L.mm_furniture(m)
    local f = {}
    for _, t in ipairs(m.furniture) do f[key(t.r, t.c)] = t.t end
    return f
end

-- ── groups (st.found = list of group indexes, st.miss) ──
function L.gr_submit(gr, st, sel)
    if #sel ~= 4 then return "pick" end
    for i, g in ipairs(gr.groups) do
        local hit = 0
        for _, w in ipairs(sel) do for _, x in ipairs(g.words) do if x == w then hit = hit + 1 end end end
        if hit == 4 then
            for _, f in ipairs(st.found) do if f == i then return "dup" end end
            st.found[#st.found + 1] = i
            return "ok"
        end
    end
    st.miss = (st.miss or 0) + 1
    for _, g in ipairs(gr.groups) do
        local hit = 0
        for _, w in ipairs(sel) do for _, x in ipairs(g.words) do if x == w then hit = hit + 1 end end end
        if hit == 3 then return "one" end
    end
    return "no"
end

-- ── letter hive (st.f = found words) ──
function L.hv_points(h, w)
    local p = (#w == 4) and 1 or #w
    for _, x in ipairs(h.pangrams) do if x == w then p = p + 7 end end
    return p
end

function L.hv_score(h, st)
    local s = 0
    for _, w in ipairs(st.f) do s = s + L.hv_points(h, w) end
    return s
end

function L.hv_enter(h, st, w)
    w = (w or ""):upper():gsub("[^A-Z]", "")
    if #w < 4 then return "Too short." end
    if not w:find(h.center, 1, true) then return "Missing the center letter." end
    for _, x in ipairs(st.f) do if x == w then return "Already found." end end
    for _, x in ipairs(h.answers) do
        if x == w then
            st.f[#st.f + 1] = w
            return "+" .. L.hv_points(h, w)
        end
    end
    return "Not in the word list."
end

function L.hv_rank(h, st)
    local fr = L.hv_score(h, st) / h.max
    local rk = "Beginner"
    for _, t in ipairs({ { .05, "Getting going" }, { .15, "Solid" }, { .3, "Good" }, { .45, "Great" }, { .6, "Amazing" }, { .8, "Genius" } }) do
        if fr >= t[1] then rk = t[2] end
    end
    return rk, fr
end

-- ── cryptogram (st[cipher letter] = guess) ──
function L.cg_letters(c)
    local seen, out = {}, {}
    for i = 1, #c.cipher do
        local x = ch(c.cipher, i)
        if x:match("%u") and not seen[x] then seen[x] = true; out[#out + 1] = x end
    end
    return out
end

function L.cg_text(c, st)
    local t = {}
    for i = 1, #c.cipher do
        local x = ch(c.cipher, i)
        t[#t + 1] = x:match("%u") and (st[x] or c.hints[x] or "_") or x
    end
    return table.concat(t)
end

function L.cg_solved(c, st) return L.cg_text(c, st) == c.plain end

function L.cg_set(st, cipher, guess)
    guess = (guess or ""):upper():sub(1, 1)
    if guess == "" or not guess:match("%u") then st[cipher] = nil return end
    for k, v in pairs(st) do if v == guess then st[k] = nil end end
    st[cipher] = guess
end

-- ── word ladder (st[i] = word for rung i) ──
function L.ld_check(l, st)
    local valid = {}
    for _, w in ipairs(l.valid) do valid[w] = true end
    local function diff(a, b)
        local n = 0
        for i = 1, 4 do if ch(a, i) ~= ch(b, i) then n = n + 1 end end
        return n
    end
    local prev, ok, marks = l.start, true, {}
    for i = 1, #l.solution - 2 do
        local w = (st[tostring(i)] or ""):upper()
        if #w ~= 4 then marks[i] = ""; ok = false
        elseif valid[w] and diff(prev, w) == 1 then marks[i] = "ok"; prev = w
        else marks[i] = "bad"; ok = false end
    end
    return ok and diff(prev, l["end"]) == 1, marks
end

-- ── quiz (st[i] = chosen option, 1-based) ──
function L.qz_score(q, st)
    local s, n = 0, 0
    for i, qq in ipairs(q.questions) do
        local a = st[tostring(i)]
        if a then n = n + 1; if a == qq.answer + 1 then s = s + 1 end end
    end
    return s, n
end

return L
