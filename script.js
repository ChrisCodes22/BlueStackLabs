// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Contact form submission is handled by an inline <script> in index.html
// (mirroring the working plans.html pattern), so no handler lives here —
// this avoids two listeners double-submitting the form.

// Add active state to navigation on scroll
window.addEventListener('scroll', () => {
    const sections = document.querySelectorAll('section[id]');

    // Subpages have no anchored sections and mark their own nav item in the
    // markup — bail out rather than clearing it off them.
    if (!sections.length) return;

    // Only same-page anchors; cross-page links keep whatever the markup set.
    const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');

    let current = '';
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        if (window.scrollY >= sectionTop - 200) {
            current = section.getAttribute('id');
        }
    });
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href').slice(1) === current) {
            link.classList.add('active');
        }
    });
});

// Hero stack: one square that opens into the three layers on click
const stack = document.querySelector('.stack-3d');

if (stack) {
    const UNWIND_MS = 600;
    const calmMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let unwindTimer;

    function openStack() {
        clearTimeout(unwindTimer);
        stack.classList.remove('is-unwinding');
        stack.style.transform = '';
        stack.classList.add('is-open');
        stack.setAttribute('aria-expanded', 'true');
    }

    function closeStack() {
        stack.classList.remove('is-open');
        stack.setAttribute('aria-expanded', 'false');

        // Simply pausing the spin would leave the square frozen at whatever
        // angle it had reached. Instead: capture the live rotation, drop the
        // animation, and transition from there back to square-on.
        if (calmMotion.matches) return;

        const current = getComputedStyle(stack).transform;
        stack.classList.add('is-unwinding');
        stack.style.transform = current;
        void stack.offsetWidth; // flush, so the next value transitions from `current`
        stack.style.transform = 'rotateY(0deg) rotateX(10deg)';

        clearTimeout(unwindTimer);
        unwindTimer = setTimeout(() => {
            // Hand the transform back to the (paused) animation.
            stack.classList.remove('is-unwinding');
            stack.style.transform = '';
        }, UNWIND_MS);
    }

    function toggleStack() {
        stack.classList.contains('is-open') ? closeStack() : openStack();
    }

    stack.addEventListener('click', toggleStack);
    stack.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
            e.preventDefault();
            toggleStack();
        }
    });
}

// Project carousel: slide between projects, click a card to flip it over
const carousel = document.querySelector('[data-carousel]');

if (carousel) {
    const track  = carousel.querySelector('.carousel-track');
    const slides = Array.from(carousel.querySelectorAll('.carousel-slide'));
    const cards  = Array.from(carousel.querySelectorAll('.flip-card'));
    const dotsBox = carousel.querySelector('[data-carousel-dots]');
    const AUTOPLAY_MS = 7000;

    let index = 0;
    let timer = null;

    // --- Flipping ---

    function setFlipped(card, flipped) {
        card.classList.toggle('is-flipped', flipped);
        card.setAttribute('aria-expanded', String(flipped));

        // Keep the hidden face out of the tab order — otherwise tabbing lands
        // on a link nobody can see.
        const link = card.querySelector('[data-flip-link]');
        if (link) link.tabIndex = flipped ? 0 : -1;
    }

    cards.forEach((card) => {
        setFlipped(card, false);

        card.addEventListener('click', (e) => {
            // The link on the back is a real destination, not a flip target.
            if (e.target.closest('[data-flip-link]')) return;
            setFlipped(card, !card.classList.contains('is-flipped'));
            stopAutoplay();
        });

        card.addEventListener('keydown', (e) => {
            if (e.target.closest('[data-flip-link]')) return;
            if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
                e.preventDefault();
                setFlipped(card, !card.classList.contains('is-flipped'));
                stopAutoplay();
            }
        });
    });

    // --- Sliding ---

    const dots = slides.map((_, i) => {
        const dot = document.createElement('button');
        dot.type = 'button';
        dot.className = 'carousel-dot';
        dot.setAttribute('aria-label', `Go to project ${i + 1}`);
        dot.addEventListener('click', () => {
            goTo(i);
            stopAutoplay();
        });
        dotsBox.appendChild(dot);
        return dot;
    });

    function goTo(next) {
        index = (next + slides.length) % slides.length;
        track.style.transform = `translateX(-${index * 100}%)`;

        slides.forEach((slide, i) => {
            const offscreen = i !== index;
            // Cards that aren't showing shouldn't be tabbable, and a card left
            // flipped would be mid-flip when it slides back into view.
            slide.setAttribute('aria-hidden', String(offscreen));
            const card = cards[i];
            card.tabIndex = offscreen ? -1 : 0;
            if (offscreen) setFlipped(card, false);
        });

        dots.forEach((dot, i) => dot.setAttribute('aria-selected', String(i === index)));
    }

    carousel.querySelector('.carousel-prev').addEventListener('click', () => {
        goTo(index - 1);
        stopAutoplay();
    });

    carousel.querySelector('.carousel-next').addEventListener('click', () => {
        goTo(index + 1);
        stopAutoplay();
    });

    // --- Autoplay ---
    // Runs until the visitor interacts, then gets out of the way for good.

    function startAutoplay() {
        if (!timer && slides.length > 1) {
            timer = setInterval(() => goTo(index + 1), AUTOPLAY_MS);
        }
    }

    function stopAutoplay() {
        clearInterval(timer);
        timer = null;
    }

    carousel.addEventListener('mouseenter', stopAutoplay);
    document.addEventListener('visibilitychange', () => {
        document.hidden ? stopAutoplay() : startAutoplay();
    });

    goTo(0);

    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        startAutoplay();
    }
}

// The cursor spotlight and warping grid live in background.js, shared with
// plans.html.

// Intersection Observer for fade-in animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe service cards and other elements
document.querySelectorAll('.service-card, .tech-item').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
});
