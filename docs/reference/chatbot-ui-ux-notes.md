# Chatbot UI/UX reference notes

Distilled from [dontriskit/awesome-ai-system-prompts](https://github.com/dontriskit/awesome-ai-system-prompts)
(fetched 2026-07-18). Most useful source: **v0 by Vercel's Design Guidelines**
(full excerpt in [v0-design-guidelines.md](v0-design-guidelines.md)); secondary:
Loveable's design-first workflow. The ChatGPT/Claude/Perplexity prompts are
mostly tool plumbing — little UI guidance.

## Principles worth adopting (v0)

**Color** — exactly 3–5 colors total: 1 primary + 2–3 neutrals + max 2 accents.
WCAG AA contrast (4.5:1 body, 3:1 large). No gradients by default.

**Typography** — max 2 font families; body ≥ 14px; line-height 1.4–1.6;
hierarchy via clear size jumps (sm → base → lg → xl → 2xl).

**Layout** — mobile-first (320px) → tablet → desktop, never the reverse.
≥16px between sections, related elements within 8px, one alignment per
section, consistent max-widths. Flexbox first, grid only for true 2D; prefer
`gap-*` over `space-*`; no arbitrary values / `!important`.

**Icons** — never emojis as icons (inconsistent, unprofessional); one icon
library, consistent 16/20/24px sizing, contrast for icon-only buttons.

**Creative framework** — enterprise/professional products: BE CONSERVATIVE,
established patterns, creativity through craft not bold choices. ("Ship
something interesting rather than boring, but never ugly.")

**Process (Loveable)** — before building: name what the design evokes and
which existing beautiful products inspire it; adjust design tokens first,
then components; first impression is the priority.

## Audit: BürgerChat vs. these guidelines

| Guideline | Status |
|---|---|
| ≤5 colors (1 primary + neutrals + ≤2 accents) | ✅ blue-600 + zinc + amber/red accents |
| ≤2 font families | ✅ Geist Sans + Geist Mono |
| Body ≥14px, line-height 1.4–1.6 | ✅ 15px body, leading-relaxed |
| No gradients | ✅ |
| Mobile-first, input pinned (dvh) | ✅ since the mobile-testing fixes |
| Flexbox/gap, no arbitrary positioning | ✅ mostly (`text-[11px]`/`[13px]` arbitrary sizes used for meta labels) |
| One alignment per section | ✅ |
| Conservative pattern for a trust product | ✅ matches our government-service positioning |
| **No emojis as icons** | ✅ swapped for Heroicons in tinted chips (2026-07-18) |
| Icon library w/ consistent sizing | ⚠️ hand-rolled inline SVGs (sizes are consistent: 4/4.5/5/6) |
| Meta labels below 14px | ⚠️ source domains 11px, notice 13px — deliberate for de-emphasis |

## Open decisions (deliberate deviations, revisit if desired)

1. ~~Emoji on starter cards~~ — resolved: Heroicons outlines (banknotes /
   user-group / building-library) in soft blue chips keep the icons
   language-neutral while satisfying the no-emoji rule.
2. **Sub-14px meta text**: source-card domain labels (11px) and the rename
   notice (13px) are intentionally de-emphasized; body text everywhere else
   is 15px. Acceptable; bump to 12/14 if readability complaints appear.
3. **Inline SVGs vs icon library**: fine at current scale (~6 icons); adopt
   a library if the icon count grows.
