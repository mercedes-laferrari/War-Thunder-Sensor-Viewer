#!/usr/bin/env python3
"""
Extract RWR / MLWS(MAW) / LWS sensor coverage for every aircraft in War Thunder.

Output: static/data.json  consumed by the 3D viewer (index.html).

Chain (see memory wt-rwr-maw-lws-extraction):
  wpcost.blkx            -> which unit ids are aircraft (+rank, country)
  flightmodels/<id>.blkx -> references gameData/sensors/<name>.blk (base + pod presets)
  sensors/<name>.blkx    -> type(rwr/mlws/lws) + receivers[] geometry + bands
"""
import json, os, re, csv, sys

# Path to a War Thunder datamine clone (e.g. gszabi99/War-Thunder-Datamine or
# klensy/wt-tools output). Override with `python extract.py <path>` or the
# WT_DATAMINE env var.
DEFAULT_ROOT = r"C:\Users\peter\WT-Datamine-git"
ROOT = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("WT_DATAMINE", DEFAULT_ROOT))
WPCOST   = os.path.join(ROOT, "char.vromfs.bin_u", "config", "wpcost.blkx")
UNITS    = os.path.join(ROOT, "lang.vromfs.bin_u", "lang", "units.csv")
FM_DIR   = os.path.join(ROOT, "aces.vromfs.bin_u", "gamedata", "flightmodels")
SENS_DIR = os.path.join(ROOT, "aces.vromfs.bin_u", "gamedata", "sensors")
OUT      = os.path.join(os.path.dirname(__file__), "static", "data.json")

WANT_TYPES = {"rwr", "mlws", "lws"}

def band_letters(sensor):
    """0-indexed bandN keys -> NATO letters; band is covered if value is truthy
    (may be True OR an array of per-receiver sensitivities)."""
    letters = []
    for k, v in sensor.items():
        m = re.fullmatch(r"band(\d+)", k)
        if not m:
            continue
        if v in (False, None, 0, "", [], {}):
            continue
        n = int(m.group(1))
        letters.append((n, chr(ord('A') + n) if n <= 12 else f"#{n}"))
    letters.sort()
    return [l for _, l in letters]

def receivers_of(sensor):
    recs = []
    r = sensor.get("receivers", {}).get("receiver")
    if r is None:
        # fall back to global rxAngle (az,el half? -> treat as full sector around nose)
        rx = sensor.get("rxAngle")
        if isinstance(rx, list) and len(rx) == 2:
            recs.append({"az": 0.0, "el": 0.0, "azW": rx[0] * 2, "elW": rx[1] * 2, "af": True})
        return recs
    if isinstance(r, dict):
        r = [r]
    for e in r:
        recs.append({
            "az": float(e.get("azimuth", 0.0)),
            "el": float(e.get("elevation", 0.0)),
            "azW": float(e.get("azimuthWidth", 360.0)),
            "elW": float(e.get("elevationWidth", 180.0)),
            "af": bool(e.get("angleFinder", False)),
            # indicate:false = detect-only / limit marker, NOT directional coverage
            "ind": e.get("indicate", True) is not False,
        })
    return recs

# ---- load sensor files lazily, cache ----
_sens_cache = {}
def load_sensor(name):
    if name in _sens_cache:
        return _sens_cache[name]
    p = os.path.join(SENS_DIR, name + ".blkx")
    s = None
    if os.path.exists(p):
        try:
            s = json.load(open(p, encoding="utf-8"))
        except Exception:
            s = None
    _sens_cache[name] = s
    return s

SENS_REF = re.compile(r"gamedata/sensors/([\w\-]+)\.blk", re.I)

def walk_sensor_refs(node, in_preset, out):
    """Recursively collect (sensor_name, is_external) from a flightmodel JSON tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            preset = in_preset or ("preset" in k.lower() or "weaponslot" in k.lower())
            if isinstance(v, str):
                m = SENS_REF.search(v)
                if m:
                    out.setdefault(m.group(1).lower(), preset)
                    # prefer internal (False) if seen both
                    if not preset:
                        out[m.group(1).lower()] = False
            else:
                walk_sensor_refs(v, preset, out)
    elif isinstance(node, list):
        for v in node:
            walk_sensor_refs(v, in_preset, out)

def clean_name(s):
    return re.sub(r"[␗‐-‧]", "", s).strip()

def main():
    if not os.path.isfile(WPCOST):
        sys.exit(
            f"Datamine not found at: {ROOT}\n"
            f"  expected: {WPCOST}\n"
            "Point it at a War Thunder datamine clone:\n"
            "  python extract.py <path-to-datamine>\n"
            "  (or set the WT_DATAMINE environment variable)"
        )
    wp = json.load(open(WPCOST, encoding="utf-8"))

    # localized english names: <id>_shop -> name
    names = {}
    with open(UNITS, encoding="utf-8") as f:
        rd = csv.reader(f, delimiter=';', quotechar='"')
        for row in rd:
            if not row:
                continue
            key = row[0]
            if key.endswith("_shop") and len(row) > 1:
                names[key[:-5]] = clean_name(row[1])

    sensors_out = {}   # name -> sensor descriptor
    planes = []

    for uid, u in wp.items():
        if not isinstance(u, dict):
            continue
        mv = u.get("unitMoveType")
        if mv not in ("air", "helicopter"):
            continue
        fm = os.path.join(FM_DIR, uid + ".blkx")
        if not os.path.exists(fm):
            continue
        try:
            data = json.load(open(fm, encoding="utf-8"))
        except Exception:
            continue

        refs = {}
        walk_sensor_refs(data, False, refs)

        plane_sensors = []
        for sname, is_ext in refs.items():
            s = load_sensor(sname)
            if not s:
                continue
            stype = s.get("type")
            types = stype if isinstance(stype, list) else [stype]
            keep = [t for t in types if t in WANT_TYPES]
            if not keep:
                continue
            if sname not in sensors_out:
                sensors_out[sname] = {
                    "file": sname,
                    "name": s.get("name", sname),
                    "types": keep,
                    "range": s.get("range"),
                    "emission": s.get("emission"),
                    "bands": band_letters(s),
                    "detectLaunch": bool(s.get("detectLaunch")) or any(
                        (isinstance(g, dict) and (g.get("detectLaunch") or g.get("launch")))
                        for g in (s.get("groups", {}).get("group", []) or [])
                        if isinstance(s.get("groups", {}).get("group", []), list)
                    ),
                    "detectTracking": bool(s.get("detectTracking")),
                    "matchSector": s.get("matchSector"),
                    "angularRateMax": s.get("angularRateMax"),
                    "receivers": receivers_of(s),
                }
            for t in keep:
                plane_sensors.append({"file": sname, "type": t, "external": bool(is_ext)})

        if not plane_sensors:
            continue

        nm = names.get(uid) or uid
        planes.append({
            "id": uid,
            "name": nm,
            "country": (u.get("country") or "").replace("country_", ""),
            "rank": u.get("rank"),
            "cls": u.get("unitClass", ""),
            "moveType": mv,
            "sensors": plane_sensors,
        })

    planes.sort(key=lambda p: (p["name"].lower()))
    out = {"planes": planes, "sensors": sensors_out}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"planes with sensors: {len(planes)}")
    print(f"distinct sensors:    {len(sensors_out)}")
    # quick breakdown
    from collections import Counter
    c = Counter()
    for s in sensors_out.values():
        for t in s["types"]:
            c[t] += 1
    print("sensor type counts:", dict(c))

if __name__ == "__main__":
    main()
