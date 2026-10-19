/*
 * Client-side model for the mockups: state, scoring, undo, persistence.
 *
 * scoreOf() is a port of app/utils/evaluate.py so numbers feel real.
 * One deliberate difference: evaluate.py counts *all* non-manual requests
 * (including "repel") in num_reqs but only scores "attract", which skews the
 * per-student ratio. Here only "attract" requests count toward the ratio.
 */
(function () {
  const STORAGE_KEY = "roomies-mock-solution-v1";
  const M = window.MOCK;

  const peopleById = Object.fromEntries(M.people.map(p => [p.id, p]));

  function freshState() {
    return {
      rooms: M.solution.rooms.map(r => ({...r, people: [...r.people]})),
      unplaced: [],
      log: [],
    };
  }

  let state = load() || freshState();
  const undoStack = [];
  const redoStack = [];
  const listeners = [];

  function load() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch (e) { return null; }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function snapshot() {
    return JSON.stringify(state);
  }

  function emit() {
    save();
    listeners.forEach(fn => fn(state));
  }

  // ---- Lookups ------------------------------------------------------------

  function assignment(rooms = state.rooms) {
    const inv = {};
    rooms.forEach(r => r.people.forEach(id => { inv[id] = r.id; }));
    return inv;
  }

  function room(id) {
    return state.rooms.find(r => r.id === Number(id));
  }

  function roomLabel(r) {
    return r.placed_name || r.internal_name;
  }

  // ---- Scoring ------------------------------------------------------------

  function satisfied(req, inv) {
    const a = inv[req.requestor], b = inv[req.requestee];
    if (a === undefined || b === undefined) return null; // someone is unplaced
    const together = a === b;
    return (req.type === "attract" || req.type === "require") ? together : !together;
  }

  function scoreOf(inv) {
    let running = 0, granted = 0, total = 0;
    const zeroGranted = [];
    const violations = [];

    for (const p of M.people) {
      const reqs = M.requests.filter(r => r.requestor === p.id && !r.manual && r.type === "attract");
      let n = 0, fails = 0;
      for (const req of reqs) {
        const s = satisfied(req, inv);
        if (s === null) continue;
        n++;
        if (s) granted++; else fails++;
      }
      total += n;
      if (n === 0) continue;
      if (fails === n) { running += 1000; zeroGranted.push(p.id); }
      running += fails / n;
    }

    for (const req of M.requests.filter(r => r.manual)) {
      if (satisfied(req, inv) === false) {
        running += 1000000;
        violations.push(req);
      }
    }

    return {score: running, granted, total, zeroGranted, violations};
  }

  function summary() {
    const inv = assignment();
    const s = scoreOf(inv);
    const overfull = state.rooms.filter(r => r.people.length > r.capacity);
    const openBeds = state.rooms.reduce((n, r) => n + Math.max(0, r.capacity - r.people.length), 0);
    const repelBroken = M.requests.filter(r => r.type === "repel" && satisfied(r, inv) === false);
    return {...s, overfull, openBeds, repelBroken, unplaced: state.unplaced.length};
  }

  // Everything one student is connected to, with live satisfaction state.
  function studentDetail(pid, inv = assignment()) {
    const mk = (req, otherId, dir) => ({
      other: peopleById[otherId], otherId, dir, type: req.type, manual: req.manual,
      satisfied: satisfied(req, inv),
    });
    const out = M.requests.filter(r => r.requestor === pid).map(r => mk(r, r.requestee, "out"));
    const inc = M.requests.filter(r => r.requestee === pid).map(r => mk(r, r.requestor, "in"));
    const wants = out.filter(x => x.type === "attract");
    return {
      person: peopleById[pid],
      roomId: inv[pid] ?? null,
      links: out.concat(inc),
      wantsMet: wants.filter(x => x.satisfied).length,
      wantsTotal: wants.length,
      wantedByMet: inc.filter(x => x.type === "attract" && x.satisfied).length,
      wantedByTotal: inc.filter(x => x.type === "attract").length,
      hasRequests: wants.length > 0,
    };
  }

  // Badge status used everywhere a student chip is drawn.
  function studentStatus(pid, inv = assignment()) {
    const d = studentDetail(pid, inv);
    if (d.roomId === null) return "unplaced";
    if (d.links.some(l => l.manual && l.satisfied === false)) return "violation";
    if (!d.hasRequests) return "none";
    if (d.wantsMet === 0) return "zero";
    if (d.wantsMet === d.wantsTotal) return "all";
    return "some";
  }

  // What happens if pid is dropped into roomId (null = unplaced pool)?
  // With swapWith, the other student goes to pid's current room instead.
  function preview(pid, roomId, swapWith = null) {
    const before = scoreOf(assignment());
    const fromId = assignment()[pid] ?? null;
    const rooms = state.rooms.map(r => ({...r, people: r.people.filter(id => id !== pid && id !== swapWith)}));
    if (roomId !== null) rooms.find(r => r.id === roomId).people.push(pid);
    if (swapWith && fromId !== null) rooms.find(r => r.id === fromId).people.push(swapWith);
    const inv = assignment(rooms);
    const after = scoreOf(inv);
    const d = studentDetail(pid, inv);
    return {
      before, after,
      deltaGranted: after.granted - before.granted,
      deltaZero: after.zeroGranted.length - before.zeroGranted.length,
      deltaViolations: after.violations.length - before.violations.length,
      deltaScore: after.score - before.score,
      student: d,
    };
  }

  // Count of attract requests crossing between two rooms (both directions).
  function affinity(roomA, roomB) {
    const a = new Set(roomA.people), b = new Set(roomB.people);
    return M.requests.filter(r => r.type === "attract" &&
      ((a.has(r.requestor) && b.has(r.requestee)) || (b.has(r.requestor) && a.has(r.requestee)))).length;
  }

  // ---- Mutations ----------------------------------------------------------

  function commit(label, fn) {
    undoStack.push(snapshot());
    redoStack.length = 0;
    fn();
    state.log.unshift({label, at: new Date().toISOString()});
    state.log = state.log.slice(0, 50);
    emit();
  }

  function move(pid, toRoomId) {
    const inv = assignment();
    const from = inv[pid] ?? null;
    if (from === toRoomId) return;
    const name = peopleById[pid].name;
    const dest = toRoomId === null ? "unplaced" : roomLabel(room(toRoomId));
    commit(`Moved ${name} → ${dest}`, () => {
      state.rooms.forEach(r => { r.people = r.people.filter(id => id !== pid); });
      state.unplaced = state.unplaced.filter(id => id !== pid);
      if (toRoomId === null) state.unplaced.push(pid);
      else room(toRoomId).people.push(pid);
    });
  }

  function swap(pidA, pidB) {
    const inv = assignment();
    const ra = inv[pidA], rb = inv[pidB];
    if (ra === undefined || rb === undefined || ra === rb) return;
    commit(`Swapped ${peopleById[pidA].name} ⇄ ${peopleById[pidB].name}`, () => {
      const A = room(ra), B = room(rb);
      A.people[A.people.indexOf(pidA)] = pidB;
      B.people[B.people.indexOf(pidB)] = pidA;
    });
  }

  function rename(roomId, placedName) {
    const r = room(roomId);
    const value = placedName && placedName.trim() ? placedName.trim() : null;
    if (r.placed_name === value) return;
    commit(value ? `Placed ${r.internal_name} in ${value}` : `Cleared placement for ${r.internal_name}`, () => {
      // A hotel room can only hold one group: clear any other holder.
      if (value) state.rooms.forEach(o => { if (o.placed_name === value) o.placed_name = null; });
      room(roomId).placed_name = value;
    });
  }

  // Put a group into a hotel room; whoever was there takes the group's old spot.
  function place(roomId, number, label) {
    const r = room(roomId);
    if (r.placed_name === number) return;
    const occupant = number && state.rooms.find(o => o.placed_name === number);
    const msg = label || (number
      ? (occupant ? `Swapped ${r.internal_name} ⇄ ${occupant.internal_name}` : `Placed ${r.internal_name} in ${number}`)
      : `Unplaced ${r.internal_name}`);
    commit(msg, () => {
      if (occupant) room(occupant.id).placed_name = r.placed_name;
      room(roomId).placed_name = number || null;
    });
  }

  function placeMany(pairs, label) {
    commit(label, () => pairs.forEach(([roomId, number]) => { room(roomId).placed_name = number; }));
  }

  function undo() {
    if (!undoStack.length) return;
    redoStack.push(snapshot());
    state = JSON.parse(undoStack.pop());
    emit();
  }

  function redo() {
    if (!redoStack.length) return;
    undoStack.push(snapshot());
    state = JSON.parse(redoStack.pop());
    emit();
  }

  function reset() {
    undoStack.length = 0;
    redoStack.length = 0;
    state = freshState();
    emit();
  }

  window.addEventListener("keydown", e => {
    if (!(e.metaKey || e.ctrlKey) || e.key.toLowerCase() !== "z") return;
    if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
    e.preventDefault();
    e.shiftKey ? redo() : undo();
  });

  // Keep multiple open mockup tabs in sync.
  window.addEventListener("storage", e => {
    if (e.key === STORAGE_KEY && e.newValue) {
      state = JSON.parse(e.newValue);
      listeners.forEach(fn => fn(state));
    }
  });

  window.Engine = {
    get state() { return state; },
    people: M.people, peopleById, requests: M.requests, solution: M.solution, hotel: M.hotel,
    assignment, room, roomLabel, summary, studentDetail, studentStatus, preview, affinity,
    move, swap, rename, place, placeMany, undo, redo, reset,
    canUndo: () => undoStack.length > 0,
    canRedo: () => redoStack.length > 0,
    onChange: fn => listeners.push(fn),
  };
})();
