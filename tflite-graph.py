#!/usr/bin/python3

import os
import re
import configparser
import argparse
import tflite
import numpy
import graphviz
import tflite_ut
import fusion

def dim2str(a):
    if isinstance(a, numpy.ndarray):
        return numpy.array2string(a, separator='x')
    return str(a)

class defvals:
    section = 'tflite-graph'

class TensorInfo:
    def __init__(self, idx, tensor):
        self.idx = idx
        self.tensor = tensor
        self.head = None
        self.tail = []

    def __str__(self):
        return dim2str(self.tensor.ShapeAsNumpy())

    def size(self):
        size = 1
        for i in self.tensor.ShapeAsNumpy():
            size *= i
        return size

class OpInfo:
    def __init__(self, idx, op_code):
        self.idx = idx
        self.op_code = op_code
        self.op_name = tflite.opcode2name(self.op_code)
        self.inputs = None # TensorInfo Refs
        self.outputs = None # TensorInfo Refs
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
        self.tensors = []
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

    def get_inputs(self, op_idx):
        op = self.subgraph.Operators(op_idx)
        tensor_idxs = [op.Inputs(i) for i in range(op.InputsLength())]
        return [self.tensors[i] for i in tensor_idxs]

    def get_outputs(self, op_idx):
        op = self.subgraph.Operators(op_idx)
        tensor_idxs = [op.Outputs(i) for i in range(op.OutputsLength())]
        return [self.tensors[i] for i in tensor_idxs]

    def parse_subgraph(self):
        self.subgraph = self.model.Subgraphs(0)
        for tensor_idx in range(self.subgraph.TensorsLength()):
            tensor = self.subgraph.Tensors(tensor_idx)
            self.tensors.append(TensorInfo(tensor_idx, tensor))
        for op_idx in range(self.subgraph.OperatorsLength()):
            op = self.subgraph.Operators(op_idx)
            op_info = OpInfo(op_idx, self.model.OperatorCodes(op.OpcodeIndex()).BuiltinCode())
            op_info.inputs = self.get_inputs(op_idx)
            op_info.outputs = self.get_outputs(op_idx)
            self.ops.append(op_info)
        # updatae OpInfo: predecessor and successor
        for op in self.ops:
            for succ_idx in self.get_successor(op.idx):
                succ_op = self.ops[succ_idx]
                op.succ.append(succ_op)
                succ_op.pred.append(op)
                # update TensorInfo
                for output in op.outputs:
                    if output in succ_op.inputs:
                        output.head = op
                        output.tail.append(succ_op)
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
                tensor = op.outputs[0]
                descs.append(str(tensor))
                g.edge(str(op.idx), str(succ.idx), label='\n'.join(descs))

        # input & output endpoints
        last = self.ops[-1].idx
        g.edge('Input', '0', str(self.ops[0].inputs[0]))
        g.edge(str(last), 'Output', str(self.ops[last].outputs[0]))

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

    fusion.do_fusion(mp)
    print('dram usage {:.0%}'.format(fusion.caculate_dram_usage(mp)))

    if args.test:
        tflite_ut.unit_test(mp)

    if args.graph:
        mp.plot()

    return

if __name__ == '__main__':
    main()
