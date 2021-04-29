#!/usr/bin/python3

import os
import re
import configparser
import argparse
import tflite
import numpy
import graphviz

class defvals:
    section = 'tflite-graph'

class OpInfo:
    def __init__(self, idx, op_code):
        self.idx = idx
        self.op_code = op_code
        self.op_name = tflite.opcode2name(self.op_code)
        self.output = None
        self.succ = []
        self.fus_grp = []

    def __str__(self):
        return '%d_%s' %(self.idx, self.op_name)

    def nodename(self):
        return '%d_%s' %(self.idx, self.op_name)

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
            info = OpInfo(op_idx, self.model.OperatorCodes(op.OpcodeIndex()).BuiltinCode())
            info.succ = self.get_successor(op_idx)
            info.output = self.get_output(op_idx, 0)
            self.ops.append(info)
        return self.ops

    def plot(self):
        g = graphviz.Digraph()
        for op in self.ops:
            if len(op.fus_grp) > 1:
                with g.subgraph(name='cluster_'+str(op.fus_grp)) as c:
                    c.attr(color='blue')
                    c.attr(label=str(op.fus_grp))
                    c.edge_attr['style'] = 'invis'
                    for x in range(len(op.fus_grp) - 1):
                        c.edge(str(op.fus_grp[x]), str(op.fus_grp[x+1]))
        for op in self.ops:
            descs = []
            descs.append(op.nodename())
            g.node(str(op.idx), label='\n'.join(descs))
            for succ in op.succ:
                descs = []
                descs.append(numpy.array2string(op.output, separator='x'))
                g.edge(str(op.idx), str(succ), label='\n'.join(descs))

        # input & output endpoints
        last = self.ops[-1].idx
        g.edge('input', '0', numpy.array2string(self.get_input(0, 0), separator='x'))
        g.edge(str(last), 'output', numpy.array2string(self.get_output(last, 0), separator='x'))

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
    args = parser.parse_args()

    mp = ModelParser(args)
    mp.load_model()
    mp.parse_subgraph()

    mp.ops[0].fus_grp = [0, 1, 2, 3]

    if args.graph:
        mp.plot()

    return

if __name__ == '__main__':
    main()
