---
name: darkevox-ui-style
description: The DarkeVox design system - pastel blue on cream. Color tokens, typography, spacing, radius, motion rules, and component specs for the tray, HUD, panel, and dialogs. Read before building or changing any UI in this repo, and keep ui/theme.py in lockstep with the tokens here.
---

# DarkeVox UI Style

The app should feel like good stationery: warm cream surfaces, one soft blue accent, dark warm-gray ink. Calm and quiet, because DarkeVox lives in the corner of the screen and interrupts people mid-thought; nothing may flash, bounce, or shout. "Modern and polished" here means alignment you can feel, few colors used consistently, generous whitespace, real rounded corners on real translucent windows, and motion that answers the hand without ever performing.

`ui/theme.py` is the single source of truth in code and must mirror the tokens below. If a design decision isn't covered here, add it here first, then implement.

## Color tokens

| Token | Hex | Use |
|---|---|---|
| `cream-50` | `#FFFDF8` | raised surfaces: cards, inputs, menus, the hero field |
| `cream-100` | `#FAF5EC` | window and dialog background (opt-in via `role="window"`) |
| `cream-200` | `#F0E7D8` | hairline borders, filled inputs, the segment track |
| `blue-100` | `#DEEBF8` | selected/hover tint on cream, pressed tint |
| `blue-200` | `#BCD6EF` | selection background, disabled primary fill |
| `blue-300` | `#97BEE5` | progress fill, listening pulse and dot |
| `blue-400` | `#6FA1D4` | the mark's ground (idle), checked borders, checkbox hover |
| `blue-500` | `#4C7FB5` | recording ground, focus borders, active accents |
| `blue-600` | `#44739F` | primary button rest (4.9:1 with cream-50 text) |
| `blue-650` | `#3F6B98` | primary hover — hover darkens when text is light |
| `blue-700` | `#3A648C` | primary pressed |
| `ink-900` | `#2A3340` | primary text, icons on light fills |
| `ink-600` | `#5B6675` | secondary text, captions, overlines, placeholders |
| `ink-400` | `#939CAA` | disabled text only — under 3:1 on cream, never labels |
| `sage-300` | `#A9C7A0` | success, "inserted", the "grounded" badge |
| `honey-300` | `#EDCF9A` | polishing state, fallback warnings |
| `clay-400` | `#D9857E` | error dots, invalid borders (non-text uses) |
| `clay-600` | `#AD5049` | error text (4.8:1 on cream-100) |

Rules that keep it coherent:

- Text on cream is `ink-900` or `ink-600`, never pure black, pure gray, or `ink-400` (that band fails contrast; it exists for disabled states only).
- Light text (`cream-50`) sits only on `blue-600` or darker. On every pastel fill, text is `ink-900`. Target 4.5:1 for all text; pastel decorative elements are exempt, text never is. When light text sits on blue, hover goes darker, never lighter.
- One accent per view. The mic is brand; Insert is the action; nothing else in the card carries saturated blue.
- Sage, honey, and clay appear only with their meanings (success, in-progress/warning, error). Never decoratively.

## Typography

Segoe UI Variable, falling back to Segoe UI (the app pins Segoe UI 10pt on Windows so Qt never falls back to MS Shell Dlg 2). Exactly four sizes, exported from `theme.py` as constants so painted text can't drift: 10 overline (uppercase, +1px letter-spacing, semibold, `ink-600`), 11 caption, 13 body, 15 section. Weights: regular and semibold only.

## Spacing and shape

Spacing scale: 4 / 8 / 12 / 16 / 20 / 24. Labels sit 4 from their control; related controls 8 apart; unrelated groups 16-24. Card padding is 20. Radius scale, exported as constants: 6 nested chrome (menu items, progress, tooltips), 10 controls/inputs/menus/tab panes, 16 cards, full pill on the HUD and badges.

Exactly one shadow exists: 0 6 24 rgba(42, 51, 64, 0.16), applied via QGraphicsDropShadowEffect to floating surfaces (panel stack, HUD, menus). Frameless windows reserve `SHADOW_MARGIN` (30 px) of transparent border so the blur never clips.

**The translucency law.** The window background fill is opt-in: framed windows set `role="window"`; a global QWidget fill is banned, because it paints opaque squares behind every rounded frameless surface. Menus and combo popups get `WA_TranslucentBackground` + frameless flags so their radius is real. Every container inside the panel and HUD stays genuinely transparent.

## Motion

Exported as duration constants from `theme.py`; curves and the reduce gate live in `ui/motion.py`. Exponential ease-outs (OutQuart/OutQuad) only — no bounce, no elastic. Everything retargets from its current value on interruption; loops stop when their surface hides; `reduce_motion` (config, or Windows' animation setting) turns every duration to zero.

- Buttons (`ui/buttons.py`): hover tint 170 ms in / 150 ms out, pressed tint 60 ms, press scale 0.97 (110 ms down, 160 ms up).
- Panel open/close: 90 ms fade in, 150 ms fade out (windowOpacity — the HUD's exact pattern). The paired-states rule: open animates, so close animates.
- Mic: press scale 0.96; recording pulse ring breathes on a 1.2 s InOutSine cycle (the one loop, shared rhythm with the HUD dot); ground color tweens 150 ms; the wave bars ride the live input level (0.35–1.0 scale) so the mark itself is the meter.
- HUD: enters in 90 ms and exits in 150 ms — it rides every hotkey dictation, so immediacy IS the polish. Width changes glide 120 ms. The done dot swells once, 1.35→1.0 over 280 ms.
- Text arrival (heard commit, polish result): a 180 ms opacity settle from 0.55. Streaming partials stay instant — animating them reads as flicker.
- Never animate: the hotkey→inject path (latency-critical), streaming partials, startup restore, drags (locked 1:1; easing belongs only to the release settle when the panel is clamped back on-screen).

## Components

**Status vocabulary (`ui/status.py`).** The one source for every state name, dot color, and status string. The controller, HUD, panel, and tray all import it — the app never says "listening" two different ways. States: ready (ink-400), listening (blue-300, pulsing, live "Listening — 0:12"), transcribing (blue-400), polishing (honey-300, carries the tone), inserted (sage-300, word count), no-speech (ink-400 — a non-event, never sage), fallback (honey-300 on every surface), error (clay-400 dot, clay-600 text).

**HUD.** The keyboard flow's visual and the panel's sibling: a frameless card, bottom-center, 8 px above the taskbar, 44 px tall, radius 16, `cream-50` fill, hairline border, the app shadow. Content, left to right: the 28 px wave mark (ground deepens and bars ride the live level while listening — the same "it hears you" signal as the panel mic), the state dot, one status.py label in `ink-900` 13 px (elides past 320 px), and the sage "grounded" badge (20 px) when polish used context. Identical structure for hold and toggle dictations; the ticking duration is the toggle tell. Auto-hide comes from status.AUTO_HIDE. Never takes focus, never accepts clicks.

**The mark.** DarkeVox's logo is an original voice-wave: five rounded `cream-50` bars (heights 0.26/0.46/0.62/0.38/0.22 of the mark) centered on a `blue-400` squircle (0.30 radius), drawn with QPainter in `ui/icons.py`. Never an emoji, never a glyph font, never a stock mic. Recording deepens the ground to `blue-500`; the tray adds a clay dot badge so the state reads at 16 px. While recording, the bars scale with the live mic level. The glyphs QSS needs as images (combo chevron, checkmark, spin arrows) are rendered at startup into the config dir — generated artifacts, never checked in.

**Buttons.** All buttons are `AnimatedButton` (`ui/buttons.py`), self-painted so states tween. Primary: `blue-600` fill, `cream-50` semibold, hover `blue-650`, pressed `blue-700`, disabled `blue-200`; one per view. Secondary: `cream-50` fill, hairline border. Chip (segmented tone picker): transparent on the `cream-200` track, checked = `cream-50` pill with hairline. Quiet: borderless 11 px `ink-600`, chrome only. Every button has focus (1 px `blue-500` border; `ink-900` on primary), hover, pressed, and disabled states — no half-defined states.

**Inputs.** Filled style: `cream-200` fill, no visible border, radius 10, `ink-600` placeholder, focus swaps to `cream-50` with a 1 px `blue-500` border. The hero variant (`variant="hero"`, the Polished field) sits raised: `cream-50` fill with hairline at rest. Disabled: `cream-100` fill, `ink-400` text. Invalid: `clay-400` border plus a `clay-600` caption saying what to fix, concretely. Scrollbars are 10 px, transparent track, rounded `ink-400`-tinted handle, no arrows.

**Panel (the floating dictation card).** ONE state: a frameless, always-on-top, draggable card 380 px wide — no minimized pill (removed by owner decision 2026-07-21: keyboard + the big panel, nothing between). It fades in at 90 ms, closes to the tray at 150 ms; Esc, the quiet "hide", and right-click → Hide all mean close-to-tray, and a tray click brings it back. Mouse contract on the mic: click toggles a session, press-and-hold (over 280 ms) is push-to-talk, slipping more than 6 px off cancels; the card drags by its header only (release settles it back on-screen if dropped off the edge). The card, top to bottom on a 4/8-grid (labels 4 from their fields, groups 12 apart, margins 20): drag header (title + quiet settings/hide), mic + a two-line status block (13 px title + 11 px caption) rendered from status.py — live Listening duration, Transcribing…, Polishing with the tone, Ready with the word count, Copied/Inserted confirmations that revert after 2 s, errors in `clay-600` that stay; the demoted HEARD field (72 px, filled) with an undo-take quiet action; the hero POLISHED field (120 px, raised); the segmented tone track (email/message/notes/verbatim, chips radius 6 on the radius-10 track); Copy / quiet Clear (36 px in the action row) / primary Insert. Voice BUILDS on the draft (append with smart joining, `ui/draft.py`); an empty take can never wipe it. Ctrl+Enter inserts, Ctrl+Shift+C copies. Insert hands focus back to the window the user was working in before pasting. On first run the panel shows bottom-right; thereafter visibility and position persist.

**Tray.** Left-click opens/hides the panel; the menu opens with a status row (status.py dot + label), then actions, and always ends with Settings and Quit. Menus are STOCK QMenu styled by QSS only: mutating a QMenu's window flags recreates its popup window and silently kills right-click after first use (field-verified bug). Windows 11 rounds popup corners natively; that is the corner story for menus. The update action tells the truth: "Check for updates" rests, "Update available — install" when one exists.

**Dialogs (settings, first-run).** `role="window"` background, content in `cream-50` cards with radius 16 and 16 padding, overline labels above controls, captions for help. Settings is tabbed (General / Polish / Injection) so it always fits on screen, and shows only the active backend's fields. First-run carries the 48 px mark, an animated `blue-300`-on-`blue-100` progress bar with the megabyte readout as a caption below it, a Retry action on failure, and Cancel; no marketing copy, no fake percentages.

## Microcopy

All user-facing text follows the `no-slop-writing` skill, compressed for UI: sentence case, plain verbs, numbers over adjectives, no exclamation marks, no "please wait", no emoji. Status titles are short and confident ("Listening — 0:12", "Polished — email", "Inserted — 24 words"). Errors say what happened and what to do next: "Ollama isn't running. Start Ollama." An action keeps its name through the flow: Insert produces "Inserted", Copy produces "Copied".
