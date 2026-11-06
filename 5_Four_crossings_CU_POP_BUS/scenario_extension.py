"""Six pink CU POP BUS proxies replace through cars; X3/X4 arrivals come from a separate observed input.

This does not add traffic or invent a bus timetable, dwell, capacity, or pedestrian volumes.
Bus shape is illustrative; default physical properties remain the replaced car's.
"""
from pathlib import Path
import os,csv,json,xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parent

def apply_extension(route_path,seed):
    settings=json.loads((ROOT/'assumptions.json').read_text())
    route_path=Path(route_path);tree=E.parse(route_path);root=tree.getroot()
    if root.find("vType[@id='cu_pop_bus']") is not None:raise ValueError('Extension must be applied once to freshly generated demand')
    begin,end=settings['bus_window_begin_s'],settings['bus_window_end_s'];count=settings['bus_count']
    cars=[v for v in root.findall('trip') if begin<=float(v.get('depart'))<end and v.get('from')=='31993796#3_E' and v.get('to')=='31993793' and not v.findall('stop')]
    if len(cars)<count:raise ValueError(f'Need {count} eligible through cars; only {len(cars)} available')
    selected=[]
    # Deterministic time-spread replacements preserve existing IDs, departure times, routes and lanes.
    for i in range(count):
        target=begin+(i+0.5)*(end-begin)/count
        v=min((c for c in cars if c not in selected),key=lambda c:(abs(float(c.get('depart'))-target),c.get('id')))
        selected.append(v)
    E.SubElement(root,'vType',id='cu_pop_bus',vClass='passenger',guiShape=settings['bus_gui_shape'],color=settings['bus_colour'],length=str(settings['bus_length_m']),minGap=str(settings['bus_min_gap_m']),accel=str(settings['bus_accel_m_s2']),decel=str(settings['bus_decel_m_s2']),sigma='0.5',maxSpeed=str(settings['bus_max_speed_m_s']))
    manifest=[]
    for v in selected:
        v.set('type','cu_pop_bus');v.set('color',settings['bus_colour'])
        E.SubElement(v,'param',key='service',value='CU POP BUS')
        E.SubElement(v,'param',key='data_status',value='PROVISIONAL replacement through vehicle; car physics')
        manifest.append(dict(id=v.get('id'),depart_s=float(v.get('depart')),origin=v.get('from'),destination=v.get('to'),lane=v.get('departLane')))
    arrivals=Path(os.environ.get('NEW_CROSSING_ARRIVALS',str(ROOT/'new_crossing_arrivals.csv')))
    added=[]
    for i,row in enumerate(csv.DictReader(arrivals.read_text().splitlines())):
        crossing=row['crossing'];direction=row['direction'];depart=float(row['depart_s'])
        if crossing not in ('X3','X4') or direction not in ('N_to_S','S_to_N') or not 0<=depart<4500:raise ValueError(f'Invalid crossing observation: {row}')
        a,b=direction.split('_to_');pid=f'PED_{crossing}_{i}'
        person=E.SubElement(root,'person',id=pid,depart=f'{depart:.2f}',type='student')
        E.SubElement(person,'walk',attrib={'from':f'walk_{crossing}_{a}','to':f'walk_{crossing}_{b}','arrivalPos':'1'})
        added.append(dict(id=pid,**row))
    defs=[x for x in root if x.tag=='vType'];items=[x for x in root if x.tag!='vType']
    root[:]=defs+sorted(items,key=lambda x:(float(x.get('depart','0')),x.get('id','')))
    E.indent(tree);tree.write(route_path,encoding='UTF-8',xml_declaration=True)
    report=dict(seed=seed,bus_count=len(manifest),bus_replacements=manifest,new_crossing_pedestrians=added,assumptions=settings)
    route_path.with_suffix('.scenario.json').write_text(json.dumps(report,indent=2))
    print(f'CU POP BUS: {len(selected)} existing through cars replaced; X3/X4 pedestrians: {len(added)}')
