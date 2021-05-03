
def ut_next_successor(mp):
    errcnt = 0
    for op in mp.ops:
        if len(op.fus_grp) < 2:
            continue
        for i in range(len(op.fus_grp) - 1):
            x = op.fus_grp[i]
            y = op.fus_grp[i+1]
            if y.idx not in x.succ:
                print('ERROR: %s not %s\'s successor' %(y.nodename(), x.nodename()))
                errcnt += 1
    return errcnt

def ut_double_fused(mp):
    errcnt = 0
    for op in mp.ops:
        if op.fus_grp and op.fus_org:
            print('ERROR: %s double fused %s %s' %(op.nodename(), str(op.fus_org.fus_idxs()), str(op.fus_idxs())))
            errcnt += 1
    return errcnt

def ut_dependence(mp):
    errcnt = 0
    executed = []
    for op in mp.ops:
        for fus_op in op.fus_grp:
            for pred in fus_op.pred:
                if pred not in executed:
                    print('ERROR: %s dependence error: %s not ready' %(fus_op.nodename(), mp.ops[pred].nodename()))
                    errcnt += 1
            executed.append(fus_op.idx)
        if op.idx not in executed:
            executed.append(op.idx)
    return errcnt

def unit_test(mp):
    errcnt = 0
    errcnt += ut_double_fused(mp)
    errcnt += ut_next_successor(mp)
    errcnt += ut_dependence(mp)
    return errcnt

