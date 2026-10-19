/* UI helpers for the solution editor: student chips, toasts, deltas. */
(function () {
  function esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  }

  const STATUS_TEXT = {
    all: "All requests granted",
    some: "Some requests granted",
    zero: "No requests granted",
    none: "Made no requests",
    violation: "Breaks a hard rule",
    unplaced: "Not in a room",
  };

  function chip(pid, inv, extraClass = "") {
    const d = Engine.studentDetail(pid, inv);
    const status = Engine.studentStatus(pid, inv);
    let pips = "";
    for (let i = 0; i < d.wantsTotal; i++) pips += `<span class="pip ${i < d.wantsMet ? "on" : ""}"></span>`;
    const icon = status === "violation" ? `<span class="icon">⚠</span>`
      : status === "none" ? `<span class="icon">–</span>` : "";
    const tip = `${STATUS_TEXT[status]} · ${d.wantsMet}/${d.wantsTotal} requests met · requested by ${d.wantedByTotal}`;
    return `<div class="chip s-${status} ${extraClass}" data-pid="${esc(pid)}" title="${esc(tip)}">
      ${icon}<span class="name">${esc(d.person.name)}</span><span class="pips">${pips}</span>
    </div>`;
  }

  let toastTimer;
  function toast(msg, withUndo = true) {
    document.querySelectorAll(".toast-msg").forEach(t => t.remove());
    const el = document.createElement("div");
    el.className = "toast-msg";
    el.innerHTML = `<span>${esc(msg)}</span>${withUndo ? `<a data-undo>Undo</a>` : ""}`;
    document.body.appendChild(el);
    const u = el.querySelector("[data-undo]");
    if (u) u.addEventListener("click", () => { Engine.undo(); el.remove(); });
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.remove(), 4000);
  }

  function fmtDelta(n, digits = 0, invert = false) {
    if (!n || Math.abs(n) < 1e-9) return "";
    const good = invert ? n < 0 : n > 0;
    const v = digits ? Math.abs(n).toFixed(digits) : Math.abs(n);
    return `<span class="delta ${good ? "up" : "down"}">${n > 0 ? "+" : "−"}${v}</span>`;
  }

  window.UI = {chip, esc, toast, fmtDelta, STATUS_TEXT};
})();
