"""Turn GeoNames cities1000 into the gazetteer, keeping the curated landmarks."""
import json, sys, zipfile, unicodedata, re
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.join(_HERE, "..", "cli"))
# Where the downloaded source datasets live. Override with WAYFARE_SOURCES.
SRC = _os.environ.get("WAYFARE_SOURCES", _os.path.join(_HERE, "sources"))

CC = {
"AD":"Andorra","AE":"United Arab Emirates","AF":"Afghanistan","AG":"Antigua","AL":"Albania","AM":"Armenia",
"AO":"Angola","AR":"Argentina","AT":"Austria","AU":"Australia","AZ":"Azerbaijan","BA":"Bosnia and Herzegovina",
"BB":"Barbados","BD":"Bangladesh","BE":"Belgium","BF":"Burkina Faso","BG":"Bulgaria","BH":"Bahrain",
"BI":"Burundi","BJ":"Benin","BN":"Brunei","BO":"Bolivia","BR":"Brazil","BS":"Bahamas","BT":"Bhutan",
"BW":"Botswana","BY":"Belarus","BZ":"Belize","CA":"Canada","CD":"DR Congo","CF":"Central African Republic",
"CG":"Congo","CH":"Switzerland","CI":"Cote d'Ivoire","CL":"Chile","CM":"Cameroon","CN":"China",
"CO":"Colombia","CR":"Costa Rica","CU":"Cuba","CV":"Cape Verde","CY":"Cyprus","CZ":"Czechia","DE":"Germany",
"DJ":"Djibouti","DK":"Denmark","DM":"Dominica","DO":"Dominican Republic","DZ":"Algeria","EC":"Ecuador",
"EE":"Estonia","EG":"Egypt","EH":"Western Sahara","ER":"Eritrea","ES":"Spain","ET":"Ethiopia","FI":"Finland",
"FJ":"Fiji","FM":"Micronesia","FO":"Faroe Islands","FR":"France","GA":"Gabon","GB":"United Kingdom",
"GD":"Grenada","GE":"Georgia","GF":"French Guiana","GH":"Ghana","GL":"Greenland","GM":"Gambia","GN":"Guinea",
"GQ":"Equatorial Guinea","GR":"Greece","GT":"Guatemala","GW":"Guinea-Bissau","GY":"Guyana","HK":"Hong Kong",
"HN":"Honduras","HR":"Croatia","HT":"Haiti","HU":"Hungary","ID":"Indonesia","IE":"Ireland","IL":"Israel",
"IN":"India","IQ":"Iraq","IR":"Iran","IS":"Iceland","IT":"Italy","JM":"Jamaica","JO":"Jordan","JP":"Japan",
"KE":"Kenya","KG":"Kyrgyzstan","KH":"Cambodia","KM":"Comoros","KP":"North Korea","KR":"South Korea",
"KW":"Kuwait","KZ":"Kazakhstan","LA":"Laos","LB":"Lebanon","LI":"Liechtenstein","LK":"Sri Lanka",
"LR":"Liberia","LS":"Lesotho","LT":"Lithuania","LU":"Luxembourg","LV":"Latvia","LY":"Libya","MA":"Morocco",
"MC":"Monaco","MD":"Moldova","ME":"Montenegro","MG":"Madagascar","MK":"North Macedonia","ML":"Mali",
"MM":"Myanmar","MN":"Mongolia","MR":"Mauritania","MT":"Malta","MU":"Mauritius","MV":"Maldives","MW":"Malawi",
"MX":"Mexico","MY":"Malaysia","MZ":"Mozambique","NA":"Namibia","NC":"New Caledonia","NE":"Niger",
"NG":"Nigeria","NI":"Nicaragua","NL":"Netherlands","NO":"Norway","NP":"Nepal","NZ":"New Zealand","OM":"Oman",
"PA":"Panama","PE":"Peru","PF":"French Polynesia","PG":"Papua New Guinea","PH":"Philippines","PK":"Pakistan",
"PL":"Poland","PR":"Puerto Rico","PS":"Palestine","PT":"Portugal","PY":"Paraguay","QA":"Qatar",
"RE":"Reunion","RO":"Romania","RS":"Serbia","RU":"Russia","RW":"Rwanda","SA":"Saudi Arabia","SB":"Solomon Islands",
"SC":"Seychelles","SD":"Sudan","SE":"Sweden","SG":"Singapore","SI":"Slovenia","SK":"Slovakia","SL":"Sierra Leone",
"SN":"Senegal","SO":"Somalia","SR":"Suriname","SS":"South Sudan","SV":"El Salvador","SY":"Syria","SZ":"Eswatini",
"TD":"Chad","TG":"Togo","TH":"Thailand","TJ":"Tajikistan","TL":"Timor-Leste","TM":"Turkmenistan","TN":"Tunisia",
"TR":"Turkey","TT":"Trinidad","TW":"Taiwan","TZ":"Tanzania","UA":"Ukraine","UG":"Uganda","US":"United States",
"UY":"Uruguay","UZ":"Uzbekistan","VE":"Venezuela","VN":"Vietnam","VU":"Vanuatu","YE":"Yemen","ZA":"South Africa",
"ZM":"Zambia","ZW":"Zimbabwe","XK":"Kosovo","GI":"Gibraltar","SM":"San Marino","VA":"Vatican","AW":"Aruba",
"CW":"Curacao","JE":"Jersey","GG":"Guernsey","IM":"Isle of Man","AX":"Aland","SJ":"Svalbard","GP":"Guadeloupe",
"MQ":"Martinique","YT":"Mayotte","NR":"Nauru","TO":"Tonga","WS":"Samoa","KI":"Kiribati","TV":"Tuvalu",
"PW":"Palau","MH":"Marshall Islands","CK":"Cook Islands","NU":"Niue","AS":"American Samoa","GU":"Guam",
"MP":"Northern Marianas","VI":"US Virgin Islands","VG":"British Virgin Islands","KY":"Cayman Islands",
"TC":"Turks and Caicos","BM":"Bermuda","AI":"Anguilla","MS":"Montserrat","BL":"St Barthelemy","MF":"St Martin",
"PM":"St Pierre","SX":"Sint Maarten","BQ":"Caribbean Netherlands","KN":"St Kitts","LC":"St Lucia",
"VC":"St Vincent","FK":"Falkland Islands","GS":"South Georgia","SH":"St Helena","IO":"British Indian Ocean",
"CX":"Christmas Island","CC":"Cocos Islands","NF":"Norfolk Island","TK":"Tokelau","WF":"Wallis and Futuna",
"PN":"Pitcairn","AQ":"Antarctica","TF":"French Southern Lands","HM":"Heard Island","UM":"US Minor Islands",
"ST":"Sao Tome","GW ":"Guinea-Bissau","MO":"Macao","BV":"Bouvet Island",
}
US_STATES = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado",
"CT":"Connecticut","DE":"Delaware","DC":"District of Columbia","FL":"Florida","GA":"Georgia","HI":"Hawaii",
"ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
"ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi",
"MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey",
"NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
"OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
"TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington",
"WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"}
CA_PROV = {"AB":"Alberta","BC":"British Columbia","MB":"Manitoba","NB":"New Brunswick","NL":"Newfoundland",
"NS":"Nova Scotia","NT":"Northwest Territories","NU":"Nunavut","ON":"Ontario","PE":"Prince Edward Island",
"QC":"Quebec","SK":"Saskatchewan","YT":"Yukon"}
AU_ST = {"NSW":"New South Wales","QLD":"Queensland","SA":"South Australia","TAS":"Tasmania",
"VIC":"Victoria","WA":"Western Australia","NT":"Northern Territory","ACT":"Capital Territory",
"01":"Canberra","02":"New South Wales","03":"Northern Territory","04":"Queensland","05":"South Australia",
"06":"Tasmania","07":"Victoria","08":"Western Australia"}
GB_REG = {"ENG":"England","SCT":"Scotland","WLS":"Wales","NIR":"Northern Ireland"}

z = zipfile.ZipFile(f"{SRC}/cities1000.zip")
rows = z.read(z.namelist()[0]).decode("utf-8").rstrip("\n").split("\n")

out = []
for line in rows:
    f = line.split("\t")
    name, lat, lon, cc, adm1, pop, dem = f[1], float(f[4]), float(f[5]), f[8], f[10], int(f[14] or 0), f[16]
    fcode = f[7]
    country = CC.get(cc, cc)
    region = country
    if cc == "US" and adm1 in US_STATES:   region = f"{US_STATES[adm1]}, United States"
    elif cc == "CA" and adm1 in CA_PROV:   region = f"{CA_PROV[adm1]}, Canada"
    elif cc == "AU" and adm1 in AU_ST:     region = f"{AU_ST[adm1]}, Australia"
    elif cc == "GB" and adm1 in GB_REG:    region = GB_REG[adm1]
    kind = "city" if pop >= 100000 else "town"
    # A seat of government is the place people mean. Orleans, Ontario is larger
    # than Orleans, France; nobody asking for Orleans means the suburb of Ottawa.
    # Population alone gets this wrong often enough to be worth a thumb on the
    # scale — enough to settle a near tie, never enough to unseat a real city.
    weight = 3.0 if fcode == "PPLC" else 1.9 if fcode.startswith("PPLA") and len(fcode) == 5 \
             else 1.5 if fcode == "PPLA2" else 1.25 if fcode.startswith("PPLA") else 1.0
    try: elev = int(dem)
    except ValueError: elev = 0
    out.append((name, round(lat,4), round(lon,4), elev, region, kind, "", pop, round(pop*weight)))

# the curated landmarks GeoNames has no populated place for
from places import ROWS as CURATED
seen_pt = {(round(r[1],2), round(r[2],2)) for r in out}
kept = 0
for nm, la, lo, el, rg, kind, al in CURATED:
    if kind in ("range","park","forest","pass","water","plain","coast") or (round(la,2), round(lo,2)) not in seen_pt:
        out.append((nm, la, lo, el, rg, kind, al, 0, 0))
        kept += 1
print(f"{len(rows):,} from GeoNames + {kept} curated = {len(out):,} places")
json.dump(out, open("places_all.json","w"), ensure_ascii=False)
