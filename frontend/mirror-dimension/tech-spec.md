# SAMAS Technical Specification

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^18.3.0 | UI framework |
| react-dom | ^18.3.0 | DOM rendering |
| three | ^0.160.0 | WebGL particle mirror canvas |
| gsap | ^3.12.0 | Animation engine + ScrollTrigger |
| @gsap/react | ^2.1.0 | GSAP React integration (useGSAP) |
| tailwindcss | ^3.4.0 | Utility CSS |
| @fontsource/outfit | ^5.0.0 | Headline font (self-hosted) |
| @fontsource/inter | ^5.0.0 | Body font (self-hosted) |
| @fontsource/space-mono | ^5.0.0 | Monospace font (self-hosted) |

## Component Inventory

### Layout Components
- **Navigation** — Fixed top bar with wordmark, hamburger, scroll progress line
- **CustomCursor** — Lag-following cursor with hover state expansion

### Section Components
- **HeroSection** — Full viewport, contains the M-irror installation
- **MirrorInstallation** — Core interactive typography (SA-M-AS hover effect)
- **TransitionSection** — Mirror dimension entrance (~50vh), clip-path + flash
- **AgentSection** — Container for 5 agent cards with sticky scroll
- **AgentCard** — Glassmorphism card for each agent (reused 5x)
- **FooterSection** — Standard footer with wordmark, links, social

### Effect Components
- **ParticleMirrorCanvas** — Three.js fullscreen shader background

## Animation Implementation Table

| Animation | Library | Implementation Approach | Complexity |
|-----------|---------|------------------------|------------|
| M-letter glow pulse | CSS @keyframes | text-shadow opacity oscillation | Low |
| Mirror line shimmer | CSS @keyframes | opacity pulse 0.3-0.6 over 3s | Low |
| SA/AS hover reveal (slide + blur) | CSS transitions | transform + filter + opacity on class toggle | Medium |
| Light ray on hover | CSS transitions | gradient overlay opacity | Low |
| Clip-path circle expansion | GSAP ScrollTrigger | scrub-linked clip-path animation | High |
| M letter shrink on scroll | GSAP ScrollTrigger | scrub-linked scale + opacity | Medium |
| Flash sweep effect | GSAP | opacity yoyo tween at transition midpoint | Medium |
| Particle mirror shader | Three.js raw ShaderMaterial | Custom GLSL fragment shader | High |
| Mouse-reactive particles | Three.js uniforms | u_mouse uniform driven by mousemove | Medium |
| Per-agent color shift | GSAP ScrollTrigger + Three.js | Interpolate u_accentColor uniform | Medium |
| Agent card scroll entrance | GSAP ScrollTrigger | staggered translateY + opacity per element | Medium |
| Custom cursor lag follow | requestAnimationFrame | lerp-based position tracking | Medium |
| Scroll progress line | GSAP ScrollTrigger | width animation tied to scroll progress | Low |
| Scroll indicator pulse | CSS @keyframes | opacity oscillation | Low |

## State & Logic Plan

### Hover State Management (Hero)
- Two hover zones (left/right divs) cover each half of viewport
- `mouseenter`/`mouseleave` listeners toggle CSS classes on hero container
- CSS handles all transitions (no JS animation needed for hover)
- Classes: `.left-active`, `.right-active`, default (neither)

### Scroll-Linked Animation State
- GSAP ScrollTrigger instances drive all scroll-based animations
- Timeline for transition section coordinates multiple concurrent animations
- Each agent card has its own ScrollTrigger for entrance
- Scroll progress line uses a single ScrollTrigger across the whole page

### Three.js Lifecycle
- Initialized in `useEffect` with cleanup on unmount
- `requestAnimationFrame` loop updates u_time uniform
- Resize listener updates renderer size and u_resolution
- Mousemove listener updates u_mouse uniform
- Lazy initialization via Intersection Observer (only when transition section approaches viewport)

### Custom Cursor Logic
- rAF loop with lerp (0.15 factor) for smooth following
- `mousemove` stores target position globally
- Hover detection via CSS `:hover` on interactive elements (cursor div has `pointer-events: none`)
- Disabled on touch devices via `matchMedia('(hover: hover)')`

## Other Key Decisions

### Raw Three.js over R3F
The particle mirror is a single fullscreen quad with a custom fragment shader — no scene graph, no 3D objects, no lighting. Raw Three.js is simpler and more performant than React Three Fiber for this use case.

### No shadcn/ui Components Used
The design is entirely custom with glassmorphism cards and typographic effects. No standard UI components (buttons, dialogs, forms) are needed.

### Font Loading Strategy
Use @fontsource packages for self-hosted fonts (no Google Fonts CDN dependency). Import in main.tsx for automatic loading.

### Mobile Fallback for Shader
Detect `navigator.hardwareConcurrency < 4` to reduce particle count to 4. On very low-end devices, disable shader entirely and show static gradient background.
