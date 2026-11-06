(function () {
  if (window.hljs) {
    document.querySelectorAll("pre code").forEach(function (b) { hljs.highlightElement(b); });
  }
  if (window.mermaid) {
    var dark = window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches;
    mermaid.initialize({ startOnLoad: false, theme: dark ? "dark" : "default", securityLevel: "strict", flowchart: { useMaxWidth: true }, sequence: { useMaxWidth: true } });
    mermaid.run({ querySelector: "pre.mermaid" });
  }
})();
