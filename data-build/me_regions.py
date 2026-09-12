"""Hand-drawn regions of Middle-earth: who the ground belongs to, and what it is.

The ME-GIS layers carry coastline, elevation, forests and marshes, but the
names of the countries are label points, not outlines. So the outlines are
drawn here, as they are for Europe in `regions.py` — generalised to within a
few tens of kilometres, which is the grain the travel model reasons at.

Coordinates are ME-GIS map kilometres (easting, northing), the same frame as
every layer in the shapefiles, so a polygon can be checked against the place
points directly: Hobbiton is at (516, 1044), Minas Tirith at (1111, 621).
`build_middle_earth.py` projects them onto the globe.

Each entry is (label, parent, terrain, [(x_km, y_km), ...]).

  label    the name a traveller would use for this ground
  parent   the wider country, for the "Province, Country" line under a place
  terrain  a biome override, or None to let elevation and the forest layer
           decide. "farmland" marks settled country; "steppe_plain" the great
           grasslands; "desert" the dry south; "high_plateau" Mordor's floor.

Smaller regions are painted over larger ones, so the Shire beats Eriador and
Gorgoroth beats Mordor whatever order they are written in.
"""

REGIONS = [
 # ── the north-west: Eriador and its parts ──
 ("Eriador", "", None, [
  (330,1420),(600,1440),(760,1420),(830,1380),(850,1250),(880,1100),(870,1000),
  (840,900),(760,850),(700,760),(560,760),(450,820),(380,900),(330,1000),(300,1150)]),
 ("Lindon", "", None, [
  (160,1420),(330,1420),(300,1150),(330,1000),(270,930),(190,900),(140,1000),(140,1250)]),
 ("Forlindon", "Lindon", None, [(160,1420),(330,1420),(300,1150),(340,1060),(230,1050),(150,1090),(140,1250)]),
 ("Harlindon", "Lindon", None, [(230,1040),(330,1040),(330,1000),(270,930),(190,900),(140,1000),(150,1040)]),
 ("Arthedain", "Eriador", None, [
  (440,1250),(700,1260),(730,1200),(700,1120),(640,1070),(560,1070),(470,1090),(430,1160)]),
 ("The Shire", "Eriador", "farmland", [
  (450,1090),(560,1090),(575,1050),(575,1000),(540,985),(470,990),(445,1030)]),
 ("Bree-land", "Eriador", "farmland", [(575,1080),(630,1080),(640,1020),(590,1010),(575,1040)]),
 ("Cardolan", "Eriador", None, [
  (440,990),(575,1000),(640,1010),(700,960),(690,880),(620,830),(520,830),(440,880)]),
 ("Minhiriath", "Eriador", None, [(430,900),(520,890),(600,850),(560,780),(450,790),(410,850)]),
 ("Rhudaur", "Eriador", None, [(700,1180),(830,1200),(880,1100),(860,1040),(770,1040),(700,1080)]),
 ("Angmar", "", None, [(700,1360),(880,1360),(900,1250),(880,1200),(760,1200),(700,1240)]),
 ("Ettenmoors", "Eriador", "upland", [(770,1210),(880,1200),(880,1130),(800,1130)]),
 ("Trollshaws", "Eriador", "forest_hills", [(780,1090),(866,1090),(870,1040),(800,1030)]),
 ("Eregion", "Eriador", None, [(730,980),(860,990),(870,900),(760,880),(720,920)]),
 ("Dunland", "", "upland", [(700,950),(770,950),(800,880),(770,840),(710,850),(690,900)]),
 ("Enedwaith", "", None, [(560,850),(700,850),(700,760),(640,720),(560,760)]),
 ("Drúwaith Iaur", "", "forest_hills", [(560,760),(700,760),(700,680),(640,640),(560,660)]),
 ("Andrast", "", None, [(440,560),(560,660),(640,640),(600,560),(520,440),(460,440)]),

 # ── the Misty Mountains and the vale of Anduin ──
 ("Misty Mountains", "", None, [
  (930,1330),(1000,1330),(1020,1250),(1010,1130),(970,1000),(920,900),(870,840),(820,830),(830,900),(880,1000),(900,1130),(920,1250)]),
 ("Vale of Anduin", "Rhovanion", None, [
  (1000,1300),(1080,1300),(1090,1130),(1070,1000),(1030,930),(1010,880),(970,900),(960,1000),(1000,1130)]),
 ("Lothlórien", "", "forest_plain", [(930,960),(990,960),(1000,910),(960,890),(925,910)]),
 ("Fangorn", "", "forest_hills", [(860,870),(920,880),(930,820),(890,790),(850,810)]),
 ("Gladden Fields", "Rhovanion", "marsh_plain", [(1000,1050),(1050,1055),(1050,1015),(1000,1010)]),

 # ── Rhovanion, Mirkwood, the Lonely Mountain ──
 ("Rhovanion", "", None, [
  (1080,1300),(1400,1320),(1520,1250),(1540,1050),(1500,900),(1420,800),(1300,760),(1180,770),(1120,820),(1100,900),(1080,1000)]),
 ("Mirkwood", "Rhovanion", "forest_plain", [
  (1085,1220),(1200,1230),(1240,1180),(1230,1100),(1200,1000),(1150,880),(1090,860),(1070,950),(1080,1100)]),
 ("Dol Guldur", "Mirkwood", "forest_hills", [(1060,960),(1120,960),(1130,900),(1070,890)]),
 ("Grey Mountains", "", None, [(1000,1330),(1330,1330),(1330,1250),(1120,1240),(1010,1250)]),
 ("Withered Heath", "", "upland", [(1180,1310),(1330,1310),(1330,1260),(1180,1260)]),
 ("Dale", "Rhovanion", "farmland", [(1220,1210),(1300,1210),(1300,1110),(1240,1100),(1220,1140)]),
 ("Iron Hills", "", None, [(1320,1230),(1420,1230),(1420,1160),(1320,1160)]),
 ("Dorwinion", "", "farmland", [(1400,1000),(1500,1000),(1520,920),(1460,880),(1400,920)]),
 ("Brown Lands", "Rhovanion", "steppe_plateau", [(1080,880),(1200,880),(1200,800),(1100,790),(1070,830)]),
 ("The Wold", "Rohan", "steppe_plain", [(940,880),(1060,880),(1070,800),(980,790),(940,830)]),
 ("Emyn Muil", "", "upland", [(1060,830),(1170,830),(1180,760),(1080,740),(1050,780)]),
 ("Dagorlad", "", "steppe_plateau", [(1150,800),(1280,800),(1290,730),(1180,730),(1150,760)]),
 ("Dead Marshes", "", "marsh_plain", [(1100,790),(1170,790),(1170,740),(1120,735)]),

 # ── Rhûn and the east ──
 ("Rhûn", "", "steppe_plain", [
  (1500,1250),(2000,1250),(2000,700),(1800,650),(1600,700),(1540,780),(1500,900),(1540,1050)]),
 ("Sea of Rhûn shore", "Rhûn", None, [(1480,960),(1650,960),(1660,800),(1500,790)]),

 # ── Rohan and the White Mountains ──
 ("Rohan", "", "steppe_plain", [
  (760,860),(870,860),(940,830),(1000,790),(1050,760),(1040,700),(960,680),(870,690),(790,720),(760,780)]),
 ("Westfold", "Rohan", "steppe_plain", [(760,800),(860,800),(870,720),(790,720),(760,760)]),
 ("Eastfold", "Rohan", "farmland", [(880,760),(1000,760),(1010,700),(900,690)]),
 ("Nan Curunír", "Rohan", None, [(790,840),(830,840),(830,800),(790,800)]),
 ("White Mountains", "", None, [
  (620,720),(790,720),(900,690),(1040,700),(1050,640),(960,630),(870,620),(760,620),(660,640),(620,680)]),

 # ── Gondor ──
 ("Gondor", "", None, [
  (620,680),(1050,700),(1120,700),(1160,650),(1170,560),(1130,480),(1080,430),(960,470),(880,500),(800,530),(700,540),(600,560)]),
 ("Anórien", "Gondor", "farmland", [(1000,700),(1125,700),(1135,610),(1105,612),(1060,628),(1000,650)]),
 ("Lebennin", "Gondor", "farmland", [(960,640),(1090,640),(1100,560),(1060,520),(980,520),(950,580)]),
 ("Lossarnach", "Gondor", "farmland", [(1060,628),(1104,626),(1104,588),(1065,588)]),
 ("Lamedon", "Gondor", None, [(860,670),(970,670),(960,600),(880,600)]),
 ("Belfalas", "Gondor", None, [(830,610),(960,600),(980,520),(940,470),(880,500),(820,540)]),
 ("Dor-en-Ernil", "Belfalas", None, [(900,580),(970,580),(980,520),(930,510)]),
 ("Anfalas", "Gondor", None, [(600,610),(830,610),(820,540),(700,540),(600,560)]),
 ("Pinnath Gelin", "Gondor", "hills", [(720,640),(830,640),(830,590),(720,590)]),
 ("Ithilien", "Gondor", "forest_hills", [(1120,760),(1170,760),(1180,560),(1170,470),(1120,470),(1110,560),(1120,660)]),
 ("Harondor", "", "steppe_plain", [(1030,480),(1170,480),(1170,400),(1080,360),(1000,400)]),

 # ── Mordor ──
 ("Mordor", "", "steppe_plateau", [
  (1160,780),(1300,780),(1420,760),(1470,700),(1460,540),(1380,480),(1250,480),(1180,520),(1160,600)]),
 ("Gorgoroth", "Mordor", "high_plateau", [(1200,720),(1330,720),(1330,600),(1210,600)]),
 ("Nurn", "Mordor", "steppe_plain", [(1250,580),(1450,600),(1450,500),(1280,490)]),
 ("Lithlad", "Mordor", "desert", [(1330,720),(1440,730),(1450,620),(1330,600)]),

 # ── Khand, Harad and the far south ──
 ("Khand", "", "steppe_plain", [(1480,700),(2000,700),(2000,320),(1750,320),(1600,400),(1480,480)]),
 ("Near Harad", "Harad", "desert", [(900,420),(1100,440),(1300,430),(1480,480),(1600,400),(1700,300),(1500,220),(1250,220),(1050,240),(920,300)]),
 ("Haradwaith", "Harad", "desert", [(960,320),(1300,320),(1300,220),(1000,220),(960,260)]),
 ("Umbar", "Harad", "hills", [(850,180),(1000,180),(1010,100),(880,80),(840,120)]),
 ("Far Harad", "Harad", "savanna", [(850,240),(1250,240),(2000,320),(2000,0),(840,0)]),
 ("Stone Fields", "Far Harad", "desert", [(1300,240),(1800,240),(1800,60),(1300,60)]),

 # ── the north ──
 ("Forodwaith", "", "tundra", [
  (0,2000),(2000,2000),(2000,1600),(1500,1500),(1200,1450),(900,1450),(700,1470),(500,1480),(300,1500),(150,1550),(0,1600)]),
 ("Forochel", "Forodwaith", "tundra", [(300,1500),(700,1500),(700,1420),(330,1420)]),
 ("Northern Waste", "Forodwaith", "tundra", [(700,1500),(1500,1520),(1500,1300),(1000,1340),(700,1400)]),
]
