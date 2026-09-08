/* ---------- finding a way across land ----------
   A* over the land mask, at a tenth of a degree. Step cost is kilometres over
   how fast the ground there lets you go, so the search prefers easy country as
   well as short country, and takes to the water only as far as the party's
   boats allow.

   Eleven kilometres is a fine mesh: a crossing of Eurasia is millions of cells.
   So before the real search runs, a half-degree grid is flooded outward from
   the goal to give every neighbourhood a lower bound on what remains. That
   field, forgiving of every strait, is what an A* heuristic wants — it can only
   under-estimate — and with it the fine search walks nearly straight instead of
   fanning out across a continent. */

const R_EARTH = 6371.0;
const MW = GW, MH = GH, MRES = GRES;
const BEST_FACTOR = 1.05;          /* the fastest ground there is */
const CF = 5;                       /* coarse cells are five fine cells across */
const CW = MW/CF, CH = MH/CF;

const BOATS = {
  none:    {label:"none — they keep their feet dry", water:null, reach:0,
            note:"No crossing of open water at all. If there is no way round, there is no way."},
  ferries: {label:"ferry crossings", water:0.16, reach:8, sea_pace:4.0, embark:6.0,
            note:"Boatmen at the narrow places. Straits and river mouths are crossable; an open sea is not worth the asking."},
  ship:    {label:"a ship", water:0.75, reach:null, sea_pace:6.5, embark:12.0,
            note:"A vessel that will take them along a coast or across a sea, sailing through the night."}
};

const cellOf = (lat,lon) => [ ((Math.floor((lon+180)/MRES) % MW) + MW) % MW,
                              Math.min(MH-1, Math.max(0, Math.floor((90-lat)/MRES))) ];
const cellCentre = (i,j) => [90 - (j+0.5)*MRES, -180 + ((((i % MW)+MW)%MW) + 0.5)*MRES];
const isLandCell = (i,j) => LAND[j*MW + (((i % MW) + MW) % MW)] === 1;

function havKm(aLat, aLon, bLat, bLon){
  const p1 = aLat*Math.PI/180, p2 = bLat*Math.PI/180;
  const dp = (bLat-aLat)*Math.PI/360, dl = (bLon-aLon)*Math.PI/360;
  const h = Math.sin(dp)**2 + Math.cos(p1)*Math.cos(p2)*Math.sin(dl)**2;
  return 2*R_EARTH*Math.asin(Math.sqrt(Math.min(1, h)));
}

/* a binary heap keyed on cost, holding integer cell keys */
function Heap(){ this.p = [0]; this.v = [0]; this.n = 0; }
Heap.prototype.push = function(pri, val){
  let i = ++this.n; this.p[i] = pri; this.v[i] = val;
  while (i > 1){
    const par = i >> 1;
    if (this.p[par] <= this.p[i]) break;
    const tp = this.p[par], tv = this.v[par];
    this.p[par] = this.p[i]; this.v[par] = this.v[i];
    this.p[i] = tp; this.v[i] = tv; i = par;
  }
};
Heap.prototype.pop = function(){
  const top = this.v[1], pri = this.p[1];
  this.p[1] = this.p[this.n]; this.v[1] = this.v[this.n]; this.n--;
  let i = 1;
  for (;;){
    const l = i << 1, r = l + 1; let s = i;
    if (l <= this.n && this.p[l] < this.p[s]) s = l;
    if (r <= this.n && this.p[r] < this.p[s]) s = r;
    if (s === i) break;
    const tp = this.p[s], tv = this.v[s];
    this.p[s] = this.p[i]; this.v[s] = this.v[i];
    this.p[i] = tp; this.v[i] = tv; i = s;
  }
  return [pri, top];
};

/* ---- the coarse grid: land if any fine cell in it is land ---- */
let COARSE = null;
function coarseMask(){
  if (COARSE) return COARSE;
  const out = new Uint8Array(CW*CH);
  for (let j = 0; j < MH; j++){
    const row = j*MW, cj = ((j/CF)|0)*CW;
    for (let i = 0; i < MW; i++) if (LAND[row+i]) out[cj + ((i/CF)|0)] = 1;
  }
  return (COARSE = out);
}

const CLAT = 180/CH, CLON = 360/CW;
/* trig per row, computed once: the inner loops run millions of times and cannot
   afford to convert degrees to radians for every neighbour */
const ROW_LAT = new Float64Array(MH), ROW_SIN = new Float64Array(MH), ROW_COS = new Float64Array(MH);
for (let j = 0; j < MH; j++){
  const la = 90 - (j+0.5)*MRES;
  ROW_LAT[j] = la; ROW_SIN[j] = Math.sin(la*Math.PI/180); ROW_COS[j] = Math.cos(la*Math.PI/180);
}
/* the eight step lengths out of a cell depend only on its row */
const STEP_NS = havKm(0, 0, MRES, 0);
const STEP_EW = new Float64Array(MH), STEP_DU = new Float64Array(MH), STEP_DD = new Float64Array(MH);
for (let j = 0; j < MH; j++){
  STEP_EW[j] = havKm(ROW_LAT[j], 0, ROW_LAT[j], MRES);
  STEP_DU[j] = j > 0      ? havKm(ROW_LAT[j], 0, ROW_LAT[j-1], MRES) : STEP_NS;
  STEP_DD[j] = j < MH-1   ? havKm(ROW_LAT[j], 0, ROW_LAT[j+1], MRES) : STEP_NS;
}
const stepKm = (j, di, dj) => di === 0 ? STEP_NS : (dj === 0 ? STEP_EW[j] : (dj < 0 ? STEP_DU[j] : STEP_DD[j]));

const CROW_LAT = new Float64Array(CH), CROW_SIN = new Float64Array(CH), CROW_COS = new Float64Array(CH);
for (let j = 0; j < CH; j++){
  const la = 90 - (j+0.5)*CLAT;
  CROW_LAT[j] = la; CROW_SIN[j] = Math.sin(la*Math.PI/180); CROW_COS[j] = Math.cos(la*Math.PI/180);
}
const CSTEP_NS = havKm(0, 0, CLAT, 0);
const CSTEP_EW = new Float64Array(CH), CSTEP_DU = new Float64Array(CH), CSTEP_DD = new Float64Array(CH);
for (let j = 0; j < CH; j++){
  CSTEP_EW[j] = havKm(CROW_LAT[j], 0, CROW_LAT[j], CLON);
  CSTEP_DU[j] = j > 0    ? havKm(CROW_LAT[j], 0, CROW_LAT[j-1], CLON) : CSTEP_NS;
  CSTEP_DD[j] = j < CH-1 ? havKm(CROW_LAT[j], 0, CROW_LAT[j+1], CLON) : CSTEP_NS;
}
const cStepKm = (j, di, dj) => di === 0 ? CSTEP_NS : (dj === 0 ? CSTEP_EW[j] : (dj < 0 ? CSTEP_DU[j] : CSTEP_DD[j]));

/* distance from a grid row to a fixed point, without rebuilding the point */
function rowDist(sinA, cosA, lonA, sinB, cosB, latB, lonB){
  const dl = (lonB - lonA)*Math.PI/360;
  const dp = Math.asin(Math.max(-1, Math.min(1, sinB))) - Math.asin(Math.max(-1, Math.min(1, sinA)));
  const h = Math.sin(dp/2)**2 + cosA*cosB*Math.sin(dl)**2;
  return 2*R_EARTH*Math.asin(Math.sqrt(Math.min(1, h)));
}
const cCentre = (i,j) => [90 - (j+0.5)*CLAT, -180 + (i+0.5)*CLON];
const cLand = (i,j) => coarseMask()[j*CW + (((i % CW)+CW)%CW)] === 1;

function coarseNearShore(i, j, reach){
  const cm = coarseMask();
  for (let r = 1; r <= reach; r++)
    for (let dj = -r; dj <= r; dj++){
      const nj = j + dj;
      if (nj < 0 || nj >= CH) continue;
      const step = Math.abs(dj) === r ? 1 : 2*r;
      for (let di = -r; di <= r; di += step)
        if (cm[nj*CW + (((i+di) % CW)+CW)%CW]) return true;
    }
  return false;
}

/* Is there land within `reach` cells of this water cell? A ferryman will put
   you across a strait and will not take you to Greenland, so his water is only
   the water you can see the far side of; a ship's is all of it. */
const SHORE = new Map();
function nearShore(i, j, reach){
  const key = (j*MW + i)*16 + reach;
  const hit = SHORE.get(key);
  if (hit !== undefined) return hit;
  let found = false;
  for (let r = 1; r <= reach && !found; r++)
    for (let dj = -r; dj <= r && !found; dj++){
      const nj = j + dj;
      if (nj < 0 || nj >= MH) continue;
      const step = Math.abs(dj) === r ? 1 : 2*r;
      for (let di = -r; di <= r; di += step)
        if (LAND[nj*MW + (((i+di) % MW)+MW)%MW]){ found = true; break; }
    }
  if (SHORE.size > 400000) SHORE.clear();
  SHORE.set(key, found);
  return found;
}

/* ---- the lower-bound field ---- */
const FIELD_CACHE = new Map();
function coarseField(a, b, water, reach){
  const ckey = [Math.round(a[0]), Math.round(a[1]), b[0].toFixed(2), b[1].toFixed(2),
                water, reach].join("|");
  const had = FIELD_CACHE.get(ckey);
  if (had) return had;

  const cell = (lat,lon) => [((Math.floor((lon+180)/CLON) % CW)+CW)%CW,
                             Math.min(CH-1, Math.max(0, Math.floor((90-lat)/CLAT)))];
  function snapC(c){
    if (water !== null || cLand(c[0], c[1])) return c;
    for (let r = 1; r <= 8; r++)
      for (let di = -r; di <= r; di++)
        for (let dj = -r; dj <= r; dj++){
          if (Math.max(Math.abs(di), Math.abs(dj)) !== r) continue;
          const ni = (((c[0]+di) % CW)+CW)%CW, nj = c[1]+dj;
          if (nj >= 0 && nj < CH && cLand(ni,nj)) return [ni,nj];
        }
    return c;
  }
  const g = snapC(cell(b[0], b[1]));
  const budget = 1.5*havKm(a[0],a[1],b[0],b[1]) + 600;

  /* the ellipse is asked about far more often than there are cells, so remember
     the answer: 0 not yet asked, 1 inside, 2 outside */
  const ell = new Uint8Array(CW*CH);
  const aSin = Math.sin(a[0]*Math.PI/180), aCos = Math.cos(a[0]*Math.PI/180);
  const bSin = Math.sin(b[0]*Math.PI/180), bCos = Math.cos(b[0]*Math.PI/180);
  function inEllipse(i, j, k){
    let v = ell[k];
    if (v) return v === 1;
    const lon = -180 + (i+0.5)*CLON;
    const d = rowDist(CROW_SIN[j], CROW_COS[j], lon, aSin, aCos, a[0], a[1])
            + rowDist(CROW_SIN[j], CROW_COS[j], lon, bSin, bCos, b[0], b[1]);
    v = d <= budget ? 1 : 2;
    ell[k] = v;
    return v === 1;
  }

  const dist = new Float64Array(CW*CH).fill(Infinity);
  const done = new Uint8Array(CW*CH);
  const heap = new Heap();
  const gk = g[1]*CW + g[0];
  dist[gk] = 0; heap.push(0, gk);
  while (heap.n){
    const [d, cur] = heap.pop();
    if (done[cur]) continue;
    done[cur] = 1;
    const ci = cur % CW, cj = (cur/CW)|0;
    for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++){
      if (!di && !dj) continue;
      const nj = cj + dj;
      if (nj < 0 || nj >= CH) continue;
      const ni = (((ci+di) % CW)+CW)%CW;
      const nk = nj*CW + ni;
      if (done[nk]) continue;
      let fac;
      if (cLand(ni,nj)) fac = BEST_FACTOR;
      else if (water === null) continue;
      else if (reach !== null && !coarseNearShore(ni,nj,reach)) continue;
      else fac = water;
      if (!inEllipse(ni, nj, nk)) continue;
      const nd = d + cStepKm(cj, di, dj)/fac;
      if (nd < dist[nk] - 1e-9){ dist[nk] = nd; heap.push(nd, nk); }
    }
  }
  if (FIELD_CACHE.size > 24) FIELD_CACHE.clear();
  FIELD_CACHE.set(ckey, dist);
  return dist;
}

function snapToLand(i, j, allowWater){
  if (allowWater || isLandCell(i,j)) return [i,j];
  for (let r = 1; r <= 10; r++){
    let best = null, bd = 1e9;
    for (let di = -r; di <= r; di++) for (let dj = -r; dj <= r; dj++){
      if (Math.max(Math.abs(di), Math.abs(dj)) !== r) continue;
      const ni = (((i+di) % MW)+MW)%MW, nj = j+dj;
      if (nj < 0 || nj >= MH || !isLandCell(ni,nj)) continue;
      const d = di*di + dj*dj;
      if (d < bd){ best = [ni,nj]; bd = d; }
    }
    if (best) return best;
  }
  return [i,j];
}

const ROUTE_CACHE = new Map();
function findWay(a, b, boat, costAt){
  const key = [a[0].toFixed(4),a[1].toFixed(4),b[0].toFixed(4),b[1].toFixed(4),boat].join("|");
  let got = ROUTE_CACHE.get(key);
  if (!got){
    if (ROUTE_CACHE.size > 200) ROUTE_CACHE.clear();
    got = searchWay(a, b, boat, costAt);
    ROUTE_CACHE.set(key, got);
  }
  return got;
}

function searchWay(a, b, boat, costAt, maxCells = 1400000){
  const bo = BOATS[boat] || BOATS.none;
  const water = bo.water, reach = bo.reach === undefined ? null : bo.reach;

  const [ai, aj] = snapToLand(...cellOf(a[0],a[1]), water !== null);
  const [bi, bj] = snapToLand(...cellOf(b[0],b[1]), water !== null);
  if (ai === bi && aj === bj) return {pts:[a,b], ok:true, wet:0};

  if (water === null){
    /* a party that will not get its feet wet cannot leave its own landmass, and
       knowing that costs two lookups instead of a search of half of Europe */
    const ca = COMP_GRID[aj*MW + ai], cb = COMP_GRID[bj*MW + bi];
    if (ca && cb && ca !== cb && ca !== 255 && cb !== 255)
      return {pts:[a,b], ok:false, wet:0};
  }

  const creach = reach === null ? null : Math.max(1, ((reach/CF)|0) + 1);
  const field = coarseField(a, b, water, creach);
  if (!isFinite(field[((aj/CF)|0)*CW + ((ai/CF)|0)]))
    return {pts:[a,b], ok:false, wet:0};

  const gLat = ROW_LAT[bj], gLon = -180 + (bi+0.5)*MRES;
  const gSin = Math.sin(gLat*Math.PI/180), gCos = Math.cos(gLat*Math.PI/180);
  const SLACK = 90;
  const heur = (i,j) => {
    const lon = -180 + (i+0.5)*MRES;
    const gc = rowDist(ROW_SIN[j], ROW_COS[j], lon, gSin, gCos, gLat, gLon)/BEST_FACTOR;
    const f = field[((j/CF)|0)*CW + ((i/CF)|0)];
    return isFinite(f) ? Math.max(gc, f - SLACK) : gc;
  };
  const passable = (i,j) => {
    if (LAND[j*MW + i]) return costAt ? Math.max(0.15, costAt(...cellCentre(i,j))) : 1;
    if (water === null) return null;
    if (reach !== null && !nearShore(i,j,reach)) return null;
    return water;
  };

  const start = aj*MW + ai, target = bj*MW + bi;
  const g = new Map(), came = new Map(), seen = new Set();
  const heap = new Heap();
  g.set(start, 0); heap.push(heur(ai,aj), start);
  let steps = 0, found = false;
  while (heap.n){
    const [, cur] = heap.pop();
    if (seen.has(cur)) continue;
    seen.add(cur);
    if (++steps > maxCells) break;
    if (cur === target){ found = true; break; }
    const ci = cur % MW, cj = (cur/MW)|0;
    const gc = g.get(cur);
    for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++){
      if (!di && !dj) continue;
      const nj = cj + dj;
      if (nj < 0 || nj >= MH) continue;
      const ni = (((ci+di) % MW)+MW)%MW;
      const nk = nj*MW + ni;
      if (seen.has(nk)) continue;
      const fac = passable(ni, nj);
      if (fac === null) continue;
      const ng = gc + stepKm(cj, di, dj)/fac;
      const old = g.get(nk);
      if (old === undefined || ng < old - 1e-9){
        g.set(nk, ng); came.set(nk, cur);
        heap.push(ng + heur(ni,nj), nk);
      }
    }
  }
  if (!found) return {pts:[a,b], ok:false, wet:0};

  const path = [target];
  while (path[path.length-1] !== start) path.push(came.get(path[path.length-1]));
  path.reverse();
  const pts = [a];
  for (let k = 1; k < path.length-1; k++) pts.push(cellCentre(path[k] % MW, (path[k]/MW)|0));
  pts.push(b);
  let wet = 0;
  for (const k of path) if (!LAND[k]) wet++;
  return {pts:simplifyPath(pts, 12), ok:true, wet:wet/Math.max(1, path.length)};
}

/* Douglas-Peucker, so a grid path becomes a handful of waypoints */
function simplifyPath(pts, tolKm){
  if (pts.length < 3) return pts;
  const keep = new Uint8Array(pts.length);
  keep[0] = keep[pts.length-1] = 1;
  const stack = [[0, pts.length-1]];
  while (stack.length){
    const [lo, hi] = stack.pop();
    if (hi <= lo + 1) continue;
    let worst = -1, wi = -1;
    for (let k = lo+1; k < hi; k++){
      const d = crossTrack(pts[k], pts[lo], pts[hi]);
      if (d > worst){ worst = d; wi = k; }
    }
    if (worst <= tolKm) continue;
    keep[wi] = 1;
    stack.push([lo, wi], [wi, hi]);
  }
  const out = [];
  for (let k = 0; k < pts.length; k++) if (keep[k]) out.push(pts[k]);
  return out;
}

function crossTrack(p, a, b){
  const kx = Math.cos(p[0]*Math.PI/180)*111.32, ky = 110.57;
  const px = (p[1]-a[1])*kx, py = (p[0]-a[0])*ky;
  const bx = (b[1]-a[1])*kx, by = (b[0]-a[0])*ky;
  const L = bx*bx + by*by;
  const t = L === 0 ? 0 : Math.max(0, Math.min(1, (px*bx + py*by)/L));
  return Math.hypot(px - t*bx, py - t*by);
}
