(() => {
    const carousel = document.querySelector("[data-carousel]");
    if (!carousel) return;

    const track = carousel.querySelector("[data-carousel-track]");
    const slides = [...carousel.querySelectorAll("[data-carousel-slide]")];
    const previous = carousel.querySelector("[data-carousel-prev]");
    const next = carousel.querySelector("[data-carousel-next]");
    const indicators = [...carousel.querySelectorAll("[data-carousel-to]")];
    const toggle = carousel.querySelector("[data-carousel-toggle]");
    const counter = carousel.querySelector("[data-carousel-counter]");
    const status = carousel.querySelector("[data-carousel-status]");
    const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    );

    if (!track || slides.length === 0) return;

    const INTERVAL = 5000;
    const DEBUG = false;

    let currentIndex = 0;
    let autoplayTimer = null;
    let playing = !reducedMotion.matches;
    let carouselVisible = false;
    let pointerInside = false;
    let trackingPointer = false;
    let pointerStartX = 0;
    let pointerStartY = 0;

    const pad = (number) => String(number).padStart(2, "0");

    const goTo = (requestedIndex, announce = true) => {
        if (!Number.isInteger(requestedIndex)) return;

        currentIndex =
            ((requestedIndex % slides.length) + slides.length) %
            slides.length;

        track.style.transform =
            `translate3d(-${currentIndex * 100}%, 0, 0)`;

        slides.forEach((slide, index) => {
            const active = index === currentIndex;
            slide.toggleAttribute("inert", !active);
            slide.setAttribute("aria-hidden", String(!active));
        });

        indicators.forEach((indicator) => {
            const active =
                Number(indicator.dataset.carouselTo) === currentIndex;

            indicator.dataset.active = String(active);

            if (active) {
                indicator.setAttribute("aria-current", "true");
            } else {
                indicator.removeAttribute("aria-current");
            }
        });

        if (counter) {
            counter.textContent =
                `${pad(currentIndex + 1)} / ${pad(slides.length)}`;
        }

        if (announce && status) {
            status.textContent =
                `Diapositiva ${currentIndex + 1} de ${slides.length}`;
        }
    };

    const stopAutoplay = () => {
        if (autoplayTimer !== null) {
            window.clearInterval(autoplayTimer);
            autoplayTimer = null;
        }
    };

    const startAutoplay = () => {
        stopAutoplay();

        const motivosDePausa = {
            pausaManual: !playing,
            pestañaOculta: document.hidden,
            carruselFueraDePantalla: !carouselVisible,
            cursorEncima: pointerInside,
            focoDentro: carousel.contains(document.activeElement),
            gestoTactilActivo: trackingPointer,
            unaSolaDiapositiva: slides.length <= 1
        };

        const debePausarse =
            Object.values(motivosDePausa).some(Boolean);

        if (DEBUG) {
            console.table(motivosDePausa);
            console.log(
                debePausarse
                    ? "Carrusel pausado"
                    : "Avance automático iniciado: cada 5 segundos"
            );
        }

        if (debePausarse) return;

        autoplayTimer = window.setInterval(() => {
            goTo(currentIndex + 1, false);
        }, INTERVAL);
    };

    const updateToggle = () => {
        if (!toggle) return;

        toggle.dataset.playing = String(playing);
        toggle.textContent = playing ? "Pausar" : "Reproducir";
        toggle.setAttribute(
            "aria-label",
            playing ? "Pausar carrusel" : "Reproducir carrusel"
        );
    };

    const setPlaying = (value) => {
        playing = value;
        updateToggle();
        startAutoplay();
    };

    const navigate = (index) => {
        goTo(index);
        startAutoplay();
    };

    previous?.addEventListener("click", () => {
        navigate(currentIndex - 1);
    });

    next?.addEventListener("click", () => {
        navigate(currentIndex + 1);
    });

    indicators.forEach((indicator) => {
        indicator.addEventListener("click", () => {
            navigate(Number(indicator.dataset.carouselTo));
        });
    });

    toggle?.addEventListener("click", () => {
        setPlaying(!playing);
    });

    // Navegación con teclado.
    carousel.addEventListener("keydown", (event) => {
        if (
            event.target instanceof Element &&
            event.target.closest(
                "input, textarea, select, [contenteditable='true']"
            )
        ) {
            return;
        }

        switch (event.key) {
            case "ArrowLeft":
                event.preventDefault();
                navigate(currentIndex - 1);
                break;

            case "ArrowRight":
                event.preventDefault();
                navigate(currentIndex + 1);
                break;

            case "Home":
                event.preventDefault();
                navigate(0);
                break;

            case "End":
                event.preventDefault();
                navigate(slides.length - 1);
                break;
        }
    });

    // Pausa al colocar el mouse sobre el carrusel.
    carousel.addEventListener("pointerenter", (event) => {
        if (event.pointerType !== "mouse") return;

        pointerInside = true;
        startAutoplay();
    });

    carousel.addEventListener("pointerleave", (event) => {
        if (event.pointerType !== "mouse") return;

        pointerInside = false;
        startAutoplay();
    });

    // Pausa mientras el carrusel o sus controles tienen el foco.
    carousel.addEventListener("focusin", () => {
        startAutoplay();
    });

    carousel.addEventListener("focusout", (event) => {
        if (!carousel.contains(event.relatedTarget)) {
            window.setTimeout(startAutoplay, 0);
        }
    });

    // Navegación por deslizamiento táctil.
    carousel.addEventListener("pointerdown", (event) => {
        if (event.pointerType === "mouse" || !event.isPrimary) return;

        trackingPointer = true;
        pointerStartX = event.clientX;
        pointerStartY = event.clientY;
        startAutoplay();
    });

    window.addEventListener("pointerup", (event) => {
        if (!trackingPointer || !event.isPrimary) return;

        trackingPointer = false;

        const deltaX = event.clientX - pointerStartX;
        const deltaY = event.clientY - pointerStartY;

        if (
            Math.abs(deltaX) > 50 &&
            Math.abs(deltaX) > Math.abs(deltaY)
        ) {
            goTo(currentIndex + (deltaX < 0 ? 1 : -1));
        }

        startAutoplay();
    });

    window.addEventListener("pointercancel", (event) => {
        if (!trackingPointer || !event.isPrimary) return;

        trackingPointer = false;
        startAutoplay();
    });

    // Pausa cuando la pestaña está oculta.
    document.addEventListener("visibilitychange", () => {
        startAutoplay();
    });

    // Respeta la preferencia de reducir movimiento.
    const handleMotionPreference = (event) => {
        if (event.matches) {
            setPlaying(false);
        }
    };

    if (typeof reducedMotion.addEventListener === "function") {
        reducedMotion.addEventListener(
            "change",
            handleMotionPreference
        );
    } else {
        reducedMotion.addListener(handleMotionPreference);
    }

    carousel.setAttribute("tabindex", "0");
    updateToggle();
    goTo(0, false);

    // Pausa cuando el carrusel queda fuera de pantalla.
    if ("IntersectionObserver" in window) {
        const visibilityObserver = new IntersectionObserver(
            ([entry]) => {
                carouselVisible = entry.isIntersecting;
                startAutoplay();
            },
            { threshold: 0 }
        );

        visibilityObserver.observe(carousel);
    } else {
        carouselVisible = true;
        startAutoplay();
    }
})();