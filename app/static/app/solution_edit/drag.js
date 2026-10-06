/*
 * Minimal pointer-based drag & drop (no library), so we control the ghost
 * element and get continuous coordinates for drawing threads.
 *
 * Drag.attach({
 *   root,             element to listen on (delegated)
 *   item,             selector for draggable things
 *   drop,             selector for drop zones
 *   scroller,         element to auto-scroll (default: window)
 *   onStart(itemEl),  return false to cancel
 *   onMove({x, y, itemEl, dropEl, overItemEl}),
 *   onDrop({itemEl, dropEl, overItemEl}),
 *   onEnd(),
 *   onClick(itemEl)   fired when the pointer didn't travel far enough to drag
 * })
 */
(function () {
  const THRESHOLD = 5;

  function attach(opts) {
    let pending = null, dragging = null, ghost = null, lastMove = null, scrollTimer = null;

    opts.root.addEventListener("pointerdown", e => {
      if (e.button !== 0) return;
      const itemEl = e.target.closest(opts.item);
      if (!itemEl || e.target.closest("[data-nodrag]")) return;
      e.preventDefault(); // don't start a text selection
      pending = {itemEl, x: e.clientX, y: e.clientY};
    });

    window.addEventListener("pointermove", e => {
      if (pending && !dragging) {
        if (Math.hypot(e.clientX - pending.x, e.clientY - pending.y) < THRESHOLD) return;
        if (opts.onStart && opts.onStart(pending.itemEl) === false) { pending = null; return; }
        dragging = pending;
        const r = dragging.itemEl.getBoundingClientRect();
        dragging.offX = pending.x - r.left;
        dragging.offY = pending.y - r.top;
        ghost = dragging.itemEl.cloneNode(true);
        ghost.classList.add("drag-ghost");
        ghost.style.width = r.width + "px";
        document.body.appendChild(ghost);
        dragging.itemEl.classList.add("drag-source");
        document.body.classList.add("is-dragging");
        scrollTimer = setInterval(autoScroll, 16);
      }
      if (!dragging) return;
      e.preventDefault();
      lastMove = {x: e.clientX, y: e.clientY};
      update();
    });

    window.addEventListener("pointerup", () => {
      if (dragging) {
        const hit = hitTest();
        if (opts.onDrop) opts.onDrop({itemEl: dragging.itemEl, ...hit});
        finish();
        dragging = null;
      } else if (pending && opts.onClick) {
        opts.onClick(pending.itemEl);
      }
      pending = null;
    });

    window.addEventListener("keydown", e => {
      if (e.key === "Escape" && dragging) { finish(); dragging = null; pending = null; }
    });

    (opts.scroller || window).addEventListener("scroll", () => { if (dragging) update(); }, {passive: true});

    function hitTest() {
      if (!lastMove) return {dropEl: null, overItemEl: null};
      const under = document.elementFromPoint(lastMove.x, lastMove.y);
      const dropEl = under ? under.closest(opts.drop) : null;
      let overItemEl = under ? under.closest(opts.item) : null;
      if (overItemEl === dragging.itemEl) overItemEl = null;
      return {dropEl, overItemEl};
    }

    function update() {
      if (!lastMove) return;
      ghost.style.transform = `translate(${lastMove.x - dragging.offX}px, ${lastMove.y - dragging.offY}px) rotate(-2deg)`;
      if (opts.onMove) opts.onMove({x: lastMove.x, y: lastMove.y, itemEl: dragging.itemEl, ...hitTest()});
    }

    function autoScroll() {
      if (!lastMove) return;
      const s = opts.scroller;
      const box = s ? s.getBoundingClientRect() : {top: 56, bottom: window.innerHeight};
      const edge = 70;
      let dy = 0;
      if (lastMove.y < box.top + edge) dy = -Math.ceil((box.top + edge - lastMove.y) / 6);
      else if (lastMove.y > box.bottom - edge) dy = Math.ceil((lastMove.y - (box.bottom - edge)) / 6);
      if (!dy) return;
      s ? (s.scrollTop += dy) : window.scrollBy(0, dy);
    }

    function finish() {
      clearInterval(scrollTimer);
      if (ghost) ghost.remove();
      ghost = null;
      dragging.itemEl.classList.remove("drag-source");
      document.body.classList.remove("is-dragging");
      if (opts.onEnd) opts.onEnd();
    }
  }

  window.Drag = {attach};
})();
