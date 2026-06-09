# WT RWR / MAW Coverage Viewer

A local, offline **3D viewer for War Thunder aircraft warning-receiver coverage**.
Pick an aircraft and one of its sensors — **RWR** (Radar Warning Receiver), **MAW**
(Missile Approach Warning, `mlws`) or **LWS** (Laser Warning System) — and see the angular
coverage as a spinnable green wireframe sphere around the jet. Two panels side-by-side for
direct comparison.

- **Green** = direction is covered by the receiver suite
- **Empty** = blind angle (no receiver covers it)

![Coverage comparison: Rafale SPECTRA (full sphere) vs MiG-29 SPO-15LM (±30° band)](static/screenshot.jpg)

*Left: the Rafale's SPECTRA RWR covers the full sphere. Right: the MiG-29's SPO-15LM only
covers a 360° × ±30° band — blind above and below, shown as empty space.*

Aircraft are chosen with cascading **Country → Aircraft → Sensor** dropdowns. Drag to spin,
scroll to zoom; toggle auto-spin, synced rotation, radial spokes, and range-scaled radius.

> Inspired by the StatShark sensor viewer. Data is extracted from the War Thunder datamine;
> this project is unofficial and not affiliated with Gaijin Entertainment.

## Quick start

```bash
# 1. (one-time) build static/data.json from a War Thunder datamine clone
python extract.py /path/to/War-Thunder-Datamine
#    or: set WT_DATAMINE=/path/to/datamine  &&  python extract.py

# 2. serve the viewer
python serve.py        # -> http://127.0.0.1:8010/
```

`data.json` is committed, so step 2 works immediately after cloning — you only need step 1
to refresh after a game patch or to regenerate it yourself.

No build step and no runtime dependencies: `extract.py` and `serve.py` use only the Python
standard library (3.8+), and Three.js (r128) is vendored under `static/`.

## How it works

`extract.py` walks the datamine:

```
char.vromfs.bin_u/config/wpcost.blkx      -> which unit ids are aircraft (+ rank, country)
aces.../gamedata/flightmodels/<id>.blkx   -> sensor .blk references (base + weapon-preset pods)
aces.../gamedata/sensors/<name>.blkx      -> type (rwr/mlws/lws), receivers[], frequency bands
```

Each sensor's coverage is the **union of its `receivers.receiver[]` sectors** — every receiver
is an antenna covering `azimuth ± azimuthWidth/2` by `elevation ± elevationWidth/2`. A direction
is "detected" if it falls inside any receiver's window. The viewer
(`static/index.html`) samples a lat/long grid, draws the covered surface in green, and reports
detection range, frequency bands (NATO letters; `bandN` is 0-indexed → `chr('A'+N)`),
launch/track-warning flags, receiver count and the fraction of the sphere covered.

Notes:
- Receivers flagged `indicate: false` are angular-limit / detect-only markers, not bearing
  coverage, so they're excluded from the shape (shown as "+N detect-only").
- A band counts as covered if its `bandN` value is truthy — it may be `true` **or** an array of
  per-receiver sensitivities.
- Coordinates: nose = +Z, up = +Y, starboard = +X; azimuth 0 = nose (+ = right), elevation + = up.

## Files

| path | what |
|---|---|
| `extract.py` | datamine → `static/data.json` |
| `serve.py` | tiny static file server (port 8010, no-cache) |
| `static/index.html` | the viewer (self-contained) |
| `static/three.min.js`, `static/OrbitControls.js` | vendored Three.js r128 (MIT) |
| `static/data.json` | extracted coverage data |

## Getting a datamine clone

Point `extract.py` at any unpacked War Thunder datamine, e.g. the community
[gszabi99/War-Thunder-Datamine](https://github.com/gszabi99/War-Thunder-Datamine) repo, or
files you unpack yourself with [klensy/wt-tools](https://github.com/klensy/wt-tools). It reads
`.blkx` (JSON) files.

## License

MIT — see [LICENSE](LICENSE). Three.js is MIT (Three.js authors). War Thunder data and names
are property of Gaijin Entertainment; this tool is a fan project for analysis only.
