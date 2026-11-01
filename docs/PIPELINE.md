# Pipeline

## 1. Geometry (Fusion API, direct modelling)
- `TemporaryBRepManager` primitives (boxes, cylinders, tori, spheres) + booleans build every part; bodies are added to named components so they can be transformed later.
- Cables are Catmull-Rom splines swept as chains of cylinders and spheres.
- The station enclosure comes from a single print-plate STL: triangles are grouped into parts by **union-find over shared vertices**, colour attributes are stripped, and each part is imported as a mesh body and placed with a rigid transform (the cover is flipped 180° about X because it was printed upside down). Fusion's face-group colouring is suppressed via `MeshBody.displayOverrides`.

## 2. Animation (per-frame state)
`state(f)` / `scene(f)` are pure functions of the frame number returning occurrence transforms, custom-graphics polylines/meshes and the camera:
- **Tensile test:** measured time is mapped onto frames (slow motion); displacement s(t) and force F(t) are linearly interpolated from the measurement; pulley angle `φ = −s/r`; after the break both fibre ends follow damped analytic motions.
- **Laser:** ultrasonic wavefronts expand at a speed chosen so a round trip takes 2 s; the reflected wave is drawn from the mirror source behind the wall. The diffraction pattern is a set of quads binned into 14 intensity levels (one custom-graphics mesh per level) to keep draw calls low.
- Dynamic objects (fibre, beams, pulses, fringes) are `CustomGraphics` → no timeline/undo growth.

## 3. Rendering
`Viewport.saveAsImageFileWithOptions` with transparent background, 1920×1080, anti-aliased. Long loops are split into batches (~150 frames) because script calls are time-limited; static shots render one frame that is reused.

## 4. Compositing
Pillow draws the background gradient, title cards, numbered captions, callout labels with leader lines, the live force-time chart (replaying the measurement up to the current time) and result panels. `run_missing.py` runs time-boxed, resumable parallel workers.

## 5. Encoding
`ffmpeg -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart`.
