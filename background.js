// Pointer glow — shared by index.html, plans.html, and the subpages.
// A soft light that trails the cursor, plus --mx/--my on :root so
// background.css can brighten the grid where the pointer is.
// Sits out entirely on touch devices and under reduced motion.

(function () {
    'use strict';

    const glow = document.querySelector('.cursor-glow');
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
    const calmMotion  = window.matchMedia('(prefers-reduced-motion: reduce)');

    if (!glow || !finePointer.matches || calmMotion.matches) return;

    const root = document.documentElement;
    let targetX = 0, targetY = 0;   // where the pointer actually is
    let x = 0, y = 0;               // where the glow is drawn
    let seen = false;
    let frame = null;

    function follow() {
        // Ease toward the pointer rather than tracking it exactly — the lag is
        // what makes this read as light following the mouse instead of a
        // sprite pinned to the cursor.
        x += (targetX - x) * 0.12;
        y += (targetY - y) * 0.12;

        glow.style.transform = `translate3d(${x}px, ${y}px, 0)`;
        root.style.setProperty('--mx', `${x}px`);
        root.style.setProperty('--my', `${y}px`);

        // Stop burning frames once the glow has effectively caught up.
        if (Math.abs(targetX - x) > 0.4 || Math.abs(targetY - y) > 0.4) {
            frame = requestAnimationFrame(follow);
        } else {
            frame = null;
        }
    }

    window.addEventListener('mousemove', (e) => {
        targetX = e.clientX;
        targetY = e.clientY;

        if (!seen) {
            // Start on the pointer instead of sliding in from the corner.
            seen = true;
            x = targetX;
            y = targetY;
            document.body.classList.add('cursor-active');
        }

        if (!frame) frame = requestAnimationFrame(follow);
    }, { passive: true });

    document.addEventListener('mouseleave', () => {
        document.body.classList.remove('cursor-active');
    });

    document.addEventListener('mouseenter', () => {
        if (seen) document.body.classList.add('cursor-active');
    });
})();
