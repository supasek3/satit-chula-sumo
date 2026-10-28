"""Makes network_base.net.xml from network.net.xml:
 - removes the extra sidewalk at lane _3 (SUMO only supports a sidewalk at lane _0)
 - stops pedestrians walking on the vehicle lanes of Soi Chula 11
 - keeps E0-E3 (north driveways, not yet joined to the main road)
Your network.net.xml is not modified."""
import xml.etree.ElementTree as ET
t = ET.parse('network.net.xml'); r = t.getroot()
STRAY = set(); STRAY_J = set()   # E0-E3 are the north driveways (Inflow 3 & 4) - keep them
PED_FIX = {'31973416#1', '31973416#1.32'}
four_lane = set()
for e in list(r.findall('edge')):
    eid = e.get('id')
    if e.get('function'):                 # internal / walkingarea / crossing: rebuilt by netconvert
        r.remove(e); continue
    if eid in STRAY:
        r.remove(e); continue
    lanes = e.findall('lane')
    if len(lanes) == 4 and lanes[3].get('allow') == 'pedestrian':
        e.remove(lanes[3]); four_lane.add(eid)
    if eid in PED_FIX:
        for ln in e.findall('lane')[1:]:
            d = ln.get('disallow', '').split()
            if 'pedestrian' not in d: ln.set('disallow', ' '.join(['pedestrian'] + d))
for j in list(r.findall('junction')):
    if j.get('id') in STRAY_J or j.get('type') == 'internal': r.remove(j); continue
    if j.get('type') == 'traffic_light': j.set('type', 'priority')  # re-made TLS by netconvert --tls.set
    for a in ('intLanes','incLanes'): j.attrib.pop(a, None)
    for q in list(j): j.remove(q)          # <request> rows, rebuilt by netconvert
for c in list(r.findall('connection')):
    if c.get('from','').startswith(':') or c.get('to','').startswith(':') or c.get('from') in STRAY or c.get('to') in STRAY \
       or (c.get('from') in four_lane and c.get('fromLane') == '3') \
       or (c.get('to') in four_lane and c.get('toLane') == '3') \
       or c.get('fromLane') == '0':        # sidewalk links, replaced by walkingareas
        r.remove(c); continue
    for a in ('via','tl','linkIndex'): c.attrib.pop(a, None)
for tl in list(r.findall('tlLogic')): r.remove(tl)   # rebuilt with pedestrian phases
t.write('network_base.net.xml', encoding='UTF-8', xml_declaration=True)
print('removed lane 3 on:', sorted(four_lane))
