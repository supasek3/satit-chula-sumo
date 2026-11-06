"""Render the compiled network so crossing placement can be inspected without launching SUMO."""
from pathlib import Path
import os,xml.etree.ElementTree as E,json
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(13,6.5));ax.set_facecolor('#f5f7fa');fig.patch.set_facecolor('white')
root=E.parse(ROOT/'network/network_crossings.net.xml').getroot()
for edge in root.findall('edge'):
    for lane in edge.findall('lane'):
        points=[tuple(map(float,p.split(','))) for p in lane.get('shape').split()]
        x,y=zip(*points)
        if edge.get('function')=='crossing':colour,width='#008b9b',5
        elif lane.get('allow')=='pedestrian':colour,width='#ccd8c5',2
        else:colour,width='#a8b0ba',3
        ax.plot(x,y,color=colour,lw=width,solid_capstyle='butt',zorder=2 if edge.get('function')=='crossing' else 1)
nodes={n.get('id'):n for n in root.findall('junction')}
for name,jid in [('X1','10784747877'),('X2','J1'),('X3','X3'),('X4','X4')]:
    n=nodes[jid];x,y=float(n.get('x')),float(n.get('y'))
    ax.annotate(name+(' — new' if name in ('X3','X4') else ' — existing'),(x,y),xytext=(x+5,y+28 if name!='X3' else y-32),fontsize=11,fontweight='bold',color='#006d77',arrowprops=dict(arrowstyle='-',color='#006d77'),zorder=5)
for loc in json.loads((ROOT/'network/manifest.json').read_text())['crossings']:
    ax.scatter([loc['x']],[loc['y']],s=50,marker='x',color='#d05a6e',zorder=6)
ax.text(535,205,'Main entry\n← westbound',ha='center',fontsize=10,color='#364152')
ax.text(160,115,'Second entrance',ha='center',fontsize=10,color='#364152')
ax.set_xlim(90,560);ax.set_ylim(85,275);ax.set_aspect('equal');ax.set_xlabel('SUMO local x (m)');ax.set_ylabel('SUMO local y (m)');ax.spines[['top','right']].set_visible(False)
ax.set_title('Satit Chula: four zebra crossings',loc='left',fontsize=17,fontweight='bold',pad=18)
fig.text(.125,.035,'Teal: model zebra crossings · Coral ×: supplied map pins · Pins snapped 5.7–7.0 m to inherited road alignment',fontsize=10,color='#52606d')
fig.savefig(ROOT/'network-preview.png',dpi=150,bbox_inches='tight');plt.close(fig)
