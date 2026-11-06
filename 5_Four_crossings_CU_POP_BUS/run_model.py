"""Launch the new four-crossing version. Every run gets its own copy and outputs."""
from pathlib import Path
import argparse,os,sys,subprocess,shutil,datetime
ROOT=Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--method',choices=['baseline','combo_B','poom','fluke'],default='combo_B');ap.add_argument('--seed',type=int,default=1);ap.add_argument('--gui',action='store_true');ap.add_argument('--backend',choices=['traci','libsumo'],default='traci');ap.add_argument('--camera-delay',choices=['none','ethernet','wifi'],default='none');ap.add_argument('--drain',action='store_true');ap.add_argument('--arrivals',type=Path);ap.add_argument('--tag',default=None);a=ap.parse_args()
    if os.environ.get('PYTHONHASHSEED')!='0':return subprocess.call([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],env=dict(os.environ,PYTHONHASHSEED='0'))
    tag=a.tag or datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');dst=ROOT/'runs'/f'{a.method}_seed{a.seed}_{tag}'
    if dst.exists():raise SystemExit(f'Choose a fresh --tag: {dst} already exists')
    arrivals_path=a.arrivals.resolve() if a.arrivals else None
    shutil.copytree(ROOT/({'poom':'combined','combo_B':'combined'}.get(a.method,a.method)),dst)
    # Let extensions be imported by copied generator scripts without depending on directory depth.
    for p in ('scenario_extension.py','assumptions.json','new_crossing_arrivals.csv'):shutil.copy2(ROOT/p,dst/p)
    os.environ.setdefault('SUMO_HOME','/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/share/sumo')
    proj='/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/framework/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/share/proj'
    if Path(proj).exists():os.environ.setdefault('PROJ_DATA',proj)
    os.chdir(dst);sys.path.insert(0,str(dst))
    os.environ['CAMERA_DELAY']='none' if a.method=='baseline' else a.camera_delay
    os.environ['OPT_PRESET']={'combo_B':'combo_B','poom':'best'}.get(a.method,'v7')
    if arrivals_path:os.environ['NEW_CROSSING_ARRIVALS']=str(arrivals_path)
    subprocess.run([sys.executable,'make_baseline.py',str(a.seed)],check=True)
    if a.backend=='libsumo':
        if a.gui:raise SystemExit('Use --backend traci with --gui')
        sys.path.insert(0,str(ROOT.parent/'SUMO_review_2026-10-22/runtime'))
        import libsumo
        sys.modules['traci']=libsumo;sys.modules['traci.constants']=libsumo.constants
    import guard_control as ctl
    if a.method=='fluke':
        import proposed_control
        proposed_control.install()
    if a.drain:ctl.SIM_END=14400
    name='sumo-gui' if a.gui else 'sumo';binary=shutil.which(name)
    if a.gui:
        fixed=ROOT.parent/'sumo-gui-llvmpipe/bin/sumo-gui'
        if fixed.exists():binary=str(fixed);os.environ['GALLIUM_DRIVER']='llvmpipe'
        os.environ.setdefault('DISPLAY',':0')
        os.environ.setdefault('FONTCONFIG_FILE','/opt/X11/etc/X11/fontconfig/fonts.conf')
    if not binary:binary=f'/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/bin/{name}'
    dropoff='dropoff_bs0x4.add.xml' if a.method in ('combo_B','poom') else 'dropoff.add.xml'
    cmd=[binary,'-c','baseline.sumocfg','--seed',str(a.seed),'-a',f'{dropoff},baseline_tls.add.xml','--collision.check-junctions','true','--collision.action','warn','--collision-output','output/collisions.xml','--error-log','output/warnings.log','--no-warnings','false']
    if a.drain:cmd+=['--end','14400']
    if a.gui:cmd+=['--start','--delay','10','--window-size','1400,900']
    import json
    (dst/'launch.json').write_text(json.dumps(dict(method=a.method,seed=a.seed,camera_delay=os.environ['CAMERA_DELAY'],command=cmd),indent=2))
    print('Outputs:',dst,flush=True);stats=ctl.run(cmd,a.seed,colors=a.gui)
    (dst/'controller.json').write_text(json.dumps(stats,indent=2));print('Completed:',dst,flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
