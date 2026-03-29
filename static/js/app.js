(() => {
  const links = document.querySelectorAll('a[href^="#"]');
  links.forEach((link) => {
    link.addEventListener("click", (e) => {
      const href = link.getAttribute("href");
      if (!href || href.length < 2) return;
      const el = document.querySelector(href);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      const navbar = document.querySelector(".navbar-collapse");
      if (navbar && navbar.classList.contains("show")) {
        navbar.classList.remove("show");
      }
    });
  });

  const panels = document.querySelectorAll(".hero-banner-panel");
  if (panels.length) {
    const isDesktop = window.matchMedia("(min-width: 992px)").matches;
    const offsets = isDesktop
      ? ["0.35rem", "1.25rem", "2.25rem", "3.25rem"]
      : ["0.25rem", "0.75rem", "1.25rem", "1.75rem"];

    panels.forEach((panel) => {
      const pick = offsets[Math.floor(Math.random() * offsets.length)];
      panel.style.setProperty("--hero-panel-bottom", pick);
    });
  }

  const drawerEl = document.getElementById("registrPoOffcanvas");
  const drawerButtons = document.querySelectorAll("[data-registr-po-open]");
  if (drawerEl && drawerButtons.length) {
    let prevOverflow = "";

    const openDrawer = () => {
      if (drawerEl.classList.contains("is-open")) return;
      prevOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      drawerEl.classList.add("is-open");
      drawerEl.setAttribute("aria-hidden", "false");
    };

    const closeDrawer = () => {
      drawerEl.classList.remove("is-open");
      drawerEl.setAttribute("aria-hidden", "true");
      document.body.style.overflow = prevOverflow;
    };

    drawerButtons.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        openDrawer();
      });
    });

    drawerEl.querySelectorAll("[data-registr-po-close]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        closeDrawer();
      });
    });

    window.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") closeDrawer();
    });
  }
})();
