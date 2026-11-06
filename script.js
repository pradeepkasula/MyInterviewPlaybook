(function () {
  var side = document.getElementById("sidebar");
  var btn = document.getElementById("menuBtn");
  var practice = document.getElementById("practice");
  var links = Array.prototype.slice.call(document.querySelectorAll(".sidebar nav a"));

  btn.addEventListener("click", function () {
    var open = side.classList.toggle("open");
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  links.forEach(function (a) {
    a.addEventListener("click", function () { side.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); });
  });

  practice.addEventListener("change", function () {
    document.body.classList.toggle("practice-on", practice.checked);
    document.querySelectorAll("p.q.open").forEach(function (p) { p.classList.remove("open"); });
  });
  document.addEventListener("click", function (e) {
    var q = e.target.closest ? e.target.closest("p.q") : null;
    if (q && document.body.classList.contains("practice-on")) q.classList.toggle("open");
  });

  if ("IntersectionObserver" in window) {
    var byId = {};
    links.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting && byId[en.target.id]) {
          links.forEach(function (a) { a.classList.remove("active"); });
          byId[en.target.id].classList.add("active");
        }
      });
    }, { rootMargin: "0px 0px -75% 0px" });
    document.querySelectorAll(".content h1[id]").forEach(function (h) { io.observe(h); });
  }
})();
