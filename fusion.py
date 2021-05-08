#!/usr/bin/python3

class defvals:
    policy = 'fus_simple_no_branch'
    #policy = 'fus_simple'

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

def caculate_dram_usage(mp):
    total = 0
    total_fus = 0
    for op in mp.ops:
        size = 0
        size_fus = 0
        fus_grp = op.fus_org.fus_grp if op.fus_org else op.fus_grp
        fus_pred = None
        fus_succ = None
        dram_rd = []
        dram_wr = []
        if len(fus_grp) > 1:
            grp_idx = fus_grp.index(op)
            fus_pred = fus_grp[grp_idx - 1] if grp_idx else None
            fus_succ = fus_grp[grp_idx + 1] if grp_idx < len(fus_grp) - 1 else None
        for x in op.inputs:
            if x.head: # Only I/O tensors
                sz = x.size()
                size += sz
                if x.head != fus_pred:
                    size_fus += sz
                    dram_rd.append(x)
        for x in op.outputs:
            if x.head: # Only I/O tensors
                sz = x.size()
                size += sz
                if x.tail[0] != fus_succ or len(x.tail) > 1:
                    size_fus += sz
                    dram_wr.append(x)

        # Debug
        if dram_rd or dram_wr:
            strs = []
            if dram_rd:
                strs.append('rd ' + ','.join([str(x) for x in dram_rd]))
            if dram_wr:
                strs.append('wr ' + ','.join([str(x) for x in dram_wr]))
            print('%s: %s' %(str(op), ', '.join(strs)))

        total += size
        total_fus += size_fus
    return float(total_fus) / float(total)

