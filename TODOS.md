# Temporary migrations (due to pre-alpha WIP)

Code/spec misalignments found during review. Pre-users → no data
migration owed; this file tracks the _code_ delta needed to bring the
implementation in line with the current spec in `FEATURES.md` — plus
doc-vs-doc drift where two documents disagree about the same feature.

Delete entries once landed. Keep the file and this header even when empty.

_No open misalignments._

---

# Next steps — unblocked work to land before the design pass

Not misalignments. This is a ranked shortlist of what should happen before
WL-5.5 (Lottie + AI art) and the UI Design Concept, because the art pass
either consumes these as input or would have to be redone around them.
Entries leave this section when the WL they point at is picked up.

Ordinary unblocked work with **no** coupling to the art pass — WL-6.1
(export/backup), WL-6.2 (PWA/offline), WL-6.5 (component tests) — is
deliberately not listed. It's worth doing, just not worth front-loading.

## WL-3.3 — decide light/dark before any asset is generated

A decision, not a task, and the cheapest item here with the largest
downstream cost if deferred.

`src/app.css` has `@theme` tokens but no `dark:` variants and no
`prefers-color-scheme` — the app is dark-only in practice, while the art
brief only says "dark-friendly". If light mode is ever wanted, every
generated sprite needs either a second variant or a theme-neutral build
(transparent background, `currentColor` strokes) — a constraint that can
only be imposed *before* generation.

Either implement `dark:` support or consciously drop those sub-items and
commit to dark-only. Both are fine. Deciding after the art exists is not.

## WL-6.4 — Accessibility & legibility, as an input to the art brief

Contrast ratios and minimum tap-target sizes are constraints the art pass
should be given, not a polish pass applied after it. Kid-sized tap targets
in particular set the chamber dot size, which sets pile density, which sets
the scene composition. Auditing afterwards means re-tinting sprites and
re-spacing the chamber floor.

## WL-5.2 — the add-to-chamber arc-in (its one open bullet)

Mechanics, not art: the diff-driven renderer already animates a dot in when
stock rises. Landing the arc now means WL-5.5 swaps a sprite into a working
animation instead of building motion and art at the same time. Also
unblocks WL-5.6.

## WL-6.7 — Ambidextrous / one-handed layout

A CSS-var layout flip is cheaper to establish before animations anchor to
fixed positions. Lowest urgency of the five, but still genuinely
pre-design.
