"""Offline checks in a retained, isolated test directory, never the live MOD."""
import importlib.util,json,pathlib,sys,time,zlib
import build_mod as build

spec=importlib.util.spec_from_file_location('installer',build.ROOT/'DECK_TRANSFER/install.py')
ins=importlib.util.module_from_spec(spec);spec.loader.exec_module(ins)
root=build.ROOT/'tests'/('run_'+str(time.time_ns()))
romfs=root/'character_mod/romfs'
(romfs/'Actor').mkdir(parents=True)
rstb=(build.SOURCE/ins.RSTB).read_bytes()
p=romfs/ins.RSTB;p.parent.mkdir(parents=True);p.write_bytes(rstb)
sentinel=romfs/'Actor/character_preserve.txt';sentinel.write_bytes(b'UNRELATED CHARACTER ASSET')
original=(build.SOURCE/'Actor/Pack/Item_Amiibo_DropTable_001.sbactorpack').read_bytes()
live_hashes={str(p):build.sha(p.read_bytes()) for p in [build.SOURCE/ins.RSTB,build.SOURCE/'Actor/Pack/Item_Amiibo_DropTable_001.sbactorpack']}
report={}
for name,pool in [('01_core',build.CORE),('02_collection',build.COLLECTION),('03_refill',build.REFILL)]:
    b=(build.ROOT/'DECK_TRANSFER/profiles'/name/'romfs'/build.PACK).read_bytes()
    build.validate_pack(b,pool,original)
    report[name]='PASS: all six progression/hit branches contain only the intended whitelist'
ins.run(romfs,'01_core')
assert not (romfs/build.PACK).exists() and p.read_bytes()==rstb
report['dry_run']='PASS: no writes'
old,named,n=ins.parse_rstb(ins.yaz_decode(rstb))
ins.run(romfs,'01_core',True)
new,after_named,nn=ins.parse_rstb(ins.yaz_decode(p.read_bytes()))
manifest=json.loads((build.ROOT/'DECK_TRANSFER/manifest.json').read_text(encoding='utf-8'))
bumps=manifest['resource_minimums']
changed={zlib.crc32(k.encode())&0xffffffff for k in bumps}
assert all(new[k]==v for k,v in old.items() if k not in changed)
assert named==after_named and n==nn
for k,v in bumps.items():assert new[zlib.crc32(k.encode())&0xffffffff]>=v
assert bytes(build.oead.yaz0.decompress(p.read_bytes()))==ins.yaz_decode(p.read_bytes())
report['rstb_merge']='PASS: unrelated entries/name table preserved; independent oead decoder accepts output'
ins.run(romfs,'02_collection',True)
assert (romfs/build.PACK).read_bytes()==(build.ROOT/'DECK_TRANSFER/profiles/02_collection/romfs'/build.PACK).read_bytes()
report['phase_switch']='PASS'
ins.run(romfs,'01_core',True,restore=True)
assert not (romfs/build.PACK).exists() and p.read_bytes()==rstb
report['restore']='PASS: byte-identical original RSTB; only added actorpack removed'
ins.run(romfs,'03_refill',True)
report['reinstall_after_restore']='PASS'
pack=romfs/build.PACK
pack.write_bytes(pack.read_bytes()+b'EXTERNAL_MODIFICATION')
try:ins.run(romfs,'01_core',True)
except ValueError:report['external_edit_guard']='PASS: refuses overwrite after external change'
else:raise AssertionError('Did not reject external edit')
assert sentinel.read_bytes()==b'UNRELATED CHARACTER ASSET'
assert all(build.sha(pathlib.Path(k).read_bytes())==v for k,v in live_hashes.items())
report['live_files']='PASS: original resources unchanged'
report['in_game']='NOT RUN; no Deck connection and local save lacks usable amiibo progress'
report['test_directory']=str(root)
(build.ROOT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
