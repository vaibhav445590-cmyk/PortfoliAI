document.addEventListener("DOMContentLoaded", () => {

    /* =========================
       SCROLL REVEAL
    ========================== */

    const revealElements =
        document.querySelectorAll(".reveal");

    const revealObserver =
        new IntersectionObserver(
            (entries) => {

                entries.forEach((entry) => {

                    if (entry.isIntersecting) {

                        entry.target.classList.add("visible");

                        /*
                         * Keep the existing reveal animation.
                         * Small stagger for grouped elements.
                         */

                        const siblings =
                            entry.target.parentElement?.querySelectorAll(
                                ".reveal:not(.visible)"
                            );

                        if (siblings && siblings.length) {
                            siblings.forEach((element, index) => {
                                element.style.transitionDelay =
                                    `${Math.min(index * 60, 240)}ms`;
                            });
                        }

                        revealObserver.unobserve(
                            entry.target
                        );
                    }

                });

            },
            {
                threshold: 0.12,
                rootMargin: "0px 0px -40px 0px"
            }
        );


    revealElements.forEach((element) => {
        revealObserver.observe(element);
    });



    /* =========================
       CURSOR GLOW
    ========================== */

    const cursorGlow =
        document.querySelector(".cursor-glow");

    if (cursorGlow) {

        window.addEventListener(
            "mousemove",
            (event) => {

                cursorGlow.style.left =
                    `${event.clientX}px`;

                cursorGlow.style.top =
                    `${event.clientY}px`;

                cursorGlow.style.opacity = "1";
            }
        );

    }



    /* =========================
       MOBILE MENU
    ========================== */

    const mobileMenu =
        document.querySelector(".mobile-menu");

    const navbar =
        document.querySelector(".navbar");

    if (mobileMenu && navbar) {

        mobileMenu.addEventListener(
            "click",
            () => {

                navbar.classList.toggle(
                    "mobile-open"
                );

            }
        );


        document
            .querySelectorAll(".nav-links a")
            .forEach((link) => {

                link.addEventListener(
                    "click",
                    () => {

                        navbar.classList.remove(
                            "mobile-open"
                        );

                    }
                );

            });

    }



    /* =========================
       RESUME UPLOAD
    ========================== */

    const resumeInput =
        document.getElementById("resumeInput");

    const resumePicker =
        document.getElementById("resumePicker");

    const resumeForm =
        document.getElementById("resumeForm");

    const fileName =
        document.getElementById("fileName");

    const fileSize =
        document.getElementById("fileSize");

    const uploadCheck =
        document.getElementById("uploadCheck");


    if (
        resumeInput &&
        resumePicker &&
        resumeForm
    ) {

        resumePicker.addEventListener(
            "click",
            () => {
                resumeInput.click();
            }
        );


        resumeInput.addEventListener(
            "change",
            async () => {

                const file =
                    resumeInput.files[0];

                if (!file) {
                    return;
                }


                if (
                    file.type !== "application/pdf" &&
                    !file.name.toLowerCase().endsWith(".pdf")
                ) {

                    alert(
                        "Please select a PDF resume."
                    );

                    resumeInput.value = "";

                    return;
                }


                const maxSize =
                    10 * 1024 * 1024;


                if (file.size > maxSize) {

                    alert(
                        "Resume must be smaller than 10 MB."
                    );

                    resumeInput.value = "";

                    return;
                }


                fileName.textContent =
                    file.name;


                const sizeMB =
                    (
                        file.size /
                        (1024 * 1024)
                    ).toFixed(2);


                fileSize.textContent =
                    `${sizeMB} MB · Uploading & extracting...`;


                uploadCheck.textContent = "⏳";


                try {

                    const formData =
                        new FormData(resumeForm);

                    const response =
                        await fetch(
                            "/upload-resume",
                            {
                                method: "POST",
                                body: formData,
                                headers: {
                                    "Accept": "application/json"
                                }
                            }
                        );

                    const data =
                        await response.json();

                    if (!response.ok) {
                        throw new Error(
                            data.error ||
                            "Upload failed."
                        );
                    }

                    uploadCheck.textContent = "✓";

                    fileSize.textContent =
                        `${sizeMB} MB · Uploaded! Click Generate below`;

                    const heroResumeName =
                        document.querySelector(".resume-name");

                    if (
                        heroResumeName &&
                        heroResumeName.textContent.trim() === "Your Resume"
                    ) {
                        heroResumeName.textContent =
                            file.name.replace(/\.[^/.]+$/, "");
                    }

                } catch (error) {

                    console.error(
                        "Resume upload error:",
                        error
                    );

                    uploadCheck.textContent = "✕";

                    fileSize.textContent =
                        `Upload failed: ${error.message}`;

                    alert(
                        error.message ||
                        "Failed to upload resume. Please try again."
                    );

                }

            }
        );

    }



    /* =========================
       CREATE MY PORTFOLIO
    ========================== */

    const createButtons =
        document.querySelectorAll(
            ".primary-button, .nav-cta"
        );


    createButtons.forEach((button) => {

        button.addEventListener(
            "click",
            (event) => {

                const target =
                    button.getAttribute("href");

                if (target === "#demo") {

                    event.preventDefault();

                    const demo =
                        document.getElementById("demo");

                    if (demo) {

                        demo.scrollIntoView({
                            behavior: "smooth"
                        });

                    }

                }

            }
        );

    });



    /* =========================
       GENERATE BUTTON
    ========================== */

    const generateButton =
        document.getElementById(
            "generateButton"
        );


    if (generateButton) {

        generateButton.addEventListener(
            "click",
            async () => {

                /*
                 * Prevent multiple clicks
                 */

                if (
                    generateButton.classList.contains(
                        "loading"
                    )
                ) {
                    return;
                }


                generateButton.classList.add(
                    "loading"
                );


                const text =
                    generateButton.querySelector(
                        "span"
                    );


                if (text) {

                    text.textContent =
                        "Preparing your portfolio...";

                }


                try {

                    /*
                     * Ask Flask to generate/update
                     * the portfolio from the stored
                     * resume.
                     */

                    const response =
                        await fetch(
                            "/generate-portfolio",
                            {
                                method: "POST",
                                headers: {
                                    "Content-Type":
                                        "application/json"
                                }
                            }
                        );


                    const data =
                        await response.json();


                    if (!response.ok) {

                        throw new Error(
                            data.error ||
                            "Portfolio generation failed."
                        );

                    }


                    /*
                     * Small delay keeps the existing
                     * visual transition feeling smooth.
                     */

                    setTimeout(() => {

                        window.location.reload();

                    }, 700);


                } catch (error) {

                    console.error(
                        "Portfolio generation error:",
                        error
                    );


                    alert(
                        error.message ||
                        "Something went wrong while generating your portfolio."
                    );


                    generateButton.classList.remove(
                        "loading"
                    );


                    if (text) {

                        text.textContent =
                            "Generate portfolio";

                    }

                }

            }
        );

    }



    /* =========================
       PROJECT CARD TILT
    ========================== */

    const projectCards =
        document.querySelectorAll(
            ".project-card"
        );


    projectCards.forEach((card) => {

        card.addEventListener(
            "mousemove",
            (event) => {

                if (
                    window.innerWidth < 900
                ) {
                    return;
                }


                const rect =
                    card.getBoundingClientRect();


                const x =
                    event.clientX -
                    rect.left;


                const y =
                    event.clientY -
                    rect.top;


                const rotateY =
                    ((x / rect.width) - .5) * 4;


                const rotateX =
                    -((y / rect.height) - .5) * 4;


                card.style.transform =
                    `
                    perspective(1000px)
                    rotateX(${rotateX}deg)
                    rotateY(${rotateY}deg)
                    translateY(-5px)
                    `;

            }
        );


        card.addEventListener(
            "mouseleave",
            () => {

                card.style.transform = "";

            }
        );

    });



    /* =========================
       AI WINDOW MOUSE EFFECT
    ========================== */

    const aiWindow =
        document.querySelector(
            ".ai-window"
        );


    if (aiWindow) {

        aiWindow.addEventListener(
            "mousemove",
            (event) => {

                if (
                    window.innerWidth < 900
                ) {
                    return;
                }


                const rect =
                    aiWindow.getBoundingClientRect();


                const x =
                    (
                        event.clientX -
                        rect.left
                    ) /
                    rect.width -
                    .5;


                const y =
                    (
                        event.clientY -
                        rect.top
                    ) /
                    rect.height -
                    .5;


                aiWindow.style.transform =
                    `
                    perspective(1200px)
                    rotateY(${x * -8}deg)
                    rotateX(${y * 5}deg)
                    translateY(-3px)
                    `;

            }
        );


        aiWindow.addEventListener(
            "mouseleave",
            () => {

                aiWindow.style.transform =
                    `
                    perspective(1200px)
                    rotateY(-7deg)
                    rotateX(3deg)
                    `;

            }
        );

    }



    /* =========================
       PROGRESS ANIMATION
    ========================== */

    const progress =
        document.querySelector(
            ".progress-track span"
        );

    const progressNumber =
        document.querySelector(
            ".progress-number"
        );


    if (
        progress &&
        progressNumber
    ) {

        let value = 0;

        const animateProgress =
            setInterval(() => {

                value += 2;

                if (value >= 78) {

                    value = 78;

                    clearInterval(
                        animateProgress
                    );

                }


                progressNumber.textContent =
                    `${value}%`;

                progress.style.width =
                    `${value}%`;

            }, 25);

    }

    

       
        /* =========================
       MAGNETIC BUTTON EFFECT
    ========================== */

    const magneticButtons = document.querySelectorAll(
        ".primary-button, .nav-cta, .glass-button"
    );

    magneticButtons.forEach((button) => {

        if (window.innerWidth < 900) {
            return;
        }

        button.addEventListener("mousemove", (event) => {

            const rect = button.getBoundingClientRect();

            const x =
                event.clientX -
                (rect.left + rect.width / 2);

            const y =
                event.clientY -
                (rect.top + rect.height / 2);

            button.style.transform =
                `translate(${x * 0.12}px, ${y * 0.12}px)`;
        });

        button.addEventListener("mouseleave", () => {

            button.style.transform = "";

        });

    });


});

/* =========================
   INTERACTIVE GLASS LIGHT
========================== */

const glassElements = document.querySelectorAll(".liquid-glass");

glassElements.forEach((element) => {

    element.addEventListener("mousemove", (event) => {

        const rect = element.getBoundingClientRect();

        const x =
            ((event.clientX - rect.left) / rect.width) * 100;

        const y =
            ((event.clientY - rect.top) / rect.height) * 100;

        element.style.setProperty("--glass-x", `${x}%`);
        element.style.setProperty("--glass-y", `${y}%`);
    });

    element.addEventListener("mouseleave", () => {

        element.style.setProperty("--glass-x", "50%");
        element.style.setProperty("--glass-y", "50%");

    });

});

/* =========================
   GLASS SCROLL LIGHT
========================== */

const glassScrollElements =
    document.querySelectorAll(".liquid-glass");

if (glassScrollElements.length) {

    let glassScrollTicking = false;

    window.addEventListener("scroll", () => {

        if (!glassScrollTicking) {

            window.requestAnimationFrame(() => {

                const scrollY = window.scrollY;

                glassScrollElements.forEach((element, index) => {

                    const shiftX =
                        50 + Math.sin(scrollY * 0.002 + index) * 8;

                    const shiftY =
                        50 + Math.cos(scrollY * 0.0015 + index) * 8;

                    element.style.setProperty(
                        "--glass-scroll-x",
                        `${shiftX}%`
                    );

                    element.style.setProperty(
                        "--glass-scroll-y",
                        `${shiftY}%`
                    );
                });

                glassScrollTicking = false;
            });

            glassScrollTicking = true;
        }
    });
}

/* =========================
   CINEMATIC VISUAL DEPTH
========================== */

const cinematicVisuals = document.querySelectorAll(
    ".hero-visual, .final-visual"
);

if (cinematicVisuals.length) {

    let cinematicTicking = false;

    window.addEventListener("scroll", () => {

        if (!cinematicTicking) {

            window.requestAnimationFrame(() => {

                cinematicVisuals.forEach((element) => {

                    const rect =
                        element.getBoundingClientRect();

                    const viewportCenter =
                        window.innerHeight / 2;

                    const elementCenter =
                        rect.top + rect.height / 2;

                    const distance =
                        (elementCenter - viewportCenter) /
                        window.innerHeight;

                    const scale =
                        1 - Math.min(
                            Math.abs(distance) * 0.025,
                            0.025
                        );

                    element.style.setProperty(
                        "--cinematic-scale",
                        scale
                    );
                });

                cinematicTicking = false;
            });

            cinematicTicking = true;
        }
    });
}

/* =========================
   CINEMATIC TEXT REVEAL
========================== */

const textRevealElements =
    document.querySelectorAll(".text-reveal");

if (textRevealElements.length) {

    const textObserver = new IntersectionObserver(
        (entries, observer) => {

            entries.forEach((entry) => {

                if (entry.isIntersecting) {

                    entry.target.classList.add("visible");

                    observer.unobserve(entry.target);
                }

            });

        },
        {
            threshold: 0.25
        }
    );

    textRevealElements.forEach((element) => {
        textObserver.observe(element);
    });
}

/* =========================
   SCROLL PROGRESS
========================== */

const scrollProgressBar =
    document.querySelector(".scroll-progress-bar");

if (scrollProgressBar) {

    let progressTicking = false;

    window.addEventListener("scroll", () => {

        if (!progressTicking) {

            window.requestAnimationFrame(() => {

                const scrollTop = window.scrollY;

                const scrollHeight =
                    document.documentElement.scrollHeight -
                    window.innerHeight;

                const progress =
                    scrollHeight > 0
                        ? (scrollTop / scrollHeight) * 100
                        : 0;

                scrollProgressBar.style.width =
                    `${progress}%`;

                progressTicking = false;
            });

            progressTicking = true;
        }

    });
}

/* =========================
   SMOOTH ANCHOR NAVIGATION
========================== */

document.querySelectorAll('a[href^="#"]').forEach((link) => {

    link.addEventListener("click", (event) => {

        const targetId = link.getAttribute("href");

        if (!targetId || targetId === "#") {
            return;
        }

        const target = document.querySelector(targetId);

        if (!target) {
            return;
        }

        event.preventDefault();

        target.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    });

});

/* =========================================================
   PORTFOLIAI — SINGLE CINEMATIC 3D RESUME
========================================================= */

(() => {
    const scene = document.querySelector(".resume-3d-scene");
    const object = document.querySelector(".resume-3d-object");

    if (!scene || !object) return;

    const desktop = window.matchMedia("(min-width: 761px)");
    if (!desktop.matches) return;

    let targetX = 8;
    let targetY = -18;
    let currentX = targetX;
    let currentY = targetY;
    let scrollRotation = 0;
    let scrollTicking = false;

    function updateScrollRotation() {
        const hero = document.querySelector(".hero");
        if (!hero) {
            scrollTicking = false;
            return;
        }

        const rect = hero.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const progress = Math.max(
            0,
            Math.min(
                1,
                (viewportHeight - rect.top) /
                (viewportHeight + rect.height)
            )
        );

        scrollRotation = progress * 160;
        scrollTicking = false;
    }

    window.addEventListener("scroll", () => {
        if (scrollTicking) return;
        scrollTicking = true;
        requestAnimationFrame(updateScrollRotation);
    }, { passive: true });

    function animateResume() {
        currentX += (targetX - currentX) * 0.075;
        currentY += (targetY - currentY) * 0.075;

        object.style.transform = `
            rotateX(${currentX}deg)
            rotateY(${currentY + scrollRotation}deg)
            rotateZ(-3deg)
        `;

        requestAnimationFrame(animateResume);
    }

    animateResume();

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            object.style.willChange = entry.isIntersecting
                ? "transform"
                : "auto";
        });
    }, { threshold: 0.05 });

    observer.observe(scene);
})();
