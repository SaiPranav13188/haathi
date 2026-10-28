# Animation licenses

Every animation in Haathi is original work made for this project. No third-party Lottie/Rive files are bundled.

| Asset | Where | Made with | License |
|---|---|---|---|
| Gajju (all states) | `components/Gajju.tsx` | Inline SVG + Motion | Project license (same as repo) |
| Ants, owl, peacock, parrot, squirrel, tortoise, butterfly, bees, chameleon, monkey, fireflies, bird, tree | `components/animals/index.tsx` | Inline SVG + Motion | Project license |
| Mic "ear" button | `components/MicButton.tsx` | Inline SVG + Motion | Project license |
| App icon | `public/icons/icon.svg` | Hand-written SVG | Project license |

## Replacing with Rive / Lottie later

`Gajju` exposes the same inputs as the planned Rive state machine (`state`, `voiceLevel`; stage/result come
from `useAnimationEvents`). To switch, drop `gajju.riv` here and render it with `@rive-app/react-canvas`
behind the same props. If you add LottieFiles animations, list each file here with its author, URL and
license (Lottie Simple License or CC), and keep each under 60 KB (haathi.md §9.1).
