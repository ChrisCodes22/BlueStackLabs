# Technical Notes

A running study reference for this site. Each entry covers **what changed**, **the
code**, **why it works**, and **the transferable principle** — the last one being the
point. The specific fix matters less than the technique you can reuse.

New entries get appended as work lands, so this grows rather than gets rewritten.

---

## Contents

1. [CSS custom properties as a single source of truth](#1-css-custom-properties-as-a-single-source-of-truth)
2. [The 3D hero stack](#2-the-3d-hero-stack)
3. [Pausing and unwinding a CSS animation](#3-pausing-and-unwinding-a-css-animation)
4. [Flip cards and backface-visibility](#4-flip-cards-and-backface-visibility)
5. [The carousel, and focus management](#5-the-carousel-and-focus-management)
6. [The pointer glow: rAF, lerp, and compositing](#6-the-pointer-glow-raf-lerp-and-compositing)
7. [Lighting the grid with a CSS mask](#7-lighting-the-grid-with-a-css-mask)
8. [The canvas grid warp (built, then removed)](#8-the-canvas-grid-warp-built-then-removed)
9. [Debugging horizontal overflow on mobile](#9-debugging-horizontal-overflow-on-mobile) ← **most useful**
10. [A regression worth studying: the scroll-spy](#10-a-regression-worth-studying-the-scroll-spy)
11. [Emoji vs SVG icons, and currentColor](#11-emoji-vs-svg-icons-and-currentcolor)
12. [Accessibility primitives](#12-accessibility-primitives)
13. [Share metadata (Open Graph)](#13-share-metadata-open-graph)
14. [The deploy model](#14-the-deploy-model)

---

## 1. CSS custom properties as a single source of truth

**Where:** `styles.css` — `--layer`, `--font-logo`

The whole hero stack is sized off one variable:

```css
.hero-visual {
    --layer: clamp(160px, 23vw, 345px);
}
```

Everything else derives from it — the box height is `calc(var(--layer) * 1.4)`, the
layer offsets are `calc(var(--layer) * 0.27)`, even the font size inside is
`calc(var(--layer) / 11)`. Responsive breakpoints then override *only* that one value:

```css
@media (max-width: 640px) {
    .hero-visual { --layer: clamp(150px, 48vw, 250px); }
}
```

**Why it works:** custom properties inherit and are resolved at use time, so
redefining `--layer` on the parent cascades into every `calc()` beneath it. You
change one number and twelve rules follow.

**The principle:** when several values must move together, express them as ratios of
one variable rather than as independent numbers. The alternative — twelve hard-coded
px values per breakpoint — is where responsive CSS rots, because you inevitably
update eleven of them.

`clamp(min, preferred, max)` is doing real work too: `23vw` scales with the viewport,
while the min and max stop it collapsing or ballooning. It replaces a stack of
media queries with one expression.

---

## 2. The 3D hero stack

**Where:** `styles.css` `.hero-visual`, `.stack-3d`, `.layer`

Three requirements have to line up for CSS 3D to work at all:

```css
.hero-visual {
    perspective: calc(var(--layer) * 4);   /* 1. viewing distance */
}

.stack-3d {
    transform-style: preserve-3d;          /* 2. children live in 3D */
    transform-origin: calc(var(--layer) / 2) calc(var(--layer) / 2);
}
```

- **`perspective`** on the *parent* sets how far the viewer is from the z=0 plane.
  Smaller = more dramatic foreshortening. Without it, `translateZ` does nothing
  visible — everything renders flat.
- **`transform-style: preserve-3d`** tells the element its children keep their own
  3D positions instead of being flattened into the parent's plane. Forget this and
  your carefully z-offset layers collapse into a single flat image.
- **`transform-origin`** is the pivot. The layers are anchored to the box's
  top-left, so the middle layer's centre sits at `(--layer/2, --layer/2)`. Setting
  the origin there makes the stack spin *in place* instead of orbiting the container's
  centre like a planet.

The three layers are positioned purely with transforms:

```css
.layer:nth-child(1) {
    transform: translate3d(calc(var(--layer) * 0.10), calc(var(--layer) * -0.10), calc(var(--layer) * 0.16));
}
```

**Why `translate3d` and not `top`/`left`:** transforms are handled by the compositor
and don't trigger layout. `top`/`left` force the browser to recalculate geometry
every frame. For anything animated, transform and opacity are the two cheap
properties — treat everything else as expensive.

---

## 3. Pausing and unwinding a CSS animation

**Where:** `styles.css` `.stack-3d`, `.is-open`, `.is-unwinding` + `script.js`

This is the most interesting problem in the codebase.

The stack should sit still when closed and spin when open. The naive approach —
adding and removing the `animation` property — snaps, because removing an animation
instantly reverts the element to its untransformed state.

**The open direction is easy.** The animation is always attached but held at frame
zero:

```css
.stack-3d {
    animation: rotate3d 20s infinite linear;
    animation-play-state: paused;   /* parked on the 0% keyframe */
}

.stack-3d.is-open {
    animation-play-state: running;
}
```

Pausing at 0% means the element renders `rotateY(0deg) rotateX(10deg)` — square-on
with a slight tilt. Resuming just continues from there. No JavaScript needed.

**The close direction is the hard part.** Pause a spin that's 200° through and the
square freezes at 200° — visibly crooked. You need to unwind it back to zero, but
you can't transition *from* an animated value, because the animation always wins
over transitions for the same property.

The fix is to capture the live value, detach the animation, then transition:

```js
function closeStack() {
    stack.classList.remove('is-open');

    const current = getComputedStyle(stack).transform;  // 1. read the live matrix
    stack.classList.add('is-unwinding');                //    (sets animation: none)
    stack.style.transform = current;                    // 2. freeze it inline
    void stack.offsetWidth;                             // 3. force a reflow
    stack.style.transform = 'rotateY(0deg) rotateX(10deg)';  // 4. now transition

    unwindTimer = setTimeout(() => {
        stack.classList.remove('is-unwinding');
        stack.style.transform = '';                     // 5. hand it back
    }, UNWIND_MS);
}
```

Step 3 is the subtle one. Browsers batch style changes and only compute them when
something forces it. Without the reflow, steps 2 and 4 collapse into a single update
and the browser sees only the final value — no transition happens. Reading a layout
property like `offsetWidth` forces synchronous recalculation, so the browser commits
`current` as a real starting point.

`void x.offsetWidth;` is the idiomatic way to write "flush pending style changes." It
looks like dead code; it isn't. Comment it, or someone will delete it.

**Why `setTimeout` rather than `transitionend`:** if the captured matrix already
equals the target, no transition runs and `transitionend` never fires — leaving the
inline styles stuck forever. A timeout always fires.

---

## 4. Flip cards and backface-visibility

**Where:** `styles.css` `.flip-card`, `.flip-inner`, `.flip-face`

```css
.flip-card  { perspective: 1600px; }
.flip-inner { transform-style: preserve-3d; transition: transform 0.7s; }
.flip-card.is-flipped .flip-inner { transform: rotateY(180deg); }

.flip-face  { position: absolute; inset: 0; backface-visibility: hidden; }
.flip-back  { transform: rotateY(180deg); }
```

Both faces are stacked in the same box with `position: absolute; inset: 0`. The back
is pre-rotated 180°, so it faces *away* from you at rest.

`backface-visibility: hidden` is the trick: when an element's back is turned to the
viewer, don't paint it. So at rest you see the front and the back is hidden; rotate
the container 180° and the roles swap.

**A consequence worth knowing:** because both faces are absolutely positioned, they
don't contribute to the container's height — so `.flip-card` needs an explicit
height. That's why it's `height: clamp(420px, 48vw, 530px)` rather than sizing to
content. Whichever face has more content sets the requirement, and you have to work
that out yourself.

---

## 5. The carousel, and focus management

**Where:** `script.js`, `styles.css` `.carousel-*`

The mechanism is trivial — a flex row of full-width slides, moved by one transform:

```js
track.style.transform = `translateX(-${index * 100}%)`;
```

The part worth studying is what happens to the slides you can't see. They're still in
the DOM, still focusable, and a screen reader will still announce them:

```js
slides.forEach((slide, i) => {
    const offscreen = i !== index;
    slide.setAttribute('aria-hidden', String(offscreen));
    cards[i].tabIndex = offscreen ? -1 : 0;
    if (offscreen) setFlipped(cards[i], false);
});
```

Three separate concerns:

- **`aria-hidden`** removes it from the accessibility tree.
- **`tabIndex = -1`** takes it out of the tab order, so keyboard users don't tab into
  a card that's scrolled off-screen and appear to lose focus entirely.
- **Resetting the flip** stops a card sliding back into view mid-rotation later.

Same idea inside the flipped card — the link on the hidden face is pulled out of the
tab order until the face is showing:

```js
const link = card.querySelector('[data-flip-link]');
if (link) link.tabIndex = flipped ? 0 : -1;
```

**The principle:** "visually hidden" and "hidden" are different things. Anything you
move off-screen with a transform is still fully present to the keyboard and to
assistive tech. If you hide something visually, hide it in the other two senses too.

---

## 6. The pointer glow: rAF, lerp, and compositing

**Where:** `background.js`

```js
function follow() {
    x += (targetX - x) * 0.12;
    y += (targetY - y) * 0.12;
    glow.style.transform = `translate3d(${x}px, ${y}px, 0)`;

    if (Math.abs(targetX - x) > 0.4 || Math.abs(targetY - y) > 0.4) {
        frame = requestAnimationFrame(follow);
    } else {
        frame = null;   // caught up — stop burning frames
    }
}
```

**The lerp.** `x += (target - x) * 0.12` moves 12% of the remaining distance each
frame. Large gap → large step; small gap → small step. That produces natural easing
with one line and no easing curve, and it's what makes the glow feel like it's
*following* the cursor rather than being welded to it. That lag is the entire effect —
set the factor to `1` and it becomes a sticker on your pointer.

**Self-terminating loop.** The `else { frame = null }` branch matters. A naive
implementation calls `requestAnimationFrame` forever and burns 60fps of battery
while the page sits idle. Here the loop stops once it's within 0.4px and only
restarts on the next `mousemove`.

**`translate3d`, not `top`/`left`.** Same reason as the stack: transforms are
composited. Animating `top` triggers layout on every frame.

**`{ passive: true }`** on the mousemove listener promises you won't call
`preventDefault()`, letting the browser skip a check before scrolling.

---

## 7. Lighting the grid with a CSS mask

**Where:** `background.css` `.grid-glow`

The grid brightens near the pointer. There are two copies of it: the normal dim one,
and a brighter one revealed only in a circle around the cursor.

```css
.grid-glow {
    -webkit-mask-image: radial-gradient(circle 120px at var(--mx, -999px) var(--my, -999px),
        #000 0%, rgba(0, 0, 0, 0.4) 50%, transparent 75%);
            mask-image: radial-gradient(...same...);
}
```

A mask uses *alpha* to decide visibility: opaque areas of the mask show the element,
transparent areas hide it. So a radial gradient from black to transparent produces a
soft circular reveal. `background.js` sets `--mx` / `--my` on `:root`, and the mask
follows.

The `-999px` fallback keeps the effect fully hidden until the mouse first moves.

**The bug worth remembering:** the mask sits on a *wrapper*, not on the grid itself.
The grid has a slow drift animation:

```css
.grid-background { animation: gridMove 20s linear infinite; }
```

A mask is applied in the element's own coordinate space, so masking the moving grid
directly would have dragged the lit circle along with it — the highlight would
slowly wander away from the cursor. Putting the mask on a static wrapper and letting
the grid move *inside* it keeps the circle pinned to the pointer.

**The principle:** transforms and masks on the same element interact. When something
must stay fixed relative to the viewport while its content moves, separate them into
two elements.

---

## 8. The canvas grid warp (built, then removed)

**Where:** removed in commit history — worth reading back if you want it again.

For a while the grid bent away from the cursor. This is documented because the
*reason it needed a canvas* is instructive.

CSS grid lines are `linear-gradient` backgrounds. A gradient is a fill — it has no
geometry, so there is nothing to bend. No amount of CSS will curve those lines. To
warp them you have to draw them yourself:

```js
function warp(x, y, t) {
    const ox = x - pointerX, oy = y - pointerY;
    const d2 = ox * ox + oy * oy;
    if (d2 < PUSH_RADIUS * PUSH_RADIUS) {
        const d = Math.sqrt(d2) || 1;
        const f = 1 - d / PUSH_RADIUS;
        const push = PUSH * f * f;        // squared = eased falloff
        dx += (ox / d) * push;
        dy += (oy / d) * push;
    }
}
```

Two details worth keeping:

- **`(ox / d, oy / d)`** is the unit vector from cursor to point — dividing by the
  distance normalises it to length 1, so you can then scale it by exactly how far you
  want to push. Reverse the subtraction and it pulls instead.
- **`f * f`** rather than `f` gives an eased falloff. Linear falloff makes the centre
  a visible spike; squaring rounds it off.

Brightness used one path stroked twice — once dim, once with a radial gradient
`strokeStyle` centred on the pointer, so lines faded back to normal past the radius.
Building the geometry once and stroking twice is much cheaper than per-segment
styling.

It ran at 100fps. It was removed because you didn't like the look — which is a
perfectly good reason, and worth noting: performance was never the deciding factor.

---

## 9. Debugging horizontal overflow on mobile

**The most useful entry here — the method generalises to almost any layout bug.**

**Symptoms:** page appeared zoomed in on a phone; zooming out shifted the whole site
left; the hero stack couldn't be tapped.

Those look like three bugs. They were one.

### Step 1: reproduce at a real width

Resizing the browser window didn't work — macOS enforces a minimum window width, so
Chrome couldn't go below ~938px. Headless Chrome screenshots at `--window-size=390`
were **actively misleading**: it laid out at a wider viewport and cropped the image to
390px, so the page *looked* broken in a way it wasn't.

What worked was an iframe, because an iframe's width is a genuine CSS viewport:

```html
<iframe src="/index.html" style="width:375px; height:760px"></iframe>
```

Media queries inside it evaluate against 375px. Real mobile layout, on a desktop.

### Step 2: measure, don't eyeball

```js
const d = frame.contentDocument;
d.documentElement.scrollWidth   // 438
d.documentElement.clientWidth   // 375
```

`scrollWidth > clientWidth` is the definition of horizontal overflow. 63px of it.

### Step 3: find the culprit

Walk every element, compare its box against the viewport:

```js
d.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.right > vw + 1 || r.left < -1) offenders.push(el);
});
```

Then **sort by right edge descending** — the furthest-right element is usually the
cause, and its ancestors follow it in the list.

Two refinements that made the output trustworthy:

- **Skip `position: fixed`** elements; they don't affect document width.
- **Skip anything with a clipping ancestor.** The carousel's off-screen slide sits at
  x=690 but is clipped by `overflow: hidden`, so it contributes nothing. Without this
  filter it dominated the results and buried the real answer:

```js
function isClipped(el) {
    for (let p = el.parentElement; p; p = p.parentElement) {
        const ox = getComputedStyle(p).overflowX;
        if (['hidden','clip','auto','scroll'].includes(ox)) return true;
    }
    return false;
}
```

### Step 4: the actual cause

```
div.stack-3d   L93  W349  R441
```

`.stack-3d` had `left: calc(var(--layer) * 0.35)` — a nudge to sit it in the
right-hand column of the two-column desktop hero. Below 968px the hero becomes one
column, but the nudge stayed, pushing the stack off the screen.

That single fact explains all three symptoms. The extra width is what let the page
pan sideways and sit left when zoomed out. And because most of the stack's hit area
was past the screen edge, there was nothing left to tap — it was never an animation
bug at all.

### Step 5: the fixes

```css
/* 1. Don't apply a desktop-only offset on mobile */
@media (max-width: 968px) {
    .stack-3d { left: 0; margin-left: auto; margin-right: auto; }
}

/* 2. The box never needed to be 100% wide */
.stack-3d { width: var(--layer); }

/* 3. body alone doesn't stop the document overflowing */
html { overflow-x: hidden; }
```

Fix 2 caught a second, invisible instance of the same bug: at `width: 100%` the box
hung ~80px past the viewport **on desktop too**. Nothing visible lived out there
(the layers are absolutely positioned against the box's top-left, so the box's width
never placed them), so nobody noticed — but it was real overflow the whole time.
Call this **phantom width**: an element whose box extends past the viewport while its
visible content doesn't.

Fix 3 is a genuine gotcha. `body { overflow-x: hidden }` on its own does *not*
prevent the document from overflowing — you need it on `html` too, or a stray wide
element still leaves the page pannable.

### Step 6: a caveat about your own instruments

Once `overflow-x: hidden` was on `html`, `scrollWidth` started reporting 375 — the
*clipped* width — even while content was still too wide. **Clipping makes
`scrollWidth` useless as a detector.** After that point only per-element
`getBoundingClientRect()` told the truth. Know which of your measurements a fix
invalidates.

### Step 7: verify functionally, not just visually

A layout that measures correctly can still be unusable, so the last check simulated a
real tap and asserted on state:

```js
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t => el.dispatchEvent(...));
// then: does .is-open appear? does aria-expanded flip? is the arrow >= 44px?
```

That's what caught the carousel arrows being 40px — under the 44px minimum touch
target, which no screenshot would have revealed.

---

## 10. A regression worth studying: the scroll-spy

**Where:** `script.js`

This code worked perfectly for a year, then silently broke:

```js
window.addEventListener('scroll', () => {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-links a');

    let current = '';
    sections.forEach(s => { if (window.scrollY >= s.offsetTop - 200) current = s.id; });

    navLinks.forEach(link => {
        link.classList.remove('active');                       // ← unconditional
        if (link.getAttribute('href').slice(1) === current) link.classList.add('active');
    });
});
```

It highlights the nav item for the section you're looking at. Fine on a one-page
site where every nav link is a `#anchor`.

Then the site was split into pages. Subpages mark their current nav item in the
markup (`class="active"`) and have no `section[id]` elements. So `current` stays
`''`, and that unconditional `remove('active')` strips the marker off every link the
moment you scroll. The underline just vanished.

```js
if (!sections.length) return;                                  // nothing to spy on
const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');  // same-page only
```

**The principle:** the bug wasn't in the code that changed, it was in code that
*didn't*. This function held an unstated assumption — "every nav link is managed by
me" — that was true when written and quietly became false. When you change an
architecture, the risk isn't only in new code; it's in old code whose assumptions
you've invalidated. Unconditional `remove()` calls are a good place to look, because
they claim ownership of state they may not own.

---

## 11. Emoji vs SVG icons, and currentColor

19 emoji were being used as UI icons. Two problems:

1. **Emoji are fonts, and every OS ships its own.** 🌐 on Windows is not 🌐 on macOS,
   which is not 🌐 on Android. Your site literally looked different per platform.
2. You can't style them — no control over weight, colour, or size relative to text.

Replaced with inline SVG on a consistent 24×24 grid:

```html
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>
    <path d="M2 12h20"/>
</svg>
```

```css
.service-icon { color: var(--light-blue); }
.service-icon svg {
    fill: none;
    stroke: currentColor;   /* ← inherits .service-icon's colour */
    stroke-width: 1.5;
}
.service-card:hover .service-icon { color: var(--accent-cyan); }
```

**`currentColor`** resolves to the element's computed `color`. Because the stroke
references it, changing `color` on hover re-tints the icon — no second rule targeting
the SVG, no fill swapping in JS. One property drives text and icon together.

`viewBox="0 0 24 24"` with no `width`/`height` on the SVG lets CSS size it freely
while the coordinate system stays fixed, so one set of path data works at any size.

`aria-hidden="true"` because these icons sit next to a text label that already says
the same thing — announcing both would just be repetition.

---

## 12. Accessibility primitives

**Skip link.** Every page starts with:

```html
<a href="#main" class="skip-link">Skip to content</a>
```

```css
.skip-link { position: absolute; top: -60px; transition: top 0.2s; }
.skip-link:focus { top: 0; }
```

Parked off-screen until focused. Without it, a keyboard or screen-reader user tabs
through all five nav links on *every page* before reaching content. Note it's hidden
by position, not `display: none` — a `display: none` element cannot receive focus, so
it could never appear.

**Landmark.** Content is wrapped in `<main id="main">`, giving assistive tech a
"jump to main content" target and the skip link somewhere to land.

**State, not just styling.** The stack is a real control:

```html
<div class="stack-3d" role="button" tabindex="0" aria-expanded="false">
```

`aria-expanded` is kept in sync in JS, and Enter/Space are handled explicitly —
because a `<div>` with `role="button"` gets none of `<button>`'s built-in keyboard
behaviour. You take on that responsibility the moment you use a div instead.

**Motion preference.** Decorative animation is disabled under
`prefers-reduced-motion: reduce`, but the stack still opens and cards still flip —
they just change state instantly. The distinction: *decoration* gets removed,
*function* stays.

---

## 13. Share metadata (Open Graph)

Without these tags, pasting a link into Slack, LinkedIn, or iMessage renders a bare
URL — no title, no description, no image.

```html
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:image" content="https://bluestacklabs.software/images/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
```

Three things that trip people up:

- **`og:image` must be an absolute URL.** Scrapers don't resolve relative paths.
- **1200×630** is the standard 1.91:1 ratio. Wrong ratios get cropped unpredictably.
- **Declaring width/height** lets platforms reserve space before fetching the image,
  so the preview doesn't reflow.

The image is generated from `tools/og-image.html` — a plain HTML page rendered at
exactly 1200×630 with headless Chrome:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --window-size=1200,630 --virtual-time-budget=8000 \
  --screenshot=og.png "http://127.0.0.1:8799/og-image.html"
```

Keeping the generator in the repo means the image is reproducible instead of being a
mystery binary — regenerate it when the logo lands.

---

## 14. The deploy model

Netlify builds from GitHub on push to `main`. There is no separate deploy step:
**`git push` is publishing.**

The consequence that bites: Netlify serves the repo directly, so *every asset a page
references must be committed*. An uncommitted image isn't an incomplete repo, it's a
broken image in production. Same for a font file, a stylesheet, anything.

It cuts the other way too — anything committed is publicly fetchable at a guessable
URL, whether or not it's linked from anywhere. That's why `July Recap.pdf` is
deliberately untracked, and why `robots.txt` disallows `/tools/` and `/docs/`.
(Note that `robots.txt` is a request to crawlers, not access control — it keeps
things out of search results, it does not make them private.)

---

## 15. The MarketReady cover, and why "bigger" wasn't the fix

The MarketReady slide now leads with `images/marketready-cover.png` — the branded
1200×630 banner — instead of the dashboard screenshot.

The first attempt used the 600×600 square logo card, and it rendered small and
floaty with wide empty gutters. The instinct is to reach for a higher-resolution
file, but resolution was never the problem, and this is the useful thing to
internalize: **`object-fit: contain` scales by aspect ratio, not by pixel count.**

`.flip-front img` is a flex child (`flex: 1; min-height: 0`) in a column, so its
*box* is as wide as the card and as tall as whatever's left under the caption —
about 658×366 at desktop width, a ratio of 1.80:1. Then:

```css
object-fit: contain;
```

`contain` scales the image until it fits *entirely* inside that box, preserving
its ratio. The limiting dimension wins:

| source | ratio | renders as | result |
|---|---|---|---|
| `marketready_card_600.png` | 1.00:1 | 366×366 | ~146px of gutter each side |
| `marketready_card_1200.png` | 1.00:1 | 366×366 | **identical** — 4× the pixels, same gap |
| `marketready_banner_1200x630.png` | 1.90:1 | 658×346 | ~10px letterbox, fills the frame |

The 1200×1200 card is four times the data and lands on exactly the same 366×366
square, because height is the constraint and the ratio didn't move. Only changing
the *shape* changes the fit — which is why the banner works: at 1.90:1 it's a
near-match for the box's 1.80:1, so it fills edge to edge with a hairline
letterbox top and bottom.

Switching to `object-fit: cover` would fill any frame, but by cropping the
overflow — on the square that meant slicing the left and right off the wordmark.
The comment above that rule warns about exactly this.

`width="1200" height="630"` stay on the tag on purpose. The browser uses the
ratio to reserve the right space before the bytes arrive, so the caption
underneath doesn't jump when a lazy-loaded image finally decodes.

## 16. Why this site has no build credit

Client sites get a `Site created by Blue Stack Labs` line in the footer — passive
marketing a visitor can follow back. This site deliberately does not.

The reasoning is worth writing down because the two lines look similar but make
different claims. The copyright line asserts *ownership of the content*. A build
credit is *attribution for the work*. On a client's site those genuinely differ:
the client owns the content, Blue Stack built it, and the credit carries real
information. On bluestacklabs.software they collapse into the same party, so the
credit says nothing the `© 2026 Blue Stack Labs` line and the entire surrounding
site don't already say. It was added here briefly and removed for that reason.
