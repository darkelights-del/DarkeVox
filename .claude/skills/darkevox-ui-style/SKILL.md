---
name: darkevox-ui-style
description: The DarkeVox design system - pastel blue on cream. Color tokens, typography, spacing, radius, motion rules, and component specs for the tray, HUD, dialogs, and the future main window. Read before building or changing any UI in this repo, and keep ui/theme.py in lockstep with the tokens here.
---

# DarkeVox UI Style

The app should feel like good stationery: warm cream surfaces, one soft blue accent, dark warm-gray ink. Calm and quiet, because DarkeVox lives in the corner of the screen and interrupts people mid-thought; nothing may flash, bounce, or shout. "Modern and polished" here means alignment you can feel, few colors used consistently, generous whitespace, and motion so restrained you only notice its absence.

`ui/theme.py` is the single source of truth in code and must mirror the tokens below. If a design decision isn't covered here, add it here first, then implement.

## Color tokens

| Token | Hex | Use |
|---|---|---|
| `cream-50` | `#FFFDF8` | raised surfaces: cards, inputs, menus |
| `cream-100` | `#FAF5EC` | window and dialog background |
| `cream-200` | `#F0E7D8` | hairline borders, hover fills, dividers |
| `blue-100` | `#DEEBF8` | selected/hover tint on cream |
| `blue-200` | `#BCD6EF` | secondary fills, progress track |
| `blue-300` | `#97BEE5` | tray icon body, progress fill, listening pulse |
| `blue-400` | `#6FA1D4` | primary buttons, active states, focus border |
| `blue-500` | `#4C7FB5` | pressed states, links, the only fill that takes light text |
| `ink-900` | `#2A3340` | primary text, icons on light fills |
| `ink-600` | `#5B6675` | secondary text, captions |
| `ink-400` | `#939CAA` | disabled text, placeholder |
| `sage-300` | `#A9C7A0` | success, the "grounded" badge |
| `honey-300` | `#EDCF9A` | polishing state, gentle warnings |
| `clay-400` | `#D9857E` | errors, destructive hover |

Rules that keep it coherent:

- Text on cream is `ink-900` or `ink-600`, never pure black or pure gray.
- Light text (`cream-50`) sits only on `blue-500` or darker. On every pastel fill (`blue-100` through `blue-400`, sage, honey, clay), text is `ink-900`. Target 4.5:1 contrast for all text; pastel-on-cream decorative elements are exempt, text never is.
- One accent per view. If blue-400 marks the primary action, nothing else in that view is blue-400.
- Sage, honey, and clay appear only with their meanings (success/grounded, in-progress/warning, error). Never decoratively.

## Typography

Segoe UI Variable, falling back to Segoe UI (the app is Windows-only; dev boxes fall back to the platform default sans). Sizes: 11 caption, 13 body, 15 emphasis/section titles, 20 window titles. Weight: regular everywhere, semibold only for the current state or the one thing that matters in the view. Never bold whole paragraphs; never use more than two sizes in one component.

## Spacing and shape

Spacing scale: 4 / 8 / 12 / 16 / 24. Controls get 8 vertical padding minimum; dialog margins are 16; unrelated groups separate by 24. Radius: 8 on controls and inputs, 12 on cards and dialogs, full pill on the HUD and badges. Borders are 1px `cream-200`; the focus state swaps the border to `blue-400` (no glow). Exactly one shadow exists in the app, on floating surfaces (HUD, menus): 0 4 16 rgba(42, 51, 64, 0.10).

## Motion

150 ms ease-out on hover and press tints. 250 ms fade for the HUD appearing and leaving. The listening pulse is the one living element: the mic dot breathes opacity 0.55 to 1.0 on a 1.2 s cycle. Nothing else animates. No bounces, no slides, no spinners where a progress bar can be honest instead.

## Components

**HUD.** A frameless, always-on-top pill, bottom-center, 8 px above the taskbar, auto-width with 16 px horizontal padding, 36 px tall. `cream-50` fill, hairline border, the single app shadow. Content: a state dot plus one short label in `ink-900` 13 px. States: listening (blue-300 dot, pulsing), transcribing (blue-400 dot, steady), polishing (honey-300 dot, label "polishing"), grounded (sage-300 mini-badge appended), done (flashes the final word count, fades in 800 ms), error (clay-400 dot, plain-words message, stays 4 s). The HUD never takes focus and never accepts clicks in v1.

**Tray icon.** 16/24/32 px roundrect, `blue-300` fill, `cream-50` mic glyph, drawn with QPainter in `ui/icons.py` (no PNG assets). Recording state swaps the fill to `blue-500`. The menu is a standard QMenu restyled: `cream-50` panel, 8 radius, hover rows `blue-100`, section labels in `ink-600` 11 px.

**Buttons.** Primary: `blue-400` fill, `ink-900` text, hover `blue-300`, pressed `blue-500` with `cream-50` text. Secondary: `cream-50` fill, hairline border, hover `cream-200`. Destructive appears only in confirmation dialogs: secondary shape with `clay-400` text.

**Inputs.** `cream-50` field, hairline border, 8 radius, `ink-400` placeholder, focus border `blue-400`. Invalid: border `clay-400` plus an 11 px `clay-400` caption below saying what to fix, concretely ("Use a combo like ctrl+alt+space", not "Invalid input").

**Panel (the floating dictation card).** A frameless, always-on-top, draggable card 380 px wide, built as a `cream-50` card with the app shadow; it collapses into a 56 px mic pill (same roundrect as the tray icon, drawn at size). Mouse contract on the mic in both states: click toggles a session, press-and-hold (over 280 ms) is push-to-talk, dragging more than 6 px moves the window and cancels the gesture; double-click on the pill expands. The card holds, top to bottom: header (title + a quiet "hide" action), round mic button with a one-line status caption, the editable "Heard" transcript (fills live while recording), the editable "Polished" field, one checkable tone button per tone (checked = `blue-100` fill, `blue-400` border), and Copy / Clear / primary Insert. Insert hands focus back to the window the user was working in before pasting. Quiet buttons (`variant="quiet"`) are borderless 11 px `ink-600` actions for chrome like "hide"; never use them for consequential actions.

**Dialogs (settings, first-run).** `cream-100` background, content in `cream-50` cards with 12 radius and 16 padding, one column, labels above controls. Inputs inside a card sit on `cream-100` so the card still reads as raised. The first-run download dialog shows the model name, a `blue-300`-on-`blue-100` progress bar labeled with the real megabyte count ("217 / 484 MB", an honest approximation), and a cancel button; no marketing copy, no fake percentages.

## Microcopy

All user-facing text follows the `no-slop-writing` skill, compressed for UI: sentence case, plain verbs, numbers over adjectives, no exclamation marks, no "please wait", no emoji. Status labels are one or two words ("listening", "polishing"). Errors say what happened and what the app already did about it: "Polish timed out. Raw transcript injected." A settings caption may be a full sentence when the stakes deserve it: "Audio leaves this machine only when this is on."
