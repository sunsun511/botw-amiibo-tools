"""Build an isolated BOTW Switch amiibo reward hub. No live game writes."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools_lib'))
import oead

SOURCE = ROOT / 'source_romfs'
ACTOR = 'Item_Amiibo_DropTable_008'
AI = 'RareRewardHubV1'
PACK = f'Actor/Pack/{ACTOR}.sbactorpack'
CORE = {
    'Weapon_Bow_072': ('黄昏弓', 25),
    'Weapon_Lsword_060': ('鬼神大剑', 20),
    'Weapon_Lsword_059': ('大鼓隆之剑', 15),
    'Armor_225_Head': ('鬼神面具', 14),
    'Armor_225_Upper': ('鬼神服', 13),
    'Armor_225_Lower': ('鬼神靴', 13),
}
COLLECTION = {
    'Weapon_Lsword_057': ('六贤者之剑', 1),
    'Weapon_Sword_057': ('女神之剑', 1),
    'Weapon_Sword_058': ('勇者之剑', 1),
    'Weapon_Sword_059': ('海风回旋镖', 1),
    'Weapon_Shield_057': ('勇者盾', 1),
    'Armor_220_Head': ('希克面罩', 1),
    'Armor_181_Head': ('神兽兵装·露塔', 1),
    'Armor_182_Head': ('神兽兵装·梅德', 1),
    'Armor_183_Head': ('神兽兵装·鲁达尼亚', 1),
    'Armor_184_Head': ('神兽兵装·娜波力斯', 1),
    'GameRomHorseSaddle_01': ('旅人马鞍', 1),
    'GameRomHorseReins_01': ('旅人缰绳', 1),
}
for n, name in [(200,'时之勇者'),(205,'风之勇者'),(210,'黄昏勇者'),(215,'天空勇者'),(230,'初代勇者')]:
    for part, label in [('Head','帽子'),('Upper','衣服'),('Lower','裤子')]:
        COLLECTION[f'Armor_{n}_{part}'] = (name+label, 1)
ALL = CORE | COLLECTION
REFILL = {k:v for k,v in ALL.items() if k.startswith('Weapon_')}

def sha(b): return hashlib.sha256(b).hexdigest()
def write_new(p, b):
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        if p.read_bytes() != b: raise FileExistsError(f'Will not overwrite: {p}')
    else: p.write_bytes(b)

def table(pool):
    names = ['Normal','SmallHit'] + [f'{kind}({stage})' for kind in ['BigHit','GreatHit'] for stage in ['Normal','Parasail','Remain']]
    a = oead.aamp.ParameterIO(); a.type = 'xml'; a.version = 0
    h = oead.aamp.ParameterObject()
    h.params['TableNum'] = oead.aamp.Parameter(len(names))
    for i,name in enumerate(names,1): h.params[f'Table{i:02}'] = oead.aamp.Parameter(oead.FixedSafeString64(name))
    a.objects['Header'] = h
    total = sum(v[1] for v in pool.values())
    for name in names:
        obj = oead.aamp.ParameterObject()
        # Normal includes the chest in the engine's total; 1 - 1 = 0 loose drops.
        # SmallHit is completely disabled. Never set Normal to 0 (would subtract 1).
        for key,val in [('RepeatNumMin',0 if name=='SmallHit' else 1),('RepeatNumMax',0 if name=='SmallHit' else 1),('ApproachType',0),('OccurrenceSpeedType',0),('ColumnNum',len(pool) if name not in ['Normal','SmallHit'] else 0)]:
            obj.params[key] = oead.aamp.Parameter(val)
        if name not in ['Normal','SmallHit']:
            for i,(actor,(_,weight)) in enumerate(pool.items(),1):
                obj.params[f'ItemName{i:02}'] = oead.aamp.Parameter(oead.FixedSafeString64(actor))
                obj.params[f'ItemProbability{i:02}'] = oead.aamp.Parameter(float(weight*100/total))
        a.objects[name] = obj
    return a

def build_pack(pool, original):
    s = oead.Sarc(oead.yaz0.decompress(original))
    w = oead.SarcWriter.from_sarc(s)
    olddrop = 'Actor/DropTable/Item_Amiibo_DropTable_001.bdrop'
    oldlink = 'Actor/ActorLink/Item_Amiibo_DropTable_001.bxml'
    oldai = 'Actor/AIProgram/Item_Amiibo_DropTable.baiprog'
    link = oead.aamp.ParameterIO.from_binary(s.get_file(oldlink).data)
    link.objects['LinkTarget'].params['DropTableUser'] = oead.aamp.Parameter(ACTOR)
    link.objects['LinkTarget'].params['AIProgramUser'] = oead.aamp.Parameter(AI)
    link.objects['LinkTarget'].params['ActorNameJpn'] = oead.aamp.Parameter('RareRewardHubV1')
    ai = oead.aamp.ParameterIO.from_binary(s.get_file(oldai).data)
    inst = ai.lists['Action'].lists['Action_0'].objects['SInst']
    for suffix in ['1st','2nd','3rd']:
        inst.params['GreatHitRate'+suffix] = oead.aamp.Parameter(100.0)
        inst.params['SmallHitRate'+suffix] = oead.aamp.Parameter(0.0)
        inst.params['DropNumRate'+suffix] = oead.aamp.Parameter(100.0)
    for name in (olddrop,oldlink,oldai): del w.files[name]
    w.files[f'Actor/DropTable/{ACTOR}.bdrop'] = table(pool).to_binary()
    w.files[f'Actor/ActorLink/{ACTOR}.bxml'] = link.to_binary()
    w.files[f'Actor/AIProgram/{AI}.baiprog'] = ai.to_binary()
    _, raw = w.write()
    return bytes(oead.yaz0.compress(raw))

def validate_pack(payload,pool,original):
    s=oead.Sarc(oead.yaz0.decompress(payload))
    a=oead.aamp.ParameterIO.from_binary(s.get_file(f'Actor/DropTable/{ACTOR}.bdrop').data)
    def val(obj,key): return obj.params[key].v
    assert val(a.objects['Normal'],'RepeatNumMin') == 1
    assert val(a.objects['SmallHit'],'RepeatNumMax') == 0
    for kind in ['BigHit','GreatHit']:
        for stage in ['Normal','Parasail','Remain']:
            obj=a.objects[f'{kind}({stage})']
            n=val(obj,'ColumnNum')
            ids=[str(val(obj,f'ItemName{i:02}')) for i in range(1,n+1)]
            assert ids==list(pool)
            assert abs(sum(val(obj,f'ItemProbability{i:02}') for i in range(1,n+1))-100)<0.001
            assert val(obj,'RepeatNumMin')==val(obj,'RepeatNumMax')==1
    link=oead.aamp.ParameterIO.from_binary(s.get_file(f'Actor/ActorLink/{ACTOR}.bxml').data)
    assert str(val(link.objects['LinkTarget'],'AIProgramUser'))==AI
    assert str(val(link.objects['LinkTarget'],'DropTableUser'))==ACTOR
    ai=oead.aamp.ParameterIO.from_binary(s.get_file(f'Actor/AIProgram/{AI}.baiprog').data)
    inst=ai.lists['Action'].lists['Action_0'].objects['SInst']
    for suffix in ['1st','2nd','3rd']:
        assert val(inst,'GreatHitRate'+suffix)==100
        assert val(inst,'SmallHitRate'+suffix)==0
    old=oead.Sarc(oead.yaz0.decompress(original))
    assert bytes(s.get_file('Actor/ModelList/None.bmodellist').data)==bytes(old.get_file('Actor/ModelList/None.bmodellist').data)
    return {'sha256':sha(payload),'compressed_bytes':len(payload),'uncompressed_bytes':len(oead.yaz0.decompress(payload)),'items':{k:{'name':v[0],'weight':v[1]} for k,v in pool.items()},'binary_roundtrip':'PASS','in_game':'NOT_TESTED'}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--owned',type=Path); p.add_argument('--out',type=Path,default=ROOT/'DECK_TRANSFER')
    args=p.parse_args(); out=args.out.resolve()
    original=(SOURCE/'Actor/Pack/Item_Amiibo_DropTable_001.sbactorpack').read_bytes()
    # Check every proposed ID against actual local reward tables, not a guessed list.
    evidence=set()
    for f in (SOURCE/'Actor/Pack').glob('Item_Amiibo_DropTable_*.sbactorpack'):
        s=oead.Sarc(oead.yaz0.decompress(f.read_bytes()))
        for member in s.get_files():
            if member.name.endswith('.bdrop'):
                a=oead.aamp.ParameterIO.from_binary(member.data)
                for obj in a.objects.values():
                    for i in range(1,80):
                        key=f'ItemName{i:02}'
                        if key in obj.params: evidence.add(str(obj.params[key].v))
    assert set(ALL)<=evidence, set(ALL)-evidence
    profiles={'01_core':CORE,'02_collection':COLLECTION,'03_refill':REFILL}
    if args.owned:
        registered=json.loads(args.owned.read_text(encoding='utf-8-sig'))['obtained']
        if not isinstance(registered,list) or not all(isinstance(k,str) for k in registered):
            raise ValueError('obtained must be a list of item IDs')
        owned=set(registered)
        if owned-set(ALL): raise ValueError(f'Unknown item IDs: {owned-set(ALL)}')
        missing={k:v for k,v in CORE.items() if k not in owned}
        stage='core'
        if not missing: missing={k:v for k,v in COLLECTION.items() if k not in owned};stage='collection'
        if not missing: missing=REFILL;stage='refill'
        profiles={f'04_remaining_{stage}':missing}
    manifest={'target':'BOTW Switch; Archer Link only; table 008','source_sha256':sha(original),'profiles':{},'in_game_tested':False}
    for name,pool in profiles.items():
        b=build_pack(pool,original); report=validate_pack(b,pool,original)
        write_new(out/'profiles'/name/'romfs'/PACK,b)
        manifest['profiles'][name]=report
    bumps={f'Actor/Pack/{ACTOR}.bactorpack':262144,f'Actor/DropTable/{ACTOR}.bdrop':262144,f'Actor/AIProgram/{AI}.baiprog':65536,f'Actor/ActorLink/{ACTOR}.bxml':16384}
    manifest['resource_minimums']=bumps
    write_new(out/'manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    installer=ROOT/'DECK_TRANSFER/install.py'
    if installer.exists():write_new(out/'install.py',installer.read_bytes())
    write_new(ROOT/'owned.example.json',(json.dumps({'obtained':[]},indent=2)+'\n').encode())
    write_new(ROOT/'catalog.json',(json.dumps({k:{'name':v[0],'core':k in CORE} for k,v in ALL.items()},ensure_ascii=False,indent=2)+'\n').encode())
    # Reuse the existing fixture format and validation; new identities do not alter old files.
    spec=importlib.util.spec_from_file_location('fixture',ROOT.parent/'AMIIBO_TEST_V1/generate_test.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    for filename,model in [('rare_hub_archer.bin','0100000003530902'),('summon_epona_tp.bin','01000000034d0902'),('summon_wolf_link.bin','01030000024f0902')]:
        b=bytearray(mod.build());b[0x1DC:0x1E4]=bytes.fromhex(model)
        assert mod.validate_plain(b)
        write_new(out/'amiibo'/filename,b)
    assert (SOURCE/'Actor/Pack/Item_Amiibo_DropTable_001.sbactorpack').read_bytes()==original
    print(json.dumps({'output':str(out),'profiles':{k:len(v) for k,v in profiles.items()},'validation':'PASS - file structure only','live_game_modified':False},ensure_ascii=False))

if __name__=='__main__': main()
