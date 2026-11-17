"""Tiny reader/writer for Valve's text VDF (KeyValues) files, used to edit Steam's config.vdf and localconfig.vdf.
Items are [key, value] pairs where value is a string or a nested list of pairs; order and unknown keys are preserved."""
import re, sys, os, json
def parse(s):
    i=0; n=len(s)
    def ws():
        nonlocal i
        while i<n and s[i] in ' \t\r\n': i+=1
    def string():
        nonlocal i
        assert s[i]=='"'; j=i+1
        while s[j]!='"':
            if s[j]=='\\': j+=1
            j+=1
        r=s[i+1:j]; i=j+1; return r
    def block():
        nonlocal i
        items=[]
        while True:
            ws()
            if i>=n or s[i]=='}': 
                if i<n: i+=1
                return items
            k=string(); ws()
            if s[i]=='{': i+=1; items.append([k,block()])
            else: items.append([k,string()])
    return block()
def ser(items,d=0):
    out=[]
    for k,v in items:
        t='\t'*d
        if isinstance(v,list): out.append(f'{t}"{k}"\n{t}{{\n{ser(v,d+1)}{t}}}\n')
        else: out.append(f'{t}"{k}"\t\t"{v}"\n')
    return ''.join(out)
def get(items,k):
    for it in items:
        if it[0]==k and isinstance(it[1],list): return it[1]
def path(items,*ks):
    for k in ks:
        items=get(items,k)
        if items is None: return None
    return items
def setkv(items,k,v):
    for it in items:
        if it[0]==k and not isinstance(it[1],list): it[1]=v; return
    items.append([k,v])
def ensure(items,k):
    b=get(items,k)
    if b is None: b=[]; items.append([k,b])
    return b
if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='roundtrip':
        for f in sys.argv[2:]:
            s=open(f,encoding='utf-8',errors='surrogateescape').read()
            print(f, ser(parse(s))==s)
