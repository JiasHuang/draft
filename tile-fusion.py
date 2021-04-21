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
        m = re.search(r'pad=(\w+)', desc)
        if m:
            vals = list(map(int, re.split('_|x', m.group(1))))
            if len(vals) >= 2:
                self.left = vals[0]
                self.right = vals[1]
            if len(vals) >= 4:
                self.top = vals[2]
                self.bottom = vals[3]

class Flt:
    def __init__(self, w, h, sx = 1, sy = 1, dx = 1, dy = 1):
        self.w = w
        self.h = h
        self.sx = sx
        self.sy = sy
        self.dx = dx
        self.dy = dy
    def parse_desc(self, desc):
        m = re.search(r'flt=(\d+)x(\d+)', desc)
        if m:
            self.w, self.h = int(m.group(1)), int(m.group(2))
        m = re.search(r'stride=(\d+)x(\d+)', desc)
        if m:
            self.sx, self.sy = int(m.group(1)), int(m.group(2))
        m = re.search(r'dilation=(\d+)x(\d+)', desc)
        if m:
            self.dx, self.dy = int(m.group(1)), int(m.group(2))

class Layer:
    def __init__(self, w = 0, h = 0, out_w = 0, out_h = 0, flt = None, pad = None, pad_type = None):
        self.w = w
        self.w = h
        self.out_w = out_w
        self.out_h = out_h
        self.flt = flt or Flt(1, 1, 1, 1)
        self.pad = pad or Pad(0, 0, 0, 0)
        self.pad_type = pad_type
    def set_pad_by_fo(self):
        pad_w = (self.out_w - 1) * self.flt.sx + self.flt.w + (self.flt.w - 1) * (self.flt.dx - 1) - self.w
        pad_h = (self.out_h - 1) * self.flt.sy + self.flt.h + (self.flt.h - 1) * (self.flt.dy - 1) - self.h
        left = pad_w // 2
        right = pad_w - left
        top = pad_h // 2
        bottom = pad_h - top
        self.pad = Pad(left, right, top, bottom)
    def get_tiles(self, tile_w, tile_h):
        tiles = []
        y = 0
        while y < self.h:
            x = 0
            while x < self.w:
                w = min(tile_w, self.w - x)
                h = min(tile_h, self.h - y)
                tiles.append(Tile(x, y, w, h))
                x += w
            y += tile_h
        return tiles
    def get_tile_by_output(self, out_tile):
        # w/ paddings
        x = out_tile.x * self.flt.sx
        y = out_tile.y * self.flt.sy
        w = (out_tile.w - 1) * self.flt.sx + self.flt.w + (self.flt.w - 1) * (self.flt.dx - 1)
        h = (out_tile.h - 1) * self.flt.sy + self.flt.h + (self.flt.h - 1) * (self.flt.dy - 1)
        # w/o paddings
        if x < self.pad.left:
            w = max(min(x + w - self.pad.left, self.w), 0)
            x = 0
        elif x in range(self.pad.left, self.pad.left + self.w + 1):
            w = min(w, self.pad.left + self.w - x)
            x -= self.pad.left
        else:
            w = 0
            x = self.w
        if y < self.pad.top:
            h = max(min(y + h - self.pad.top, self.h), 0)
            y = 0
        elif y in range(self.pad.top, self.pad.top + self.h + 1):
            h = min(h, self.pad.top + self.h - y)
            y -= self.pad.top
        else:
            h = 0
            y = self.h
        return Tile(x, y, w, h)
    def parse_desc(self, desc):
        m = re.search('in=(\d+)x(\d+)', desc)
        if m:
            self.w, self.h = int(m.group(1)), int(m.group(2))
        m = re.search('out=(\d+)x(\d+)', desc)
        if m:
            self.out_w, self.out_h = int(m.group(1)), int(m.group(2))
        m = re.search('pad_type=(\w+)', desc)
        if m:
            self.pad_type = m.group(1)
        self.flt.parse_desc(desc)
        self.pad.parse_desc(desc)
        if self.pad_type == 'SAME':
            self.set_pad_by_fo()
    def get_dim_with_padding(self):
        w = self.w + self.pad.left + self.pad.right
        h = self.h + self.pad.top + self.pad.bottom
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
        ax.add_patch(Rectangle(pos, layer.w, layer.h, color='blue', fill=False))
        plt.text(x, -10, 'layer {}x{} (pad: {}x{})\nflt {}x{} stride {}x{} dilation {}x{}'.format(layer.w, layer.h, w, h,
            layer.flt.w, layer.flt.h,
            layer.flt.sx, layer.flt.sy,
            layer.flt.dx, layer.flt.dy))
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

    print('-' * 80)
    for idx, layer in enumerate(layers):
        print('layer {} : in {}x{} pad {}x{} ({}, {}, {}, {}) out {}x{}'.format(
            idx, layer.w, layer.h,
            layer.w + layer.pad.left + layer.pad.right, layer.h + layer.pad.top + layer.pad.bottom,
            layer.pad.left, layer.pad.right, layer.pad.top, layer.pad.bottom,
            layer.out_w, layer.out_h))

    tile_dim = list(map(int, args.tile_dim.split('x')))
    tiles_by_layer = do_tile_fusion(layers, tile_dim[0], tile_dim[1])

    if args.plot:
        do_plot(layers, tiles_by_layer)

    return

if __name__ == '__main__':
    main()
