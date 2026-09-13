"""Compact municipal graph export for the same offline JavaScript router used in the demo."""
import base64,json,hashlib
from pathlib import Path
import numpy as np
from .core import PROJECT

def packed(values,dtype):
    a=np.asarray(values,dtype=dtype)
    return {'dtype':a.dtype.str,'count':a.size,'base64':base64.b64encode(a.tobytes()).decode()}

def export_graph(network,output,pairs,rejected=None,tolerance=150,synthetic=False):
    matrix,labels,lookup,stats=network.view(tolerance,rejected)
    selected=sorted(set(lookup.values()))
    old_to_new={v:i for i,v in enumerate(selected)}
    uv=[];length=[];kind=[];gaps=[];offsets=[0];geometry=[]
    origin=np.floor(np.min(network.coords,axis=0)/1000)*1000
    for i in selected:
        e=network.edges[i];uv.extend([e.u,e.v]);length.append(e.length)
        kind.append(2 if e.gap_id else 0 if e.source=='osm' else 1)
        gaps.append(e.gap_id)
        geometry.extend(np.rint((np.asarray(e.geometry.coords)-origin)*100).astype(np.int32).ravel().tolist())
        offsets.append(len(geometry)//2)
    edge_indices=[old_to_new[lookup[(u,int(v))]] for u in range(matrix.shape[0]) for v in matrix.indices[matrix.indptr[u]:matrix.indptr[u+1]]]
    terminals=[]
    for p in pairs:
        if synthetic:
            a=p['origin'];b=p['destination']
        else:
            a=PROJECT.transform(float(p['origin_lon']),float(p['origin_lat']))
            b=PROJECT.transform(float(p['dest_lon']),float(p['dest_lat']))
        terminals.append({'id':p['id'],'origin':(np.asarray(a)-origin).tolist(),'destination':(np.asarray(b)-origin).tolist()})
    data={'format':'forest-routes-compact-v1','synthetic':synthetic,'node_count':len(network.coords),'edge_count':len(selected),
          'coordinates':'local metres from private projected origin','projected_origin_m':origin.tolist() if not synthetic else [0,0],
          'policy':{'max_gap_m':tolerance,'walking_allowance_per_end_m':1000,'gap_weight':5,'walking_weight':10,'field_verified':False},
          'terminals':terminals,'gap_ids':gaps,'stats':stats,
          'nodes':packed(np.rint((np.asarray(network.coords)-origin)*100).ravel(),'<i4'),
          'uv':packed(uv,'<u4'),'lengths':packed(length,'<f8'),'kinds':packed(kind,'u1'),
          'offsets':packed(offsets,'<u4'),'geometry':packed(geometry,'<i4'),
          'csr_offsets':packed(matrix.indptr,'<u4'),'csr_nodes':packed(matrix.indices,'<u4'),
          'csr_edges':packed(edge_indices,'<u4'),'components':packed(labels,'<u4')}
    path=output/'compact-graph.json';path.write_text(json.dumps(data,separators=(',',':')))
    (output/'compact-manifest.json').write_text(json.dumps({'bytes':path.stat().st_size,'nodes':len(network.coords),'edges':len(selected),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'geometry_quantization_m':.01,'edge_lengths':'original float64 metres',
        'purpose':'Offline browser route computation; no server, runtime API, or precomputed routes required.'},indent=2))
    write_offline_page(output)
    print('Exported compact graph',path.stat().st_size,'bytes',flush=True)
    return data


def write_offline_page(output):
    source=Path(__file__).parent
    template=(source/'offline_template.html').read_text()
    html=template.replace('__ROUTER__',(source/'router.js').read_text()).replace('__GRAPH__',(output/'compact-graph.json').read_text()).replace('__UI__',(source/'demo-ui.js').read_text())
    (output/'offline-router.html').write_text(html)
