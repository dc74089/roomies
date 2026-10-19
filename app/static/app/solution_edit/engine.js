/*
 * Client-side model for the solution editor: state, scoring, undo, and
 * syncing edits to the server.
 *
 * Every edit is applied locally first (so the UI is instant), then the
 * difference between the old and new state is sent to the server as
 * move / swap / rename calls, one at a time, in order. Once the queue is idle
 * the server re-scores the solution so Solution.score stays current.
 *
 * scoreOf() mirrors app/utils/evaluate.py so the numbers on the page match
 * the score stored on the Solution.
 */
(function () {
  let M, api, state;
  let peopleById = {}, reqOut = {}, reqIn = {}, attractOut = {}, manualReqs = [];
  const undoStack = [];
  const redoStack = [];
  const listeners = [];
  const statusListeners = [];

  let queue = Promise.resolve();
  let pending = 0;
  let failed = false;
  let scoreTimer = null;

  function init(payload, apiConfig) {
    M = payload;
    api = apiConfig;
    peopleById = Object.fromEntries(M.people.map(p => [p.id, p]));
    M.people.forEach(p => { reqOut[p.id] = []; reqIn[p.id] = []; attractOut[p.id] = []; });
    M.requests.forEach(r => {
      reqOut[r.requestor].push(r);
      reqIn[r.requestee].push(r);
      if (r.manual) manualReqs.push(r);
      else if (r.type === "attract") attractOut[r.requestor].push(r);
    });
    state = {
      rooms: M.rooms.map(r => ({...r, people: [...r.people]})),
      unplaced: [...M.unplaced],
      log: [],
    };
    window.addEventListener("beforeunload", e => {
      if (pending > 0) { e.preventDefault(); e.returnValue = ""; }
    });
  }

  function clone(s) {
    return JSON.parse(JSON.stringify(s));
  }

  function emit() {
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
      if (p.gender !== M.solution.gender) continue;
      let n = 0, fails = 0;
      for (const req of attractOut[p.id]) {
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

    for (const req of manualReqs) {
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
    const out = reqOut[pid].map(r => mk(r, r.requestee, "out"));
    const inc = reqIn[pid].map(r => mk(r, r.requestor, "in"));
    const wants = out.filter(x => x.type === "attract" && !x.manual);
    const wantedBy = inc.filter(x => x.type === "attract" && !x.manual);
    return {
      person: peopleById[pid],
      roomId: inv[pid] ?? null,
      links: out.concat(inc),
      wantsMet: wants.filter(x => x.satisfied).length,
      wantsTotal: wants.length,
      wantedByMet: wantedBy.filter(x => x.satisfied).length,
      wantedByTotal: wantedBy.length,
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
    const current = assignment();
    const before = scoreOf(current);
    const fromId = current[pid] ?? null;
    const inv = {...current};
    delete inv[pid];
    if (roomId !== null) inv[pid] = roomId;
    if (swapWith) {
      delete inv[swapWith];
      if (fromId !== null) inv[swapWith] = fromId;
    }
    const after = scoreOf(inv);
    return {
      before, after, inv,
      deltaGranted: after.granted - before.granted,
      deltaZero: after.zeroGranted.length - before.zeroGranted.length,
      deltaViolations: after.violations.length - before.violations.length,
      deltaScore: after.score - before.score,
      student: studentDetail(pid, inv),
    };
  }

  // Count of attract requests crossing between two rooms (both directions).
  function affinity(roomA, roomB) {
    const b = new Set(roomB.people);
    let n = 0;
    roomA.people.forEach(id => {
      attractOut[id].forEach(r => { if (b.has(r.requestee)) n++; });
      reqIn[id].forEach(r => { if (!r.manual && r.type === "attract" && b.has(r.requestor)) n++; });
    });
    return n;
  }

  // ---- Server sync --------------------------------------------------------

  // Turn the difference between two states into server calls.
  function diffOps(prev, next) {
    const a = assignment(prev.rooms), b = assignment(next.rooms);
    const everyone = new Set([...Object.keys(a), ...Object.keys(b)]);
    const moved = [...everyone].filter(pid => a[pid] !== b[pid]);
    const ops = [];

    const [x, y] = moved;
    const isSwap = moved.length === 2 && a[x] !== undefined && a[y] !== undefined &&
      a[x] === b[y] && a[y] === b[x];
    if (isSwap) ops.push({url: api.swap, data: {solution: M.solution.id, a: x, b: y}});
    else moved.forEach(pid => ops.push({url: api.move, data: {solution: M.solution.id, person: pid, to: b[pid] ?? ""}}));

    next.rooms.forEach(r => {
      const old = prev.rooms.find(o => o.id === r.id);
      if ((old.placed_name || "") !== (r.placed_name || "")) {
        ops.push({url: api.rename, data: {id: r.id, new: r.placed_name || ""}});
      }
    });
    return ops;
  }

  async function post(url, data) {
    const body = new FormData();
    Object.entries(data).forEach(([k, v]) => body.append(k, v));
    const res = await fetch(url, {
      method: "POST",
      body,
      headers: {"X-CSRFToken": api.csrf},
      credentials: "same-origin",
    });
    // login_required answers with a redirect to the login page
    if (res.redirected) throw new Error("logged-out");
    if (!res.ok) throw new Error(`${res.status} from ${url}`);
    return res.json();
  }

  function setStatus(s, detail) {
    statusListeners.forEach(fn => fn(s, detail));
  }

  function enqueue(ops) {
    if (!ops.length || failed) return;
    pending++;
    setStatus("saving");
    queue = queue
      .then(async () => { for (const op of ops) await post(op.url, op.data); })
      .then(() => {
        pending--;
        if (pending === 0 && !failed) {
          setStatus("saved");
          clearTimeout(scoreTimer);
          scoreTimer = setTimeout(rescore, 1500);
        }
      })
      .catch(err => {
        pending = 0;
        failed = true;
        console.error(err);
        setStatus("error", err.message === "logged-out"
          ? "You've been logged out, so the last change wasn't saved. Log in again, then reload."
          : "Couldn't save the last change. Reload to see what the server has.");
      });
  }

  // Have the server re-score so the stored Solution.score stays current.
  async function rescore() {
    if (pending || failed) return;
    try {
      const res = await fetch(`${api.reevaluate}?solution=${M.solution.id}`, {credentials: "same-origin"});
      if (!res.ok || res.redirected) throw new Error(res.status);
      const data = await res.json();
      const local = scoreOf(assignment()).score;
      if (Math.abs(local - data.score) > 0.01) {
        console.warn(`Score mismatch: page says ${local}, server says ${data.score}`);
      }
      setStatus("saved", data.score);
    } catch (e) {
      console.warn("Re-score failed", e);
    }
  }

  // ---- Mutations ----------------------------------------------------------

  function commit(label, fn) {
    if (failed) return;
    const prev = clone(state);
    undoStack.push(prev);
    redoStack.length = 0;
    fn();
    state.log.unshift({label, at: new Date().toISOString()});
    state.log = state.log.slice(0, 50);
    emit();
    enqueue(diffOps(prev, state));
  }

  function move(pid, toRoomId) {
    const inv = assignment();
    const from = inv[pid] ?? null;
    if (from === toRoomId) return;
    const name = peopleById[pid].name;
    const dest = toRoomId === null ? "Unplaced" : roomLabel(room(toRoomId));
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
    const value = (placedName || "").trim();
    if ((r.placed_name || "") === value) return;
    commit(value ? `Named ${r.internal_name} “${value}”` : `Cleared name for ${r.internal_name}`, () => {
      room(roomId).placed_name = value;
    });
  }

  function restore(target, stackPush) {
    if (failed) return;
    const prev = clone(state);
    stackPush.push(prev);
    // Keep the activity log; it describes what happened, not the state
    state = {...target, log: [{label: stackPush === redoStack ? "Undo" : "Redo", at: new Date().toISOString()}, ...state.log]};
    emit();
    enqueue(diffOps(prev, state));
  }

  function undo() {
    if (undoStack.length) restore(undoStack.pop(), redoStack);
  }

  function redo() {
    if (redoStack.length) restore(redoStack.pop(), undoStack);
  }

  window.addEventListener("keydown", e => {
    if (!(e.metaKey || e.ctrlKey) || e.key.toLowerCase() !== "z") return;
    if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
    e.preventDefault();
    e.shiftKey ? redo() : undo();
  });

  window.Engine = {
    init,
    get state() { return state; },
    get people() { return M.people; },
    get peopleById() { return peopleById; },
    get solution() { return M.solution; },
    assignment, room, roomLabel, summary, studentDetail, studentStatus, preview, affinity,
    move, swap, rename, undo, redo,
    canUndo: () => undoStack.length > 0 && !failed,
    canRedo: () => redoStack.length > 0 && !failed,
    onChange: fn => listeners.push(fn),
    onStatus: fn => statusListeners.push(fn),
  };
})();
