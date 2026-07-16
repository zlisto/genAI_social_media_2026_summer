/**
 * Soft deterrent only — not real DRM.
 * Screenshots cannot be blocked on the web.
 * Copy can still be bypassed via View Source / DevTools / disabling JS.
 */
(function () {
  const root = document.documentElement;

  root.classList.add("no-select-assignment");

  const block = (event) => {
    event.preventDefault();
    return false;
  };

  ["copy", "cut", "contextmenu", "dragstart"].forEach((type) => {
    document.addEventListener(type, block, { capture: true });
  });

  document.addEventListener(
    "keydown",
    (event) => {
      const key = event.key.toLowerCase();
      const mod = event.ctrlKey || event.metaKey;
      if (!mod) return;
      if (key === "c" || key === "x" || key === "a" || key === "s" || key === "p" || key === "u") {
        event.preventDefault();
      }
    },
    { capture: true }
  );
})();
