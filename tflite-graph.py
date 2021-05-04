#!/usr/bin/python3

import os
import re
import configparser
import argparse
import tflite
import numpy
import graphviz
import tflite_ut

class defvals:
    section = 'tflite-graph'

class OpInfo:
    def __init__(self, idx, op_code):
        self.idx = idx
        self.op_code = op_code
        self.op_name = tflite.opcode2name(self.op_code)
        self.output = None
        self.pred = []
        self.succ = []
        self.fus_grp = [] # refs list (only for 1st op)
        self.fus_org = None # 1st op ref (only for other ops)

    def __str__(self):
        return '%d_%s' %(self.idx, self.op_name)

    def nodename(self):
        return '%d_%s' %(self.idx, self.op_name)

    def fus_idxs(self):
        return [op.idx for op in self.fus_grp]

class ModelParser:
    def __init__(self, args):
        self.args = args
        self.model = None
        self.subgraph = None
        self.ops = []

    def __str__(self):
        return '\n'.join([op.nodename() for op in self.ops])

    def load_model(self):
        with open(self.args.model, 'rb') as fd:
            self.model = tflite.Model.GetRootAsModel(fd.read(), 0)
        return self.model

    def get_successor(self, op_idx):
        results = []
        op = self.subgraph.Operators(op_idx)
        outputs = op.OutputsAsNumpy()
        for i in range(self.subgraph.OperatorsLength()):
            op = self.subgraph.Operators(i)
            for x in op.InputsAsNumpy():
                if x in outputs:
                    results.append(i)
        return results

    def get_input(self, op_idx, i):
        op = self.subgraph.Operators(op_idx)
        if i in range(op.InputsLength()):
            tensor_index = op.Inputs(i)
            tensor = self.subgraph.Tensors(tensor_index)
            return tensor.ShapeAsNumpy()
        return None

    def get_output(self, op_idx, i):
        op = self.subgraph.Operators(op_idx)
        if i in range(op.OutputsLength()):
            tensor_index = op.Outputs(i)
            tensor = self.subgraph.Tensors(tensor_index)
            return tensor.ShapeAsNumpy()
        return None

    def parse_subgraph(self):
        self.subgraph = self.model.Subgraphs(0)
        for op_idx in range(self.subgraph.OperatorsLength()):
            op = self.subgraph.Operators(op_idx)
            op_info = OpInfo(op_idx, self.model.OperatorCodes(op.OpcodeIndex()).BuiltinCode())
            op_info.output = self.get_output(op_idx, 0)
            self.ops.append(op_info)
        # updatae OpInfo: predecessor and successor
        for op in self.ops:
            for succ_idx in self.get_successor(op.idx):
                succ_op = self.ops[succ_idx]
                op.succ.append(succ_op)
                succ_op.pred.append(op)
        return self.ops

    def add_fus_idxs(self, idxs):
        org_idx = idxs[0]
        org = self.ops[org_idx]
        for cur_idx in idxs:
            cur = self.ops[cur_idx]
            if cur in org.fus_grp:
                continue
            org.fus_grp.append(cur) # refs list (only for 1st op)
            if cur_idx != org_idx:
                cur.fus_org = org # 1st op ref (only for other ops)

    def plot(self):
        g = graphviz.Digraph()
        for op in self.ops:
            if len(op.fus_grp) > 1:
                with g.subgraph(name='cluster_'+str(op.idx)) as c:
                    fus_idxs = op.fus_idxs()
                    c.attr(color='blue', fontcolor='blue', label=str(fus_idxs))
                    c.edge_attr['style'] = 'invis'
                    for x in range(len(fus_idxs) - 1):
                        c.edge(str(fus_idxs[x]), str(fus_idxs[x+1]))
        for op in self.ops:
            descs = []
            descs.append(op.nodename())
            g.node(str(op.idx), label='\n'.join(descs))
            for succ in op.succ:
                descs = []
                descs.append(numpy.array2string(op.output, separator='x'))
                g.edge(str(op.idx), str(succ.idx), label='\n'.join(descs))

        # input & output endpoints
        last = self.ops[-1].idx
        g.edge('Input', '0', numpy.array2string(self.get_input(0, 0), separator='x'))
        g.edge(str(last), 'Output', numpy.array2string(self.get_output(last, 0), separator='x'))

        if self.args.render:
            g.render()
        else:
            g.view()

class LoadConfig(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        cfg = configparser.ConfigParser()
        cfg.read(values)
        section = cfg[defvals.section]
        for k in section:
            if isinstance(getattr(namespace, k), int):
                setattr(namespace, k, int(section[k]))
            else:
                setattr(namespace, k, section[k])

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', action=LoadConfig)
    parser.add_argument('-m', '--model', required=True)
    parser.add_argument('-g', '--graph', type=str2bool, nargs='?', const=True, default=False)
    parser.add_argument('-r', '--render', type=str2bool, nargs='?', const=True, default=False)
    parser.add_argument('-t', '--test', type=str2bool, nargs='?', const=True, default=False)
    args = parser.parse_args()

    mp = ModelParser(args)
    mp.load_model()
    mp.parse_subgraph()

    # fusion indices
    mp.add_fus_idxs([0, 1, 3])
    mp.add_fus_idxs([1, 5, 6])
    mp.add_fus_idxs([25, 26, 30])

    if args.test:
        tflite_ut.unit_test(mp)

    if args.graph:
        mp.plot()

    return

if __name__ == '__main__':
    main()
