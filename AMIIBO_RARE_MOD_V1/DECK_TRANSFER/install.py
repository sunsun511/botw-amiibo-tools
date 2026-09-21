"""Python 3 standard-library installer: merge RSTB, backup, restore, dry-run.

Run only with the emulator fully closed. Targets one existing MOD romfs;
never traverses a game archive, NAND, keys or saves. No network access.
"""
from pathlib import Path
import argparse, hashlib, json, os, struct, sys, zlib

ROOT=Path(__file__).resolve().parent
PACK='Actor/Pack/Item_Amiibo_DropTable_008.sbactorpack'
RSTB='System/Resource/ResourceSizeTable.product.srsizetable'
STATE_DIR='.amiibo_rare_v1_backup'

def digest(b): return hashlib.sha256(b).hexdigest()

def yaz_decode(b):
    if b[:4]!=b'Yaz0': return b
    size=struct.unpack_from('>I',b,4)[0]
    if size>16*1024*1024: raise ValueError('Unexpectedly large RSTB')
    out=bytearray(); p=16
    while len(out)<size:
        code=b[p];p+=1
        for bit in range(7,-1,-1):
            if len(out)>=size: break
            if code&(1<<bit): out.append(b[p]);p+=1
            else:
                x,y=b[p:p+2];p+=2;dist=((x&15)<<8|y)+1;n=x>>4
                if n==0:n=b[p]+0x12;p+=1
                else:n+=2
                if dist>len(out) or len(out)+n>size: raise ValueError('Invalid Yaz0 match')
                for _ in range(n):out.append(out[-dist])
    return bytes(out)

def yaz_encode(b):
    # Valid literal-only Yaz0: avoids platform-specific compiled dependencies.
    out=bytearray(b'Yaz0'+struct.pack('>I',len(b))+b'\0'*8)
    for p in range(0,len(b),8):out.append(255);out.extend(b[p:p+8])
    return bytes(out)

def parse_rstb(raw):
    if raw[:4]!=b'RSTB':raise ValueError('Expected Switch RSTB header')
    count,names=struct.unpack_from('<II',raw,4)
    if len(raw)!=12+count*8+names*132:raise ValueError('RSTB size/endianness mismatch')
    entries=dict(struct.iter_unpack('<II',raw[12:12+count*8]))
    if len(entries)!=count:raise ValueError('Duplicate RSTB CRC entries')
    return entries,raw[12+count*8:],names

def merge_rstb(blob,minimums):
    entries,named,n=parse_rstb(yaz_decode(blob)); named=bytearray(named)
    for name,size in minimums.items():
        crc=zlib.crc32(name.encode())&0xffffffff
        entries[crc]=max(entries.get(crc,0),size)
        for i in range(n):
            if bytes(named[i*132:i*132+128]).split(b'\0')[0].decode()==name:
                old=struct.unpack_from('<I',named,i*132+128)[0]
                struct.pack_into('<I',named,i*132+128,max(old,size))
    raw=b'RSTB'+struct.pack('<II',len(entries),n)+b''.join(struct.pack('<II',k,v) for k,v in sorted(entries.items()))+named
    return yaz_encode(raw)

def safe_path(root,relative):
    p=root/relative
    if not p.resolve().is_relative_to(root.resolve()):raise ValueError(f'Path escapes romfs: {relative}')
    # Refuse symlinks even when they happen to resolve within this tree.
    q=p
    while q!=root:
        if q.is_symlink():raise ValueError(f'Symlink not supported: {q}')
        q=q.parent
    return p

def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.rare-v1-tmp')
    with tmp.open('xb') as f:f.write(data)
    try:os.replace(tmp,path)
    except Exception:
        tmp.unlink(missing_ok=True);raise

def run(romfs,profile,apply=False,restore=False):
    romfs=Path(romfs).expanduser().resolve()
    if romfs.name!='romfs' or not (romfs/'Actor').is_dir():raise ValueError('Select the existing character MOD romfs directory')
    if not (romfs/RSTB).is_file():raise ValueError('Existing character MOD RSTB is required; do not select an empty mod')
    backup=romfs.parent/STATE_DIR
    if backup.is_symlink():raise ValueError('Backup directory is a symlink')
    state_path=backup/'state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else None
    if state and state['romfs']!=str(romfs):raise ValueError('Backup belongs to a different romfs')
    if state:
        for rel,expected in state['installed'].items():
            p=safe_path(romfs,rel)
            actual=digest(p.read_bytes()) if p.exists() else None
            if actual!=expected:raise ValueError(f'File changed after installation; refusing overwrite: {rel}')
    if restore:
        if not state:raise ValueError('No installation backup found')
        data={}
        for rel,original_hash in state['original'].items():
            if original_hash is None:data[rel]=None
            else:
                b=(backup/'original'/rel).read_bytes()
                if digest(b)!=original_hash:raise ValueError('Backup checksum mismatch')
                data[rel]=b
    else:
        manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        if profile not in manifest['profiles']:raise ValueError('Unknown profile')
        pack=(ROOT/'profiles'/profile/'romfs'/PACK).read_bytes()
        if digest(pack)!=manifest['profiles'][profile]['sha256']:raise ValueError('Package checksum mismatch')
        data={PACK:pack,RSTB:merge_rstb(safe_path(romfs,RSTB).read_bytes(),manifest['resource_minimums'])}
    before={rel:(safe_path(romfs,rel).read_bytes() if safe_path(romfs,rel).exists() else None) for rel in data}
    result={'mode':'restore' if restore else profile,'apply':apply,'romfs':str(romfs),'files':{rel:('remove our added file' if b is None else f'{len(b)} bytes') for rel,b in data.items()},'backup':str(backup)}
    if not apply:return result
    if not state:
        if backup.exists():raise ValueError('Unfinished backup directory exists; inspect before retrying')
        backup.mkdir()
        state={'romfs':str(romfs),'original':{},'installed':{}}
        for rel,b in before.items():
            state['original'][rel]=digest(b) if b is not None else None
            if b is not None:
                p=backup/'original'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        # Recovery metadata is committed before any target write.
        state['installed']={rel:digest(b) if b is not None else None for rel,b in before.items()}
        atomic_write(state_path,json.dumps(state,indent=2).encode())
    try:
        for rel,b in data.items():
            p=safe_path(romfs,rel)
            if b is None:p.unlink(missing_ok=True)
            else:atomic_write(p,b)
        if restore:
            # Keep originals and a receipt; permit a later checked reinstall.
            atomic_write(backup/'restore_receipt.json',json.dumps(result,indent=2).encode())
            state['installed']={rel:(digest(b) if b is not None else None) for rel,b in data.items()}
            state['profile']='RESTORED'
            atomic_write(state_path,json.dumps(state,indent=2).encode())
        else:
            state['installed']={rel:digest(b) for rel,b in data.items()}
            state['profile']=profile
            atomic_write(state_path,json.dumps(state,indent=2).encode())
    except Exception:
        for rel,b in before.items():
            p=safe_path(romfs,rel)
            if b is None:p.unlink(missing_ok=True)
            else:atomic_write(p,b)
        raise
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--romfs',required=True,type=Path)
    p.add_argument('--profile',default='01_core')
    p.add_argument('--apply',action='store_true',help='Without this flag, only show the plan')
    p.add_argument('--restore',action='store_true')
    args=p.parse_args()
    print(json.dumps(run(args.romfs,args.profile,args.apply,args.restore),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
