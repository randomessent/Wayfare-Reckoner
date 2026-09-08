/* ---------- model tables (mirror of scripts/wayfare.py) ---------- */
const TERRAIN = {
  plain:          {label:"open plain",        sin:1.14, spd:1.00, exp:1.10, t:"t2"},
  farmland:       {label:"settled farmland",  sin:1.16, spd:1.00, exp:1.15, t:"t2"},
  river_plain:    {label:"river plain",       sin:1.13, spd:1.02, exp:1.20, t:"t1"},
  river_valley:   {label:"river valley road", sin:1.12, spd:1.03, exp:0.95, t:"t1"},
  steppe_plain:   {label:"grass steppe",      sin:1.12, spd:1.00, exp:1.15, t:"t2"},
  steppe_plateau: {label:"arid plateau",      sin:1.16, spd:0.95, exp:1.05, t:"t2"},
  coastal:        {label:"coastal lowland",   sin:1.22, spd:0.94, exp:1.05, t:"t2"},
  coastal_karst:  {label:"karst coast",       sin:1.38, spd:0.72, exp:1.10, t:"t4"},
  hills:          {label:"rolling hills",     sin:1.24, spd:0.88, exp:1.00, t:"t3"},
  upland:         {label:"high moorland",     sin:1.32, spd:0.80, exp:1.25, t:"t4"},
  forest_plain:   {label:"lowland forest",    sin:1.24, spd:0.86, exp:0.85, t:"t3"},
  forest_hills:   {label:"wooded hills",      sin:1.32, spd:0.78, exp:0.90, t:"t4"},
  forest_upland:  {label:"forested uplands",  sin:1.38, spd:0.72, exp:0.95, t:"t4"},
  marsh_plain:    {label:"marsh and delta",   sin:1.34, spd:0.72, exp:1.45, t:"t3"},
  mountain:       {label:"mountains",         sin:1.55, spd:0.63, exp:1.30, t:"t5"},
  high_mountain:  {label:"high mountains",    sin:1.62, spd:0.55, exp:1.55, t:"t6"},
  savanna:        {label:"savanna",           sin:1.14, spd:0.98, exp:1.20, t:"t2"},
  desert:         {label:"desert",            sin:1.12, spd:0.90, exp:1.45, t:"t1"},
  sand_sea:       {label:"sand sea",          sin:1.30, spd:0.62, exp:1.60, t:"t1"},
  rainforest:     {label:"rainforest",        sin:1.45, spd:0.52, exp:0.90, t:"t5"},
  taiga:          {label:"boreal forest",     sin:1.35, spd:0.70, exp:1.15, t:"t4"},
  tundra:         {label:"tundra",            sin:1.25, spd:0.78, exp:1.50, t:"t2"},
  high_plateau:   {label:"high plateau",      sin:1.40, spd:0.58, exp:1.50, t:"t5"},
  open_water:     {label:"open water",        sin:1.02, spd:1.00, exp:1.30, t:"tw"},
};
const MODES = {
  foot:          {label:"on foot",                     pace:4.3, sus:8.0,  max:15.0, hardDays:8},
  foot_laden:    {label:"on foot with baggage",        pace:3.6, sus:7.5,  max:13.0, hardDays:7},
  horse:         {label:"on horseback",                pace:8.0, sus:9.0,  max:16.0, hardDays:6},
  horse_remount: {label:"on horseback with remounts",  pace:9.8, sus:10.0, max:18.0, hardDays:9},
  cart:          {label:"with carts",                  pace:3.2, sus:8.0,  max:12.0, hardDays:8},
};
const REGIMES = {
  high:   {label:"Unhurried", hours:6.0,  wander:1.06, night:false, fat:0.006,
           note:"Full night's sleep, a proper camp, meals, and time to look around."},
  medium: {label:"Purposeful", hours:8.0, wander:1.00, night:false, fat:0.006,
           note:"Seven hours' sleep, quick camp, halts only to water the animals and eat cold."},
  low:    {label:"Driven", hours:13.0,    wander:0.98, night:true,  fat:0.006,
           note:"Four or five hours' snatched sleep, night marching, no halt that isn't forced."},
};
const ROADS = {
  roads:      {label:"the old paved roads",        sin:0.90, spd:1.10},
  mixed:      {label:"main roads and cart trails", sin:1.00, spd:1.00},
  trails:     {label:"cart trails and drove roads",sin:1.08, spd:0.90},
  wilderness: {label:"pathless country",           sin:1.24, spd:0.70},
};
const WEATHER = {
  clear:{label:"clear",spd:1.00,halt:0}, overcast:{label:"grey and dry",spd:0.99,halt:0},
  wind:{label:"hard wind",spd:0.94,halt:0}, fog:{label:"fog",spd:0.80,halt:0.02},
  light_rain:{label:"intermittent rain",spd:0.93,halt:0}, heavy_rain:{label:"heavy rain",spd:0.74,halt:0.04},
  storm:{label:"storms",spd:0.55,halt:0.14}, heat:{label:"punishing heat",spd:0.85,halt:0.03},
  snow:{label:"snow",spd:0.58,halt:0.08}, deep_snow:{label:"deep snow",spd:0.34,halt:0.20},
};
const SEASONS = {spring:4.0, summer:21.0, autumn:-4.0, winter:-21.0};
/* Each tier has a horse everyone already knows, because "1.10x speed and an
   extra hour in the saddle" means nothing to a reader and Bucephalus does. */
const MOUNTS = {
  mundane:      {label:"ordinary stock", spd:0.94, hours:-1, like:"a Rocinante",
                 lore:"Don Quixote\u2019s bony nag: willing enough, and no more than that."},
  hardy:        {label:"endurance-bred", spd:1.00, hours:0,  like:"a Marengo",
                 lore:"Napoleon\u2019s grey Arabian, who carried him at Austerlitz and out of Russia."},
  exceptional:  {label:"exceptional bloodstock", spd:1.10, hours:1, like:"a Bucephalus",
                 lore:"Alexander\u2019s, whom no one else could ride, and who went as far as the Hydaspes."},
  otherworldly: {label:"otherworldly", spd:1.30, hours:3, like:"a Shadowfax",
                 lore:"Lord of horses, who bore no saddle and outran the wind."},
};
const HAZARD = {none:0, low:0.020, moderate:0.055, high:0.110};
const HAZARD_ORDER = ["none","low","moderate","high"];
const REGISTERS = {
  chronicle:{label:"Chronicle", wilderness:1.00, endurance:0.0, fatigue:1.00,
    floor:"none", mounts:["mundane","hardy"],
    note:"The land is as it is mapped and people tire on schedule. Nothing here a 12th-century itinerary could not vouch for."},
  romance:{label:"Romance", wilderness:1.06, endurance:0.5, fatigue:0.85,
    floor:"low", mounts:["mundane","hardy","exceptional"],
    note:"The wilds are deeper than the map admits and the roads less certain — but the people who cross them are built to."},
  saga:{label:"Saga", wilderness:1.14, endurance:1.5, fatigue:0.65,
    floor:"moderate", mounts:["mundane","hardy","exceptional","otherworldly"],
    note:"The map is a rumour. Forests run for weeks, the roads are older than anyone living, and these people do not tire like farmhands."},
};
const NIGHT_SPEED = 0.55, R = 6371.0;

/* ---------- geometry ---------- */
const rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI;
function hav(a1,o1,a2,o2){
  const p1=rad(a1),p2=rad(a2),dp=p2-p1,dl=rad(o2-o1);
  const h=Math.sin(dp/2)**2+Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)**2;
  return 2*R*Math.asin(Math.sqrt(h));
}
function lerpGC(a1,o1,a2,o2,f){
  const d=hav(a1,o1,a2,o2)/R;
  if(d<1e-9) return [a1,o1];
  const p1=rad(a1),l1=rad(o1),p2=rad(a2),l2=rad(o2);
  const A=Math.sin((1-f)*d)/Math.sin(d), B=Math.sin(f*d)/Math.sin(d);
  const x=A*Math.cos(p1)*Math.cos(l1)+B*Math.cos(p2)*Math.cos(l2);
  const y=A*Math.cos(p1)*Math.sin(l1)+B*Math.cos(p2)*Math.sin(l2);
  const z=A*Math.sin(p1)+B*Math.sin(p2);
  return [deg(Math.atan2(z,Math.hypot(x,y))), deg(Math.atan2(y,x))];
}
function daylight(lat,dec){
  const c=-Math.tan(rad(lat))*Math.tan(rad(dec));
  if(c<=-1) return 24; if(c>=1) return 0;
  return 2*deg(Math.acos(c))/15;
}
function partyFactor(n){
  if(n<=3) return [1.00,"a handful of travellers"];
  if(n<=10) return [0.97,"a small band"];
  if(n<=30) return [0.92,"a large company"];
  if(n<=100) return [0.85,"a small column"];
  return [0.78,"a host"];
}

/* ---------- route ---------- */
function terrainSpeed(lat,lon){ return TERRAIN[zoneAt(lat,lon)[1]].spd; }

function legSegments(a,b,cfg,allowWater){
  const A=[a.lat,a.lon], B=[b.lat,b.lon];
  const gc=hav(A[0],A[1],B[0],B[1]);
  const n=Math.max(10,Math.floor(gc/15));
  const road=ROADS[cfg.roads], wx=WEATHER[cfg.weather];
  const wander=REGIMES[cfg.rest].wander*REGISTERS[cfg.register].wilderness;
  const scale=cfg.scale;
  const winter=cfg.season==="winter", cart=cfg.mode==="cart";
  const segs=[];
  for(let i=0;i<n;i++){
    const p0=lerpGC(A[0],A[1],B[0],B[1],i/n), p1=lerpGC(A[0],A[1],B[0],B[1],(i+1)/n);
    const mid=lerpGC(A[0],A[1],B[0],B[1],(i+0.5)/n);
    // the router already proved a way over land, so water under a chord here
    // is the chart cutting the corner off a bay, not a real crossing
    const wet = allowWater && !isLandCell(...cellOf(mid[0],mid[1]));
    const [zl,tk] = wet ? ["Open Water","open_water"] : zoneAt(mid[0],mid[1]);
    const t=TERRAIN[tk];
    let sf=t.sin*road.sin*wander, sp=t.spd*road.spd;
    if(cart&&["mountain","high_mountain","marsh_plain","coastal_karst","forest_upland"].includes(tk)){sf*=1.30; sp*=0.70;}
    if(winter&&tk==="high_mountain"){sf*=1.15; sp*=0.68;}
    else if(winter&&tk==="mountain"){sp*=0.78;}
    sp*=Math.max(0.30,1-(1-wx.spd)*t.exp);
    sp=Math.max(0.20,sp);
    const gcl=hav(p0[0],p0[1],p1[0],p1[1]);
    if (wet){ sf = 1.02; sp = 1.0; }
    segs.push({zone:zl,terrain:tk,water:wet,gc:gcl*scale,km:gcl*sf*scale,sf:sp,
               lat0:p0[0],lon0:p0[1],lat1:p1[0],lon1:p1[1]});
  }
  return segs;
}
function buildRoute(points,cfg){
  const nodes=points.map(resolve);
  let gc=0, segs=[], blocked=false;
  for(let i=0;i<nodes.length-1;i++){
    const A=nodes[i], B=nodes[i+1];
    gc+=hav(A.lat,A.lon,B.lat,B.lon);
    const way=findWay([A.lat,A.lon],[B.lat,B.lon],cfg.boat,terrainSpeed);
    if(!way.ok) blocked=true;
    const allowWater = cfg.boat!=="none" || !way.ok;
    for(let k=0;k<way.pts.length-1;k++)
      segs=segs.concat(legSegments({lat:way.pts[k][0],lon:way.pts[k][1]},
                                   {lat:way.pts[k+1][0],lon:way.pts[k+1][1]},cfg,allowWater));
  }
  return {nodes,gc:gc*cfg.scale,segs,blocked};
}
function positionAt(segs,km){
  let acc=0;
  for(const s of segs){
    if(acc+s.km>=km){const f=s.km?(km-acc)/s.km:0; return lerpGC(s.lat0,s.lon0,s.lat1,s.lon1,f);}
    acc+=s.km;
  }
  const l=segs[segs.length-1]; return [l.lat1,l.lon1];
}

/* ---------- simulation ---------- */
function simulate(segs,cfg,meanLat){
  const mode=MODES[cfg.mode], reg=REGIMES[cfg.rest], rg=REGISTERS[cfg.register];
  const mounted=cfg.mode.startsWith("horse"), mt=MOUNTS[cfg.mount];
  const [pf,plabel]=partyFactor(cfg.party);
  const pace=mode.pace*pf*(mounted?mt.spd:1);
  const sus=mode.sus+(mounted?mt.hours:0)+rg.endurance;
  const budget=Math.min(reg.hours,mode.max);
  const nightOk=cfg.night===null?reg.night:cfg.night;
  const dl=daylight(meanLat,SEASONS[cfg.season]);
  const sunrise=12-dl/2, sunset=12+dl/2;

  const seaPace = BOATS[cfg.boat].seaPace || 5.0;
  let seaToday = 0, seaKm = 0;
  const total=segs.reduce((s,x)=>s+x.km,0);
  const hardDays = mode.hardDays + (cfg.register==="saga" ? 2 : cfg.register==="romance" ? 1 : 0);
  let t=cfg.departHour, start=t, done=0, si=0, segDone=0, fat=0, ht=0, strain=0;
  let nightHours=0, dayKm=0, dayZones=[], dayTerr=[], days=[], rest=0, guard=0;

  const closeDay=(kind="march")=>{
    const [la,lo]=positionAt(segs,done); const [pl,pd]=nearestPlace(la,lo);
    days.push({day:days.length+1,kind,km:dayKm,hours:ht,
               zones:[...new Set(dayZones)],terr:[...new Set(dayTerr)],
               camp:pl,campKm:Math.round(pd),fat,cum:done});
    dayKm=0; dayZones=[]; dayTerr=[]; ht=0;
  };

  while(done<total-1e-6 && guard<400000){
    guard++;
    const tod=((t%24)+24)%24;
    const isNight = tod<sunrise-1e-6 || tod>=sunset;
    if(ht===0 && isNight && !(nightOk || segs[si].water)){
      const nxt=(t-tod)+(tod<sunrise?sunrise:24+sunrise);
      t = nxt>t+1e-6 ? nxt : nxt+24;
      continue;
    }
    const atSea = segs[si].water;
    const budgetNow = atSea ? 20.0 : budget;
    if(ht>=budgetNow-1e-9 || (isNight && !(nightOk||atSea))){
      // a day mostly spent aboard costs the party nothing in legs
      const over = seaToday > ht/2 ? 0 : Math.max(0,ht-sus);
      fat+=over*reg.fat*rg.fatigue;
      // a night's sleep gives back a fixed amount plus a share of what's there,
      // so tiredness settles at a plateau instead of compounding into a halt
      fat=Math.max(0,Math.min(0.30,fat-0.010-0.15*fat));
      strain = over>0.25 ? strain+1 : 0;
      seaToday = 0;
      closeDay();
      if(strain>=hardDays){
        const [la,lo]=positionAt(segs,done); const [pl,pd]=nearestPlace(la,lo);
        days.push({day:days.length+1,kind:"rest",km:0,hours:0,zones:[],terr:[],
                   camp:pl,campKm:Math.round(pd),fat,cum:done,
                   note:mounted?"forced halt — the animals are spent":"forced halt — the party is spent"});
        fat*=0.30; strain=0; rest++; t+=24;
      }
      t=(t-(((t%24)+24)%24))+24+sunrise+1e-6;
      continue;
    }
    const seg=segs[si];
    let speed = seg.water ? seaPace
      : pace*seg.sf*(1-fat)*(isNight?NIGHT_SPEED:1);
    speed=Math.max(0.35,speed);
    let dt=Math.min(0.25,budgetNow-ht);
    if(dt<=1e-9) continue;
    let step=speed*dt;
    const rem=seg.km-segDone;
    if(step>=rem){
      step=rem; dt=speed?step/speed:0; segDone=0; dayZones.push(seg.zone); dayTerr.push(seg.terrain); si++;
      if(si>=segs.length){
        si=segs.length-1; done=total; ht+=dt; t+=dt;
        if(isNight) nightHours+=dt; dayKm+=step; break;
      }
    } else { segDone+=step; dayZones.push(seg.zone); dayTerr.push(seg.terrain); }
    done+=step; dayKm+=step; ht+=dt;
    if(seg.water){ seaToday+=dt; seaKm+=step; }
    if(isNight) nightHours+=dt; t+=dt;
  }
  if(dayKm>0||ht>0) closeDay();

  const marching=days.filter(d=>d.kind==="march").length;
  return {elapsed:t-start, marching, rest, days, pace, budget, sus, seaKm,
          nightHours, dl, sunrise, sunset, plabel, total,
          haltDays:marching*WEATHER[cfg.weather].halt};
}

/* ---------- reckon ---------- */
function reckon(cfg){
  const rg=REGISTERS[cfg.register];
  // the register decides which mounts are in the story, and floors the hazard
  cfg.mountUsed = rg.mounts.includes(cfg.mount) ? cfg.mount : rg.mounts[rg.mounts.length-1];
  cfg.hazardUsed = HAZARD_ORDER.indexOf(cfg.hazard) < HAZARD_ORDER.indexOf(rg.floor)
    ? rg.floor : cfg.hazard;
  const {nodes,gc,segs,blocked}=buildRoute([cfg.from,...cfg.via,cfg.to],cfg);
  const meanLat=(nodes[0].lat+nodes[nodes.length-1].lat)/2;
  const sim=simulate(segs,{...cfg,mount:cfg.mountUsed},meanLat);
  let embarkations = segs.length && segs[0].water ? 1 : 0;
  for (let i=1;i<segs.length;i++) if (segs[i].water && !segs[i-1].water) embarkations++;
  const embarkHours = embarkations * (BOATS[cfg.boat].embark || 0);
  sim.elapsed += embarkHours;
  const hazardDays=sim.marching*HAZARD[cfg.hazardUsed];
  const extra=sim.haltDays+hazardDays;
  const zones={};
  for(const s of segs){ zones[s.zone]=zones[s.zone]||{km:0,terrain:s.terrain}; zones[s.zone].km+=s.km; }
  return {
    nodes, gc, segs, sim, hazardDays, extra, register:rg, blocked,
    seaKm:sim.seaKm, embarkations, embarkHours,
    mountUsed:cfg.mountUsed, hazardUsed:cfg.hazardUsed,
    mountForced:cfg.mountUsed!==cfg.mount, hazardForced:cfg.hazardUsed!==cfg.hazard,
    best:sim.elapsed, expected:sim.elapsed+extra*24, worst:sim.elapsed+extra*48,
    zones:Object.entries(zones).map(([k,v])=>({zone:k,km:v.km,terrain:v.terrain,pct:100*v.km/sim.total}))
                .sort((a,b)=>b.km-a.km),
  };
}
