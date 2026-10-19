/* Shared UI helpers: navbar (matches base.html), student chips, toasts. */
(function () {
  const STATIC = "../../app/static/app/";

  function navbar(active) {
    const links = [
      ["index.html", "Overview"],
      ["a_workbench.html", "A · Workbench"],
      ["b_hotel.html", "B · Hotel placement"],
      ["c_focus.html", "C · Fix-it queue"],
    ].map(([href, label]) =>
      `<li class="nav-item ${href === active ? "active" : ""}"><a class="nav-link" href="${href}">${label}</a></li>`
    ).join("");

    document.body.insertAdjacentHTML("afterbegin", `
      <nav class="navbar navbar-expand-md navbar-dark bg-primary fixed-top">
        <a class="navbar-brand py-0" href="index.html">
          <img src="${STATIC}favicon.svg" width="32" height="32" class="d-inline-block align-top" alt="">
          <span class="font-weight-bold">Roomies</span>
        </a>
        <ul class="navbar-nav mr-auto ml-3">${links}</ul>
        <ul class="navbar-nav">
          <li class="nav-item active"><a class="nav-link" href="#" id="reset-demo">Reset demo data</a></li>
          <li class="nav-item active"><a class="nav-link" href="#">Database</a></li>
          <li class="nav-item active"><a class="nav-link" href="#">Logout</a></li>
        </ul>
      </nav>`);
    document.getElementById("reset-demo").addEventListener("click", e => {
      e.preventDefault();
      if (confirm("Reset the dummy solution to its machine-generated state?")) Engine.reset();
    });
  }

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
      : status === "none" ? `<span class="icon" title="No requests">–</span>` : "";
    const tip = `${STATUS_TEXT[status]} · ${d.wantsMet}/${d.wantsTotal} requests met · wanted by ${d.wantedByTotal}`;
    return `<div class="chip s-${status} ${extraClass}" data-pid="${pid}" title="${esc(tip)}">
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

  window.UI = {navbar, chip, esc, toast, fmtDelta, STATUS_TEXT};
})();
