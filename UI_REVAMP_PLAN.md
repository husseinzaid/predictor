# GUI Revolution — World Cup 2026 Predictor

A design + implementation brief for taking the frontend from "functional SaaS
form" to "World Cup broadcast experience." Written for an agent with no prior
context on this conversation — read `HANDOVER.md` and `API_CONTRACT.md` first
for how the app/data work; this doc is purely about the **look, feel, and
interactions**. No backend or formula changes are needed for this work.

## Current state (what we're replacing)

`frontend/src/App.tsx` (555 lines) + `frontend/src/App.css` (659 lines) +
`frontend/src/index.css`. Plain CSS custom properties, a teal accent
(`#0f766e`) on a pale slate background, system fonts (Inter is referenced in
`--sans` but never actually loaded), no animation, no icons, emoji flags as
the only "graphic" element. It works, but looks like an internal admin tool.
`recharts` is in `package.json` but unused — fine to remove once nothing
references it.

Run it locally with:
```bash
cd frontend && npm run dev   # http://localhost:5173, defaults to mocks (VITE_USE_MOCKS=true)
```

---

## 1. Design direction

**Theme: "Night Match" — a floodlit stadium broadcast graphics package.**
Dark, high-contrast canvas that makes color (team flags, score bars, the
World Cup palette) pop, with bold geometric type and motion that feels like a
sports broadcast lower-third / stats overlay, not a corporate dashboard.

### Color palette

Inspired by the 2026 FIFA World Cup (Canada/Mexico/USA) identity and host-nation
colors — not pixel-exact official assets (don't import FIFA logos/marks), but
the same energy: bold green, deep blue, red, and trophy gold on near-black.

```css
--bg:            #0a0e1a;   /* near-black stadium night */
--bg-elevated:   #11182b;   /* panel background */
--bg-elevated-2: #1a2440;   /* hover/active surface */
--surface:       #141c33;
--border:        rgba(255, 255, 255, 0.08);
--border-strong: rgba(255, 255, 255, 0.16);

--text:          #e7ecf7;
--text-strong:   #ffffff;
--muted:         #8b97b8;

--green:         #2DBE4E;   /* pitch / "go" */
--green-glow:    rgba(45, 190, 78, 0.35);
--blue:          #2A4BD7;   /* WC2026 blue */
--red:           #E52A39;   /* WC2026 red */
--gold:          #FFC72C;   /* trophy / champion */
--gold-glow:     rgba(255, 199, 44, 0.4);

--gradient-brand: linear-gradient(135deg, var(--green) 0%, var(--blue) 55%, var(--red) 100%);
--gradient-gold:  linear-gradient(135deg, #FFE07A 0%, var(--gold) 50%, #E8A100 100%);

--shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
--radius: 16px;
```

Use the brand gradient sparingly — hero headline text (gradient text-fill),
the primary "Simulate" button, the champion power-score bar, progress
"score-track" fills. Gold is reserved for **the champion / winner state
only** (champion pill, trophy icon, confetti, winning bracket path) so it
stays special.

Offer a light mode too (swap the above for a clean white/slate palette,
keep the same accent hues) via a `data-theme="light"` attribute + toggle in
the header — but dark is the default and the "wow" mode.

### Typography

Add via `@fontsource` packages (self-hosted, no Google Fonts CDN dependency):

```bash
npm install @fontsource/bricolage-grotesque @fontsource/inter @fontsource-variable/jetbrains-mono
```

- **Display / headings**: `Bricolage Grotesque` (variable weight, very
  current, has a sporty/editorial feel) — `font-family: "Bricolage Grotesque", sans-serif`
- **Body / UI**: `Inter` (already referenced, just wasn't loaded)
- **Scorelines / numbers / percentages**: `JetBrains Mono` (variable) with
  `font-variant-numeric: tabular-nums` — gives the scoreboard/ticker feel for
  match scores, Power Score, Champion %.

Import the font CSS files at the top of `src/index.css` (or `main.tsx`):
```ts
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource/inter/400.css";
import "@fontsource/inter/600.css";
import "@fontsource-variable/jetbrains-mono";
```

### Motifs

- Subtle pitch-line texture or grain on the page background (low-opacity SVG
  or CSS `repeating-linear-gradient`) — evokes a stadium pitch without being
  literal.
- Flags stay as emoji (already in the data), but render larger and inside a
  small rounded "chip" with a soft shadow so they read as badges, not inline
  text.
- Trophy 🏆 as the recurring "champion" icon — animated (see §4).

---

## 2. New packages

```bash
npm install framer-motion canvas-confetti lucide-react clsx
npm install -D @types/canvas-confetti
npm install @fontsource-variable/bricolage-grotesque @fontsource/inter @fontsource-variable/jetbrains-mono
npm uninstall recharts
```

| Package | Why |
|---|---|
| `framer-motion` | Industry-standard React animation. Entrance animations, layout transitions (bracket rounds advancing), animated number/bar fills, `AnimatePresence` for the results panel appearing. |
| `canvas-confetti` | Tiny (~5kb), no React wrapper needed — call `confetti({...})` imperatively when a champion is decided. Supports custom colors and `confetti.shapeFromText({ text: "🏆" })` / emoji shapes for on-theme bursts. |
| `lucide-react` | Clean, modern icon set (tree-shakeable). Replace the bare "i" info-dot, add icons per factor category (see §3). |
| `clsx` | Tiny classname-joining helper — current code already does manual ternaries like `factorEnabled ? "factor-control" : "factor-control disabled"`; `clsx` cleans this up everywhere, especially once more conditional states are added (top-3 highlight, qualified, winner, etc.). |
| `@fontsource/*` | Self-hosted fonts, no external request, no FOUC/CLS concerns. |

Do **not** add a full component library (MUI/Chakra/AntD) or migrate to
Tailwind — the existing CSS-custom-properties architecture is fine and a
framework swap would be a much bigger, riskier change than what's being asked
for here. Keep `App.css`, just redo the tokens and component styles.

---

## 3. Component-by-component redesign

### 3.1 Header / Hero

- Replace the plain `eyebrow + h1 + p` stack with a header bar: small
  "WC2026 PREDICTOR" wordmark/logo-mark on the left (could be a simple
  geometric badge using the brand gradient + a football emoji or
  `lucide-react`'s `Trophy`/`Goal` icon), light/dark theme toggle on the
  right.
- Hero headline ("Your formula. Your World Cup champion.") gets the brand
  gradient as a text-fill (`background: var(--gradient-brand);
  -webkit-background-clip: text; color: transparent`), large Bricolage
  Grotesque weight 800+.
- Animate the hero in on load with `framer-motion` (`initial={{ opacity: 0,
  y: 16 }} animate={{ opacity: 1, y: 0 }}`).
- Optional: faint animated gradient blobs or a slowly-panning pitch-line
  texture behind the hero (CSS only, `prefers-reduced-motion` aware).

### 3.2 Controls panel (factor sliders)

- Each factor category (`form`, `ranking`, `squad`, `market`, `history`,
  `fun`) gets a `lucide-react` icon in its heading:
  - `form` → `Activity` (Elo)
  - `ranking` → `ListOrdered` (FIFA rank)
  - `squad` → `Users` (squad quality / league strength)
  - `market` → `TrendingUp` (betting odds)
  - `history` → `History` (tournament experience)
  - `fun` → `Sparkles` or per-factor icons (`Globe` for population,
    `DollarSign` for GDP, `Plane` for travel, `Sun` for heat, `Home` for
    home advantage)
- Restyle the `<input type="range">` sliders entirely (custom
  `::-webkit-slider-thumb`/`::-moz-range-thumb`): brand-gradient track fill
  up to the current value, a glowing circular thumb (box-shadow using
  `--green-glow`) that scales up slightly on drag/focus.
- "Solo" button → small pill/chip, brand-gradient border when active for
  that factor (i.e. when it's the only enabled one).
- "AI Recommended defaults" button: keep the "AI" badge but give it a subtle
  animated gradient shimmer (CSS `background-position` keyframe animation on
  a gradient background, `background-size: 200% 100%`).
- "Randomize" button: `lucide-react`'s `Shuffle` icon, spin 360° on click
  (`framer-motion` `whileTap` or a CSS animation triggered by a key change).
- "Simulate World Cup" primary button: full brand-gradient background,
  glow/shadow using `--green-glow`, scale-down `whileTap`. While loading,
  swap the label for a small spinning football/`lucide-react` `Loader2`
  icon + "Simulating...".

### 3.3 Power rankings table

- Wrap each row in `motion.tr` with a staggered entrance
  (`transition={{ delay: index * 0.02 }}`) when results first appear.
- Top 3 rows: left border accent in gold/silver/bronze
  (`#FFC72C` / `#C0C7D1` / `#D8975A`) plus a small medal emoji or
  `lucide-react` `Medal` icon next to the rank number.
- Power Score / Champion % bars (`.score-track`): animate the inner bar's
  `width` from 0 → target with `framer-motion` (`initial={{ width: 0 }}
  animate={{ width: \`${pct}%\` }}`), brand-gradient fill for Power Score,
  gold gradient for Champion % (it's literally "chance of winning the
  trophy").
- Flags render in the rounded "chip" style from §1, slightly larger
  (`1.4em`).

### 3.4 Group stage

- Each group card becomes a "scoreboard" tile: dark elevated surface,
  subtle top border in the brand gradient, group letter as a large faint
  watermark numeral in the corner.
- Match scores: large `JetBrains Mono` tabular numerals, animate in with a
  quick scale/opacity pop (`framer-motion`, staggered per matchday).
- Qualified teams: replace the current `.qualified` row tint with a small
  green `lucide-react` `CheckCircle2` icon next to their position, and a
  thin green left-border on the row.

### 3.5 Knockout bracket — the centerpiece

This is the highest-impact visual change. Currently it's just stacked round
columns with no connecting lines — replace with an actual bracket-tree
layout:

- Render rounds as columns (already the structure) but add SVG (or
  absolutely-positioned `div`) connector lines between each match and the
  match it feeds into in the next round, like a real tournament bracket.
  This can be hand-rolled with CSS (each match card has a pseudo-element
  "elbow" connector) — no need for a bracket library, the round/match
  structure from the API is already a clean binary tree.
- Winning team in each match: bold text, small green up-chevron
  (`lucide-react` `ChevronUp` or a green dot), brand-gradient left border on
  their slot. Losing team: muted/dimmed text.
- The **Final**'s winner — i.e. `result.bracket.champion` — gets the full
  "champion treatment": gold gradient background on their slot, a `Trophy`
  icon, and is the element that triggers confetti (see §4).
- Penalty shootout note (`pen. 4-3`): small pill badge instead of plain text.

### 3.6 Champion reveal

- Add a new "Champion" hero card at the top of the results stack (above
  power rankings), shown once `result` is set: large flag, team name in
  Bricolage Grotesque, gold gradient background/border, animated trophy
  (`lucide-react` `Trophy` with a CSS bounce/shine keyframe, or an emoji 🏆
  with a subtle rotate+scale loop).
- This card is what triggers the confetti burst on mount (see §4) — it's the
  "moment" of the experience, so it should feel like one.

---

## 4. Confetti

Use `canvas-confetti` imperatively in a `useEffect` keyed on
`result?.bracket.champion`:

```ts
import confetti from "canvas-confetti";

useEffect(() => {
  if (!champion) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const colors = ["#2DBE4E", "#2A4BD7", "#E52A39", "#FFC72C"];
  confetti({ particleCount: 120, spread: 90, origin: { y: 0.3 }, colors });
  confetti({
    particleCount: 40,
    spread: 60,
    origin: { y: 0.3 },
    shapes: [confetti.shapeFromText({ text: "🏆", scalar: 2 })],
  });
}, [champion]);
```

- Fire once per new simulation result (not on every render — key the effect
  on `result.bracket.champion` + maybe a result identity/timestamp so
  re-running with the *same* champion still celebrates).
- Respect `prefers-reduced-motion`.
- Keep it to 1-2 bursts — don't loop or keep firing; it should feel like a
  "ta-da" moment, not noise.

---

## 5. Motion principles (framer-motion)

- **Page load**: hero + panels fade/slide in, staggered ~80ms apart.
- **Results appearing**: wrap the whole results stack in
  `AnimatePresence`/`motion.div` with a fade+slide-up when `result` first
  becomes non-null.
- **Bars/numbers**: animate from 0 to target value on mount (Power Score,
  Champion %, group standings GF/GA could tick up too if cheap to do).
- **Buttons**: `whileHover={{ scale: 1.02 }}`, `whileTap={{ scale: 0.98 }}`
  on primary/secondary buttons.
- **Respect `prefers-reduced-motion`**: wrap animation values so reduced-
  motion users get instant/near-instant transitions (framer-motion's
  `useReducedMotion()` hook).

---

## 6. Implementation checklist

1. `npm install` the packages from §2; remove `recharts`.
2. Import fonts in `main.tsx`/`index.css`; set `--sans`/new `--display`/
   `--mono` custom properties.
3. Rewrite `src/index.css` tokens per §1 (dark theme default; optional light
   theme via `data-theme` attribute + toggle).
4. Rebuild the header/hero (§3.1).
5. Restyle the controls panel: category icons, custom sliders, buttons
   (§3.2).
6. Add the Champion reveal card + confetti hook (§3.6, §4).
7. Restyle power rankings table: animated bars, top-3 highlight (§3.3).
8. Restyle group stage cards (§3.4).
9. Rebuild the bracket with connector lines and champion treatment (§3.5).
10. Add framer-motion entrance/stagger animations throughout (§5).
11. Add a light/dark theme toggle (persists to `localStorage`).

## 7. Verification — test in the browser, not just `tsc`/`eslint`

```bash
cd frontend && npm run dev   # mocks on, http://localhost:5173
```

Walk through:
- Initial load: hero animates in, sliders show "AI Recommended" defaults.
- Click **Simulate World Cup**: results appear, champion card shows,
  confetti fires once.
- Click **Simulate World Cup** again (same weights): confetti fires again
  (don't let it get "stuck" only firing the first time).
- Use a **Solo** button (e.g. Population) and re-simulate: results update,
  no animation glitches from re-render of an already-visible results panel.
- Expand "Show all 48 teams" in power rankings — stagger animation
  shouldn't re-trigger absurdly for 48 rows (cap delay or disable stagger
  past row ~12).
- Toggle light/dark theme — check contrast on score bars, bracket
  connectors, confetti colors still visible on light background.
- Resize to mobile width — controls panel, group grid, and bracket columns
  should remain usable (bracket may need horizontal scroll on narrow
  screens — that's fine, just make sure it's scrollable not clipped).
- Set `prefers-reduced-motion: reduce` (browser devtools) and confirm
  confetti and most animations are suppressed/instant.
