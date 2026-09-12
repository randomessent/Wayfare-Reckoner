/* ---------- the ground, at a tenth of a degree ----------
   Three grids over the same 3600x1800 cells: which are land, what terrain each
   is, and what the country there is called. All three arrive run-length encoded,
   which is how eleven megabytes of raster becomes two of text.

   Every world is built on the same frame, so the frame is fixed once and only
   the grids are swapped when the traveller changes world. */
const FIRST_WORLD = WORLDS[Object.keys(WORLDS)[0]];
const GRES = FIRST_WORLD.grids.res, GW = FIRST_WORLD.grids.w, GH = FIRST_WORLD.grids.h;
const TERRAIN_KEYS = ["plain","farmland","river_plain","river_valley","steppe_plain",
  "steppe_plateau","coastal","coastal_karst","hills","upland","forest_plain","forest_hills",
  "forest_upland","marsh_plain","mountain","high_mountain","savanna","desert","sand_sea",
  "rainforest","taiga","tundra","high_plateau","open_water"];
let NAME_TABLE = null;

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

let LAND = null, TERRAIN_GRID = null, NAME_GRID = null, COMP_GRID = null, COAST = null;
function loadGrids(world){
  const g = world.grids;
  COAST = world.coast;
  if (g.res !== GRES || g.w !== GW || g.h !== GH)
    throw new Error("every world must share the " + GW + "x" + GH + " frame");
  NAME_TABLE   = g.nameTable;
  LAND         = expandAlt(g.land, Uint8Array);
  TERRAIN_GRID = expandPairs(g.terrain[0], g.terrain[1], Uint8Array);
  NAME_GRID    = expandPairs(g.names[0],   g.names[1],   Uint16Array);
  COMP_GRID    = expandPairs(g.comps[0],   g.comps[1],   Uint8Array);
}

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
