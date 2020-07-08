#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import glob

pattern = r'struct\s+old_t\s+([a-zA-Z0-9\[\]_]+).*?};'
struct_old = 'struct old_t'
struct_new = 'struct new_t'

code_text_head = """
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct old_t {
    int a;
    int b;
};

struct new_t {
    int a;
    int b;
    int c;
    int d;
};

@vtext

"""

code_text_body_1 = """
static void output(@struct_new *p)
{
    printf("struct new_t @vname = {\\n");
    if (p->a) printf("\\t.a = %d,\\n", p->a);
    if (p->b) printf("\\t.b = %d,\\n", p->b);
    if (p->c) printf("\\t.c = %d,\\n", p->c);
    if (p->d) printf("\\t.d = %d,\\n", p->d);
    printf("};\\n");
}

static void convert(@struct_new *p, @struct_old *old)
{
    p->a = old->a;
    p->b = old->b;
}

int main()
{
    @struct_new n = {0};
    convert(&n, &@vname);
    output(&n);
    return 0;
}

"""

code_text_body_n = """
static void output(@struct_new *p, int cnt)
{
    int i;
    printf("@struct_new @vname[] = {\\n");
    for (i = 0; i < cnt; i++) {
        printf("\\t{\\n");
        if (p->a) printf("\\t\\t.a = %d,\\n", p->a);
        if (p->b) printf("\\t\\t.b = %d,\\n", p->b);
        if (p->c) printf("\\t\\t.c = %d,\\n", p->c);
        if (p->d) printf("\\t\\t.d = %d,\\n", p->d);
        printf("\\t},\\n");
        p++;
    }
    printf("};\\n");
}

static void convert(@struct_new *p, @struct_old *old, int cnt)
{
    int i;
    for (i = 0; i < cnt; i++) {
        p->a = old->a;
        p->b = old->b;
        p++;
        old++;
    }
}

int main()
{
    int cnt = sizeof(@vname) / sizeof(@struct_old);
    int size = sizeof(@struct_new) * cnt;
    struct new_t *n = malloc(size);
    memset(n, 0, size);
    convert(n, @vname, cnt);
    output(n, cnt);
    return 0;
}

"""

def readLocal(local, buffering=-1):
    if os.path.exists(local):
        fd = open(local, 'r', buffering)
        txt = fd.read()
        fd.close()
        return txt
    return ''

def saveLocal(local, text, buffering=-1):
    fd = open(local, 'w', buffering)
    fd.write(text)
    fd.close()
    return

def convert(vtext, vname):
        global struct_old
        global struct_new
        global code_text_head
        global code_text_body_1
        global code_text_body_n

        m = re.search(r'(.*?)\[', vname)
        if m:
            vname = m.group(1)
            text = code_text_head + code_text_body_n
        else:
            text = code_text_head + code_text_body_1

        text = text.replace('@struct_old', struct_old)
        text = text.replace('@struct_new', struct_new)
        text = text.replace('@vtext', vtext)
        text = text.replace('@vname', vname)

        saveLocal('__code__.c', text)
        os.system('gcc __code__.c -o __code__.bin')
        os.system('./__code__.bin > __code__.out')
        return readLocal('__code__.out')

def cleanup():
        os.system('rm -f __code__*')
        return

def main():
    global pattern
    for i in range(1, len(sys.argv)):
        f = sys.argv[i]
        text = readLocal(f)
        for m in re.finditer(pattern, text, re.DOTALL | re.MULTILINE):
            vtext = m.group()
            vname = m.group(1)
            print('converting %s:%s ...' %(f, vname))
            new_vtext = convert(vtext, vname)
            text = text.replace(vtext, new_vtext)
            saveLocal(f, text)
    cleanup()

if __name__ == '__main__':
    main()
