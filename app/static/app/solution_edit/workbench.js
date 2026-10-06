/*
 * Workbench: the solution editor page. Expects Engine.init() to have run.
 */
(function () {
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  let selected = null;
  let dragCtx = null;

  function syncChromeHeight() {
    document.documentElement.style.setProperty("--chrome-h", $("#toolbar").offsetHeight + "px");
  }
  jQuery("#legend").on("shown.bs.collapse hidden.bs.collapse", syncChromeHeight);
  window.addEventListener("resize", syncChromeHeight);

  // ---- Derived room info ----------------------------------------------------

  function roomHappiness(r, inv) {
    let met = 0, total = 0;
    r.people.forEach(pid => {
      const d = Engine.studentDetail(pid, inv);
      met += d.wantsMet; total += d.wantsTotal;
    });
    return {met, total, pct: total ? met / total : 1};
  }

  function strongestNeighbor(r) {
    let best = null, score = 0;
    Engine.state.rooms.forEach(o => {
      if (o === r) return;
      const a = Engine.affinity(r, o);
      if (a > score) { best = o; score = a; }
    });
    return best ? {room: best, score} : null;
  }

  // ---- Render ---------------------------------------------------------------

  function render() {
    const inv = Engine.assignment();
    const s = Engine.summary();

    const pct = s.total ? Math.round(100 * s.granted / s.total) : 0;
    $("#stats").innerHTML = `
      <div class="stat" id="st-granted"><span class="v">${s.granted}/${s.total} <small class="text-muted">${pct}%</small><span class="pd"></span></span><span class="k">Requests granted</span></div>
      <div class="stat ${s.zeroGranted.length ? "bad" : "good"}" id="st-zero"><span class="v">${s.zeroGranted.length}<span class="pd"></span></span><span class="k">Got none</span></div>
      <div class="stat ${s.violations.length ? "bad" : "good"}" id="st-hard"><span class="v">${s.violations.length}<span class="pd"></span></span><span class="k">Hard rules broken</span></div>
      <div class="stat ${s.overfull.length ? "bad" : ""}"><span class="v">${s.openBeds}</span><span class="k">Open beds</span></div>
      <div class="stat"><span class="v">${s.score.toFixed(2)}</span><span class="k">Score (lower = better)</span></div>`;

    // Rooms
    const sort = $("#sort").value;
    const rooms = [...Engine.state.rooms];
    if (sort === "placed") rooms.sort((a, b) => (a.placed_name || "￿").localeCompare(b.placed_name || "￿", undefined, {numeric: true}));
    if (sort === "happy") rooms.sort((a, b) => roomHappiness(a, inv).pct - roomHappiness(b, inv).pct);

    $("#rooms").innerHTML = rooms.map(r => {
      const h = roomHappiness(r, inv);
      const nb = strongestNeighbor(r);
      let beds = "";
      for (let i = 0; i < Math.max(r.capacity, r.people.length); i++) {
        beds += `<span class="bed ${i >= r.capacity ? "over" : i < r.people.length ? "full" : ""}"></span>`;
      }
      return `<div class="room ${r.people.length > r.capacity ? "overfull" : ""}" data-drop data-room="${r.id}" id="room-${r.id}">
        <span class="drop-delta"></span>
        <div class="room-h">
          <div class="labels">
            <input class="placed-input" data-nodrag data-rename="${r.id}" value="${UI.esc(r.placed_name || "")}" placeholder="Hotel room #">
            <div class="internal">${UI.esc(r.internal_name)}</div>
          </div>
          <div class="beds" title="${r.people.length} of ${r.capacity} beds">${beds}</div>
        </div>
        <div class="room-body">${r.people.map(pid => UI.chip(pid, inv)).join("")}</div>
        <div class="room-f">
          ${h.total ? `<span title="${h.met} of ${h.total} requests from this room are met inside it">
            <span class="happy"><i style="width:${Math.round(h.pct * 100)}%"></i></span> ${h.met}/${h.total}
          </span>` : `<span>${r.people.length ? "No requests" : "Empty"}</span>`}
          ${nb ? `<span class="link" data-flash="${nb.room.id}" title="Most cross-requests with this room. A good candidate for a connecting door">⇄ ${UI.esc(Engine.roomLabel(nb.room))} (${nb.score})</span>` : ""}
        </div>
      </div>`;
    }).join("");

    // Pool
    $("#pool").innerHTML = Engine.state.unplaced.length
      ? Engine.state.unplaced.map(pid => UI.chip(pid, inv)).join("")
      : `<span class="empty">Drag students here to set them aside while you rearrange</span>`;
    $("#pool-count").textContent = Engine.state.unplaced.length || "";

    renderAttention(s);
    $("#log").innerHTML = Engine.state.log.slice(0, 12).map(l => `<li>${UI.esc(l.label)}</li>`).join("")
      || `<li class="text-muted">No edits yet</li>`;

    $("#undo").disabled = !Engine.canUndo();
    $("#redo").disabled = !Engine.canRedo();

    renderInspector();
    applySearch();
    syncChromeHeight();
  }

  function renderAttention(s) {
    const name = pid => UI.esc(Engine.peopleById[pid].name);
    const items = [];
    s.violations.forEach(v => items.push(`<li data-select="${UI.esc(v.requestor)}"><span class="tag hard">Rule</span>
      ${name(v.requestor)} ${v.type === "forbid" ? "must not be with" : "must be with"} ${name(v.requestee)}</li>`));
    if (s.unplaced) items.push(`<li><span class="tag cap">Pool</span>${s.unplaced} student${s.unplaced > 1 ? "s" : ""} not in a room</li>`);
    s.overfull.forEach(r => items.push(`<li data-flash="${r.id}"><span class="tag cap">Over</span>${UI.esc(Engine.roomLabel(r))} has ${r.people.length}/${r.capacity}</li>`));
    s.zeroGranted.forEach(pid => items.push(`<li data-select="${UI.esc(pid)}" title="None of their requests are granted"><span class="tag zero">0 met</span>${name(pid)}</li>`));
    s.repelBroken.forEach(v => items.push(`<li data-select="${UI.esc(v.requestor)}"><span class="tag repel">Not with</span>
      ${name(v.requestor)} is with ${name(v.requestee)}</li>`));
    const unnamed = Engine.state.rooms.filter(r => !r.placed_name).length;
    if (unnamed) items.push(`<li data-focus-unnamed><span class="tag place">Hotel</span>${unnamed} room${unnamed > 1 ? "s" : ""} without a hotel room #</li>`);
    $("#attn").innerHTML = items.join("") || `<li class="text-success">Everything looks good ✓</li>`;
  }

  function where(pid, inv) {
    const rid = inv[pid];
    return rid === undefined ? "unplaced" : Engine.roomLabel(Engine.room(rid));
  }

  function renderInspector() {
    const el = $("#inspector");
    $$(".chip.selected, .chip.related").forEach(c => c.classList.remove("selected", "related"));
    if (!selected) {
      el.innerHTML = `<div class="insp-empty">Click a student to see their requests, where those people are, and the best moves for them.<br><br>
        Hover a student to see their threads.</div>`;
      return;
    }
    const inv = Engine.assignment();
    const d = Engine.studentDetail(selected, inv);
    const status = Engine.studentStatus(selected, inv);
    $$(`.chip[data-pid="${CSS.escape(selected)}"]`).forEach(c => c.classList.add("selected"));
    d.links.forEach(l => $$(`.chip[data-pid="${CSS.escape(l.otherId)}"]`).forEach(c => c.classList.add("related")));

    const mark = l => l.satisfied === null ? `<span class="na">·</span>` : l.satisfied ? `<span class="ok">✓</span>` : `<span class="no">✗</span>`;
    const kind = l => l.type === "attract" ? "" : `<span class="kind ${l.type}">${{repel: "not with", forbid: "never", require: "must"}[l.type]}</span>`;
    const row = l => `<li data-select="${UI.esc(l.otherId)}">${mark(l)}<span>${UI.esc(l.other.name)}</span>${kind(l)}<span class="where">${UI.esc(where(l.otherId, inv))}</span></li>`;
    const out = d.links.filter(l => l.dir === "out"), inc = d.links.filter(l => l.dir === "in");

    el.innerHTML = `
      <div class="p-2">
        <div class="d-flex align-items-start">
          <div class="flex-fill">
            <p class="insp-name">${UI.esc(d.person.name)}</p>
            <div class="insp-sub">${UI.STATUS_TEXT[status]} · in <b>${UI.esc(where(selected, inv))}</b></div>
          </div>
          <button class="close" data-deselect>&times;</button>
        </div>
      </div>
      <div class="panel-h">Requested (${d.wantsMet}/${d.wantsTotal} met)</div>
      <ul class="rel px-1">${out.map(row).join("") || `<li class="text-muted">No requests submitted</li>`}</ul>
      <div class="panel-h">Requested by (${d.wantedByMet}/${d.wantedByTotal} met)</div>
      <ul class="rel px-1">${inc.map(row).join("") || `<li class="text-muted">Nobody</li>`}</ul>
      <div class="panel-h">Best moves <small class="text-muted">computed live</small></div>
      <ul class="sugg px-2" id="sugg"><li class="text-muted">Calculating…</li></ul>
      <div class="p-2">
        <button class="btn btn-sm btn-outline-warning btn-block" data-unplace="${UI.esc(selected)}">Set aside in Unplaced</button>
      </div>`;

    // Suggestions: best single moves + best swaps, ranked by score change
    const forPid = selected;
    requestAnimationFrame(() => {
      if (selected !== forPid || !$("#sugg")) return;
      const opts = [];
      const from = inv[forPid];
      Engine.state.rooms.forEach(r => {
        if (r.id === from) return;
        if (r.people.length < r.capacity) opts.push({kind: "move", room: r, p: Engine.preview(forPid, r.id)});
        if (from !== undefined) {
          r.people.forEach(other => opts.push({kind: "swap", room: r, other, p: Engine.preview(forPid, r.id, other)}));
        }
      });
      const ranked = opts.sort((a, b) => a.p.deltaScore - b.p.deltaScore).slice(0, 5);
      $("#sugg").innerHTML = ranked.map(o => {
        const g = o.p.deltaGranted, z = o.p.deltaZero, h = o.p.deltaViolations;
        const bits = [];
        if (g) bits.push(`${g > 0 ? "+" : ""}${g} granted`);
        if (z) bits.push(`${z < 0 ? "fixes " + -z : "+" + z} with none`);
        if (h) bits.push(`<b class="text-danger">${h > 0 ? "breaks" : "fixes"} hard rule</b>`);
        const better = o.p.deltaScore < -1e-9;
        const label = o.kind === "move"
          ? `Move to <b>${UI.esc(Engine.roomLabel(o.room))}</b>`
          : `Swap with <b>${UI.esc(Engine.peopleById[o.other].name)}</b> <span class="text-muted">(${UI.esc(Engine.roomLabel(o.room))})</span>`;
        const data = o.kind === "move" ? `data-move="${o.room.id}"` : `data-swap="${UI.esc(o.other)}"`;
        return `<li><div class="what">${label}<small>${bits.join(" · ") || "no change"}</small></div>
          <button class="btn ${better ? "btn-success" : "btn-outline-secondary"}" ${data}>${o.kind === "move" ? "Move" : "Swap"}</button></li>`;
      }).join("") || `<li class="text-muted">No moves available</li>`;
      if (from !== undefined && ranked.length && ranked[0].p.deltaScore >= -1e-9) {
        $("#sugg").insertAdjacentHTML("afterbegin", `<li class="text-muted small d-block">Already in the best spot a single move can find.</li>`);
      }
    });
  }

  function applySearch() {
    const q = $("#search").value.trim().toLowerCase();
    $$(".chip").forEach(c => {
      const hit = q && c.querySelector(".name").textContent.toLowerCase().includes(q);
      c.classList.toggle("search-hit", !!hit);
      c.classList.toggle("dim", !!q && !hit);
    });
  }

  // ---- Threads on hover -------------------------------------------------------

  function chipFor(pid, excludeEl) {
    return $$(`.room .chip[data-pid="${CSS.escape(pid)}"], .pool .chip[data-pid="${CSS.escape(pid)}"]`)
      .find(e => e !== excludeEl && !e.classList.contains("drag-ghost"));
  }

  function linksFor(pid, inv, excludeEl) {
    return Engine.studentDetail(pid, inv).links.map(l => ({
      el: chipFor(l.otherId, excludeEl),
      type: l.type, dir: l.dir, satisfied: l.satisfied, name: l.other.name,
    }));
  }

  document.addEventListener("mouseover", e => {
    if (document.body.classList.contains("is-dragging")) return;
    const c = e.target.closest(".chip");
    if (!c || c.classList.contains("drag-ghost")) return;
    const r = c.getBoundingClientRect();
    Threads.draw({x: r.left + r.width / 2, y: r.top + r.height / 2}, linksFor(c.dataset.pid, Engine.assignment(), c));
  });
  document.addEventListener("mouseout", e => {
    if (document.body.classList.contains("is-dragging")) return;
    const c = e.target.closest(".chip");
    if (c && !(e.relatedTarget && e.relatedTarget.closest(".chip") === c)) Threads.clear();
  });
  $("#main").addEventListener("scroll", () => { if (!dragCtx) Threads.clear(); }, {passive: true});

  // ---- Drag & drop ------------------------------------------------------------

  Drag.attach({
    root: document.body,
    item: ".room .chip, .pool .chip",
    drop: "[data-drop]",
    scroller: $("#main"),
    onStart(itemEl) {
      const pid = itemEl.dataset.pid;
      const from = Engine.assignment()[pid];
      // Precompute the delta for every possible destination once per drag
      const deltas = {};
      Engine.state.rooms.forEach(r => { if (r.id !== from) deltas[r.id] = Engine.preview(pid, r.id); });
      const best = Object.entries(deltas)
        .filter(([, p]) => p.deltaScore < -1e-9)
        .sort((a, b) => a[1].deltaScore - b[1].deltaScore)
        .slice(0, 2).map(([id]) => Number(id));

      $$(".room").forEach(el => {
        const id = Number(el.dataset.room);
        const tag = el.querySelector(".drop-delta");
        el.classList.toggle("best", best.includes(id));
        if (id === from) { tag.textContent = "current"; tag.className = "drop-delta"; return; }
        const p = deltas[id];
        if (p.deltaViolations > 0) { tag.textContent = "⚠ hard rule"; tag.className = "drop-delta hard"; return; }
        const g = p.deltaGranted;
        tag.textContent = g ? `${g > 0 ? "+" : ""}${g} granted` : (p.deltaScore < -1e-9 ? "better" : "±0");
        tag.className = "drop-delta " + (p.deltaScore < -1e-9 ? "good" : p.deltaScore > 1e-9 ? "bad" : "");
      });
      dragCtx = {pid, from};
      if (selected !== pid) { selected = pid; renderInspector(); }
    },
    onMove({x, y, itemEl, dropEl, overItemEl}) {
      const {pid, from} = dragCtx;
      $$(".room.hover, .pool.hover").forEach(e => e.classList.remove("hover", "swap"));
      $$(".chip.swap-target").forEach(e => e.classList.remove("swap-target"));

      let target = null, swapWith = null;
      if (dropEl) {
        target = dropEl.dataset.room === "pool" ? null : Number(dropEl.dataset.room);
        dropEl.classList.add("hover");
        const overPid = overItemEl && overItemEl.dataset.pid;
        if (overPid && target !== null && target !== from && from !== undefined) {
          swapWith = overPid;
          overItemEl.classList.add("swap-target");
          dropEl.classList.add("swap");
        }
      }

      // Threads reflect the hypothetical placement
      let inv = Engine.assignment();
      let label = "";
      if (dropEl && target !== (from ?? null)) {
        const p = Engine.preview(pid, target, swapWith);
        inv = p.inv;
        const name = Engine.peopleById[pid].name;
        const dest = target === null ? "Unplaced" : Engine.roomLabel(Engine.room(target));
        label = swapWith ? `Swap ${name} ⇄ ${Engine.peopleById[swapWith].name}` : `Move ${name} → ${dest}`;
        label += ` · granted ${p.deltaGranted >= 0 ? "+" : ""}${p.deltaGranted}`;
        if (p.deltaZero) label += ` · got-none ${p.deltaZero > 0 ? "+" : ""}${p.deltaZero}`;
        if (p.deltaViolations > 0) label += " · ⚠ breaks hard rule";
        setStatDeltas(p);
      } else {
        setStatDeltas(null);
      }
      $("#preview-bar").textContent = label || "Drop on a room to move, on a student to swap";
      Threads.draw({x, y}, linksFor(pid, inv, itemEl));
    },
    onDrop({dropEl, overItemEl}) {
      const {pid, from} = dragCtx;
      if (!dropEl) return;
      const target = dropEl.dataset.room === "pool" ? null : Number(dropEl.dataset.room);
      const overPid = overItemEl && overItemEl.dataset.pid;
      const before = Engine.summary();
      const lastEntry = Engine.state.log[0];
      if (overPid && target !== null && target !== from && from !== undefined) Engine.swap(pid, overPid);
      else Engine.move(pid, target);
      if (Engine.state.log[0] !== lastEntry) {
        const g = Engine.summary().granted - before.granted;
        UI.toast(`${Engine.state.log[0].label}${g ? ` (${g > 0 ? "+" : ""}${g} granted)` : ""}`);
      }
    },
    onEnd() {
      dragCtx = null;
      Threads.clear();
      setStatDeltas(null);
      $$(".room.hover, .room.best, .pool.hover").forEach(e => e.classList.remove("hover", "best", "swap"));
      $$(".chip.swap-target").forEach(e => e.classList.remove("swap-target"));
    },
    onClick(itemEl) {
      selected = selected === itemEl.dataset.pid ? null : itemEl.dataset.pid;
      renderInspector();
    },
  });

  function setStatDeltas(p) {
    const set = (id, html) => { const el = document.querySelector(`#${id} .pd`); if (el) el.innerHTML = html; };
    set("st-granted", p ? UI.fmtDelta(p.deltaGranted) : "");
    set("st-zero", p ? UI.fmtDelta(p.deltaZero, 0, true) : "");
    set("st-hard", p ? UI.fmtDelta(p.deltaViolations, 0, true) : "");
  }

  // ---- Save status --------------------------------------------------------------

  Engine.onStatus((status, detail) => {
    const el = $("#save-status");
    el.className = `save-status ${status}`;
    if (status === "saving") el.textContent = "Saving…";
    if (status === "saved") el.textContent = "All changes saved";
    if (status === "error") {
      el.innerHTML = `${UI.esc(detail)} <a href="">Reload</a>`;
      render();
    }
  });

  // ---- Other interactions -------------------------------------------------------

  function toastLast() {
    if (Engine.state.log[0]) UI.toast(Engine.state.log[0].label);
  }

  document.addEventListener("click", e => {
    const t = e.target;
    const sel = t.closest("[data-select]");
    if (sel) { selected = sel.dataset.select; renderInspector(); scrollToStudent(selected); return; }
    const fl = t.closest("[data-flash]");
    if (fl) { flashRoom(fl.dataset.flash); return; }
    if (t.closest("[data-focus-unnamed]")) {
      const input = $$(".placed-input").find(i => !i.value);
      if (input) { input.scrollIntoView({block: "center", behavior: "smooth"}); input.focus(); }
      return;
    }
    if (t.closest("[data-deselect]")) { selected = null; renderInspector(); return; }
    if (t.dataset.move) { Engine.move(selected, Number(t.dataset.move)); toastLast(); return; }
    if (t.dataset.swap) { Engine.swap(selected, t.dataset.swap); toastLast(); return; }
    if (t.dataset.unplace) { Engine.move(t.dataset.unplace, null); toastLast(); }
  });

  function scrollToStudent(pid) {
    const c = chipFor(pid);
    if (c) c.scrollIntoView({block: "center", behavior: "smooth"});
  }

  function flashRoom(id) {
    const el = $(`#room-${id}`);
    if (!el) return;
    el.scrollIntoView({block: "center", behavior: "smooth"});
    el.classList.add("flash");
    setTimeout(() => el.classList.remove("flash"), 1200);
  }

  document.addEventListener("keydown", e => {
    if (e.target.dataset && e.target.dataset.rename && e.key === "Enter") e.target.blur();
    if (e.key === "Escape" && !dragCtx && selected) { selected = null; renderInspector(); }
  });
  document.addEventListener("change", e => {
    if (e.target.dataset.rename) {
      Engine.rename(Number(e.target.dataset.rename), e.target.value);
      toastLast();
    }
  });

  $("#search").addEventListener("input", applySearch);
  $("#sort").addEventListener("change", render);
  const dismissToast = () => $$(".toast-msg").forEach(t => t.remove());
  $("#undo").addEventListener("click", () => { dismissToast(); Engine.undo(); });
  $("#redo").addEventListener("click", () => { dismissToast(); Engine.redo(); });
  window.addEventListener("keydown", e => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") dismissToast(); });

  Engine.onChange(render);
  render();
})();
