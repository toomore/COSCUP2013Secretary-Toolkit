#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
from timeit import timeit

def read_csv(f):
    c = csv.DictReader(f.readlines())
    for i in c:
        for v in i:
            i[v] = unicode(i[v], 'utf-8')
        yield i

def dict_staff(data, groupby):
    result = {}
    datas = [i for i in data]
    keys = set([i[groupby] for i in datas])
    for i in keys:
        result[i] = []

    for p in datas:
        p['phone'] = '+886' + p['phone'].replace(' ','')[1:]
        result[p[groupby]].append(p)

    return result

if __name__ == '__main__':
    with open('sec.csv') as f:
        a = dict_staff(read_csv(f), 'coll')
    print a
