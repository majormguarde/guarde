(() => {
  const getCookie = (name) => {
    const parts = (`; ${document.cookie || ""}`).split(`; ${name}=`);
    if (parts.length < 2) return "";
    return (parts.pop() || "").split(";").shift() || "";
  };

  const setCookie = (name, value, maxAgeSeconds) => {
    const encoded = encodeURIComponent(value || "");
    const maxAge = Number.isFinite(maxAgeSeconds) && maxAgeSeconds > 0 ? `; max-age=${Math.floor(maxAgeSeconds)}` : "";
    document.cookie = `${name}=${encoded}${maxAge}; path=/; samesite=lax`;
  };

  const consentCookieName = "guarde_consent";
  const hasConsent = () => getCookie(consentCookieName) === "1";

  const consentModalEl = document.getElementById("consentModal");
  if (consentModalEl && typeof window.bootstrap !== "undefined" && window.bootstrap.Modal) {
    const checkEl = document.getElementById("consentCheck");
    const acceptBtn = document.getElementById("consentAccept");
    const modal = new window.bootstrap.Modal(consentModalEl, { backdrop: "static", keyboard: false, focus: true });

    const syncUi = () => {
      const ok = hasConsent();
      document.body.classList.toggle("consent-required", !ok);
      if (checkEl) checkEl.checked = false;
      if (acceptBtn) acceptBtn.disabled = true;
    };

    const ensureShown = () => {
      if (!hasConsent()) modal.show();
    };

    const blockIfNoConsent = (e) => {
      if (hasConsent()) return;
      if (consentModalEl.contains(e.target)) return;
      e.preventDefault();
      e.stopPropagation();
      ensureShown();
    };

    syncUi();
    if (!hasConsent()) {
      modal.show();
      document.addEventListener("click", blockIfNoConsent, true);
      document.addEventListener("submit", blockIfNoConsent, true);
      window.addEventListener(
        "keydown",
        (e) => {
          if (hasConsent()) return;
          if (e.key !== "Tab") return;
          ensureShown();
        },
        true
      );
    }

    consentModalEl.addEventListener("hide.bs.modal", (ev) => {
      if (!hasConsent()) ev.preventDefault();
    });

    if (checkEl && acceptBtn) {
      checkEl.addEventListener("change", () => {
        acceptBtn.disabled = !checkEl.checked;
      });
      acceptBtn.addEventListener("click", () => {
        if (!checkEl.checked) {
          ensureShown();
          return;
        }
        setCookie(consentCookieName, "1", 365 * 24 * 60 * 60);
        document.body.classList.remove("consent-required");
        modal.hide();
      });
    }
  }

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

  document.addEventListener(
    "submit",
    (ev) => {
      const form = ev.target;
      if (!(form instanceof HTMLFormElement)) return;
      if (!form.hasAttribute("data-submit-guard")) return;
      if (form.dataset.submitted === "1") {
        ev.preventDefault();
        ev.stopPropagation();
        return;
      }
      form.dataset.submitted = "1";
      form.setAttribute("aria-busy", "true");
      form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach((btn) => {
        btn.disabled = true;
        btn.setAttribute("aria-disabled", "true");
      });
    },
    true
  );

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
        if (drawerEl.classList.contains("is-open")) {
          closeDrawer();
          return;
        }
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

  const supportDrawerEl = document.getElementById("supportOffcanvas");
  const supportButtons = document.querySelectorAll("[data-support-open]");
  if (supportDrawerEl && supportButtons.length) {
    let prevOverflow2 = "";

    const openSupport = () => {
      if (supportDrawerEl.classList.contains("is-open")) return;
      prevOverflow2 = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      supportDrawerEl.classList.add("is-open");
      supportDrawerEl.setAttribute("aria-hidden", "false");
      document.body.classList.add("support-drawer-open");
    };

    const closeSupport = () => {
      supportDrawerEl.classList.remove("is-open");
      supportDrawerEl.setAttribute("aria-hidden", "true");
      document.body.style.overflow = prevOverflow2;
      document.body.classList.remove("support-drawer-open");
    };

    supportButtons.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (supportDrawerEl.classList.contains("is-open")) {
          closeSupport();
          return;
        }
        openSupport();
      });
    });

    supportDrawerEl.querySelectorAll("[data-support-close]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        closeSupport();
      });
    });

    window.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") closeSupport();
    });
  }

  const supportForm = document.getElementById("supportForm");
  if (supportForm) {
    const fileInput = supportForm.querySelector('input[type="file"][name="files"]');
    const noteInput = supportForm.querySelector('input[name="files_note"]');
    const btnPaste = supportForm.querySelector("[data-media-paste]");
    const btnAudio = supportForm.querySelector("[data-media-audio]");
    const btnVideo = supportForm.querySelector("[data-media-video]");
    let armedPaste = false;

    const addFiles = (files) => {
      if (!fileInput || !files || !files.length) return;
      const dt = new DataTransfer();
      Array.from(fileInput.files || []).forEach((f) => dt.items.add(f));
      Array.from(files).forEach((f) => dt.items.add(f));
      fileInput.files = dt.files;
    };

    const isImageFile = (f) => {
      if (!f) return false;
      const t = (f.type || "").toLowerCase();
      if (t.startsWith("image/")) return true;
      const n = (f.name || "").toLowerCase();
      return n.endsWith(".png") || n.endsWith(".jpg") || n.endsWith(".jpeg") || n.endsWith(".webp") || n.endsWith(".gif") || n.endsWith(".bmp");
    };

    const extFromMime = (mime, fallback) => {
      const m = (mime || "").toLowerCase();
      if (m.includes("png")) return "png";
      if (m.includes("jpeg") || m.includes("jpg")) return "jpg";
      if (m.includes("webp")) return "webp";
      if (m.includes("gif")) return "gif";
      if (m.includes("ogg")) return "ogg";
      if (m.includes("mp4")) return "mp4";
      if (m.includes("quicktime")) return "mov";
      return fallback;
    };

    const fileName = (prefix, mime) => {
      const ext = extFromMime(mime, "webm");
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      return `${prefix}_${ts}.${ext}`;
    };

    const tryReadClipboardImage = async () => {
      if (!navigator.clipboard || typeof navigator.clipboard.read !== "function") return null;
      const items = await navigator.clipboard.read();
      for (const item of items) {
        const type = (item.types || []).find((t) => (t || "").startsWith("image/"));
        if (!type) continue;
        const blob = await item.getType(type);
        return new File([blob], fileName("paste", type), { type });
      }
      return null;
    };

    const extractImageFilesFromPaste = (e) => {
      const dt = e.clipboardData;
      if (!dt || !dt.items) return;
      const files = [];
      for (const it of dt.items) {
        if (!it || it.kind !== "file") continue;
        const f = it.getAsFile();
        if (!isImageFile(f)) continue;
        files.push(new File([f], fileName("paste", f.type), { type: f.type || "image/png" }));
      }
      return files;
    };

    const handlePasteEvent = (e) => {
      const files = extractImageFilesFromPaste(e);
      if (files && files.length) {
        e.preventDefault();
        addFiles(files);
        armedPaste = false;
      }
    };

    supportForm.addEventListener("paste", handlePasteEvent);
    document.addEventListener(
      "paste",
      (e) => {
        if (!armedPaste) return;
        if (!supportForm.contains(document.activeElement)) return;
        handlePasteEvent(e);
      },
      true
    );

    if (btnPaste) {
      btnPaste.addEventListener("click", async () => {
        try {
          const f = await tryReadClipboardImage();
          if (f) {
            addFiles([f]);
            return;
          }
        } catch (e) {
        }
        armedPaste = true;
        if (noteInput) noteInput.focus();
        alert("Нажмите Ctrl+V, чтобы вставить изображение из буфера обмена.");
      });
    }

    const pickMimeType = (candidates) => {
      if (!window.MediaRecorder || typeof window.MediaRecorder.isTypeSupported !== "function") return "";
      for (const t of candidates) {
        if (window.MediaRecorder.isTypeSupported(t)) return t;
      }
      return "";
    };

    const makeRecorder = async (kind) => {
      if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
        throw new Error("no_getusermedia");
      }
      const constraints =
        kind === "audio" ? { audio: true } : { audio: true, video: { width: { ideal: 1280 }, height: { ideal: 720 } } };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      const mimeType =
        kind === "audio"
          ? pickMimeType(["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"])
          : pickMimeType(["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"]);
      const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      const chunks = [];
      rec.addEventListener("dataavailable", (ev) => {
        if (ev.data && ev.data.size) chunks.push(ev.data);
      });
      return { rec, stream, chunks, mimeType };
    };

    const stopTracks = (stream) => {
      try {
        (stream.getTracks ? stream.getTracks() : []).forEach((t) => t.stop());
      } catch (e) {
      }
    };

    const bindRecordButton = (btn, kind) => {
      if (!btn) return;
      let state = null;
      const idleText = btn.textContent;
      const idleClassName = btn.className;
      const start = async () => {
        try {
          state = await makeRecorder(kind);
        } catch (e) {
          alert(kind === "audio" ? "Не удалось получить доступ к микрофону." : "Не удалось получить доступ к камере.");
          state = null;
          return;
        }
        btn.className = idleClassName;
        btn.classList.remove("btn-outline-secondary");
        btn.classList.add("btn-danger", "recording-indicator");
        btn.textContent = "● REC";
        state.rec.start();
      };
      const stop = () => {
        if (!state) return;
        state.rec.addEventListener(
          "stop",
          () => {
            const blob = new Blob(state.chunks, { type: state.mimeType || (kind === "audio" ? "audio/webm" : "video/webm") });
            addFiles([new File([blob], fileName(kind, blob.type), { type: blob.type })]);
            stopTracks(state.stream);
            state = null;
            btn.className = idleClassName;
            btn.textContent = idleText;
          },
          { once: true }
        );
        try {
          state.rec.stop();
        } catch (e) {
          stopTracks(state.stream);
          state = null;
          btn.className = idleClassName;
          btn.textContent = idleText;
        }
      };
      btn.addEventListener("click", () => {
        if (state) stop();
        else start();
      });
    };

    bindRecordButton(btnAudio, "audio");
    bindRecordButton(btnVideo, "video");
  }
})();
