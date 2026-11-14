# Checkpoint 1: Theme

Settled by Deva on 15 Nov 2026.

## What Deva asked for

Deva supplied a reference, a shift-pattern grid (`reference.png` in this folder), and said "I want this kind of theme".

## The decision

- White page (`#FFFFFF`) with a faint grey canvas for app chrome (`#FAFAFB`) and hairline borders (`#E6E8EC`).
- Soft pastel fills with a slightly deeper pastel border for every categorical block.
- Periwinkle (`#E4E8F7` fill, `#CDD4EE` border) and mint (`#E6F3EB` fill, `#C8E2D1` border) are the two lead tints.
- Further tints (sand, rose, lilac, sky) are derived at the same lightness for tiers and chart series.
- Text is near-black (`#1F2328`) at regular weight inside blocks.
- Labels and column heads are light grey, small, and never bold.
- Corner radius is 6 px on blocks and controls, with 8 px gaps between blocks and generous rows of about 56 px.
- The typeface is Inter, with tabular numerals for times and figures.
- The accent for primary actions and focus is a muted indigo from the periwinkle family.
- No saturated colours appear except the crew-status red and amber, kept as soft fills with dark text.
- Every token is checked to WCAG AA for text with the dataviz validator.

## One change made during the check

The reference label grey `#7A808A` measured 3.98 to 1 on white, which is below the 4.5 to 1 needed for small text.
It was stepped down to `#656B75`, which measures 5.37 to 1 on white and 4.88 to 1 on the hover wash.
The look stays light grey; the difference is barely visible.

## Final tokens

The full set lives in `frontend/src/theme/tokens.css`.

| Role | Value |
|---|---|
| Page | `#FFFFFF` |
| Canvas | `#FAFAFB` |
| Hover wash | `#F3F4F7` |
| Hairline border | `#E6E8EC` |
| Control border | `#D3D7DE` |
| Text | `#1F2328` |
| Secondary text | `#4B515B` |
| Labels and column heads | `#656B75` |
| Accent | `#4F5DB0` |
| Accent hover | `#45529F` |
| Accent soft fill | `#E4E8F7` |
| Destructive action | `#B4382C` |
| Spacing scale | 8 px steps (4 px half step for tight inline gaps) |
| Control height | 36 px on desktop, 44 px on phones (640 px wide and below) |
| Grid and table rows | 56 px |
| Radius | 6 px on blocks and controls, 10 px on dialogs |
| Type | Inter 400, 500 and 600; 12, 13, 14, 16, 20, 24 and 32 px |

Tints, each with a fill, a border and a dark ink for text and icons on that fill:

| Tint | Fill | Border | Ink |
|---|---|---|---|
| Periwinkle | `#E4E8F7` | `#CDD4EE` | `#333F8C` |
| Mint | `#E6F3EB` | `#C8E2D1` | `#22633F` |
| Sand | `#F7EFDD` | `#E9D9B4` | `#6F4708` |
| Rose | `#F9E6E5` | `#EDCDCB` | `#8A2A20` |
| Lilac | `#EEE7F6` | `#DACCEB` | `#5A3E8A` |
| Sky | `#E3F0F7` | `#C4DEEC` | `#1E5878` |
| Neutral | `#F1F2F4` | `#DFE2E7` | `#4B515B` |

Readiness tiers always pair the colour with an icon and a plain label, so colour never carries the meaning alone.

| Tier | Label | Colour |
|---|---|---|
| fit | Fit | Mint (good) |
| fit_with_controls | Fit with controls | Amber (warning) |
| reassign | Reassign today | Red (critical) |
| refer | Refer | Lilac |
| unknown | Unknown | Neutral grey |

## Contrast check

Measured with the dataviz skill's validator (`contrast()` from `validate_palette.js`, WCAG 2 ratio).
Text needs 4.5 to 1.
Non-text marks such as the focus ring and status dots need 3 to 1.

| Text or mark | Hex | Background | Hex | Ratio | Needed | Result |
|---|---|---|---|---|---|---|
| Body text | `#1F2328` | Page | `#FFFFFF` | 15.80:1 | 4.5:1 | Pass |
| Body text | `#1F2328` | Canvas | `#FAFAFB` | 15.14:1 | 4.5:1 | Pass |
| Body text | `#1F2328` | Hover wash | `#F3F4F7` | 14.36:1 | 4.5:1 | Pass |
| Secondary text | `#4B515B` | Page | `#FFFFFF` | 7.99:1 | 4.5:1 | Pass |
| Secondary text | `#4B515B` | Canvas | `#FAFAFB` | 7.66:1 | 4.5:1 | Pass |
| Label grey | `#656B75` | Page | `#FFFFFF` | 5.37:1 | 4.5:1 | Pass |
| Label grey | `#656B75` | Canvas and table header | `#FAFAFB` | 5.14:1 | 4.5:1 | Pass |
| Label grey | `#656B75` | Hover wash | `#F3F4F7` | 4.88:1 | 4.5:1 | Pass |
| Reference label grey (replaced) | `#7A808A` | Page | `#FFFFFF` | 3.98:1 | 4.5:1 | Fail, replaced |
| Disabled text | `#9AA0A9` | Page | `#FFFFFF` | 2.63:1 | Exempt | Exempt |
| Button label | `#FFFFFF` | Accent | `#4F5DB0` | 5.96:1 | 4.5:1 | Pass |
| Button label | `#FFFFFF` | Accent hover | `#45529F` | 7.09:1 | 4.5:1 | Pass |
| Button label | `#FFFFFF` | Destructive | `#B4382C` | 5.93:1 | 4.5:1 | Pass |
| Accent link | `#4F5DB0` | Page | `#FFFFFF` | 5.96:1 | 4.5:1 | Pass |
| Accent ink | `#333F8C` | Accent soft | `#E4E8F7` | 7.70:1 | 4.5:1 | Pass |
| Body text | `#1F2328` | Periwinkle | `#E4E8F7` | 12.93:1 | 4.5:1 | Pass |
| Body text | `#1F2328` | Mint | `#E6F3EB` | 13.83:1 | 4.5:1 | Pass |
| Body text | `#1F2328` | Sand | `#F7EFDD` | 13.80:1 | 4.5:1 | Pass |
| Body text | `#1F2328` | Rose | `#F9E6E5` | 13.15:1 | 4.5:1 | Pass |
| Body text | `#1F2328` | Lilac | `#EEE7F6` | 13.09:1 | 4.5:1 | Pass |
| Body text | `#1F2328` | Sky | `#E3F0F7` | 13.60:1 | 4.5:1 | Pass |
| Periwinkle ink | `#333F8C` | Periwinkle | `#E4E8F7` | 7.70:1 | 4.5:1 | Pass |
| Mint ink | `#22633F` | Mint | `#E6F3EB` | 6.29:1 | 4.5:1 | Pass |
| Sand ink | `#6F4708` | Sand | `#F7EFDD` | 7.11:1 | 4.5:1 | Pass |
| Rose ink | `#8A2A20` | Rose | `#F9E6E5` | 7.18:1 | 4.5:1 | Pass |
| Lilac ink | `#5A3E8A` | Lilac | `#EEE7F6` | 6.98:1 | 4.5:1 | Pass |
| Sky ink | `#1E5878` | Sky | `#E3F0F7` | 6.64:1 | 4.5:1 | Pass |
| Neutral ink | `#4B515B` | Neutral | `#F1F2F4` | 7.14:1 | 4.5:1 | Pass |
| Good ink | `#22633F` | Good fill | `#E6F3EB` | 6.29:1 | 4.5:1 | Pass |
| Warning ink | `#6F4708` | Warning fill | `#FCF0D8` | 7.21:1 | 4.5:1 | Pass |
| Critical ink | `#8A2A20` | Critical fill | `#FBE4E2` | 7.11:1 | 4.5:1 | Pass |
| Destructive text | `#B4382C` | Page | `#FFFFFF` | 5.93:1 | 4.5:1 | Pass |
| Focus ring | `#4F5DB0` | Page | `#FFFFFF` | 5.96:1 | 3:1 | Pass |
| Good dot | `#2F9A68` | Page | `#FFFFFF` | 3.53:1 | 3:1 | Pass |
| Warning dot | `#B57B12` | Page | `#FFFFFF` | 3.62:1 | 3:1 | Pass |
| Critical dot | `#C8473B` | Page | `#FFFFFF` | 4.75:1 | 3:1 | Pass |
| Neutral dot | `#8A909A` | Page | `#FFFFFF` | 3.21:1 | 3:1 | Pass |

Usage rule from the check: the label grey measures 4.39 to 1 on the periwinkle fill, so text inside coloured blocks is always near-black or the block's own ink, never the label grey.
This matches the reference, where block text is near-black.

## Chart colours

Chart series are the deeper steps of the same tint families, in a fixed order that is never cycled.

| Slot | Family | Hex |
|---|---|---|
| 1 | Periwinkle | `#5B6BC0` |
| 2 | Mint | `#2F9A68` |
| 3 | Lilac | `#9A5FC0` |
| 4 | Sand | `#C27A1E` |
| 5 | Sky | `#2F8FBF` |
| 6 | Rose | `#C9506A` |

All 120 orderings with periwinkle first were run through the validator; 9 passed every check, and this one was chosen because it opens with the two lead tints.
Validator result on white: lightness band pass, chroma floor pass, colour-blind separation pass (worst adjacent pair 14.0, target 8), normal-vision separation pass (worst adjacent pair 22.3, floor 15), contrast pass (all six at least 3 to 1).

The shaded grid uses one periwinkle ramp from light to dark: `#EEF0FA`, `#CDD4EE`, `#A3AEE0`, `#8190D3`, `#5D6DC1`, `#333F8C`.
The validator confirms it reads light to dark in even steps with a single hue.
The lightest step is close to white by design, as allowed for continuous shading, and carries a periwinkle border so the block edge stays visible.
Numbers inside the four lighter steps are near-black (at least 5.16 to 1); inside the two darker steps they are white (at least 4.75 to 1).

## Single light theme

The product uses one light theme by choice, as settled here.
There is no dark mode.
