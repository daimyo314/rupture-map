#!/usr/bin/env python3
"""Local static server and read-only StarRupture CL127004 position reader."""
import argparse, errno, hashlib, ipaddress, json, math, os, re, struct, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import buildings as building_tracker
import base_tracker
import infection_tracker

ROOT = Path(__file__).resolve().parent
GAME = Path('/legames/steamapps/common/StarRupture')
try:
    ORE_CATALOG = json.loads((ROOT / 'ore-catalog.json').read_text())['entries']
except (OSError, ValueError, KeyError):
    ORE_CATALOG = []

try:
    OBJECTIVE_CATALOG = json.loads((ROOT / 'objectives-catalog.json').read_text())
    LANDMARKS = json.loads((ROOT / 'landmarks-catalog.json').read_text())
except (OSError, ValueError, KeyError):
    OBJECTIVE_CATALOG, LANDMARKS = {}, []

OFFSETS = (0x0E0236D0, 0x230, 0x38, 0x30, 0x368, 0x1B8, 0x140)

GAME_LOG = Path('/legames/steamapps/compatdata/1631270/pfx/drive_c/users/steamuser/AppData/Local/StarRupture/Saved/Logs/StarRupture.log')
_connection_cache = (0, None)

def remote_identity():
    # Only read the Browse destination; do not retain query strings or tokens.
    global _connection_cache
    now=time.monotonic()
    if now-_connection_cache[0]<5:return _connection_cache[1]
    result=None
    try:
        browse=''
        with GAME_LOG.open('rb') as f:
            f.seek(0,os.SEEK_END);cursor=f.tell();following=b'';needle=b'LogNet: Browse: '
            while cursor:
                size=min(cursor,65536);cursor-=size;f.seek(cursor)
                block=f.read(size)+following
                at=block.rfind(needle)
                if at>=0:
                    browse=block[at+len(needle):].split(b'\n',1)[0].decode('utf-8','replace')
                    break
                following=block[:512]
        match=re.match(r'^((?:[0-9]{1,3}\.){3}[0-9]{1,3}):([0-9]+)(?:/|\?|$)',browse)
        if match and 1<=int(match.group(2))<=65535:
            host=str(ipaddress.ip_address(match.group(1)))
            result=hashlib.sha256(f'{host}:{int(match.group(2))}'.encode()).hexdigest()
    except (OSError, ValueError):pass
    _connection_cache=(now,result)
    return result

def connection_info(read, world):
    try:
        driver=struct.unpack('<Q',read(world+0x38,8))[0]
        server=struct.unpack('<Q',read(driver+0xf8,8))[0] if driver else 0
        if not server:return {'mode':'local'}
        identity=remote_identity()
        try: names=json.loads((ROOT/'server-worlds.json').read_text())
        except (OSError,ValueError): names={}
        return {'mode':'client','server_id':identity,'world_name':names.get(identity) if identity else None}
    except (OSError,RuntimeError,struct.error):return {'mode':'unknown'}

def wave_status(read, ptr, world):
    # NextTime is a replicated server-world deadline, not a duration.
    try:
        game_state=ptr(world+0x1b0); timer=ptr(game_state+0x318)
        deadline,phase,paused=struct.unpack('<fiB',read(timer+0x2a8,9))
        local_clock=struct.unpack('<d',read(world+0x180,8))[0]
        delta=struct.unpack('<f',read(game_state+0x2e0,4))[0]
        clock=local_clock+delta
        if not math.isfinite(deadline) or not math.isfinite(clock) or deadline<=0 or clock<=0 or phase<0 or phase>100 or paused not in (0,1):
            return None
        remaining=deadline-clock
        frequency_value=read(game_state+0xb2c,1)[0]
        frequency={0:'Rarely',1:'Normal',2:'Often'}.get(frequency_value)
        if not -300<=remaining<=86400:return None
        return {'seconds':max(0,remaining),'phase':phase,'paused':bool(paused),'pending':remaining<=0,'clock':clock,'deadline':deadline,'frequency':frequency}
    except (OSError,RuntimeError,struct.error):return None

def radiation_status(read, ptr, world):
    # CL127004: the map replication helper carries the world's radiation level.
    try:
        game_state=ptr(world+0x1b0); helper=ptr(game_state+0x368)
        level=struct.unpack('<i',read(helper+0x468,4))[0]
        return level if level in (0,1) else None
    except (OSError,RuntimeError,struct.error):return None

def other_player_markers(read, ptr, world, pawn):
    # Replicated map-marker positions may update intermittently.
    try:
        def u64(a): return struct.unpack('<Q',read(a,8))[0]
        def i32(a): return struct.unpack('<i',read(a,4))[0]
        def string(a):
            address=u64(a); size=i32(a+8)
            if not 1<=size<=128:return ''
            return read(address,size*2).decode('utf-16le').rstrip('\0')
        state=ptr(world+0x1b0);helper=ptr(state+0x368)
        local_state=ptr(pawn+0x6e0); local_name=string(local_state+0x348)
        if not local_name:return None
        array=u64(state+0x2c0); count=i32(state+0x2c8)
        if not 0<=count<=32:return None
        present=set()
        for i in range(count):
            ps=u64(array+i*8)
            if not ps:continue
            flags=read(ps+0x2b2,1)[0]
            if not flags&0x20:present.add(string(ps+0x348))
        records=u64(helper+0x7b8); count=i32(helper+0x7c0)
        if not 0<=count<=32:return None
        result=[]
        for i in range(count):
            item=records+i*0x40;name=string(item+0x10)
            if not name or name not in present:continue
            x,y,r,g,b,a,yaw,flags=struct.unpack('<7fB',read(item+0x20,29))
            if not all(math.isfinite(v) for v in (x,y,r,g,b,a)) or abs(x)>1e7 or abs(y)>1e7:continue
            color=[max(0,min(1,c)) for c in (r,g,b)]
            result.append({'id':i32(item),'name':name,'x':x,'y':y,'yaw':yaw%360 if math.isfinite(yaw) and abs(yaw)<1e6 else None,'color':color,'flags':flags})
        # Equal names cannot identify the local marker safely. Keep all ambiguous
        # records rather than silently hiding another player.
        local_matches=[v for v in result if v['name']==local_name]
        if len(local_matches)==1:result.remove(local_matches[0])
        elif len(local_matches)>1:
            for v in local_matches:v['possibly_local']=True
        ids=[v['id'] for v in result]
        if len(ids)!=len(set(ids)):return None
        return result
    except (OSError,RuntimeError,struct.error,UnicodeError,ValueError):return None

def position():
    manifest = (GAME.parent.parent / 'appmanifest_1631270.acf').read_text() if (GAME.parent.parent / 'appmanifest_1631270.acf').is_file() else ''
    if not (GAME / 'CL127004').is_file() or not re.search(r'"buildid"\s+"26781824"', manifest):
        raise RuntimeError('Unsupported game build; tracking is limited to CL127004')
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            command = (entry/'cmdline').read_bytes()
        except (OSError, PermissionError):
            continue
        if b'StarRuptureGameSteam-Win64-Shipping.exe' not in command: continue
        try:
            maps = (entry/'maps').read_text()
            match = re.search(r'^([0-9a-f]+)-[0-9a-f]+\s+\S+\s+00000000\s+.*StarRuptureGameSteam-Win64-Shipping\.exe$', maps, re.M)
            if not match: continue
            base = int(match.group(1),16)
            fd = os.open(entry/'mem',os.O_RDONLY)
            try:
                def read(addr, n):
                    data=os.pread(fd,n,addr)
                    if len(data)!=n: raise RuntimeError('Incomplete game memory read')
                    return data
                def ptr(addr):
                    value=struct.unpack('<Q',read(addr,8))[0]
                    if value < 0x10000 or value > 0x7fffffffffff: raise RuntimeError('Game is not in a playable world')
                    return value
                world=ptr(base+OFFSETS[0]); instance=ptr(world+OFFSETS[1]); players=ptr(instance+OFFSETS[2])
                count=struct.unpack('<i',read(instance+OFFSETS[2]+8,4))[0]
                if not 1 <= count <= 4: raise RuntimeError('Local player is not available')
                local=ptr(players); controller=ptr(local+OFFSETS[3]); pawn=ptr(controller+OFFSETS[4]); root=ptr(pawn+OFFSETS[5])
                xyz=struct.unpack('<ddd',read(root+OFFSETS[6],24))
                if not all(math.isfinite(v) and abs(v)<100000000 for v in xyz): raise RuntimeError('Invalid position data')
                # Controller yaw is the horizontal look direction, in degrees.
                yaw = None
                try:
                    value = struct.unpack('<d', read(controller + 0x340, 8))[0]
                    if math.isfinite(value) and abs(value) < 1000000: yaw = value % 360
                except (OSError, RuntimeError, struct.error):
                    pass
                return {'ok':True,'x':xyz[0],'y':xyz[1],'z':xyz[2],'yaw':yaw,'time':time.time(),'connection':connection_info(read,world),'wave':wave_status(read,ptr,world),'radiation_level':radiation_status(read,ptr,world),'other_players':other_player_markers(read,ptr,world,pawn)}
            finally: os.close(fd)
        except (FileNotFoundError, ProcessLookupError): continue
        except PermissionError: raise RuntimeError('Cannot read game process; start the tracker with the same user and check Linux process permissions')
        except OSError as exc: raise RuntimeError('Game position is temporarily unavailable') from exc
    raise RuntimeError('StarRupture is not running or is not visible to this process')

RESOURCE_REWARDS = {'I_Hydrobulb_C':'Hydrobulb','I_Polifruit_C':'Polifruit','I_Oxallop_C':'Oxallop','I_Purplant_C':'Purplant','I_SerpentRoot_C':'Serpent Root','I_Prickler_C':'Prickler','I_PrismHerb_C':'Prism Herb','I_Sulheart_C':'Sulheart','I_StarTears_C':'Star Tears','I_FoxEgg_C':'Vulpir Egg','I_CrabEgg_C':'Coralion Egg','I_Glowcap_C':'Glowcap','I_Grubbler_C':'Grubbler'}

ORE_CHUNKS = {'I_CalciumOre_C':'Calcium chunk','I_TitaniumOre_C':'Titanium chunk','I_WolframOre_C':'Wolfram chunk','I_HeliumOre_C':'Helium-3 chunk','I_FireWaveOre_C':'Ignitium','I_QuartzOre_C':'Quartz'}
GATHERABLE_CLASSES = {'BP_SikkimRhubarb_Fruit_C':'Glowcap','BP_Gatherable_GoldFruitTree_Large_A_C':'Grubbler','BP_Gatherable_GoldFruitTree_Large_F_C':'Grubbler','BP_Gatherable_Thornfruit_Fruit_C':'Prickler','BP_Gatherable_NootkaLupine_Fruit_C':'Prism Herb'}

def resources(radius_m=100):
    player=position()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            if b'StarRuptureGameSteam-Win64-Shipping.exe' not in (entry/'cmdline').read_bytes(): continue
            maps=(entry/'maps').read_text();match=re.search(r'^([0-9a-f]+)-[0-9a-f]+\s+\S+\s+00000000\s+.*StarRuptureGameSteam-Win64-Shipping\.exe$',maps,re.M)
            if not match: continue
            base=int(match.group(1),16);fd=os.open(entry/'mem',os.O_RDONLY)
            break
        except (FileNotFoundError,ProcessLookupError,PermissionError):continue
    else: raise RuntimeError('Game process unavailable')
    try:
        def read(addr,n):
            if addr<0x10000 or addr>0x7fffffffffff:return b''
            try:return os.pread(fd,n,addr)
            except OSError:return b''
        def u64(addr):
            b=read(addr,8);return struct.unpack('<Q',b)[0] if len(b)==8 else 0
        def i32(addr):
            b=read(addr,4);return struct.unpack('<i',b)[0] if len(b)==4 else 0
        pool=base+0xDFE7000+2678336
        namecache={}
        def name(idx):
            if idx in namecache:return namecache[idx]
            if idx<0 or idx>0x1ffffff:return ''
            chunk=u64(pool+0x10+(idx>>16)*8);address=chunk+2*(idx&65535);b=read(address,2)
            if len(b)!=2:return ''
            header=struct.unpack('<H',b)[0];length=header>>6
            if not 0<length<=150:return ''
            try:value=read(address+2,length*(2 if header&1 else 1)).decode('utf-16le' if header&1 else 'utf-8')
            except UnicodeError:value=''
            namecache[idx]=value;return value
        world=u64(base+OFFSETS[0]);level_list=u64(world+0x1c8);level_count=i32(world+0x1d0)
        if not 0<level_count<5000:raise RuntimeError('World levels are unavailable')
        seen=set();out=[];meteor_class_cache={}
        def is_meteor_class(cls):
            if cls in meteor_class_cache:return meteor_class_cache[cls]
            start=cls;visited=set();result=False
            while cls and cls not in visited and len(visited)<32:
                visited.add(cls)
                if name(i32(cls+0x18))=='CrMeteOreActor':
                    result=True;break
                cls=u64(cls+0x40)
            meteor_class_cache[start]=result;return result
        for z in range(level_count):
            level=u64(level_list+z*8);actors=u64(level+0xa0);n=i32(level+0xa8)
            if not 0<n<100000:continue
            raw=read(actors,n*8)
            if len(raw)!=n*8:continue
            for (actor,) in struct.iter_unpack('<Q',raw):
                if not actor or actor in seen:continue
                seen.add(actor);cls=u64(actor+0x10);classname=name(i32(cls+0x18));is_foundable=False
                # Ground deposits use socket actors; the generic socket does not name its mineral.
                if classname in ('BP_OreSocket_C','BP_GoethiteOreSocket_C'):
                    kind='Goethite deposit' if classname=='BP_GoethiteOreSocket_C' else 'Ore deposit (type unknown)'
                    is_socket=True
                    is_ore_chunk=False
                elif classname.startswith('BP_Gatherable_') or classname in ('BP_Purplant_C','BP_SikkimRhubarb_Fruit_C'):
                    reward=u64(actor+0x310);kind=RESOURCE_REWARDS.get(name(i32(reward+0x18))) if reward else None
                    if not kind:kind=GATHERABLE_CLASSES.get(classname)
                    is_socket=False
                    is_ore_chunk=False
                elif classname in ('BP_CalciumMeteOreChunk_C','BP_TitaniumMeteOreChunk_C','BP_WolframMeteOreChunk_C','BP_HeliumMeteOreChunk_C','BP_FireWaveMeteOreChunk_C','BP_QuartzOre_C'):
                    resource=u64(actor+0x2d8);kind=ORE_CHUNKS.get(name(i32(resource+0x18))) if resource else None
                    is_socket=False
                    is_ore_chunk=True
                elif classname.startswith('BP_Foundable_Drone_') and classname.endswith('_C'):
                    kind='Drone Wreck';is_socket=False;is_ore_chunk=False;is_foundable=True
                elif 'meteore' in classname.lower() and is_meteor_class(cls):
                    kind='Meteorite';is_socket=False;is_ore_chunk=True
                else:continue
                if not kind:continue
                root=u64(actor+0x1b8)
                if is_foundable and u64(root+0xc8):continue
                rawpos=read(root+0x140,24)
                if len(rawpos)!=24:continue
                x,y,zpos=struct.unpack('<ddd',rawpos)
                if not all(math.isfinite(v) and abs(v)<1e7 for v in (x,y,zpos)):continue
                if math.hypot(x-player['x'],y-player['y'])>radius_m*100:continue
                if is_socket:
                    matches=[row for row in ORE_CATALOG if abs(row[0]-x)<=50 and abs(row[1]-y)<=50]
                    if len(matches)==1:kind=matches[0][2]+' deposit'
                flag=read(actor+0x320,1) if kind=='Meteorite' else (read(actor+0x31d,1) if not is_socket and not is_ore_chunk and not is_foundable else b'')
                out.append({'type':kind,'x':round(x,1),'y':round(y,1),'depleted':bool(flag[0]) if len(flag)==1 else None})
        # Replicated map foundables: type 1 is a pre-placed lootable dead body.
        try:
            state=u64(world+0x1b0);helper=u64(state+0x368)
            marker_array=u64(helper+0x698);marker_count=i32(helper+0x6a0)
            if 0<=marker_count<=10000 and (marker_count==0 or marker_array):
                for index in range(marker_count):
                    data=read(marker_array+index*0x28+0x18,9)
                    if len(data)!=9:continue
                    x,y,kind=struct.unpack('<ffB',data)
                    if kind==1 and all(math.isfinite(v) and abs(v)<1e7 for v in (x,y)):
                        out.append({'type':'Dead Body (foundable)','x':round(x,1),'y':round(y,1),'depleted':None})
        except (OSError,RuntimeError,struct.error):pass
        return {'ok':True,'resources':out,'radius_m':radius_m,'time':time.time()}
    finally:os.close(fd)

def infection_hud():
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            if b'StarRuptureGameSteam-Win64-Shipping.exe' not in (entry/'cmdline').read_bytes():continue
            match=re.search(r'^([0-9a-f]+)-[0-9a-f]+\s+\S+\s+00000000\s+.*StarRuptureGameSteam-Win64-Shipping\.exe$',(entry/'maps').read_text(),re.M)
            if not match:continue
            fd=os.open(entry/'mem',os.O_RDONLY)
            try:return {'ok':True, **infection_tracker.status(fd,int(match.group(1),16))}
            finally:os.close(fd)
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:raise RuntimeError('Cannot read game process')
    raise RuntimeError('Game process unavailable')

def buildings(scan_rails=False):
    player=position()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            if b'StarRuptureGameSteam-Win64-Shipping.exe' not in (entry/'cmdline').read_bytes():continue
            match=re.search(r'^([0-9a-f]+)-[0-9a-f]+\s+\S+\s+00000000\s+.*StarRuptureGameSteam-Win64-Shipping\.exe$',(entry/'maps').read_text(),re.M)
            if not match:continue
            fd=os.open(entry/'mem',os.O_RDONLY)
            try:return building_tracker.scan(fd,int(match.group(1),16),player,scan_rails=scan_rails)
            finally:os.close(fd)
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:raise RuntimeError('Cannot read game process')
    raise RuntimeError('Game process unavailable')

def death_drops():
    player=position()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            if b'StarRuptureGameSteam-Win64-Shipping.exe' not in (entry/'cmdline').read_bytes():continue
            match=re.search(r'^([0-9a-f]+)-[0-9a-f]+\s+\S+\s+00000000\s+.*StarRuptureGameSteam-Win64-Shipping\.exe$',(entry/'maps').read_text(),re.M)
            if not match:continue
            fd=os.open(entry/'mem',os.O_RDONLY)
            try:return building_tracker.scan(fd,int(match.group(1),16),player,scan_drops=True)
            finally:os.close(fd)
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:raise RuntimeError('Cannot read game process')
    raise RuntimeError('Game process unavailable')

def base_data():
    player=position()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            if b'StarRuptureGameSteam-Win64-Shipping.exe' not in (entry/'cmdline').read_bytes():continue
            match=re.search(r'^([0-9a-f]+)-[0-9a-f]+\s+\S+\s+00000000\s+.*StarRuptureGameSteam-Win64-Shipping\.exe$',(entry/'maps').read_text(),re.M)
            if not match:continue
            fd=os.open(entry/'mem',os.O_RDONLY)
            try:
                base=int(match.group(1),16)
                try: bases,cyst_status=base_tracker.progress(fd,base,LANDMARKS);base_error=None
                except (RuntimeError,OSError,struct.error) as exc:bases=None;cyst_status=None;base_error=str(exc)
                try: cysts=building_tracker.scan(fd,base,player,radius_m=10000,scan_cysts=True)['cysts'];cyst_error=None
                except (RuntimeError,OSError,struct.error) as exc:cysts=None;cyst_error=str(exc)
                return {'ok':True,'bases':bases,'base_error':base_error,'cysts':cysts,'cyst_error':cyst_error,'cyst_status':cyst_status}
            finally:os.close(fd)
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:raise RuntimeError('Cannot read game process')
    raise RuntimeError('Game process unavailable')

def objectives():
    player=position()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            if b'StarRuptureGameSteam-Win64-Shipping.exe' not in (entry/'cmdline').read_bytes():continue
            match=re.search(r'^([0-9a-f]+)-[0-9a-f]+\s+\S+\s+00000000\s+.*StarRuptureGameSteam-Win64-Shipping\.exe$',(entry/'maps').read_text(),re.M)
            if not match:continue
            base=int(match.group(1),16);fd=os.open(entry/'mem',os.O_RDONLY);break
        except (OSError,PermissionError):continue
    else:raise RuntimeError('Game process unavailable')
    try:
        def read(addr,n):
            if not 0x10000<=addr<0x7fffffffffff:raise RuntimeError('Objective data is unavailable')
            b=os.pread(fd,n,addr)
            if len(b)!=n:raise RuntimeError('Incomplete objective data')
            return b
        def u64(addr):return struct.unpack('<Q',read(addr,8))[0]
        def i32(addr):return struct.unpack('<i',read(addr,4))[0]
        world=u64(base+OFFSETS[0]);game_state=u64(world+0x1b0);owner=u64(game_state+0x380);arr=u64(owner+0x2a8);count=i32(owner+0x2b0)
        if not 0<=count<=256:raise RuntimeError('Invalid objective count')
        entries=[];completed=0
        for index in range(count):
            a=arr+index*0x30;guid='-'.join(f'{v:08X}' for v in struct.unpack('<4I',read(a+0x0c,16)));state=read(a+0x1c,1)[0]
            if state==2:completed+=1
            if state!=1:continue
            data=OBJECTIVE_CATALOG.get(guid,{});items=[];count_sub=i32(a+0x28);ptr=u64(a+0x20)
            if not 0<=count_sub<=64:raise RuntimeError('Invalid sub-objective count')
            for n in range(count_sub):
                initial,current,target,show=struct.unpack('<iiiB',read(ptr+n*16,13));names=data.get('subobjectives',[]);label=names[n] if n<len(names) and names[n] else 'Objective step'
                items.append({'text':label,'current':current if show and abs(current)<100000000 else None,'target':target if show and abs(target)<100000000 else None})
            entries.append({'name':data.get('name','Unknown objective'),'steps':items})
        nearby=[v for v in LANDMARKS if math.hypot(v['x']-player['x'],v['y']-player['y'])<=10000]
        return {'ok':True,'active':entries,'completed':completed,'total':count,'landmarks':nearby}
    finally:os.close(fd)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        if self.headers.get('Host', '') not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            self.send_error(403); return
        if self.path in ('/api/position','/api/resources','/api/objectives','/api/buildings','/api/rails','/api/bases','/api/infection-hud','/api/death-drops'):
            try: payload=death_drops() if self.path=='/api/death-drops' else infection_hud() if self.path=='/api/infection-hud' else (position() if self.path=='/api/position' else (resources() if self.path=='/api/resources' else (objectives() if self.path=='/api/objectives' else (base_data() if self.path=='/api/bases' else buildings(self.path=='/api/rails')))))
            except Exception as exc: payload={'ok':False,'error':str(exc)}
            body=json.dumps(payload).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        else: super().do_GET()
    def end_headers(self):
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    try:
        httpd=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError as exc:
        if exc.errno==errno.EADDRINUSE:
            parser.exit(1, f'Port {args.port} is already in use. Stop the existing map server or choose another port with --port.\n')
        raise
    print(f'Rupture Map: http://127.0.0.1:{args.port}/',flush=True)
    httpd.serve_forever()
