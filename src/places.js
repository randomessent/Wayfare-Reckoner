/* ---------- the gazetteer ----------
   Every settlement above a thousand people — about 171,000 of them — plus the
   ranges, passes, parks and rivers a journey gets described by. The rows arrive
   sorted by population, which is the whole of the disambiguation rule: ask for
   Springfield and you get the big one. */
const KINDS = {c:"city", t:"town", r:"range", p:"park", f:"forest", s:"pass",
               w:"water", n:"plain", o:"coast", u:"custom"};

const P_NAME = [], P_LAT = [], P_LON = [], P_REG = [], P_POP = [],
      P_KIND = [], P_ALIAS = [];
(function parse(){
  const rows = PLACES_TSV.split("\n");
  for (let k = 0; k < rows.length; k++){
    const f = rows[k].split("\t");
    if (f.length < 6) continue;
    P_NAME.push(f[0]); P_LAT.push(+f[1]); P_LON.push(+f[2]);
    P_REG.push(+f[3]); P_POP.push(+f[4]); P_KIND.push(f[5]);
    P_ALIAS.push(f.length > 6 ? f[6] : "");
  }
})();
const NPLACE = P_NAME.length;

/* Combining marks, written as escapes: a regex with invisible accents in it
   is a regex one bad copy-paste away from being broken. */
const COMBINING = /[\u0300-\u036f]/g;
function fold(s){
  return String(s).normalize("NFKD").replace(COMBINING, "")
    .toLowerCase().replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ").trim();
}

/* name -> the best row carrying it, and a coarse bucket for "what is near here" */
const INDEX = new Map(), BUCKET = new Map(), FOLDED = new Array(NPLACE);
(function buildIndex(){
  for (let i = 0; i < NPLACE; i++){
    const k = fold(P_NAME[i]);
    FOLDED[i] = k;
    if (k && !INDEX.has(k)) INDEX.set(k, i);
    if (P_ALIAS[i]){
      const parts = P_ALIAS[i].split("|");
      for (let a = 0; a < parts.length; a++){
        const fa = fold(parts[a]);
        if (fa && !INDEX.has(fa)) INDEX.set(fa, i);
      }
    }
    const bk = (Math.floor(P_LAT[i]) * 1000) + Math.floor(P_LON[i]);
    let b = BUCKET.get(bk);
    if (!b) BUCKET.set(bk, b = []);
    b.push(i);
  }
})();

const PLACE_COUNT = NPLACE;
function regionOf(i){ return REGION_TABLE[P_REG[i]] || ""; }

/* ---- places the traveller adds themselves ---- */
const CUSTOM = [];
const CUSTOM_KEY = "wayfare.places.v2";
function customIndex(name){
  const f = fold(name);
  for (let k = 0; k < CUSTOM.length; k++) if (fold(CUSTOM[k].name) === f) return k;
  return -1;
}
function pushCustom(c){
  const i = P_NAME.length;
  P_NAME.push(c.name); P_LAT.push(c.lat); P_LON.push(c.lon);
  P_REG.push(-1); P_POP.push(0); P_KIND.push("u"); P_ALIAS.push("");
  FOLDED.push(fold(c.name));
  INDEX.set(fold(c.name), i);
  c.row = i;
  c.region = c.region || (zoneAt(c.lat, c.lon)[0] + " — added by you");
  return i;
}
function loadCustom(){
  let raw = null;
  try { raw = localStorage.getItem(CUSTOM_KEY); } catch(e){ return; }
  if (!raw) return;
  try {
    for (const c of JSON.parse(raw)){ CUSTOM.push(c); pushCustom(c); }
  } catch(e){ /* corrupt store — ignore it rather than break the page */ }
}
function saveCustom(){
  try { localStorage.setItem(CUSTOM_KEY,
    JSON.stringify(CUSTOM.map(c=>({name:c.name, lat:c.lat, lon:c.lon, region:c.region})))); }
  catch(e){}
}
function addCustomPlace(name, lat, lon){
  if (customIndex(name) >= 0) removeCustomPlace(name);
  const c = {name, lat, lon};
  CUSTOM.push(c); pushCustom(c); saveCustom();
}
function removeCustomPlace(name){
  const k = customIndex(name);
  if (k < 0) return;
  const c = CUSTOM[k];
  CUSTOM.splice(k, 1);
  if (INDEX.get(fold(c.name)) === c.row) INDEX.delete(fold(c.name));
  P_NAME[c.row] = " "; P_POP[c.row] = -1; FOLDED[c.row] = "";
  saveCustom();
}
function customPlaces(){ return CUSTOM.slice(); }
loadCustom();

/* ---- coordinates ---- */
const COORD_RE = /^\s*(?:([^@:]+?)\s*[@:]\s*)?([-+]?\d{1,2}(?:\.\d+)?)\s*([NnSs])?\s*[,; ]\s*([-+]?\d{1,3}(?:\.\d+)?)\s*([EeWw])?\s*$/;
function parseCoords(text){
  const m = COORD_RE.exec(String(text));
  if (!m) return null;
  let lat = parseFloat(m[2]), lon = parseFloat(m[4]);
  if (m[3] && m[3].toLowerCase() === "s") lat = -Math.abs(lat);
  if (m[5] && m[5].toLowerCase() === "w") lon = -Math.abs(lon);
  if (!(lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180)) return null;
  return {label:(m[1]||"").trim(), lat, lon};
}

class PlaceNotFound extends Error {
  constructor(query, suggestions){ super(query); this.query = query; this.suggestions = suggestions; }
}
function rec(i, how){
  let region;
  if (P_REG[i] < 0){
    const c = CUSTOM.find(x=>x.row === i);
    region = (c && c.region) || "added by you";
  } else region = regionOf(i);
  return {name:P_NAME[i], lat:P_LAT[i], lon:P_LON[i], elev:0, region,
          kind:KINDS[P_KIND[i]] || "town", pop:P_POP[i], matchedAs:how};
}

/* Words that carry no weight in a place name: a search for "Parque Regional de
   la Sierra de Gredos" is really a search for "Sierra de Gredos". */
const STOP = new Set(["the","of","de","del","la","le","les","los","las","el","du","da","do","di",
  "der","die","das","und","and","am","an","sur","en","y","a","parque","parc","park","nacional",
  "national","natural","regional","reserve","reserva","naturpark","nationalpark","county","city",
  "province","region","department","district","state"]);

function resolve(query){
  const raw = String(query||"").trim();
  if (!raw) throw new PlaceNotFound(raw, []);

  const c = parseCoords(raw);
  if (c) return {name:c.label || (c.lat.toFixed(3) + ", " + c.lon.toFixed(3)),
                 lat:c.lat, lon:c.lon, elev:0, region:zoneAt(c.lat, c.lon)[0],
                 kind:"coords", pop:0, matchedAs:"coordinates"};

  const q = fold(raw);
  if (INDEX.has(q)) return rec(INDEX.get(q), "name");

  const segs = raw.split(/[,/]/).map(fold).filter(Boolean);

  /* "Raleigh, North Carolina" — the first piece names the place, the rest says
     which of the many Raleighs is meant. */
  if (segs.length > 1){
    const head = segs[0];
    const want = segs.slice(1).join(" ").split(" ").filter(t=>t.length > 1 && !STOP.has(t));
    if (want.length){
      let best = -1;
      for (let i = 0; i < NPLACE; i++){
        if (FOLDED[i] !== head) continue;
        const rg = fold(regionOf(i));
        if (!rg) continue;
        let all = true;
        for (const t of want) if (!rg.includes(t)){ all = false; break; }
        if (all && (best < 0 || P_POP[i] > P_POP[best])) best = i;
      }
      if (best >= 0) return rec(best, "name and region");
    }
  }

  /* progressively drop trailing pieces: "Sierra de Gredos, Ávila, Spain" */
  for (let cut = segs.length; cut > 0; cut--){
    const j = segs.slice(0, cut).join(" ");
    if (INDEX.has(j)) return rec(INDEX.get(j), "name");
  }
  for (const s of segs) if (INDEX.has(s)) return rec(INDEX.get(s), "name");

  /* still nothing: look for a known name inside what was typed, preferring the
     longest match and letting population break the ties */
  let best = -1, bestScore = 0;
  for (const cand of [q].concat(segs)){
    if (cand.length < 4) continue;
    const words = cand.split(" ").filter(t=>!STOP.has(t));
    for (let n = words.length; n >= 1; n--){
      for (let s = 0; s + n <= words.length; s++){
        const key = words.slice(s, s + n).join(" ");
        if (key.length < 4 || !INDEX.has(key)) continue;
        const i = INDEX.get(key);
        const score = n*10 + key.length/40 + Math.min(1, P_POP[i]/2e6);
        if (score > bestScore){ best = i; bestScore = score; }
      }
    }
  }
  if (best >= 0 && bestScore >= 10) return rec(best, "partial name");

  throw new PlaceNotFound(raw, suggest(raw));
}

/* crude edit-distance ratio, enough to catch typos */
function ratio(a, b){
  if (a === b) return 1;
  const m = a.length, n = b.length;
  if (!m || !n || Math.abs(m - n) > 3) return 0;
  let prev = Array.from({length:n+1}, (_,j)=>j), cur = new Array(n+1);
  for (let i = 1; i <= m; i++){
    cur[0] = i;
    for (let j = 1; j <= n; j++)
      cur[j] = Math.min(prev[j]+1, cur[j-1]+1, prev[j-1] + (a[i-1] === b[j-1] ? 0 : 1));
    const t = prev; prev = cur; cur = t;
  }
  return 1 - prev[n]/Math.max(m, n);
}
function suggest(query, n=6){
  /* 171,000 names is too many to score one by one, so only rows of about the
     right length that start near enough are even considered */
  const cands = [fold(query)].concat(String(query).split(/[,/]/).map(fold).filter(Boolean));
  const out = [];
  for (const c of cands){
    if (c.length < 3) continue;
    const head = c.slice(0, 2);
    for (let i = 0; i < NPLACE; i++){
      const k = FOLDED[i];
      if (!k || Math.abs(k.length - c.length) > 2) continue;
      if (k[0] !== c[0] && !k.startsWith(head)) continue;
      const s = ratio(c, k);
      if (s >= 0.6) out.push([P_NAME[i], s + Math.min(0.2, P_POP[i]/5e6)]);
    }
  }
  const seen = new Set(), picked = [];
  for (const e of out.sort((a,b)=>b[1]-a[1])){
    if (seen.has(e[0])) continue;
    seen.add(e[0]); picked.push(e[0]);
    if (picked.length >= n) break;
  }
  return picked;
}

/* ---- typeahead: prefix first, biggest first, then a fuzzy sweep ---- */
function searchPlaces(query, limit=8){
  const q = fold(query);
  if (!q) return [];
  const pre = [], mid = [];
  for (let i = 0; i < NPLACE && pre.length < limit; i++){
    const k = FOLDED[i];
    if (!k) continue;
    if (k.startsWith(q)) pre.push(i);
    else if (mid.length < limit && k.length > q.length + 2 && k.includes(q)) mid.push(i);
  }
  const out = [], seen = new Set();
  for (const i of pre.concat(mid)){
    if (seen.has(P_NAME[i])) continue;
    seen.add(P_NAME[i]); out.push(P_NAME[i]);
    if (out.length >= limit) break;
  }
  if (!out.length) for (const s of suggest(query, limit)) out.push(s);
  return out.slice(0, limit);
}

/* the row behind a typeahead line, so the list can show where it is */
function placeInfo(name){
  const i = INDEX.get(fold(name));
  return i === undefined ? null : rec(i, "name");
}

/* ---- what is near a point ---- */
function nearestPlaceOf(lat, lon, minPop){
  let best = -1, bd = 1e18;
  const k = Math.cos(lat*Math.PI/180);
  const bj = Math.floor(lat), bi = Math.floor(lon);
  for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++){
    const b = BUCKET.get((bj+dj)*1000 + (bi+di));
    if (!b) continue;
    for (let x = 0; x < b.length; x++){
      const i = b[x];
      if (P_POP[i] < minPop) continue;
      const dy = P_LAT[i] - lat, dx = (P_LON[i] - lon)*k;
      const d = dy*dy + dx*dx;
      if (d < bd){ best = i; bd = d; }
    }
  }
  return best < 0 ? [null, 1e9] : [P_NAME[best], Math.sqrt(bd)*111.32];
}

/* A camp is described by the town it is near, and with 171,000 of them a hamlet
   of nine hundred is not a landmark — so ask for somewhere of a few thousand
   souls first, and settle for less only if the country is empty. */
function nearestPlace(lat, lon){
  const tries = [[20000,140],[2000,140],[0,400]];
  for (const t of tries){
    const got = nearestPlaceOf(lat, lon, t[0]);
    if (got[0] && got[1] < t[1]) return got;
  }
  return [null, 1e9];
}
