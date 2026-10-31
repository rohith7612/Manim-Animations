from fractions import Fraction
from pathlib import Path
import av
import numpy as np

def inspect(path):
    with av.open(str(path)) as c:
        video = next((s for s in c.streams if s.type == 'video'), None)
        if video is None:
            raise ValueError('Please upload a video file.')
        duration = float(c.duration / av.time_base) if c.duration else float(video.duration*video.time_base)
        if duration <= 0 or duration > 180:
            raise ValueError('Choose a video up to 3 minutes long.')
        return {'duration':duration,'width':video.width,'height':video.height,
                'has_audio':any(s.type=='audio' for s in c.streams)}

def audio_samples(path):
    resample=av.AudioResampler(format='fltp',layout='mono',rate=16000)
    chunks=[]
    with av.open(str(path)) as c:
        if not c.streams.audio:
            raise ValueError('This video has no narration. Upload a video with audio.')
        for frame in c.decode(audio=0):
            chunks.extend(f.to_ndarray().reshape(-1) for f in resample.resample(frame))
    chunks.extend(f.to_ndarray().reshape(-1) for f in resample.resample(None))
    if not chunks:
        raise ValueError('No readable audio was found.')
    return np.concatenate(chunks)

def mux(video_path, audio_path, output_path):
    with av.open(str(video_path)) as v, av.open(str(audio_path)) as a, av.open(str(output_path),'w',options={'movflags':'+faststart'}) as out:
        vs=v.streams.video[0]
        if not a.streams.audio:
            raise ValueError('Source audio is missing.')
        aus=a.streams.audio[0]
        ov=out.add_stream_from_template(vs);oa=out.add_stream_from_template(aus)
        def packets(container,stream,target):
            for p in container.demux(stream):
                if p.dts is not None:
                    t=Fraction(p.dts)*p.time_base;p.stream=target;yield t,p
        vi=iter(packets(v,vs,ov));ai=iter(packets(a,aus,oa))
        vp=next(vi,None);ap=next(ai,None)
        while vp is not None or ap is not None:
            if ap is None or (vp is not None and vp[0]<=ap[0]):
                out.mux(vp[1]);vp=next(vi,None)
            else:
                out.mux(ap[1]);ap=next(ai,None)

def poster(path, output):
    with av.open(str(path)) as c:
        for f in c.decode(video=0):
            if f.time >= 1:
                im=f.to_image();im.thumbnail((540,960));im.save(output);return

def srt(segments):
    def stamp(t):
        n=round(t*1000)
        return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'
    return '\n\n'.join(f"{i}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['text'].strip()}" for i,s in enumerate(segments,1))
