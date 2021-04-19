#!/usr/bin/python3

import os
import re
import configparser
import argparse

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

class Pad:
    def __init__(self, left, right, top, bottom):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
    def parse_desc(self, desc):
        vals = list(map(int, re.split('_|x', desc)))
        if len(vals) >= 2:
            self.left = vals[0]
            self.right = vals[1]
        if len(vals) >= 4:
            self.top = vals[2]
            self.bottom = vals[3]

class Flt:
    def __init__(self, width, height, stride_x = 1, stride_y = 1, dilation_x = 1, dilation_y = 1):
        self.width = width
        self.height = height
        self.stride_x = stride_x
        self.stride_y = stride_y
        self.dilation_x = dilation_x
        self.dilation_y = dilation_y
    def parse_desc(self, desc):
        vals = list(map(int, re.split('_|x', desc)))
        if len(vals) >= 2:
            self.width = vals[0]
            self.height = vals[1]
        if len(vals) >= 4:
            self.stride_x = vals[2]
            self.stride_y = vals[3]
        if len(vals) >= 6:
            self.dilation_x = vals[4]
            self.dilation_y = vals[5]

class Layer:
    def __init__(self, width = 0, height = 0, flt = None, pad = None, pad_type = None):
        self.width = width
        self.height = height
        self.flt = flt or Flt(1, 1, 1, 1)
        self.pad = pad or Pad(0, 0, 0, 0)
        self.pad_type = pad_type
    def set_pad_by_fo(self, out_w, out_h):
        pad_w = (out_w - 1) * self.flt.stride_x + self.flt.width + (self.flt.width - 1) * (self.flt.dilation_x - 1) - self.width
        pad_h = (out_h - 1) * self.flt.stride_y + self.flt.height + (self.flt.height - 1) * (self.flt.dilation_y - 1) - self.height
        left = pad_w // 2
        right = pad_w - left
        top = pad_h // 2
        bottom = pad_h - top
        self.pad = Pad(left, right, top, bottom)
    def get_tiles(self, tile_w, tile_h):
        tiles = []
        y = 0
        while y < self.height:
            x = 0
            while x < self.width:
                w = min(tile_w, self.width - x)
                h = min(tile_h, self.height - y)
                tiles.append(Tile(x, y, w, h))
                x += w
            y += tile_h
        return tiles
    def get_tile_by_output(self, out_tile):
        # w/ paddings
        x = out_tile.x * self.flt.stride_x
        y = out_tile.y * self.flt.stride_y
        w = (out_tile.w - 1) * self.flt.stride_x + self.flt.width + (self.flt.width - 1) * (self.flt.dilation_x - 1)
        h = (out_tile.h - 1) * self.flt.stride_y + self.flt.height + (self.flt.height - 1) * (self.flt.dilation_y - 1)
        # w/o paddings
        if x < self.pad.left:
            w = max(min(x + w - self.pad.left, self.width), 0)
            x = 0
        elif x in range(self.pad.left, self.pad.left + self.width + 1):
            w = min(w, self.pad.left + self.width - x)
            x -= self.pad.left
        else:
            w = 0
            x = self.width
        if y < self.pad.top:
            h = max(min(y + h - self.pad.top, self.height), 0)
            y = 0
        elif y in range(self.pad.top, self.pad.top + self.height + 1):
            h = min(h, self.pad.top + self.height - y)
            y -= self.pad.top
        else:
            h = 0
            y = self.height
        return Tile(x, y, w, h)
    def parse_desc(self, desc):
        m = re.search('dim=(\w+)', desc)
        if m:
            vals = list(map(int, re.split('_|x', m.group(1))))
            self.width = vals[0]
            self.height = vals[1]
        m = re.search('pad_type=(\w+)', desc)
        if m:
            self.pad_type = m.group(1)
        m = re.search('flt=(\w+)', desc)
        if m:
            self.flt.parse_desc(m.group(1))
        m = re.search('pad=(\w+)', desc)
        if m:
            self.pad.parse_desc(m.group(1))
    def get_dim_with_padding(self):
        w = self.width + self.pad.left + self.pad.right
        h = self.height + self.pad.top + self.pad.bottom
        return (w, h)

class Tile:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

class LoadConfig(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        cfg = configparser.ConfigParser()
        cfg.read(values)
        for k in cfg['tile-fusion']:
            if k in ['layer']:
                vals = re.split('\s| ', cfg['tile-fusion'][k].strip())
                setattr(namespace, k, vals)
            else:
                setattr(namespace, k, cfg['tile-fusion'][k])

def do_tile_fusion(layers, last_layer_tile_w, last_layer_tile_h):
    tiles_by_layer = []
    # tiling from bottom up
    for idx, layer in enumerate(layers[::-1]):
        if idx == 0:
            tiles_by_layer.insert(0, layer.get_tiles(last_layer_tile_w, last_layer_tile_h))
        else:
            tiles = []
            for out_tile in tiles_by_layer[0]:
                tiles.append(layer.get_tile_by_output(out_tile))
            tiles_by_layer.insert(0, tiles)

    print('-' * 80)
    for idx, layer in enumerate(layers):
        print('layer {}'.format(idx))
        for tile_idx, tile in enumerate(tiles_by_layer[idx]):
            print('\ttile {} --- ({}, {}) {}x{}'.format(tile_idx, tile.x, tile.y, tile.w, tile.h))

    return tiles_by_layer

def do_plot(layers, tiles_by_layer):

    fig = plt.figure(figsize=(80,80))
    ax = fig.add_subplot()

    #draw layers
    x = 0
    y = 0
    max_h = 0
    for idx, layer in enumerate(layers):
        # w/ padding
        w, h = layer.get_dim_with_padding()
        ax.add_patch(Rectangle((x, y), w, h, color = 'black', fill=False))
        # w/o padding
        pos = (x + layer.pad.left, y + layer.pad.top)
        ax.add_patch(Rectangle(pos, layer.width, layer.height, color='blue', fill=False))
        plt.text(x, -10, 'layer {}x{} (pad: {}x{})\nflt {}x{} stride {}x{} dilation {}x{}'.format(layer.width, layer.height, w, h,
            layer.flt.width, layer.flt.height,
            layer.flt.stride_x, layer.flt.stride_y,
            layer.flt.dilation_x, layer.flt.dilation_y))
        for tile_idx, tile in enumerate(tiles_by_layer[idx]):
            if tile.w and tile.h:
                pos = (x + layer.pad.left + tile.x, y + layer.pad.top + tile.y)
                ax.add_patch(Rectangle(pos, tile.w, tile.h, color = 'red', ls=':', fill=False))
                plt.text(pos[0], pos[1], 'tile-{} ({},{}) {}x{}'.format(tile_idx, tile.x, tile.y, tile.w, tile.h))
        x += max(w + 10, 100)
        max_h = max(max_h, h)

    #display plot
    plt.xlim(0, x)
    plt.ylim(0, max_h)
    plt.gca().invert_yaxis()
    plt.show()

    return

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
    parser.add_argument('-l', '--layer', nargs='+')
    parser.add_argument('-t', '--tile_dim')
    parser.add_argument('-p', '--plot', type=str2bool, nargs='?', const=True, default=False)
    args = parser.parse_args()

    for k in ['layer', 'tile_dim']:
        if not getattr(args, k):
            print('invalid {}'.format(k))
            return

    layers = []
    for layer_desc in args.layer:
        layers.append(Layer())
        layers[-1].parse_desc(layer_desc)

    # update padding from next layer
    for idx, layer in enumerate(layers[:-1]):
        if isinstance(layer.pad_type, str):
            if layer.pad_type == 'SAME':
                layer.set_pad_by_fo(layers[idx+1].width, layers[idx+1].height)

    print('-' * 80)
    for idx, layer in enumerate(layers):
        print('layer {} orig {}x{} padding ({}, {}, {}, {}) => {}x{}'.format(
            idx, layer.width, layer.height,
            layer.pad.left, layer.pad.right, layer.pad.top, layer.pad.bottom,
            layer.width+layer.pad.left+layer.pad.right,
            layer.height+layer.pad.top+layer.pad.bottom))

    tile_dim = list(map(int, args.tile_dim.split('x')))
    tiles_by_layer = do_tile_fusion(layers, tile_dim[0], tile_dim[1])

    if args.plot:
        do_plot(layers, tiles_by_layer)

    return

if __name__ == '__main__':
    main()
