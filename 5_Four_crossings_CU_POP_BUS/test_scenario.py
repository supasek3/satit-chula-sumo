"""Run: python3 test_scenario.py. Tests exact demand replacements and traversable X3/X4 zebra crossings."""
from pathlib import Path
import sys,unittest,json,subprocess,tempfile,shutil,os,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent if (ROOT.parent/'with_delay').exists() else ROOT.parent/'sumo-source-2026-11-06'
sys.path.insert(0,str(ROOT.parent/'SUMO_review_2026-10-22/runtime'))

class ScenarioTests(unittest.TestCase):
    def test_four_crossings_and_preserved_geometry(self):
        new=E.parse(ROOT/'network/network_crossings.net.xml').getroot()
        old=E.parse(SOURCE/'with_delay/1_Baseline/baseline_v7/network_crossings.net.xml').getroot()
        self.assertEqual({e.get('id') for e in new.findall('edge') if e.get('function')=='crossing'},{':10784747877_c0',':J1_c0',':X3_c0',':X4_c0'})
        edges={e.get('id'):e for e in new.findall('edge')}
        for e in old.findall('edge'):
            if e.get('id')=='31993796#3_E':continue
            n=edges[e.get('id')]
            self.assertEqual(len(e.findall('lane')),len(n.findall('lane')))
            for a,b in zip(e.findall('lane'),n.findall('lane')):self.assertAlmostEqual(float(a.get('length')),float(b.get('length')),delta=.05)
        for loc in json.loads((ROOT/'network/manifest.json').read_text())['crossings']:self.assertLess(loc['snap_distance_m'],8)

    def test_six_replacements_preserve_demand(self):
        from scenario_extension import apply_extension
        for seed in (1,2,21):
            with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
                tmp=Path(tmp)
                for p in (ROOT/'combined').iterdir():
                    if p.is_file() and p.suffix in ('.py','.csv'):shutil.copy2(p,tmp/p.name)
                # Generate the unextended source first, without modifying the original project.
                p=tmp/'make_baseline.py';p.write_text(p.read_text().split('# Four-crossing / provisional CU POP BUS extension.')[0])
                subprocess.run([sys.executable,'make_baseline.py',str(seed)],cwd=tmp,env=dict(os.environ,PYTHONHASHSEED='0',OPT_PRESET='combo_B'),capture_output=True,check=True)
                route=tmp/'baseline.rou.xml';old=E.parse(route).getroot()
                apply_extension(route,seed);new=E.parse(route).getroot()
                olditems={v.get('id'):v for v in old if v.tag in ('person','trip')};newitems={v.get('id'):v for v in new if v.tag in ('person','trip')}
                self.assertEqual(olditems.keys(),newitems.keys())
                buses=[v for v in new.findall('trip') if v.get('type')=='cu_pop_bus'];self.assertEqual(len(buses),6)
                for bid,v in newitems.items():
                    orig=olditems[bid]
                    for key in ('depart','from','to','departLane'):self.assertEqual(orig.get(key),v.get(key))
                    self.assertEqual([(x.get('busStop'),x.get('duration')) for x in orig.findall('stop')],[(x.get('busStop'),x.get('duration')) for x in v.findall('stop')])
                for v in buses:
                    self.assertFalse(v.findall('stop'));self.assertEqual(v.get('to'),'31993793');self.assertTrue(1800<=float(v.get('depart'))<4500)

    def test_pink_survives_gui_colour_updates(self):
        from unittest.mock import Mock,patch
        sys.path.insert(0,str(ROOT/'baseline'));import car_colors
        fake=Mock();fake.simulation.getDepartedIDList.return_value=['bus'];fake.simulation.getArrivedIDList.return_value=[];fake.vehicle.getTypeID.return_value='cu_pop_bus'
        with patch.object(car_colors,'traci',fake):car_colors.CarColors().step()
        fake.vehicle.setColor.assert_called_once_with('bus',(255,105,180,255))

    def test_both_directions_actually_use_new_crossings(self):
        import libsumo as t
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp=Path(tmp);routes=E.Element('routes');E.SubElement(routes,'vType',id='student',vClass='pedestrian')
            expected={}
            for cross in ('X3','X4'):
                for a,b in [('N','S'),('S','N')]:
                    pid=cross+a;person=E.SubElement(routes,'person',id=pid,type='student',depart='1');E.SubElement(person,'walk',attrib={'from':f'walk_{cross}_{a}','to':f'walk_{cross}_{b}','arrivalPos':'1'});expected[pid]=f':{cross}_c0'
            E.ElementTree(routes).write(tmp/'ped.rou.xml')
            t.start(['sumo','-n',str(ROOT/'network/network_crossings.net.xml'),'-r',str(tmp/'ped.rou.xml'),'--step-length','.1','--no-step-log','true','--error-log',str(tmp/'warnings.log')])
            seen={p:set() for p in expected};arrived=set()
            try:
                while t.simulation.getMinExpectedNumber()>0 and t.simulation.getTime()<180:
                    t.simulationStep();arrived.update(t.simulation.getArrivedPersonIDList())
                    for p in t.person.getIDList():seen[p].add(t.person.getRoadID(p))
                self.assertEqual(arrived,set(expected))
                for p,edge in expected.items():self.assertIn(edge,seen[p])
            finally:t.close()

if __name__=='__main__':unittest.main(verbosity=2)
