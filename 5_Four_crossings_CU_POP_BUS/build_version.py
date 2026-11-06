"""Build a separate four-crossing model from pinned 6 November source."""
from pathlib import Path
import copy, json, subprocess, shutil, math, xml.etree.ElementTree as E
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent if (HERE.parent/'with_delay').exists() else HERE.parent/'sumo-source-2026-11-06'
SUMO=Path('/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO')
RUNTIME=HERE.parent/'SUMO_review_2026-10-22'/'runtime'

def write(tree,path):
    E.indent(tree);tree.write(path,encoding='UTF-8',xml_declaration=True)

def network():
    import sys
    sys.path.insert(0,str(RUNTIME));import libsumo as traci
    base=SOURCE/'with_delay/1_Baseline/baseline_v7/network_crossings.net.xml'
    traci.start(['sumo','-n',str(base),'--no-step-log','true'])
    locations=[]
    for name,lat,lon in [('X3',13.737955,100.529222),('X4',13.738044,100.528696)]:
        x,y=traci.simulation.convertGeo(lon,lat,fromGeo=True)
        locations.append(dict(id=name,latitude=lat,longitude=lon,x=x,y=y))
    traci.close()
    out=HERE/'network';out.mkdir(exist_ok=True)
    subprocess.run([str(SUMO/'bin/netconvert'),'-s',str(base),'--plain-output-prefix',str(out/'original'),'--offset.disable-normalization','true'],check=True)
    nodes=E.parse(out/'original.nod.xml');edges=E.parse(out/'original.edg.xml');cons=E.parse(out/'original.con.xml')
    edge=next(e for e in edges.getroot() if e.get('id')=='31993796#3_E')
    # Place crossings at the longitudinal positions of the pins. Snap to inherited road reference alignment,
    # rather than bending the road toward a pin selected on a map. Original click coordinates remain in manifest.
    shape=[tuple(map(float,p.split(','))) for p in edge.get('shape').split()]
    a,b=shape[0],shape[-1];dx,dy=b[0]-a[0],b[1]-a[1];norm=math.hypot(dx,dy)
    for loc in locations:
        u=((loc['x']-a[0])*dx+(loc['y']-a[1])*dy)/(norm*norm)
        x,y=a[0]+u*dx,a[1]+u*dy
        loc.update(node_x=x,node_y=y,snap_distance_m=math.hypot(x-loc['x'],y-loc['y']))
        E.SubElement(nodes.getroot(),'node',id=loc['id'],x=str(x),y=str(y),type='priority')
    # Keep the original entry ID so existing routes still start on the same entry edge.
    ids=['31993796#3_E','31993796#3_E_X3','31993796#3_E_X4']
    ends=[edge.get('from'),'X3','X4',edge.get('to')]
    coords=[a]+[(p['node_x'],p['node_y']) for p in locations]+[b]
    edges.getroot().remove(edge)
    for i,eid in enumerate(ids):
        child=copy.deepcopy(edge);child.set('id',eid);child.set('from',ends[i]);child.set('to',ends[i+1]);child.set('shape',' '.join(f'{x:.6f},{y:.6f}' for x,y in coords[i:i+2]));edges.getroot().append(child)
    for c in cons.getroot().findall('connection'):
        if c.get('from')==ids[0]:c.set('from',ids[-1])
    for i,loc in enumerate(locations):
        for lane in range(3):E.SubElement(cons.getroot(),'connection',attrib={'from':ids[i],'to':ids[i+1],'fromLane':str(lane),'toLane':str(lane)})
        # Two pedestrian-only access stubs create usable waiting areas on both sides of the road.
        # New crossings are unsignalized, with pedestrian priority; no fabricated signal schedule.
        for side,sign in [('N',1),('S',-1)]:
            nx,ny=dy/norm,-dx/norm  # + side faces north for this westbound road
            x,y=loc['node_x']+sign*nx*18,loc['node_y']+sign*ny*18
            pad=f"pad_{loc['id']}_{side}";walk=f"walk_{loc['id']}_{side}"
            E.SubElement(nodes.getroot(),'node',id=pad,x=str(x),y=str(y),type='dead_end')
            E.SubElement(edges.getroot(),'edge',attrib={'id':walk,'from':pad,'to':loc['id'],'priority':'-1','numLanes':'1','speed':'1.39','width':'3','allow':'pedestrian'})
        E.SubElement(cons.getroot(),'crossing',node=loc['id'],edges=ids[i+1],priority='1',width='4')
    for tree,ext in [(nodes,'nod'),(edges,'edg'),(cons,'con')]:write(tree,out/f'four_crossings.{ext}.xml')
    subprocess.run([str(SUMO/'bin/netconvert'),'--node-files',str(out/'four_crossings.nod.xml'),'--edge-files',str(out/'four_crossings.edg.xml'),'--connection-files',str(out/'four_crossings.con.xml'),'--tllogic-files',str(out/'original.tll.xml'),'--type-files',str(out/'original.typ.xml'),'--output-file',str(out/'network_crossings.net.xml'),'--lefthand','true','--walkingareas','true','--offset.disable-normalization','true','--no-turnarounds','true','--geometry.avoid-overlap','false'],check=True)
    json.dump({'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),'crossings':locations,'new_entry_edges':ids},open(out/'manifest.json','w'),indent=2)

def models():
    for name,source in [('baseline','1_Baseline/baseline_v7'),('combined','2_Optimisations/scenario_combined_v7'),('fluke','2_Optimisations/scenario_fluke_v7')]:
        dest=HERE/name;dest.mkdir(exist_ok=True)
        for p in (SOURCE/'with_delay'/source).iterdir():
            if p.is_file() and p.suffix in ('.py','.csv','.xml','.sumocfg'):shutil.copy2(p,dest/p.name)
            elif p.name=='background':shutil.copytree(p,dest/'background',dirs_exist_ok=True)
        shutil.copy2(HERE/'network/network_crossings.net.xml',dest/'network_crossings.net.xml')
        (dest/'output').mkdir(exist_ok=True)
        # Through-lane queue logic and commitment must cover all three pieces of the split entry.
        driver=dest/'driver_logic.py';s=driver.read_text();s=s.replace('["31993796#3_E",','["31993796#3_E", "31993796#3_E_X3", "31993796#3_E_X4",');s=s.replace('("31993796#3_E_1",','("31993796#3_E_1", "31993796#3_E_X3_1", "31993796#3_E_X4_1",');driver.write_text(s)
        colour=dest/'car_colors.py';s=colour.read_text();s=s.replace('            if traci.vehicle.getStops(v):','            if traci.vehicle.getTypeID(v) == "cu_pop_bus":\n                traci.vehicle.setColor(v, (255, 105, 180, 255))\n                continue\n            if traci.vehicle.getStops(v):');colour.write_text(s)
        # Existing generator CLI (including --rou) remains supported by original batch runners.
        gen=dest/'make_baseline.py';s=gen.read_text();s+='\n# Four-crossing / provisional CU POP BUS extension.\nimport sys as _sys\nfrom pathlib import Path as _Path\n_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))\nfrom scenario_extension import apply_extension\napply_extension(_Path(ROU if "ROU" in globals() else "baseline.rou.xml"), SEED)\n';gen.write_text(s)

if __name__=='__main__':network();models()
