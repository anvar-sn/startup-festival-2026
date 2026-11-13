/* ============================================================
   STARTUP LOYIHALAR FESTIVALI – 2026
   Interactive UI Engine (Theme, Countdown, Forms, Animations)
   ============================================================ */

(function () {
  "use strict";

  /* ================= 1. TUN / KUN (THEME SWITCHER) ================= */
  const html = document.documentElement;
  const savedTheme = localStorage.getItem("slf_theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initialTheme = savedTheme || (prefersDark ? "dark" : "light");

  function applyTheme(theme) {
    html.setAttribute("data-theme", theme);
    localStorage.setItem("slf_theme", theme);

    // Barcha theme-toggle tugmalaridagi ikonkani yangilash
    document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
      if (theme === "dark") {
        btn.innerHTML = '<i class="fa-solid fa-sun" style="color:#f59e0b" title="Kun rejimiga o\'tish"></i>';
        btn.setAttribute("aria-label", "Kun rejimiga o'tish");
      } else {
        btn.innerHTML = '<i class="fa-solid fa-moon" style="color:#6366f1" title="Tun rejimiga o\'tish"></i>';
        btn.setAttribute("aria-label", "Tun rejimiga o'tish");
      }
    });
  }

  applyTheme(initialTheme);

  document.addEventListener("DOMContentLoaded", () => {
    // Theme toggle tugmasini ulash
    document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const current = html.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        applyTheme(next);
      });
    });

    /* ================= 2. NAVBAR & MOBILE MENU ================= */
    const nav = document.querySelector(".site-nav");
    if (nav) {
      window.addEventListener("scroll", () => {
        nav.classList.toggle("scrolled", window.scrollY > 20);
      }, { passive: true });
    }

    const burger = document.querySelector(".nav-burger");
    const drawer = document.getElementById("mobile-drawer");
    if (burger && drawer) {
      burger.addEventListener("click", () => {
        drawer.classList.toggle("open");
        const isOpen = drawer.classList.contains("open");
        burger.innerHTML = isOpen ? '<i class="fa-solid fa-xmark"></i>' : '<i class="fa-solid fa-bars"></i>';
      });

      drawer.querySelectorAll("a").forEach((a) => {
        a.addEventListener("click", () => {
          drawer.classList.remove("open");
          if (burger) burger.innerHTML = '<i class="fa-solid fa-bars"></i>';
        });
      });
    }

    /* ================= 3. COUNTDOWN TIMER ================= */
    const cdWrap = document.querySelector("[data-countdown-date]");
    if (cdWrap) {
      const targetDateStr = cdWrap.getAttribute("data-countdown-date") || "2026-11-19T09:00:00+05:00";
      const targetTime = new Date(targetDateStr).getTime();

      const daysEl = document.getElementById("cd-days");
      const hoursEl = document.getElementById("cd-hours");
      const minsEl = document.getElementById("cd-mins");
      const secsEl = document.getElementById("cd-secs");

      function updateCountdown() {
        const now = Date.now();
        const diff = Math.max(0, targetTime - now);

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const secs = Math.floor((diff % (1000 * 60)) / 1000);

        if (daysEl) daysEl.textContent = String(days).padStart(2, "0");
        if (hoursEl) hoursEl.textContent = String(hours).padStart(2, "0");
        if (minsEl) minsEl.textContent = String(mins).padStart(2, "0");
        if (secsEl) secsEl.textContent = String(secs).padStart(2, "0");
      }

      updateCountdown();
      setInterval(updateCountdown, 1000);
    }

    /* ================= 4. SCROLL REVEAL & PROGRESS BARS ================= */
    if ("IntersectionObserver" in window) {
      const critObserver = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const fill = entry.target.querySelector(".criteria-fill");
              if (fill) {
                const targetWidth = fill.getAttribute("data-score");
                fill.style.width = targetWidth + "%";
              }
              obs.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.2 }
      );

      document.querySelectorAll(".criteria-item").forEach((item) => {
        critObserver.observe(item);
      });
    }

    /* ================= 5. FAQ ACCORDION ================= */
    document.querySelectorAll(".faq-question").forEach((qBtn) => {
      qBtn.addEventListener("click", () => {
        const parent = qBtn.closest(".faq-item");
        const isOpen = parent.classList.contains("open");

        // Boshqa ochilganlarini yopish
        document.querySelectorAll(".faq-item").forEach((it) => it.classList.remove("open"));

        if (!isOpen) {
          parent.classList.add("open");
        }
      });
    });

    /* ================= 6. FORM POLISH & VALIDATION (REGISTER) ================= */
    // Telefon maskasi: +998 (XX) XXX-XX-XX
    const phoneInput = document.getElementById("id_phone") || document.querySelector('input[type="tel"]');
    if (phoneInput) {
      phoneInput.addEventListener("input", function (e) {
        let val = this.value.replace(/\D/g, "");
        if (val.startsWith("998")) {
          val = val.substring(3);
        }
        val = val.substring(0, 9);

        let formatted = "+998";
        if (val.length > 0) formatted += " (" + val.substring(0, 2);
        if (val.length >= 2) formatted += ") " + val.substring(2, 5);
        if (val.length >= 5) formatted += "-" + val.substring(5, 7);
        if (val.length >= 7) formatted += "-" + val.substring(7, 9);

        this.value = formatted;
      });
    }

    // Textarea simvollar sanagichi
    document.querySelectorAll(".form-textarea").forEach((textarea) => {
      const maxLen = 1500;
      const counter = document.createElement("div");
      counter.style.cssText = "font-size:0.75rem;color:var(--text-muted);text-align:right;margin-top:2px;";
      counter.textContent = `${textarea.value.length} / ${maxLen} belgi`;
      textarea.parentNode.appendChild(counter);

      textarea.addEventListener("input", function () {
        counter.textContent = `${this.value.length} / ${maxLen} belgi`;
        if (this.value.length > maxLen) {
          counter.style.color = "var(--danger)";
        } else {
          counter.style.color = "var(--text-muted)";
        }
      });
    });

    // Rasm fayllari previewsi
    const imgInput = document.querySelector('input[type="file"][multiple]');
    if (imgInput) {
      const previewBox = document.createElement("div");
      previewBox.className = "file-preview-list";
      imgInput.parentNode.appendChild(previewBox);

      imgInput.addEventListener("change", function () {
        previewBox.innerHTML = "";
        const files = Array.from(this.files).slice(0, 5);
        files.forEach((file) => {
          if (file.type.startsWith("image/")) {
            const reader = new FileReader();
            reader.onload = (e) => {
              const img = document.createElement("img");
              img.className = "file-preview-item";
              img.src = e.target.result;
              img.title = file.name;
              previewBox.appendChild(img);
            };
            reader.readAsDataURL(file);
          }
        });
      });
    }

    // Forma yuborilayotganda tugmani bloklash va loader qo'shish
    const mainForm = document.querySelector(".form-card");
    if (mainForm) {
      mainForm.addEventListener("submit", function () {
        const submitBtn = this.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Ariza yuborilmoqda, kuting...';
        }
      });
    }

    /* ================= 7. COPY TO CLIPBOARD ================= */
    window.copyToClipboard = function (text, triggerEl) {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
          showToast(`Nusxalandi: ${text}`);
          if (triggerEl) {
            const original = triggerEl.innerHTML;
            triggerEl.innerHTML = '<i class="fa-solid fa-check"></i> Nusxa olindi!';
            setTimeout(() => { triggerEl.innerHTML = original; }, 2000);
          }
        });
      } else {
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        showToast(`Nusxalandi: ${text}`);
      }
    };

    function showToast(msg) {
      let toast = document.getElementById("slf-toast");
      if (!toast) {
        toast = document.createElement("div");
        toast.id = "slf-toast";
        toast.style.cssText = "position:fixed;bottom:24px;right:24px;background:#0f172a;color:#fff;padding:12px 20px;border-radius:10px;font-size:0.9rem;font-weight:600;box-shadow:0 10px 25px rgba(0,0,0,0.3);z-index:99999;border:1px solid #06b6d4;transition:opacity 0.3s ease;";
        document.body.appendChild(toast);
      }
      toast.textContent = msg;
      toast.style.opacity = "1";
      setTimeout(() => { toast.style.opacity = "0"; }, 3000);
    }

    /* ================= 8. CONFETTI (SUCCESS) ================= */
    if (window.CONFETTI_ACTIVE) {
      const canvas = document.getElementById("confetti-canvas");
      if (canvas) {
        const ctx = canvas.getContext("2d");
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const pieces = Array.from({ length: 120 }, () => ({
          x: Math.random() * canvas.width,
          y: Math.random() * -canvas.height,
          size: Math.random() * 8 + 4,
          speed: Math.random() * 3 + 2,
          color: ["#06b6d4", "#f59e0b", "#10b981", "#6366f1", "#ec4899"][Math.floor(Math.random() * 5)]
        }));

        let frame = 0;
        function dropConfetti() {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          pieces.forEach((p) => {
            p.y += p.speed;
            ctx.fillStyle = p.color;
            ctx.fillRect(p.x, p.y, p.size, p.size * 1.5);
          });
          if (++frame < 240) {
            requestAnimationFrame(dropConfetti);
          } else {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
          }
        }
        dropConfetti();
      }
    }
  });
})();

    /* ================= 9. INTERAKTIV 100 BALLIK BAHOLASH KALKULYATORI ================= */
    const scoreSliders = document.querySelectorAll(".score-slider-input");
    const totalScoreEl = document.getElementById("calc-total-score");
    const scoreBadgeEl = document.getElementById("calc-status-badge");

    function updateScoreSimulator() {
      let sum = 0;
      scoreSliders.forEach((slider) => {
        const val = parseInt(slider.value, 10) || 0;
        sum += val;
        const valDisplay = document.getElementById("val-" + slider.id);
        if (valDisplay) valDisplay.textContent = val + " ball";
      });

      if (totalScoreEl) totalScoreEl.textContent = sum;

      if (scoreBadgeEl) {
        if (sum >= 85) {
          scoreBadgeEl.textContent = "🥇 Bosh sovrin / G'oliblik salohiyati!";
          scoreBadgeEl.style.background = "rgba(245,158,11,0.2)";
          scoreBadgeEl.style.color = "#f59e0b";
        } else if (sum >= 70) {
          scoreBadgeEl.textContent = "🥈 Sovrindorlik darajasi (Yuqori ball)";
          scoreBadgeEl.style.background = "rgba(6,182,212,0.2)";
          scoreBadgeEl.style.color = "var(--primary)";
        } else if (sum >= 50) {
          scoreBadgeEl.textContent = "🥉 Yaxshi loyiha (Prototipni kuchaytiring)";
          scoreBadgeEl.style.background = "rgba(16,185,129,0.2)";
          scoreBadgeEl.style.color = "var(--accent-emerald)";
        } else {
          scoreBadgeEl.textContent = "💡 G'oyani pishitish va amaliyot talab etiladi";
          scoreBadgeEl.style.background = "rgba(148,163,184,0.15)";
          scoreBadgeEl.style.color = "var(--text-muted)";
        }
      }
    }

    scoreSliders.forEach((s) => s.addEventListener("input", updateScoreSimulator));
    updateScoreSimulator();

    /* ================= 10. JONLI 7 DAQIQALIK PITCH TAYMERI (NIZOM 8-BANDI) ================= */
    const pitchTimerBtn = document.getElementById("pitch-timer-toggle");
    const pitchResetBtn = document.getElementById("pitch-timer-reset");
    const pitchDisplay = document.getElementById("pitch-timer-display");
    const pitchPhaseEl = document.getElementById("pitch-current-phase");

    let pitchRemaining = 7 * 60; // 420 soniya
    let pitchInterval = null;
    let pitchIsRunning = false;

    function renderPitchTime() {
      const mins = Math.floor(pitchRemaining / 60);
      const secs = pitchRemaining % 60;
      if (pitchDisplay) {
        pitchDisplay.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
      }

      const elapsed = (7 * 60) - pitchRemaining;
      if (pitchPhaseEl) {
        if (elapsed < 120) {
          pitchPhaseEl.innerHTML = '<span style="color:var(--primary)">1-bosqich: Tanishuv & Loyiha maqsadi (2 daqiqa)</span>';
        } else if (elapsed < 300) {
          pitchPhaseEl.innerHTML = '<span style="color:var(--accent-emerald)">2-bosqich: Prototip & MVP namoyishi (3 daqiqa)</span>';
        } else if (elapsed < 420) {
          pitchPhaseEl.innerHTML = '<span style="color:var(--accent-gold)">3-bosqich: Hakamlar savol-javobi (2 daqiqa)</span>';
        } else {
          pitchPhaseEl.innerHTML = '<span style="color:var(--danger)">Vaqt yakunlandi! Rahmat!</span>';
        }
      }
    }

    if (pitchTimerBtn) {
      pitchTimerBtn.addEventListener("click", () => {
        if (!pitchIsRunning) {
          pitchIsRunning = true;
          pitchTimerBtn.innerHTML = '<i class="fa-solid fa-pause"></i> To\'xtatish';
          pitchTimerBtn.classList.remove("btn-primary");
          pitchTimerBtn.classList.add("btn-outline");

          pitchInterval = setInterval(() => {
            if (pitchRemaining > 0) {
              pitchRemaining--;
              renderPitchTime();
            } else {
              clearInterval(pitchInterval);
              pitchIsRunning = false;
              pitchTimerBtn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Boshidan boshlash';
            }
          }, 1000);
        } else {
          clearInterval(pitchInterval);
          pitchIsRunning = false;
          pitchTimerBtn.innerHTML = '<i class="fa-solid fa-play"></i> Davom ettirish';
          pitchTimerBtn.classList.add("btn-primary");
          pitchTimerBtn.classList.remove("btn-outline");
        }
      });
    }

    if (pitchResetBtn) {
      pitchResetBtn.addEventListener("click", () => {
        clearInterval(pitchInterval);
        pitchIsRunning = false;
        pitchRemaining = 7 * 60;
        renderPitchTime();
        if (pitchTimerBtn) {
          pitchTimerBtn.innerHTML = '<i class="fa-solid fa-play"></i> Mashqni boshlash (7 daqiqa)';
          pitchTimerBtn.classList.add("btn-primary");
          pitchTimerBtn.classList.remove("btn-outline");
        }
      });
    }

    /* ================= 11. SENIOR-GRADE FORM DRAFT AUTO-SAVE ================= */
    const draftInputs = document.querySelectorAll('.form-card input:not([type="file"]):not([type="hidden"]):not([type="password"]), .form-card textarea, .form-card select');
    if (draftInputs.length > 0 && mainForm) {
      draftInputs.forEach((inp) => {
        const storageKey = "slf_draft_" + (inp.name || inp.id);
        const savedVal = localStorage.getItem(storageKey);
        if (savedVal && !inp.value && inp.type !== "checkbox") {
          inp.value = savedVal;
        }
        inp.addEventListener("input", () => {
          localStorage.setItem(storageKey, inp.value);
        });
      });

      mainForm.addEventListener("submit", () => {
        draftInputs.forEach((inp) => {
          localStorage.removeItem("slf_draft_" + (inp.name || inp.id));
        });
      });
    }
