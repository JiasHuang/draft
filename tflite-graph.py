#!/usr/bin/python3

import os
import re
import configparser
import argparse
import tflite
import numpy

from graphviz import Digraph

class defvals:
    section = 'tflite-graph'

class OpCtx:
    def __init__(self, idx, op_code):
        self.idx = idx
        self.op_code = op_code.BuiltinCode()
        self.op_name = tflite.opcode2name(self.op_code)
        self.output = None
        self.succ = []
        self.fus_grp = []
    def __str__(self):
        return '%d_%s' %(self.idx, self.op_name)
    def nodename(self):
        return '%d_%s' %(self.idx, self.op_name)

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

def parse_model(args):
    with open(args.model, 'rb') as fd:
        return tflite.Model.GetRootAsModel(fd.read(), 0)
    return None

def get_successor(subgraph, op):
    results = []
    outputs = op.OutputsAsNumpy()
    for i in range(subgraph.OperatorsLength()):
        op = subgraph.Operators(i)
        for x in op.InputsAsNumpy():
            if x in outputs:
                results.append(i)
    return results

def get_output(subgraph, op):
    if op.OutputsLength():
        tensor_index = op.Outputs(0)
        tensor = subgraph.Tensors(tensor_index)
        return tensor.ShapeAsNumpy()
    return None

def parse_subgraph(args, model):
    results = []
    subgraph = model.Subgraphs(0)
    for i in range(subgraph.OperatorsLength()):
        op = subgraph.Operators(i)
        ctx = OpCtx(i, model.OperatorCodes(op.OpcodeIndex()))
        ctx.succ = get_successor(subgraph, op)
        ctx.output = get_output(subgraph, op)
        results.append(ctx)
    return results

def do_plot(args, ctxs):
    g = Digraph()
    for ctx in ctxs:
        if len(ctx.fus_grp) > 1:
            with g.subgraph(name='cluster_'+str(ctx.fus_grp)) as c:
                c.attr(color='blue')
                c.attr(label=str(ctx.fus_grp))
                c.edge_attr['style'] = 'invis'
                for x in range(len(ctx.fus_grp) - 1):
                    a = ctx.fus_grp[x]
                    b = ctx.fus_grp[x+1]
                    c.edge(ctxs[a].nodename(), ctxs[b].nodename())
    for ctx in ctxs:
        g.node(ctx.nodename())
        for succ in ctx.succ:
            g.edge(ctx.nodename(), ctxs[succ].nodename(), label=numpy.array2string(ctx.output, separator='x'))
    g.view()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', action=LoadConfig)
    parser.add_argument('-m', '--model', required=True)
    parser.add_argument('-g', '--graph', type=str2bool, nargs='?', const=True, default=False)
    args = parser.parse_args()

    model = parse_model(args)
    ctxs = parse_subgraph(args, model)

    for ctx in ctxs:
        print(ctx)

    ctxs[0].fus_grp = [0, 1, 2, 3]
    ctxs[6].fus_grp = [6, 7, 8, 9]

    if args.graph:
        do_plot(args, ctxs)

    return

if __name__ == '__main__':
    main()
