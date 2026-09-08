/* ---------- the chart ----------
   Projection is EPSG:3857 (spherical Web Mercator), so the graticule is
   rectilinear and the terrain zones — which are lat/lon boxes — stay
   graticule is rectilinear. The coastline is Natural Earth's, generalised
   to about six kilometres; the ground inside it is painted pixel by pixel
   from the same tenth-of-a-degree terrain grid the reckoning walks over, so
   what you see is exactly what was counted.                              */

const R3857 = 6378137;
const MAXLAT = 85.05112878;
const mx = lon => R3857 * lon * Math.PI/180;
const my = lat => R3857 * Math.log(Math.tan(Math.PI/4 + Math.max(-MAXLAT,Math.min(MAXLAT,lat))*Math.PI/360));
const xlon = x => x / R3857 * 180/Math.PI;
const ylat = y => (2*Math.atan(Math.exp(y/R3857)) - Math.PI/2) * 180/Math.PI;

const LIM = { x0: mx(-179.5), x1: mx(179.5), y0: my(-82), y1: my(83) };
const MIN_SPAN = 60000;                      // ~40 km of real ground at 45°N

let MAP = null;        // {cx, cy, span} in EPSG:3857 metres
let MAPR = null, MAPCFG = null, MAPKEY = "";

function clampView(v){
  const H = MAPH, W = MAPW;
  v.span = Math.max(MIN_SPAN, Math.min(LIM.x1 - LIM.x0, v.span));
  const sy = v.span * H / W;
  const maxSy = LIM.y1 - LIM.y0;
  if (sy > maxSy){ v.span = maxSy * W / H; }
  const hx = v.span/2, hy = v.span * H / W / 2;
  v.cx = Math.max(LIM.x0 + hx, Math.min(LIM.x1 - hx, v.cx));
  v.cy = Math.max(LIM.y0 + hy, Math.min(LIM.y1 - hy, v.cy));
  return v;
}

/* The chart is wider than it is tall on a desk, where there is width to spare.
   On a phone that leaves a 220-pixel letterbox, so it squares up. */
const NARROW = typeof matchMedia === "function" && matchMedia("(max-width: 820px)").matches;
const MAPW = 1000, MAPASPECT = NARROW ? 1.05 : 1.62;
const MAPH = Math.round(MAPW / MAPASPECT);

function fitToRoute(r){
  let x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity;
  const touch=(la,lo)=>{ const X=mx(lo), Y=my(la);
    x0=Math.min(x0,X); x1=Math.max(x1,X); y0=Math.min(y0,Y); y1=Math.max(y1,Y); };
  for (const s of r.segs){ touch(s.lat0,s.lon0); touch(s.lat1,s.lon1); }
  for (const n of r.nodes) touch(n.lat, n.lon);
  const padX = Math.max((x1-x0)*0.20, 40000), padY = Math.max((y1-y0)*0.20, 40000);
  x0-=padX; x1+=padX; y0-=padY; y1+=padY;
  const span = Math.max(x1-x0, (y1-y0) * MAPW / MAPH);
  return clampView({cx:(x0+x1)/2, cy:(y0+y1)/2, span});
}


/* ---------- the ground, painted ----------
   One pass over the visible pixels, each asking the terrain grid what it is
   standing on. The colours come from the stylesheet so the chart follows the
   reader's light or dark theme without a second palette to keep in step. */
let PAL = null, PAL_THEME = "";
function palette(host){
  const theme = getComputedStyle(host).getPropertyValue("--water").trim();
  if (PAL && PAL_THEME === theme) return PAL;
  const probe = document.createElement("canvas").getContext("2d");
  const cs = getComputedStyle(host);
  PAL = TERRAIN_KEYS.map(key=>{
    const raw = cs.getPropertyValue("--k_" + key).trim();
    probe.fillStyle = raw || "#888888";
    const hex = probe.fillStyle;
    return [parseInt(hex.slice(1,3),16), parseInt(hex.slice(3,5),16), parseInt(hex.slice(5,7),16)];
  });
  PAL_THEME = theme;
  return PAL;
}

let GROUND_CANVAS = null;
function paintGround(host, v, k, W, H, wantLabels, labelsOut){
  const pal = palette(host);
  const pw = 1000, ph = Math.round(1000*H/W);
  const cv = GROUND_CANVAS || (GROUND_CANVAS = document.createElement("canvas"));
  cv.width = pw; cv.height = ph;
  const ctx = cv.getContext("2d");
  const img = ctx.createImageData(pw, ph);
  const px = img.data;

  /* Label placement, gathered in the same pass rather than a second one. The
     centroid alone is not enough — Italy's centroid is in the Adriatic — so a
     scattering of the actual land pixels is kept, and the name goes to whichever
     of those is nearest the middle. */
  const sumX = new Map(), sumY = new Map(), count = new Map(), spots = new Map();

  for (let py = 0; py < ph; py++){
    const uy = (py + 0.5) * H / ph;
    const lat = ylat(v.cy - (uy - H/2)/k);
    const j = Math.min(GH-1, Math.max(0, Math.floor((90 - lat)/GRES)));
    const row = j*GW;
    for (let pxi = 0; pxi < pw; pxi++){
      const ux = (pxi + 0.5) * W / pw;
      let lon = xlon(v.cx + (ux - W/2)/k);
      lon = ((lon + 180) % 360 + 360) % 360 - 180;
      const i = Math.min(GW-1, Math.max(0, Math.floor((lon + 180)/GRES)));
      const cell = row + i;
      const o = (py*pw + pxi)*4;
      if (!LAND[cell]) continue;               /* sea: leave it clear */
      const c = pal[TERRAIN_GRID[cell]];
      px[o] = c[0]; px[o+1] = c[1]; px[o+2] = c[2]; px[o+3] = 255;
      const nm = NAME_GRID[cell];
      if (nm && wantLabels.size){
        const label = NAME_TABLE[nm];
        if (wantLabels.has(label)){
          const n = (count.get(label)||0) + 1;
          sumX.set(label, (sumX.get(label)||0) + ux);
          sumY.set(label, (sumY.get(label)||0) + uy);
          count.set(label, n);
          if (n % 23 === 1){
            let sp = spots.get(label);
            if (!sp) spots.set(label, sp = []);
            if (sp.length < 400) sp.push(ux, uy);
          }
        }
      }
    }
  }
  ctx.putImageData(img, 0, 0);

  const need = pw*ph/380;                       /* too small a patch, no room for a name */
  for (const [label, n] of count){
    if (n < need) continue;
    const cx = sumX.get(label)/n, cy = sumY.get(label)/n;
    const sp = spots.get(label) || [];
    let bx = cx, by = cy, bd = Infinity;
    for (let i = 0; i < sp.length; i += 2){
      const d = (sp[i]-cx)**2 + (sp[i+1]-cy)**2;
      if (d < bd){ bd = d; bx = sp[i]; by = sp[i+1]; }
    }
    labelsOut.push({label, x:bx, y:by});
  }

  return cv.toDataURL("image/png");
}

/* ---------- drawing ---------- */
function drawMap(){
  const r = MAPR, cfg = MAPCFG, host = $("mapsvg");
  if (!r || !host) return;
  const W = MAPW, H = MAPH, v = MAP;
  const k = W / v.span;
  const X = lon => (mx(lon) - v.cx) * k + W/2;
  const Y = lat => H/2 - (my(lat) - v.cy) * k;
  const lon0 = xlon(v.cx - v.span/2), lon1 = xlon(v.cx + v.span/2);
  const lat1 = ylat(v.cy + v.span*H/W/2), lat0 = ylat(v.cy - v.span*H/W/2);
  const inView = (la,lo) => la>lat0-0.2 && la<lat1+0.2 && lo>lon0-0.3 && lo<lon1+0.3;

  const pxw = Math.max(300, (host.clientWidth || 1000));
  /* Type on the chart is sized in SVG units, so it shrinks with the container.
     On a phone that puts place names below legibility — so they are scaled up,
     and because fewer then fit, fewer are drawn. Larger and sparser beats
     complete and unreadable. */
  const fs = NARROW ? Math.max(1, Math.min(3.9, 1000 / pxw * 1.32))
                    : Math.max(1, Math.min(2.9, 1000 / pxw));

  const path = flat => {
    let d = "";
    for (let i = 0; i < flat.length; i += 2)
      d += (i ? "L" : "M") + X(flat[i]).toFixed(1) + " " + Y(flat[i+1]).toFixed(1);
    return d + "Z";
  };

  /* ground: the terrain grid itself, one pixel at a time.
     A raster is the honest way to draw an eleven-kilometre grid — the old
     rectangles were a lie about how the country is shaped — and it costs one
     pass over a quarter of a million pixels, which is nothing. Cells that are
     sea are left clear so the ocean shows through. */
  const routeZones = new Set(r.zones.filter(z=>z.pct >= 8).map(z=>z.zone));
  const zoneLabels = [];
  const groundImg = paintGround(host, v, k, W, H, routeZones, zoneLabels);

  /* the land itself: Natural Earth's rings, culled to what is on screen */
  let coast = "";
  const ringPath = flat => {
    let d = "", lo0 = 1e9, lo1 = -1e9, la0 = 1e9, la1 = -1e9;
    for (let i = 0; i < flat.length; i += 2){
      const lo = flat[i], la = flat[i+1];
      if (lo < lo0) lo0 = lo; if (lo > lo1) lo1 = lo;
      if (la < la0) la0 = la; if (la > la1) la1 = la;
    }
    if (lo1 < lon0 - 0.5 || lo0 > lon1 + 0.5 || la1 < lat0 - 0.5 || la0 > lat1 + 0.5) return "";
    for (let i = 0; i < flat.length; i += 2)
      d += (i ? "L" : "M") + X(flat[i]).toFixed(1) + " " + Y(flat[i+1]).toFixed(1);
    return d + "Z";
  };
  const minRing = (lon1 - lon0) / 220;          /* skip islets too small to see */
  for (const flat of COAST.land){
    let lo0r = 1e9, lo1r = -1e9, la0r = 1e9, la1r = -1e9;
    for (let i = 0; i < flat.length; i += 2){
      if (flat[i] < lo0r) lo0r = flat[i]; if (flat[i] > lo1r) lo1r = flat[i];
      if (flat[i+1] < la0r) la0r = flat[i+1]; if (flat[i+1] > la1r) la1r = flat[i+1];
    }
    if (Math.max(lo1r-lo0r, la1r-la0r) < minRing) continue;
    const d = ringPath(flat);
    if (d) coast += d;
  }
  let lakeD = "";
  for (const flat of COAST.lakes){
    const d = ringPath(flat);
    if (d) lakeD += d;
  }

  /* graticule, stepped to whatever is on screen */
  const degSpan = lon1 - lon0;
  const step = degSpan > 150 ? 30 : degSpan > 70 ? 15 : degSpan > 26 ? 5
             : degSpan > 11 ? 2 : degSpan > 5 ? 1 : degSpan > 2 ? 0.5 : 0.25;
  const dec = step < 1 ? (step < 0.5 ? 2 : 1) : 0;
  let grat = "";
  for (let la = Math.ceil(lat0/step)*step; la <= lat1; la += step)
    grat += `<line x1="0" y1="${Y(la).toFixed(1)}" x2="${W}" y2="${Y(la).toFixed(1)}" class="grat"></line>`
         +  `<text x="4" y="${(Y(la)-3).toFixed(1)}" class="gratlab">${la.toFixed(dec)}°N</text>`;
  for (let lo = Math.ceil(lon0/step)*step; lo <= lon1; lo += step)
    grat += `<line x1="${X(lo).toFixed(1)}" y1="0" x2="${X(lo).toFixed(1)}" y2="${H}" class="grat"></line>`
         +  `<text x="${(X(lo)+4).toFixed(1)}" y="${H-5}" class="gratlab">${Math.abs(lo).toFixed(dec)}°${lo<0?"W":"E"}</text>`;

  /* the night stops, worked out first so place names can dodge them */
  const march = r.sim.days.filter(d=>d.kind !== "rest");
  /* how often a night gets a number: the smaller the chart, the fewer fit */
  const slots = NARROW ? 7 : 12;
  const every = march.length > slots*2 ? Math.ceil(march.length/slots)
              : (march.length > slots ? 2 : 1);
  const stopAt = r.sim.days.map(d=>{
    const [la,lo] = positionAt(r.segs, d.cum);
    return {d, x:X(lo), y:Y(la), on:inView(la,lo)};
  });

  /* settlements, and as many names as will fit */
  /* With 171,000 of them, drawing every settlement would be a grey smear. The
     wider the view, the larger a place has to be to earn a dot: continents get
     capitals, a valley gets villages. Camps on the route are always drawn. */
  let dots = "";
  const near = [];
  const isNode = new Set(r.nodes.map(n=>n.name));
  const camps = new Set(r.sim.days.map(d=>d.camp));
  const degSpanNow = lon1 - lon0;
  const floor = degSpanNow > 120 ? 1500000 : degSpanNow > 60 ? 600000
              : degSpanNow > 26 ? 200000 : degSpanNow > 11 ? 70000
              : degSpanNow > 5 ? 25000 : degSpanNow > 2 ? 8000 : 1500;
  for (let i = 0; i < P_NAME.length; i++){
    const n = P_NAME[i];
    if (P_POP[i] < 0 || isNode.has(n)) continue;
    const isCamp = camps.has(n);
    if (P_POP[i] < floor && !isCamp && P_KIND[i] !== "u") continue;
    if (!inView(P_LAT[i], P_LON[i])) continue;
    const x = X(P_LON[i]), y = Y(P_LAT[i]);
    if (x < -20 || x > W+20 || y < -20 || y > H+20) continue;
    const big = P_KIND[i] === "c";
    dots += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${big?2:1.4}" class="pdot${big?" big":""}"></circle>`;
    near.push({n, x, y, rank:(big?0:1) + (P_KIND[i]==="u"?-1:0) - Math.min(1, P_POP[i]/1e6)});
    if (near.length > 4000) break;
  }
  near.sort((a,c)=> (camps.has(c.n)?1:0)-(camps.has(a.n)?1:0) || a.rank-c.rank || a.x-c.x);
  const placed = [];
  let names = "";
  const clearOf = (x, w, y) =>
    x > 4 && x + w < W - 4 && y > 12*fs && y < H - 16*fs &&
    !placed.some(p => x < p.x2 + 10*fs && x + w > p.x1 - 10*fs && Math.abs(p.y - y) < 13*fs) &&
    !stopAt.some(s => s.x > x - 12*fs && s.x < x + w + 12*fs && Math.abs(s.y - y) < 22*fs);
  const maxNames = Math.round(26 / fs);
  for (const q of near){
    if (placed.length >= maxNames) break;
    const w = q.n.length * 4.6 * fs;
    let x1 = q.x + 5, anchor = "start";
    if (!clearOf(x1, w, q.y)){ x1 = q.x - 5 - w; anchor = "end"; if (!clearOf(x1, w, q.y)) continue; }
    placed.push({x1, x2:x1 + w, y:q.y});
    names += `<text x="${(anchor==="start"? q.x+5 : q.x-5).toFixed(1)}" y="${(q.y+3).toFixed(1)}" text-anchor="${anchor}" class="pname">${esc(q.n)}</text>`;
  }

  /* the road */
  let pts = "", wetPath = "", wasWet = false;
  r.segs.forEach((s,i)=>{
    if (i === 0) pts += `M${X(s.lon0).toFixed(1)} ${Y(s.lat0).toFixed(1)}`;
    pts += `L${X(s.lon1).toFixed(1)} ${Y(s.lat1).toFixed(1)}`;
    if (s.water){
      if (!wasWet) wetPath += `M${X(s.lon0).toFixed(1)} ${Y(s.lat0).toFixed(1)}`;
      wetPath += `L${X(s.lon1).toFixed(1)} ${Y(s.lat1).toFixed(1)}`;
    }
    wasWet = s.water;
  });

  let gap = 1e9;
  for (let i = 1; i < stopAt.length; i++){
    const g = Math.hypot(stopAt[i].x - stopAt[i-1].x, stopAt[i].y - stopAt[i-1].y);
    if (g > 0.5) gap = Math.min(gap, g);
  }
  const RD = Math.max(1.5, Math.min(3.4*fs, gap * 0.3));
  let stops = "";
  stopAt.forEach(({d,x,y,on})=>{
    if (!on) return;
    const halt = d.kind === "rest";
    const idx = march.indexOf(d);
    const show = halt || idx === 0 || idx === march.length-1 || idx % every === 0;
    const numY = halt ? y + 12*fs + 2 : y - 7*fs - 2;
    stops += `<g class="stop${halt?" halt":""}" data-day="${d.day}" tabindex="0" role="button"
        aria-label="Day ${d.day}${halt?", forced halt":""}, ${Math.round(d.km)} kilometres, ${esc(d.camp)}">
      <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${Math.max(9,RD*2.4).toFixed(1)}" class="hitbox"></circle>
      ${halt?`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(Math.max(RD,3)+2.6).toFixed(1)}" class="haltring"></circle>`:""}
      <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(halt?Math.max(RD,3):RD).toFixed(1)}" class="stopdot" style="stroke-width:${RD<2.4?0:1.4}"></circle>
      ${show?`<text x="${x.toFixed(1)}" y="${numY.toFixed(1)}" class="stopnum">${d.day}</text>`:""}
    </g>`;
  });

  let ends = "";
  r.nodes.forEach((n,i)=>{
    if (!inView(n.lat, n.lon)) return;
    const x = X(n.lon), y = Y(n.lat), last = i === r.nodes.length-1, first = i === 0;
    const half = n.name.length * 3.1 * fs;
    const anchor = x - half < 6 ? "start" : x + half > W - 6 ? "end" : "middle";
    const tx = anchor === "start" ? 6 : anchor === "end" ? W - 6 : x;
    const ty = y + (last ? (anchor!=="middle" ? 30*fs : 20*fs) : first ? 18*fs : -12*fs);
    ends += `<g class="endpt">
      <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="6" class="endhalo"></circle>
      <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" class="enddot"></circle>
      <text x="${tx.toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="${anchor}" class="endname">${esc(n.name)}</text></g>`;
  });

  /* scale bar — Mercator stretches with latitude, so measure at the middle */
  const midLat = ylat(v.cy);
  const mPerUnit = (v.span / W) * Math.cos(midLat*Math.PI/180);
  const want = mPerUnit * W * 0.18;
  const pow = Math.pow(10, Math.floor(Math.log10(want)));
  const nice = [1,2,5,10].map(m=>m*pow).reduce((a,b)=> Math.abs(b-want) < Math.abs(a-want) ? b : a);
  const barW = nice / mPerUnit;
  const barLabel = nice >= 1000 ? `${Math.round(nice/1000)} km` : `${Math.round(nice)} m`;
  const by = H - 16*fs, bx = W - 14 - barW;
  const scalebar = `<g class="scalebar">
    <line x1="${bx.toFixed(1)}" y1="${by.toFixed(1)}" x2="${(bx+barW).toFixed(1)}" y2="${by.toFixed(1)}"></line>
    <line x1="${bx.toFixed(1)}" y1="${(by-3.5*fs).toFixed(1)}" x2="${bx.toFixed(1)}" y2="${(by+3.5*fs).toFixed(1)}"></line>
    <line x1="${(bx+barW).toFixed(1)}" y1="${(by-3.5*fs).toFixed(1)}" x2="${(bx+barW).toFixed(1)}" y2="${(by+3.5*fs).toFixed(1)}"></line>
    <text x="${(bx+barW/2).toFixed(1)}" y="${(by-6*fs).toFixed(1)}">${barLabel}</text></g>`;

  const zl = zoneLabels.map(z=>`<text x="${z.x.toFixed(1)}" y="${z.y.toFixed(1)}" class="zonelab">${esc(z.label)}</text>`).join("");

  host.style.setProperty("--fs", fs.toFixed(2));
  host.innerHTML =
    `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img"
       aria-label="Chart of the route from ${esc(r.nodes[0].name)} to ${esc(r.nodes[r.nodes.length-1].name)}, with a marker at each night's end.">
      <rect width="${W}" height="${H}" class="ocean"></rect>
      <image href="${groundImg}" x="0" y="0" width="${W}" height="${H}"
             preserveAspectRatio="none"></image>
      <path d="${coast}" class="coast"></path>
      ${lakeD ? `<path d="${lakeD}" class="lake"></path>` : ""}
      ${zl}${grat}${dots}
      <path d="${pts}" class="roadcase"></path><path d="${pts}" class="road"></path>
      ${wetPath ? `<path d="${wetPath}" class="searoad"></path>` : ""}
      ${names}${stops}${ends}${scalebar}
    </svg>`;
  wireStops();
}

/* ---------- gestures ---------- */
function zoomBy(f, px, py){
  const host = $("mapsvg"); if (!host) return;
  const rect = host.getBoundingClientRect();
  const W = MAPW, H = MAPH, k = W / MAP.span;
  const ux = px === undefined ? W/2 : (px - rect.left) * W / rect.width;
  const uy = py === undefined ? H/2 : (py - rect.top)  * W / rect.width;
  const wx = MAP.cx + (ux - W/2)/k, wy = MAP.cy - (uy - H/2)/k;
  MAP.span *= f;
  clampView(MAP);
  const k2 = W / MAP.span;
  MAP.cx = wx - (ux - W/2)/k2;
  MAP.cy = wy + (uy - H/2)/k2;
  clampView(MAP);
  scheduleMap();
}

let mapFrame = null;
function scheduleMap(){
  if (mapFrame) return;
  mapFrame = requestAnimationFrame(()=>{ mapFrame = null; drawMap(); });
}

function wireChart(){
  const host = $("mapsvg"); if (!host) return;
  host.addEventListener("wheel", e=>{
    e.preventDefault();
    zoomBy(Math.exp(e.deltaY * 0.0016), e.clientX, e.clientY);
  }, {passive:false});

  let drag = null;
  /* Every finger and the mouse arrive as pointers. One of them drags the map;
     two of them pinch it, which on a phone is what the scroll wheel is on a
     desk — so the live ones are tracked rather than just the first. */
  const live = new Map();

  const pinchState = () => {
    const pts = [...live.values()];
    const dx = pts[0].x - pts[1].x, dy = pts[0].y - pts[1].y;
    return {dist:Math.hypot(dx, dy) || 1,
            mx:(pts[0].x + pts[1].x)/2, my:(pts[0].y + pts[1].y)/2};
  };
  let pinch = null;

  host.addEventListener("pointerdown", e=>{
    if (e.target.closest(".stop")) return;
    live.set(e.pointerId, {x:e.clientX, y:e.clientY});
    host.setPointerCapture(e.pointerId);
    if (live.size === 2){
      drag = null; host.classList.remove("grabbing");
      pinch = {...pinchState(), span:MAP.span};
    } else if (live.size === 1){
      drag = {x:e.clientX, y:e.clientY, cx:MAP.cx, cy:MAP.cy};
      host.classList.add("grabbing");
    }
  });
  host.addEventListener("pointermove", e=>{
    if (live.has(e.pointerId)) live.set(e.pointerId, {x:e.clientX, y:e.clientY});
    if (pinch && live.size === 2){
      const now = pinchState();
      const want = pinch.span * (pinch.dist / now.dist);
      const rect = host.getBoundingClientRect(), k = MAPW / MAP.span;
      const ux = (now.mx - rect.left) * MAPW / rect.width;
      const uy = (now.my - rect.top)  * MAPW / rect.width;
      const wx = MAP.cx + (ux - MAPW/2)/k, wy = MAP.cy - (uy - MAPH/2)/k;
      MAP.span = want; clampView(MAP);
      const k2 = MAPW / MAP.span;
      MAP.cx = wx - (ux - MAPW/2)/k2; MAP.cy = wy + (uy - MAPH/2)/k2;
      clampView(MAP); scheduleMap();
      return;
    }
    if (!drag) return;
    const rect = host.getBoundingClientRect(), k = MAPW / MAP.span;
    const ux = (e.clientX - drag.x) * MAPW / rect.width;
    const uy = (e.clientY - drag.y) * MAPW / rect.width;
    MAP.cx = drag.cx - ux/k; MAP.cy = drag.cy + uy/k;
    clampView(MAP); scheduleMap();
  });
  const stop = e=>{
    live.delete(e.pointerId);
    if (live.size < 2) pinch = null;
    if (live.size === 1){
      /* one finger lifted mid-pinch: carry on panning from where the other is */
      const [only] = [...live.values()];
      drag = {x:only.x, y:only.y, cx:MAP.cx, cy:MAP.cy};
    }
    if (!live.size && drag){ drag = null; host.classList.remove("grabbing"); }
    try{ host.releasePointerCapture(e.pointerId); }catch(_){}
  };
  host.addEventListener("pointerup", stop);
  host.addEventListener("pointercancel", stop);
  host.addEventListener("dblclick", e=>{ e.preventDefault(); zoomBy(0.55, e.clientX, e.clientY); });

  $("zin").onclick  = ()=> zoomBy(0.62);
  $("zout").onclick = ()=> zoomBy(1/0.62);
  $("zfit").onclick = ()=> { MAP = fitToRoute(MAPR); scheduleMap(); };
}

/* ---------- the shell, and the link to the itinerary ---------- */
function mapShell(r, cfg){
  return `<div class="mapwrap">
    <div id="mapsvg" class="mapsvg"></div>
    <div class="mapctl">
      <button type="button" id="zin"  aria-label="Zoom in">+</button>
      <button type="button" id="zout" aria-label="Zoom out">&minus;</button>
      <button type="button" id="zfit" aria-label="Fit the whole route">⤢</button>
    </div>
    <div class="maptip" id="maptip" hidden></div>
    <p class="mapnote">Web Mercator (EPSG:3857). The coastline is Natural Earth's, generalised to about six
      kilometres; the ground inside it is painted straight from the terrain grid the reckoning walks over — a tenth
      of a degree, near enough eleven kilometres — so the colours are the ground that was actually counted, not a
      picture laid over it. Every dot on the road is a night's end${r.sim.rest ? `, and the ringed ones are forced halts` : ``}.
      ${NARROW ? `Drag to pan, pinch to zoom, tap a dot to find it in the itinerary.`
                : `Drag to pan, scroll or double-click to zoom, hover or tab a dot to find it in the itinerary.`}
      ${r.seaKm ? `The dashed stretches are under sail.` : ``}
      ${cfg.scale > 1.001 ? `Distances are reckoned at ×${cfg.scale.toFixed(2)}, so the road is longer than the scale bar suggests.` : ``}</p>
  </div>`;
}

function wireStops(){
  const tip = $("maptip"), wrap = document.querySelector(".mapwrap");
  if (!wrap || !MAPR) return;
  const byDay = {}; MAPR.sim.days.forEach(d=>byDay[d.day] = d);
  const show = (day, ev) => {
    const d = byDay[day]; if (!d) return;
    document.querySelectorAll("[data-day]").forEach(el=>
      el.classList.toggle("lit", el.dataset.day === String(day)));
    tip.hidden = false;
    tip.innerHTML = d.kind === "rest"
      ? `<b>Day ${d.day}</b> forced halt<br><span>${esc(d.camp)}</span>`
      : `<b>Day ${d.day}</b> ${Math.round(d.km)} km in ${d.hours.toFixed(1)} h<br>
         <span>${esc(d.zones[d.zones.length-1]||"")} &middot; ${d.campKm<=12?esc(d.camp):`${d.campKm} km from ${esc(d.camp)}`}</span>`;
    const box = wrap.getBoundingClientRect();
    const px = ev ? ev.clientX - box.left : box.width/2;
    const py = ev ? ev.clientY - box.top : 30;
    tip.style.left = Math.max(8, Math.min(box.width - 8 - tip.offsetWidth, px - tip.offsetWidth/2)) + "px";
    tip.style.top  = Math.max(4, py - tip.offsetHeight - 14) + "px";
  };
  const hide = () => { tip.hidden = true;
    document.querySelectorAll("[data-day].lit").forEach(el=>el.classList.remove("lit")); };
  wrap.querySelectorAll(".stop").forEach(g=>{
    g.addEventListener("mousemove", e=>show(g.dataset.day, e));
    g.addEventListener("mouseleave", hide);
    g.addEventListener("focus", ()=>show(g.dataset.day, null));
    g.addEventListener("blur", hide);
  });
  document.querySelectorAll("tr[data-day]").forEach(tr=>{
    tr.addEventListener("mouseenter", ()=>document.querySelectorAll("[data-day]").forEach(el=>
      el.classList.toggle("lit", el.dataset.day === tr.dataset.day)));
    tr.addEventListener("mouseleave", hide);
  });
}

/* called by render() once the results HTML is in the DOM */
function mountMap(r, cfg){
  const key = [cfg.from, cfg.to, cfg.via.join("|"), cfg.scale].join("::");
  MAPR = r; MAPCFG = cfg;
  if (!MAP || key !== MAPKEY){ MAP = fitToRoute(r); MAPKEY = key; }
  else clampView(MAP);
  drawMap();
  wireChart();
}
