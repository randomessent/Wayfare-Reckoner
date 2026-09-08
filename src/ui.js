/* ---------- ui ---------- */
const $ = id => document.getElementById(id);
const out = $("out");
window.addEventListener("resize", ()=>{ clearTimeout(window.__rz); window.__rz = setTimeout(render, 220); });
let restVal = "medium", regVal = "chronicle", nightTouched = false;

/* ---------- typeahead ---------- */
const KIND_LABEL = {city:"town", town:"town", range:"range", park:"park", forest:"forest",
                    pass:"pass", water:"water", plain:"plain", coast:"coast", custom:"yours"};

function attachTypeahead(id){
  const input = $(id), list = $(id + "-opts");
  let items = [], active = -1;

  const close = () => { list.hidden = true; input.setAttribute("aria-expanded","false"); active = -1; };
  const paint = () => {
    [...list.children].forEach((li,i)=>li.setAttribute("aria-selected", String(i===active)));
    if (active >= 0 && list.children[active]) list.children[active].scrollIntoView({block:"nearest"});
  };
  const term = () => {
    const v = input.value;
    if (id !== "via") return v;
    const parts = v.includes(";") ? v.split(";") : [v];
    return parts[parts.length-1].trim();
  };
  const choose = (name) => {
    if (id === "via" && input.value.includes(";")){
      const parts = input.value.split(";");
      parts[parts.length-1] = " " + name;
      input.value = parts.join(";");
    } else input.value = name;
    close(); render();
  };

  const open = () => {
    const q = term();
    if (!q.trim()){ close(); return; }
    const c = parseCoords(q);
    items = c ? [] : searchPlaces(q, 8);
    if (c){
      list.innerHTML = `<li role="option" data-v="${esc(q)}"><span class="nm">${c.label||"These coordinates"}</span>
        <span class="rg"><b>coordinates</b> &middot; ${c.lat.toFixed(3)}, ${c.lon.toFixed(3)} &middot; ${esc(zoneAt(c.lat,c.lon)[0])}</span></li>`;
      items = [q];
    } else if (items.length){
      list.innerHTML = items.map(n=>{
        const p = placeInfo(n);
        if (!p) return `<li role="option" data-v="${esc(n)}"><span class="nm">${esc(n)}</span></li>`;
        const size = p.pop >= 1000 ? ` &middot; ${p.pop.toLocaleString()}` : "";
        return `<li role="option" data-v="${esc(n)}"><span class="nm">${esc(n)}</span>
          <span class="rg"><b>${KIND_LABEL[p.kind]||p.kind}</b> &middot; ${esc(p.region)}${size}</span></li>`;
      }).join("");
    } else {
      list.innerHTML = `<li class="none">Nothing by that name. Coordinates always work — try <span class="mono">40.66, -4.70</span>.</li>`;
    }
    list.hidden = false; input.setAttribute("aria-expanded","true"); active = -1; paint();
  };

  input.addEventListener("input", open);
  input.addEventListener("focus", open);
  input.addEventListener("blur", ()=>setTimeout(close, 140));
  input.addEventListener("keydown", e=>{
    if (list.hidden || !items.length){
      if (e.key === "ArrowDown") open();
      return;
    }
    if (e.key === "ArrowDown"){ e.preventDefault(); active = (active+1) % items.length; paint(); }
    else if (e.key === "ArrowUp"){ e.preventDefault(); active = (active-1+items.length) % items.length; paint(); }
    else if (e.key === "Enter" && active >= 0){ e.preventDefault(); choose(items[active]); }
    else if (e.key === "Escape") close();
  });
  list.addEventListener("mousedown", e=>{
    const li = e.target.closest("li[data-v]");
    if (li){ e.preventDefault(); choose(li.dataset.v); }
  });
}
["from","to","via"].forEach(attachTypeahead);

/* ---------- places of your own ---------- */
function paintMine(){
  const mine = customPlaces().sort((a,b)=>a.name.localeCompare(b.name));
  $("mine").innerHTML = mine.length
    ? mine.map(c=>`<div class="row"><span>${esc(c.name)} <span class="mono" style="color:var(--ink-faint)">${c.lat.toFixed(2)}, ${c.lon.toFixed(2)}</span></span>
        <button type="button" data-rm="${esc(c.name)}" aria-label="Remove ${esc(c.name)}">&times;</button></div>`).join("")
    : "";
}
function checkAdd(){
  const ok = $("newname").value.trim() && !isNaN(parseFloat($("newlat").value)) && !isNaN(parseFloat($("newlon").value));
  $("addplace").disabled = !ok;
}
["newname","newlat","newlon"].forEach(id=>$(id).addEventListener("input", checkAdd));
$("addplace").addEventListener("click", ()=>{
  const name = $("newname").value.trim();
  const lat = parseFloat($("newlat").value), lon = parseFloat($("newlon").value);
  if (!name || isNaN(lat) || isNaN(lon)) return;
  addCustomPlace(name, Math.max(-90,Math.min(90,lat)), Math.max(-180,Math.min(180,lon)));
  $("newname").value = $("newlat").value = $("newlon").value = "";
  checkAdd(); paintMine(); render();
});
$("mine").addEventListener("click", e=>{
  const b = e.target.closest("button[data-rm]");
  if (b){ removeCustomPlace(b.dataset.rm); paintMine(); render(); }
});
paintMine();

function splitVia(v){
  if (!v.trim()) return [];
  if (v.includes(";")) return v.split(";").map(s=>s.trim()).filter(Boolean);
  // no semicolon: split on commas, but keep "lat, lon" pairs together
  const parts = v.split(",").map(s=>s.trim()).filter(Boolean), out = [];
  for (let i=0;i<parts.length;i++){
    const pair = parts[i] + ", " + (parts[i+1]||"");
    if (parts[i+1] && parseCoords(pair)){ out.push(pair); i++; }
    else out.push(parts[i]);
  }
  return out;
}

function fmtDH(h){
  let d = Math.floor(h/24), r = h - d*24;
  if (r > 23.949){ d += 1; r = 0; }
  if (d && r >= 0.05) return `${d} day${d!==1?"s":""}, ${r.toFixed(1)} hours`;
  if (d) return `${d} day${d!==1?"s":""}`;
  return `${r.toFixed(1)} hours`;
}
function bigDH(h){
  let d = Math.floor(h/24), r = Math.round(h - d*24);
  if (r >= 24){ d += 1; r = 0; }          // 23.7 h must not print as "24 h"
  return d ? `${d}<em> day${d!==1?"s":""}</em> ${r}<em> h</em>`
           : `${h.toFixed(1)}<em> hours</em>`;
}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}

function readConfig(){
  const [hh,mm] = $("depart").value.split(":").map(Number);
  return {
    from: $("from").value, to: $("to").value,
    via: splitVia($("via").value),
    mode: $("mode").value, rest: restVal, register: regVal,
    scale: parseFloat($("scale").value), weather: $("weather").value,
    season: $("season").value, roads: $("roads").value, mount: $("mount").value,
    hazard: $("hazard").value, boat: $("boat").value,
    party: Math.max(1, parseInt($("party").value)||1),
    departHour: (hh||0) + (mm||0)/60,
    depart: $("depart").value || "06:00",
    night: nightTouched ? $("night").checked : null,
  };
}

function strip(r){
  const days = r.sim.days, total = r.sim.total;
  const W = Math.max(980, days.length*30), H = 108;
  const y = 22, h = 30, pad = 10;
  const iw = W - pad*2;
  let x = 0, bars = "";
  for (const s of r.segs){
    const w = s.km/total*iw;
    bars += `<rect x="${(pad+x).toFixed(2)}" y="${y}" width="${Math.max(w,0.4).toFixed(2)}" height="${h}" style="fill:var(--${TERRAIN[s.terrain].t})"></rect>`;
    x += w;
  }
  let ticks = "", labels = "", marks = "";
  // rest days cover no ground, so they share a tick position with the day
  // before — draw them as a dot only, and number the marching days
  const march = days.filter(d => d.kind !== "rest");
  const every = march.length > 26 ? Math.ceil(march.length/13) : (march.length > 13 ? 2 : 1);
  for (const d of days) if (d.kind === "rest")
    marks += `<circle cx="${(pad + d.cum/total*iw).toFixed(2)}" cy="${y-7}" r="3" style="fill:var(--warn)"></circle>`;
  march.forEach((d,i)=>{
    const px = pad + d.cum/total*iw;
    const major = (i===march.length-1) || (i % every === 0);
    ticks += `<line x1="${px.toFixed(2)}" y1="${y}" x2="${px.toFixed(2)}" y2="${y+h+(major?7:4)}" style="stroke:var(--surface);stroke-width:1"></line>`;
    if (major){
      ticks += `<line x1="${px.toFixed(2)}" y1="${y+h}" x2="${px.toFixed(2)}" y2="${y+h+7}" style="stroke:var(--ink-faint);stroke-width:1"></line>`;
      const anchor = i===march.length-1 ? "end" : (i===0 ? "start" : "middle");
      labels += `<text x="${px.toFixed(2)}" y="${y+h+20}" text-anchor="${anchor}" style="fill:var(--ink-faint);font-family:'IBM Plex Mono',monospace;font-size:9.5px">${d.day}</text>`;
    }
  });
  const startName = esc(r.nodes[0].name), endName = esc(r.nodes[r.nodes.length-1].name);
  const heads = `<text x="${pad}" y="14" style="fill:var(--ink);font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.08em">${startName.toUpperCase()}</text>`
    + `<text x="${W-pad}" y="14" text-anchor="end" style="fill:var(--ink);font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.08em">${endName.toUpperCase()}</text>`;
  const foot = `<text x="${pad}" y="${y+h+34}" style="fill:var(--ink-faint);font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.14em">DAY</text>`;
  return `<div class="stripwrap"><svg class="strip-anim" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Route strip from ${startName} to ${endName}, coloured by terrain with a tick for each day's end.">${bars}${ticks}${marks}${heads}${labels}${foot}</svg></div>`;
}

function legend(r){
  const seen = new Map();
  for (const z of r.zones) if (!seen.has(z.terrain)) seen.set(z.terrain, TERRAIN[z.terrain]);
  return `<div class="legend">` + [...seen].map(([k,v])=>
    `<span><i style="background:var(--${v.t})"></i>${esc(v.label)}</span>`).join("") +
    (r.sim.rest ? `<span><i style="background:var(--warn);border-radius:50%;width:9px"></i>forced halt</span>` : "") +
    `</div>`;
}

function notes(r,cfg){
  const n = [];
  if (r.blocked)
    n.push(["warn",`<b style="font-weight:500">There is no way round.</b> Open water lies across this journey and
      the party has nothing to cross it in, so the figures above are for the straight line only —
      not a journey anyone could make. Give them ferries or a ship.`]);
  if (r.seaKm)
    n.push(["",`${Math.round(r.seaKm)} km of this journey is on the water, in ${r.embarkations}
      crossing${r.embarkations!==1?"s":""}. A boat sails through the night, so those days run to 20 hours;
      the ${r.embarkHours} h added is waiting on a tide and a boatman.`]);
  const hard = r.zones.filter(z=>["mountain","high_mountain"].includes(z.terrain));
  const hardPct = hard.reduce((s,z)=>s+z.pct,0);
  if (hardPct > 25 && !cfg.via.length)
    n.push(["warn",`${Math.round(hardPct)}% of this line runs through ${hard.map(z=>z.zone).join(" and ")}. A real traveller would look for a way round — try naming valley towns under <em>by way of</em>.`]);
  if (cfg.season==="winter" && r.zones.some(z=>z.terrain==="high_mountain"))
    n.push(["warn","Winter closes the high passes. The figures assume they get through at all."]);
  if (r.sim.rest)
    n.push(["warn",`${r.sim.rest} forced halt${r.sim.rest!==1?"s":""} — at this pace the ${cfg.mode.startsWith("horse")?"horses":"party"} cannot keep going without a day down.`]);
  if (r.sim.nightHours > 1)
    n.push(["",`${r.sim.nightHours.toFixed(0)} hours of this journey are travelled in darkness, at a little over half daylight speed.`]);
  if (WEATHER[cfg.weather].halt > 0)
    n.push(["",`${WEATHER[cfg.weather].label.replace(/^./,c=>c.toUpperCase())} is expected to pin them down about ${r.sim.haltDays.toFixed(1)} day${r.sim.haltDays.toFixed(1)==="1.0"?"":"s"} outright.`]);
  if (r.hazardDays > 0)
    n.push(["",`${r.hazardUsed.replace(/^./,c=>c.toUpperCase())} hazard adds roughly ${r.hazardDays.toFixed(1)} days of delay — a lamed horse, a washed-out ford, a lord's toll.`]);
  if (r.hazardForced)
    n.push(["",`${REGISTERS[cfg.register].label} sets a floor of ${r.hazardUsed} hazard: in this register something is always out there.`]);
  if (cfg.scale > 1.001)
    n.push(["",`The world is set ×${cfg.scale.toFixed(2)} the size of ours, so ${Math.round(r.gc)} km of crow flight stands in for ${Math.round(r.gc/cfg.scale)} km on a modern map.`]);
  if (WEATHER[cfg.weather].halt >= 0.04 && r.sim.marching > 5)
    n.push(["",`This weather is applied to every day of the journey. Weeks of unbroken ${esc(WEATHER[cfg.weather].label)} is a hard assumption — for a front that passes, take the fair-weather figure and add the bad days.`]);
  if (cfg.party > 30)
    n.push(["",`${cfg.party} travellers move as a column: ${r.sim.plabel}, at the pace of the slowest element.`]);
  if (!n.length) return "";
  return `<section><h2>What to watch</h2><div class="notes">` +
    n.map(([c,t])=>`<div class="n ${c}"><div>${t}</div></div>`).join("") + `</div></section>`;
}

function resolveSafe(v){ try { resolve(v); return true; } catch(e){ return false; } }

function render(){
  const cfg = readConfig();
  const rg = REGISTERS[regVal];
  $("regnote").textContent = rg.note;
  $("scaleval").textContent = cfg.scale === 1 ? "our map" : `\u00d7${cfg.scale.toFixed(2)} our map`;
  document.querySelectorAll("#mount option").forEach(o => {
    o.disabled = !rg.mounts.includes(o.value);
    o.textContent = o.textContent.replace(/ \u2014 .*$/, "") + (o.disabled ? " \u2014 not in this register" : "");
  });
  $("restnote").textContent = REGIMES[restVal].note;
  $("boatnote").textContent = BOATS[cfg.boat].note;

  const mt = MOUNTS[rg.mounts.includes(cfg.mount) ? cfg.mount : rg.mounts[rg.mounts.length-1]];
  $("mountnote").innerHTML = cfg.mode.startsWith("horse")
    ? `<b style="font-weight:500;color:var(--ink-soft)">${esc(mt.like)}</b> \u2014 ${esc(mt.lore)}`
    : "Mounts only matter on horseback.";

  /* The night box is real or it is decoration, and which one depends on the
     pace, the mode and how much daylight the season gives. When it cannot
     change the answer it is stood down rather than left to be clicked in
     vain — and comes back the moment the days get short enough to matter. */
  if (!nightTouched) $("night").checked = REGIMES[restVal].night;
  const dayHours = Math.min(REGIMES[restVal].hours, MODES[cfg.mode].max);
  const light = daylight((resolveSafe(cfg.from) ? resolve(cfg.from).lat : 45), SEASONS[cfg.season]);
  const moot = dayHours <= light - 0.2;
  $("night").disabled = moot;
  $("night").closest(".chk").classList.toggle("off", moot);
  $("nightlabel").textContent = moot ? "Travel through the night (nothing to decide here)"
    : nightTouched ? "Travel through the night"
    : `Travel through the night (${REGIMES[restVal].night ? "on" : "off"} at this pace)`;
  $("nightnote").textContent = moot
    ? `Moot here: ${dayHours} h on the move fits inside ${light.toFixed(1)} h of ${cfg.season} daylight, `
      + `so they stop before dusk either way. It bites when the day is longer than the light — `
      + `a driven pace, a winter journey, or somewhere far north.`
    : `${(dayHours - light).toFixed(1)} h of this day fall after dark — travelled at little over half speed if allowed, `
      + `and waited out until dawn if not.`;

  /* Nothing to reckon yet. An error panel would be a lie — the traveller has
     not asked for anything wrong, only not asked yet — so say so kindly and
     offer a road to start on. */
  if (!cfg.from.trim() || !cfg.to.trim()){
    MAPR = null; MAP = null; MAPKEY = "";
    const missing = !cfg.from.trim() && !cfg.to.trim() ? "Both ends are still open"
                  : !cfg.from.trim() ? "No starting place yet" : "No destination yet";
    out.innerHTML = `<div class="blank">
      <h2>Every journey wants two ends</h2>
      <p>${missing}. Name where they set out and where they are bound, and the
      reckoning will find a way over the ground between — round the seas, along the
      valleys, and out the far side with a count of the days.</p>
      <div class="egs">
        ${[["Lyon","Zagreb"],["Sierra de Gredos","Burgos"],["Raleigh","Santa Fe, New Mexico"],
           ["Samarkand","Kashgar"],["Cairo","Timbuktu"]]
          .map(([a,b])=>`<button type="button" data-a="${esc(a)}" data-b="${esc(b)}">${esc(a)} &rarr; ${esc(b)}</button>`).join("")}
      </div>
    </div>`;
    out.querySelectorAll(".egs button").forEach(btn=>btn.addEventListener("click",()=>{
      $("from").value = btn.dataset.a; $("to").value = btn.dataset.b; render();
    }));
    return;
  }

  let r;
  try { r = reckon(cfg); }
  catch (e) {
    const sug = (e.suggestions || []);
    out.innerHTML = `<div class="err">
      <b>No place matching “${esc(e.query || e.message)}”.</b>
      The gazetteer holds ${PLACE_COUNT.toLocaleString()} settlements, ranges, forests, passes and parks.
      For anywhere else — or anywhere invented — give coordinates like
      <span class="mono">40.66, -4.70</span>, or save it under <em>add a place of your own</em>.
      ${sug.length ? `<div class="chips">${sug.map(s=>`<button type="button" data-sug="${esc(s)}">${esc(s)}</button>`).join("")}</div>` : ""}
    </div>`;
    out.querySelectorAll("button[data-sug]").forEach(btn=>btn.addEventListener("click",()=>{
      const field = resolveSafe($("from").value) ? (resolveSafe($("to").value) ? "via" : "to") : "from";
      $(field).value = btn.dataset.sug; render();
    }));
    return;
  }
  if (r.mountForced) $("mount").value = r.mountUsed;   // never show a mount the register forbids
  const names = r.nodes.map(n=>esc(n.name));
  const detour = r.sim.total / r.gc;
  const arrAbs = cfg.departHour + r.expected;
  const arrDay = Math.floor(arrAbs/24) + 1;
  const arrClock = `${String(Math.floor(arrAbs%24)).padStart(2,"0")}:${String(Math.round((arrAbs%24%1)*60)%60).padStart(2,"0")}`;
  const avg = r.sim.total / Math.max(1, r.sim.marching);

  out.innerHTML = `
  <div class="verdict">
    <div class="route">${names.join(" &rarr; ")}</div>
    <div class="band" style="font-size:12px;color:var(--ink-faint)">${
      r.nodes.map(n=>`${esc(n.name)} <span style="opacity:.75">${esc(n.region)}</span>`).join(" &nbsp;·&nbsp; ")}</div>
    <div class="figure">${bigDH(r.expected)}</div>
    <div class="band">${r.extra > 0.02 ? `Best case <b>${fmtDH(r.best)}</b> &middot; with bad luck <b>${fmtDH(r.worst)}</b> &middot; ` : ""}${cfg.party} travelling ${esc(MODES[cfg.mode].label)} at a ${REGIMES[cfg.rest].label.toLowerCase()} pace<br>
      <span style="color:var(--ink-faint)">${rg.label} register &middot; ${cfg.scale>1.001?`a world &times;${cfg.scale.toFixed(2)} the size of ours`:"our own map"} &middot; ${esc(MOUNTS[r.mountUsed].label)} mounts${r.extra > 0.02 ? "" : " &middot; nothing set to go wrong"}<br>
      Leaving at ${cfg.depart}, they arrive on <b style="font-weight:500;color:var(--ink-soft)">day ${arrDay} around ${arrClock}</b>.</span></div>
  </div>

  <div class="stats">
    <div class="stat"><div class="k">Crow flight</div><div class="v">${Math.round(r.gc)}<small> km</small></div></div>
    <div class="stat"><div class="k">Ground covered</div><div class="v">${Math.round(r.sim.total)}<small> km</small></div></div>
    <div class="stat"><div class="k">Detour</div><div class="v">&times;${detour.toFixed(2)}</div></div>
    <div class="stat"><div class="k">Marching days</div><div class="v">${r.sim.marching}${r.sim.rest?`<small> + ${r.sim.rest} halt</small>`:""}</div></div>
    <div class="stat"><div class="k">Day’s march</div><div class="v">${avg.toFixed(0)}<small> km</small></div></div>
    <div class="stat"><div class="k">Moving pace</div><div class="v">${r.sim.pace.toFixed(1)}<small> km/h</small></div></div>
    <div class="stat"><div class="k">On the move</div><div class="v">${r.sim.budget.toFixed(1)}<small> /day</small></div></div>
    ${r.seaKm ? `<div class="stat"><div class="k">At sea</div><div class="v">${Math.round(r.seaKm)}<small> km</small></div></div>` : ""}
    <div class="stat"><div class="k">Daylight</div><div class="v">${r.sim.dl.toFixed(1)}<small> h</small></div></div>

  </div>

  <section><h2>The route</h2>${mapShell(r, cfg)}</section>

  <section><h2>The road, day by day</h2>${strip(r)}${legend(r)}</section>

  <section><h2>Ground crossed</h2><div class="share">${
    r.zones.map(z=>`<div class="line">
      <span>${esc(z.zone)}</span>
      <span class="barwrap"><span class="bar" style="width:${z.pct.toFixed(1)}%;background:var(--${TERRAIN[z.terrain].t})"></span></span>
      <span class="amt">${Math.round(z.km)} km · ${Math.round(z.pct)}%</span>
    </div>`).join("")}</div></section>

  ${notes(r,cfg)}

  <section><h2>Itinerary</h2><div class="tablewrap"><table>
    <thead><tr><th>Day</th><th class="num">Km</th><th class="num">Hours</th><th>Night's end</th><th>Through</th><th class="num">Done</th></tr></thead>
    <tbody>${r.sim.days.map(d=>{
      if (d.kind==="rest") return `<tr class="halt" data-day="${d.day}"><td class="num">${d.day}</td><td class="num">—</td><td class="num">—</td>
        <td colspan="2">${esc(d.note)}</td><td class="num">${Math.round(100*d.cum/r.sim.total)}%</td></tr>`;
      const where = d.campKm<=12 ? esc(d.camp)
        : d.campKm<=45 ? `near ${esc(d.camp)}`
        : `${esc(d.zones[d.zones.length-1]||"open country")} — ${d.campKm} km from ${esc(d.camp)}`;
      return `<tr data-day="${d.day}"><td class="num">${d.day}</td><td class="num">${d.km.toFixed(0)}</td><td class="num">${d.hours.toFixed(1)}</td>
        <td>${where}</td><td class="terr">${d.zones.map(esc).join(", ")}</td>
        <td class="num">${Math.round(100*d.cum/r.sim.total)}%</td></tr>`;
    }).join("")}</tbody>
  </table></div></section>

  <footer>Distances are great-circle lines between town centres, stretched by a sinuosity factor for country where nothing runs straight. Paces are kilometres per hour of actual movement — halts, meals and camp are handled by the rest regime, not folded into the speed. Figures are tuned against documented pre-modern rates: a Roman <em>iter iustum</em> of 30 km, Sigeric's 79-stage walk from Rome to Canterbury at 25 km a day, mounted travel at 50–70 km a day, ox-carts at 25–35. The way across the ground is found by search over a quarter-degree land mask, so a
    party walks round a sea rather than over it. Plausible for fiction; not survey data. Round them in prose.</footer>`;

  mountMap(r, cfg);
}

document.querySelectorAll("#register button").forEach(b=>{
  b.addEventListener("click",()=>{
    regVal = b.dataset.v;
    document.querySelectorAll("#register button").forEach(x=>x.setAttribute("aria-pressed", String(x===b)));
    render();
  });
});
$("scale").addEventListener("input",render);
document.querySelectorAll("#rest button").forEach(b=>{
  b.addEventListener("click",()=>{
    restVal = b.dataset.v;
    document.querySelectorAll("#rest button").forEach(x=>x.setAttribute("aria-pressed", String(x===b)));
    nightTouched = false;
    render();
  });
});
$("night").addEventListener("change",()=>{ nightTouched = true; render(); });

/* Start afresh. The defaults are whatever the markup shipped with, captured
   before anyone has touched anything, so there is no second list of them to
   fall out of step with the first. */
const FIELDS = ["from","to","via","mode","party","mount","depart","roads","season",
                "hazard","weather","boat","scale"];
const DEFAULTS = {};
for (const id of FIELDS) DEFAULTS[id] = $(id).value;
const DEFAULT_NIGHT = $("night").checked;

$("reset").addEventListener("click", ()=>{
  for (const id of FIELDS) $(id).value = DEFAULTS[id];
  $("night").checked = DEFAULT_NIGHT;
  nightTouched = false;
  restVal = "medium"; regVal = "chronicle";
  document.querySelectorAll("#rest button")
    .forEach(x=>x.setAttribute("aria-pressed", String(x.dataset.v === restVal)));
  document.querySelectorAll("#register button")
    .forEach(x=>x.setAttribute("aria-pressed", String(x.dataset.v === regVal)));
  MAPR = null; MAP = null; MAPKEY = "";
  render();
  $("from").focus();
});
["from","to","via","mode","party","mount","depart","roads","season","hazard","weather","boat"]
  .forEach(id=>{ $(id).addEventListener("input",render); $(id).addEventListener("change",render); });
render();
