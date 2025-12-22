(function () {
  const navToggle = document.querySelector(".nav-toggle");
  const navLinks = document.querySelector(".nav-links");
  const nav = document.querySelector(".nav");

  if (navToggle && navLinks) {
    const closeNav = () => {
      navLinks.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
    };

    navToggle.addEventListener("click", () => {
      const isOpen = navLinks.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
      if (isOpen) {
        const firstLink = navLinks.querySelector("a");
        if (firstLink) {
          firstLink.focus();
        }
      }
    });

    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        if (window.innerWidth <= 800) {
          closeNav();
        }
      });
    });

    document.addEventListener("click", (event) => {
      if (
        !nav?.contains(event.target) &&
        navLinks.classList.contains("is-open")
      ) {
        closeNav();
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 800) {
        navLinks.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  );
  const sliderStates = new WeakMap();

  const initializeSlider = (slider) => {
    if (sliderStates.has(slider)) {
      const state = sliderStates.get(slider);
      if (!state) {
        return;
      }
      if (prefersReducedMotion.matches) {
        state.stopAutoAdvance();
      } else {
        state.restartAutoAdvance();
      }
      return;
    }

    const track = slider.querySelector("[data-slider-track]");
    const slides = Array.from(slider.querySelectorAll("[data-slide]"));
    const prevButton = slider.querySelector("[data-slider-prev]");
    const nextButton = slider.querySelector("[data-slider-next]");
    const dotsContainer = slider.querySelector("[data-slider-dots]");

    if (!track || slides.length === 0) {
      return;
    }

    let currentIndex = 0;
    let autoAdvanceId = null;
    const interval = parseInt(slider.dataset.autoAdvance || "", 10);
    const dots = [];

    const updateActiveSlide = () => {
      track.style.transform = `translateX(-${currentIndex * 100}%)`;
      dots.forEach((dot, index) => {
        dot.classList.toggle("is-active", index === currentIndex);
        dot.setAttribute(
          "aria-pressed",
          index === currentIndex ? "true" : "false",
        );
      });
      slider.setAttribute("data-active-index", currentIndex.toString());
    };

    const goToSlide = (index) => {
      currentIndex = (index + slides.length) % slides.length;
      updateActiveSlide();
    };

    if (dotsContainer) {
      dotsContainer.innerHTML = "";
      slides.forEach((_, index) => {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = index === 0 ? "is-active" : "";
        dot.setAttribute("aria-label", `Go to slide ${index + 1}`);
        dot.addEventListener("click", () => {
          goToSlide(index);
          restartAutoAdvance();
        });
        dotsContainer.appendChild(dot);
        dots.push(dot);
      });
    }

    const startAutoAdvance = () => {
      if (
        !Number.isFinite(interval) ||
        interval <= 0 ||
        prefersReducedMotion.matches
      ) {
        return;
      }
      stopAutoAdvance();
      autoAdvanceId = window.setInterval(() => {
        goToSlide(currentIndex + 1);
      }, interval);
    };

    const stopAutoAdvance = () => {
      if (autoAdvanceId) {
        clearInterval(autoAdvanceId);
        autoAdvanceId = null;
      }
    };

    const restartAutoAdvance = () => {
      stopAutoAdvance();
      startAutoAdvance();
    };

    prevButton?.addEventListener("click", () => {
      goToSlide(currentIndex - 1);
      restartAutoAdvance();
    });

    nextButton?.addEventListener("click", () => {
      goToSlide(currentIndex + 1);
      restartAutoAdvance();
    });

    slider.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        goToSlide(currentIndex + 1);
        restartAutoAdvance();
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goToSlide(currentIndex - 1);
        restartAutoAdvance();
      }
    });

    let pointerStart = null;
    slider.addEventListener("pointerdown", (event) => {
      if (event.pointerType === "mouse" && event.button !== 0) {
        return;
      }
      pointerStart = { id: event.pointerId, x: event.clientX };
      slider.setPointerCapture(event.pointerId);
      stopAutoAdvance();
    });

    slider.addEventListener("pointermove", (event) => {
      if (!pointerStart || pointerStart.id !== event.pointerId) {
        return;
      }
      const deltaX = event.clientX - pointerStart.x;
      if (Math.abs(deltaX) > 50) {
        if (deltaX > 0) {
          goToSlide(currentIndex - 1);
        } else {
          goToSlide(currentIndex + 1);
        }
        pointerStart = null;
      }
    });

    const pointerEnd = (event) => {
      if (pointerStart && pointerStart.id === event.pointerId) {
        pointerStart = null;
      }
      restartAutoAdvance();
    };

    slider.addEventListener("pointerup", pointerEnd);
    slider.addEventListener("pointercancel", pointerEnd);
    slider.addEventListener("mouseleave", () => {
      pointerStart = null;
    });

    slider.addEventListener("mouseenter", stopAutoAdvance);
    slider.addEventListener("focusin", stopAutoAdvance);
    slider.addEventListener("mouseleave", restartAutoAdvance);
    slider.addEventListener("focusout", restartAutoAdvance);

    goToSlide(0);
    startAutoAdvance();

    sliderStates.set(slider, {
      restartAutoAdvance,
      stopAutoAdvance,
    });
  };

  document
    .querySelectorAll("[data-slider]")
    .forEach((slider) => initializeSlider(slider));

  prefersReducedMotion.addEventListener("change", () => {
    document
      .querySelectorAll("[data-slider]")
      .forEach((slider) => initializeSlider(slider));
  });

  const contactForm = document.querySelector(".contact-form");
  if (contactForm) {
    const feedback = contactForm.querySelector(".form-feedback");
    const submitButton = contactForm.querySelector('button[type="submit"]');

    contactForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!contactForm.checkValidity()) {
        contactForm.reportValidity();
        return;
      }

      if (!feedback || !submitButton) {
        return;
      }

      feedback.textContent = "";
      feedback.classList.remove("is-error");
      const originalText = submitButton.textContent;
      submitButton.disabled = true;
      submitButton.textContent = "Sending…";

      try {
        await new Promise((resolve) => setTimeout(resolve, 800));
        feedback.textContent = "Message sent! I will be in touch shortly.";
        contactForm.reset();
      } catch (error) {
        feedback.textContent =
          "Something went wrong. Please email me directly.";
        feedback.classList.add("is-error");
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = originalText || "Send Message";
      }
    });
  }
})();
