/* ---------- the ground, at a tenth of a degree ----------
   Three grids over the same 3600x1800 cells: which are land, what terrain each
   is, and what the country there is called. All three arrive run-length encoded,
   which is how eleven megabytes of raster becomes two of text. */
const GRES = GRIDS.res, GW = GRIDS.w, GH = GRIDS.h;
const TERRAIN_KEYS = ["plain","farmland","river_plain","river_valley","steppe_plain",
  "steppe_plateau","coastal","coastal_karst","hills","upland","forest_plain","forest_hills",
  "forest_upland","marsh_plain","mountain","high_mountain","savanna","desert","sand_sea",
  "rainforest","taiga","tundra","high_plateau","open_water"];
const NAME_TABLE = GRIDS.nameTable;

function expandAlt(lens, Arr){
  /* runs that alternate 0,1,0,1 — the land mask */
  const out = new Arr(GW*GH);
  let at = 0, v = 0;
  for (let k = 0; k < lens.length; k++){
    const n = lens[k];
    if (v) out.fill(1, at, at+n);
    at += n; v ^= 1;
  }
  return out;
}
function expandPairs(vals, lens, Arr){
  const out = new Arr(GW*GH);
  let at = 0;
  for (let k = 0; k < lens.length; k++){
    const n = lens[k], v = vals[k];
    if (v) out.fill(v, at, at+n);
    at += n;
  }
  return out;
}

const LAND    = expandAlt(GRIDS.land, Uint8Array);
const TERRAIN_GRID = expandPairs(GRIDS.terrain[0], GRIDS.terrain[1], Uint8Array);
const NAME_GRID    = expandPairs(GRIDS.names[0],   GRIDS.names[1],   Uint16Array);
const COMP_GRID    = expandPairs(GRIDS.comps[0],   GRIDS.comps[1],   Uint8Array);

function cellIndex(lat, lon){
  const j = Math.min(GH-1, Math.max(0, Math.floor((90 - lat)/GRES)));
  const i = ((Math.floor((lon + 180)/GRES) % GW) + GW) % GW;
  return j*GW + i;
}
function isLand(lat, lon){ return LAND[cellIndex(lat,lon)] === 1; }

/* Which walkable landmass a point is on. 0 is water, 255 a speck too small to
   have earned a number. Two different numbers cannot be walked between. */
function landmass(lat, lon){ return COMP_GRID[cellIndex(lat,lon)]; }

function zoneAt(lat, lon){
  const k = cellIndex(lat, lon);
  const terr = TERRAIN_KEYS[TERRAIN_GRID[k]];
  if (terr === "open_water") return ["Open Water", "open_water"];
  const nm = NAME_GRID[k];
  return [nm ? NAME_TABLE[nm] : "Open Country", terr];
}
