"""Time-boxed worker: composes missing frames only. Usage: python run_missing.py MODULE N PART PARTS"""
import sys, os, importlib, time
mod=importlib.import_module(sys.argv[1]); n=int(sys.argv[2]); part=int(sys.argv[3]); parts=int(sys.argv[4])
t0=time.time()
for f in range(n):
    if f%parts!=part or os.path.exists(mod.DST+'/o%04d.jpg'%f): continue
    if time.time()-t0>150: break
    mod.compose(f)
