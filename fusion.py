#!/usr/bin/python3

class defvals:
    policy = 'fus_simple_no_branch'

def fus_simple(mp):
    fused = []
    for op in mp.ops:
        if op in fused:
            continue
        fus_grp = []
        cur = op
        while cur:
            if len(cur.pred) > 1:
                excluded = [pred for pred in cur.pred if pred not in fused and pred not in fus_grp]
                if excluded:
                    break
            fus_grp.append(cur)
            cur = cur.succ[0] if cur.succ else None
        if fus_grp:
            mp.add_fus_idxs([opx.idx for opx in fus_grp])
            fused.extend(fus_grp)

def fus_simple_no_branch(mp):
    fused = []
    for op in mp.ops:
        if op in fused:
            continue
        fus_grp = []
        cur = op
        while cur:
            if len(cur.pred) > 1:
                excluded = [pred for pred in cur.pred if pred not in fused and pred not in fus_grp]
                if excluded:
                    break
            if len(cur.succ) > 1:
                fus_grp.append(cur)
                break
            fus_grp.append(cur)
            cur = cur.succ[0] if cur.succ else None
        if fus_grp:
            mp.add_fus_idxs([opx.idx for opx in fus_grp])
            fused.extend(fus_grp)

def do_fusion(mp):
    eval('%s(mp)' %(defvals.policy))
