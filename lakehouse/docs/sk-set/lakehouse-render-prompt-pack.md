# Render Prompt Pack — RL Lakehouse SK Set (Rev 0.1)

**How to use:** paste `BASE +` one shot prompt per generation. Midjourney: add `--ar 16:9 --style raw` (details and interiors read better at `--ar 4:5` or `--ar 3:2`). Flux / SDXL / GPT-image: drop the flags, the prose carries it.

**BASE (prepend to every prompt):**
> Photorealistic architectural photograph, inland lake in northern Michigan, red pines and hemlock forest, calm water, late-summer evening light, medium-format camera, 24mm tilt-shift, natural color grade, no people, no text, no watermark —

---

## SK-1 · STACKED CHALET

1. **Hero from the water** — classic A-frame cabin with a full-height glass gable facing the lake, steep cedar-clad roof planes, riding on a 3D-printed concrete plinth with visible horizontal print layer lines and one sweeping curved corner, walkout lower level, wide cedar deck with black steel railing, 20-ft shipping-container plunge pool set flush at the deck edge, dark bronze standing-seam trim, warm interior glow through the gable glazing, seen from a dock across still water
2. **Dusk deck + pool** — close view along the lakeside cedar deck at dusk, steaming container plunge pool flush with the decking, black railing, glowing A-frame glass gable rising above, printed-concrete plinth below with corduroy layer lines catching warm light
3. **3DP detail** — macro architectural detail, curved 3D-printed concrete plinth wall wrapping a cabin entry, exposed print layers reading like strata, cedar soffit above, raking evening light
4. **Aerial** — drone three-quarter shot of an A-frame cabin on a wooded slope above a lake, garage doors in the uphill gable end of the concrete base, deck and container pool on the lake side, gravel drive winding through pines
5. **Interior** — A-frame great room looking through full-height gable glazing to a lake, exposed rafters converging overhead, loft catwalk, warm cedar, blackened steel, low sun on the water

## SK-2 · A + BAR

1. **Hero at dusk** — matte-black standing-seam A-frame with warm wood soffits beside a flat-roof two-story bar volume clad in torrefied ash, joined by a low curved white GFRC entry link with subtle printed texture, slim black railing on the bar's rooftop deck, matte-black container plunge pool running perpendicular toward the lake as a third module, dusk sky, lake reflection
2. **Pool axis** — view straight down a cedar deck toward the lake along a container plunge pool, black A-frame wall on the left, wood-clad flat-roof volume with roof terrace on the right, curved white printed link glowing between the two volumes
3. **3DP link detail** — detail shot of a curved GFRC facade panel entry link between a black A-frame and a torrefied-wood box, thin shadow gaps between panels, printed-mold surface texture, crisp joints
4. **Aerial** — drone shot of an A-frame plus flat-roof bar composition in a lakefront clearing, furnished roof deck, container pool as a third parallel bar, long shadows through pines
5. **Roof deck** — golden-hour view from the bar's rooftop terrace past the black A-frame ridge to a northern lake, wood decking, slim railing, drink on a side table

## SK-3 · KICKED RIDGE

1. **Hero side elevation** — asymmetric modern lake cabin, one long zinc-gray standing-seam roof plane descending over a drive-under garage, the opposite lake-end eave sweeping upward in a curved glulam kick over a deep lakeside deck, curved larch and GFRC gable panels following the roofline, blackened-steel base, morning mist on the water
2. **Under the kick** — view from beneath a dramatically upswept curved timber eave sheltering a lake-facing deck, exposed curved glulam rafters overhead, container plunge pool nosing toward the water at the deck corner, low sun flaring under the roof edge
3. **Panel detail** — close-up of curved GFRC facade panels with fine printed texture tracking a sweeping roof edge, larch siding below, knife-edge shadow lines
4. **Aerial** — aerial of an asymmetric long-roof cabin on a lake, roofline curling upward at the water end, deck with a perpendicular container pool, gravel drive disappearing under the roof tail
5. **Interior** — great room beneath an asymmetric curving roof, curved glulam beams overhead, glazed gable to the lake, larch ceiling, concrete floor

---

## Consistency across each scheme's set

- Generate shot 1 first; feed it back as the style/image reference (`--sref` in Midjourney, IP-Adapter or image-prompt elsewhere) for shots 2–5, and lock a seed per scheme.
- Keep the material string identical within a scheme — that's what holds the set together.
- The precedent photos from chat work as additional `--sref` anchors for mood.

## Geometry-faithful route (the better one)

- Feed the **elevation diagrams from the SK deck** into ControlNet (lineart or canny) with Flux or SDXL, denoise ~0.6–0.75 — the render then honors the actual parti geometry instead of hallucinating massing. Your incoming RTX PRO 5000 Blackwell runs this locally in ComfyUI without breaking a sweat; until it lands, PromeAI / LookX do sketch-to-render in the browser.
- Once a parti is massed in Revit, **Veras** renders directly on the model (or Enscape/D5 for real-time) — true geometry, no prompt drift. That's the Rev 0.2 path.
