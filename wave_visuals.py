"""Read the replicated wave visual substages for supported build CL127004."""
import os, struct, threading, time
_lock=threading.Lock()
_cache={'process':None,'actor':0,'next_scan':0}

def read_status(fd,base):
    def read(a,n):
        if not 0x10000<=a<0x7fffffffffff:return b''
        try:return os.pread(fd,n,a)
        except OSError:return b''
    def u64(a):
        b=read(a,8);return struct.unpack('<Q',b)[0] if len(b)==8 else 0
    def i32(a):
        b=read(a,4);return struct.unpack('<i',b)[0] if len(b)==4 else -1
    pool=base+0xDFE7000+2678336;cache={}
    def name(i):
        if i in cache:return cache[i]
        if not 0<=i<=0x1ffffff:return ''
        a=u64(pool+0x10+(i>>16)*8)+2*(i&65535);b=read(a,2)
        if len(b)!=2:return ''
        h=struct.unpack('<H',b)[0];length=h>>6
        if not 0<length<=150:return ''
        try:v=read(a+2,length*(2 if h&1 else 1)).decode('utf-16le' if h&1 else 'utf-8')
        except UnicodeError:return ''
        cache[i]=v;return v
    def valid(a):return bool(a and name(i32(u64(a+0x10)+0x18))=='CrEnviroWaveVisualsReplicationActor' and name(i32(a+0x18))=='CrEnviroWaveVisualsReplicationActor')
    with _lock:
        process=(base,os.fstat(fd).st_ino)
        if _cache['process']!=process:_cache.update(process=process,actor=0,next_scan=0)
        actor=_cache['actor']
        if not valid(actor):
            if time.monotonic()<_cache['next_scan']:return None
            _cache['next_scan']=time.monotonic()+10;actors=[];obj=base+0xe359240;chunks=u64(obj);n=i32(obj+0x14)
            if not 0<n<=3000000:return None
            for j in range((n+65535)//65536):
                chunk=u64(chunks+j*8);count=min(65536,n-j*65536);data=read(chunk,count*24)
                if len(data)!=count*24:continue
                for i in range(count):
                    a=struct.unpack_from('<Q',data,i*24)[0]
                    if valid(a):actors.append(a)
            if len(actors)!=1:return None
            actor=actors[0];_cache['actor']=actor
        b=read(actor+0x2a8,10)
        if len(b)!=10 or b[0] not in (0,1) or b[8]>3 or b[9]>3:return None
        return {'water_evaporated':bool(b[0]),'fadeout':b[8],'growback':b[9]}
