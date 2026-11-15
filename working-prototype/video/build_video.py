"""Cuts screencast footage (from kit.mjs) into a narrated video.

    python3 build.py --script script.json --footage footage[,footage-part2] --out out.mp4

script.json:
  { "size": [1920, 1080],
    "voice": { "engine": "auto", "azure": "en-US-AndrewNeural", "system": "Daniel", "rate": "0%" },
    "timeline": [ { "beats": ["intro"], "line": "What the narrator says." },
                  { "beats": ["load"], "line": "...", "still": { "load": 2 } } ] }

Voice engines: azure | system | silent | auto (azure if keys exist, then system, then silent).
A line the chosen engine fails on drops to the next engine and is listed at the end.
Needs ffmpeg and ffprobe on PATH; Python stdlib only.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

FPS = 30
LEAD_IN, TAIL = 0.9, 1.3  # unhurried: room to breathe around every line
XFADE = 0.8  # seconds each shot blends into the next
X264 = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(FPS)]
AAC = ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']
fallbacks = []


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'command failed: {" ".join(map(str, cmd[:5]))} ...\n{r.stderr[-2000:]}')
    return r.stdout


def duration(path):
    return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]).strip())


# ------------------------------------------------------------------ voice
def azure_target():
    """(url, key) from AZURE_SPEECH_KEY + AZURE_SPEECH_REGION, or an Azure AI Services endpoint host + key."""
    if os.environ.get('AZURE_SPEECH_KEY') and os.environ.get('AZURE_SPEECH_REGION'):
        return f"https://{os.environ['AZURE_SPEECH_REGION']}.tts.speech.microsoft.com/cognitiveservices/v1", os.environ['AZURE_SPEECH_KEY']
    if os.environ.get('AZURE_OPENAI_ENDPOINT') and os.environ.get('AZURE_OPENAI_API_KEY'):
        host = urlparse(os.environ['AZURE_OPENAI_ENDPOINT']).hostname
        return f'https://{host}/tts/cognitiveservices/v1', os.environ['AZURE_OPENAI_API_KEY']
    return None


def say_azure(text, cfg, out):
    target = azure_target()
    if not target:
        raise RuntimeError('no Azure speech keys in the environment')
    url, key = target
    ssml = (f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
            f"<voice name='{cfg.get('azure', 'en-US-AndrewNeural')}'><prosody rate='{cfg.get('rate', '0%')}'>{escape(text)}</prosody></voice></speak>")
    req = Request(url, data=ssml.encode(), method='POST', headers={
        'Ocp-Apim-Subscription-Key': key, 'Content-Type': 'application/ssml+xml',
        'X-Microsoft-OutputFormat': 'riff-48khz-16bit-mono-pcm', 'User-Agent': 'narrated-video-builder'})
    with urlopen(req, timeout=120) as r:
        out.write_bytes(r.read())


def say_system(text, cfg, out):
    tmp = out.with_suffix('.raw')
    if platform.system() == 'Darwin' and shutil.which('say'):
        subprocess.run(['say', '-v', cfg.get('system', 'Daniel'), '-o', f'{tmp}.aiff', text], check=True)
        src = f'{tmp}.aiff'
    elif shutil.which('espeak-ng'):
        subprocess.run(['espeak-ng', '-w', f'{tmp}.wav', text], check=True)
        src = f'{tmp}.wav'
    else:
        raise RuntimeError('no system voice (say or espeak-ng)')
    run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-ar', 48000, '-ac', 1, '-c:a', 'pcm_s16le', out])
    Path(src).unlink()


def say_silent(text, cfg, out):
    secs = max(1.5, len(text.split()) / 2.6)   # about 155 words a minute
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono', '-t', f'{secs:.2f}', '-c:a', 'pcm_s16le', out])


ENGINES = {'azure': say_azure, 'system': say_system, 'silent': say_silent}


def speak(text, cfg, build):
    want = cfg.get('engine', 'auto')
    order = ['azure', 'system', 'silent'] if want == 'auto' else [want, 'system', 'silent']
    if want == 'auto' and not azure_target():
        order.remove('azure')
    (build / 'voice').mkdir(parents=True, exist_ok=True)
    for engine in dict.fromkeys(order):
        key = f"{engine}|{cfg.get('azure')}|{cfg.get('system')}|{cfg.get('rate')}|{text}"
        out = build / 'voice' / f'{engine}-{hashlib.sha1(key.encode()).hexdigest()[:16]}.wav'
        if out.exists():
            return out, engine
        try:
            ENGINES[engine](text, cfg, out)
            return out, engine
        except Exception as e:  # noqa: BLE001 - any failure drops to the next engine
            out.unlink(missing_ok=True)
            print(f'  voice {engine} failed ({e}); trying the next engine', file=sys.stderr)
    sys.exit('no voice engine worked')


# ------------------------------------------------------------------ footage
class Footage:
    def __init__(self, roots):
        self.beats, self.cache = {}, {}
        for root in roots:
            for b in json.loads((root / 'beats.json').read_text()):
                self.beats[b['id']] = {**b, 'root': root}   # a later part replaces the same beat

    def frames(self, b):
        k = (b['root'], b['who'])
        if k not in self.cache:
            self.cache[k] = json.loads((b['root'] / b['who'] / 'frames.json').read_text())
        return self.cache[k]

    def holds(self, bid, still=None):
        """Each frame of the beat and how long it stays up. `still` caps a stretch where nothing changes."""
        b = self.beats[bid]
        fr, t0, t1 = self.frames(b), b['t0'], b['t1']
        before = [f for f in fr if f[0] <= t0]
        inside = [f for f in fr if t0 < f[0] < t1]
        seq = ([[t0, before[-1][1]]] if before else []) + inside
        if not seq:                      # a screen that never changed: use the first frame it ever sent
            seq = [[t0, fr[0][1]]]
        seq[0] = [t0, seq[0][1]]
        out = []
        for (ta, fa), nxt in zip(seq, seq[1:] + [[t1, None]]):
            d = max(0.001, (nxt[0] - ta) / 1000)
            out.append((fa, min(d, still) if still else d))
        return out

    def clip(self, bid, out, speed, size, still=None):
        b = self.beats[bid]
        holds = self.holds(bid, still)
        d = (b['root'] / b['who']).resolve()
        lines = [f"file '{d / fa}'\nduration {du:.4f}" for fa, du in holds] + [f"file '{d / holds[-1][0]}'"]
        lst = out.with_suffix('.txt')
        lst.write_text('\n'.join(lines) + '\n')
        w, h = size
        vf = (f'setpts=PTS/{speed:.4f},fps={FPS},scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,'
              f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=white,format=yuv420p')
        run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf', vf, *X264, '-an', out])

    def raw(self, bid, still=None):
        return sum(d for _, d in self.holds(bid, still))


def segment(foot, n, it, voice, size, build, out):
    vdur = duration(voice) if voice else 0
    need = vdur + LEAD_IN + TAIL
    still = it.get('still', {})
    raw = {b: foot.raw(b, still.get(b)) for b in it['beats']}
    waits = [b for b in it['beats'] if foot.beats[b].get('wait')]
    plain = sum(v for b, v in raw.items() if b not in waits)
    speed = {b: 1.0 for b in it['beats']}
    if waits:   # waits shrink to what the voice still needs, never below two seconds in total
        target = max(2.0, need - plain) / len(waits)
        for b in waits:
            speed[b] = max(1.0, raw[b] / target)
    elif plain > need + 3:
        for b in it['beats']:
            speed[b] = min(1.35, plain / (need + 2))
    clips = []
    for b in it['beats']:
        c = build / 'clips' / f'{n:02d}-{b}.mp4'
        foot.clip(b, c, speed[b], size, still.get(b))
        clips.append(c)
    lst = build / 'clips' / f'{n:02d}.txt'
    lst.write_text(''.join(f"file '{c}'\n" for c in clips))
    body = build / 'clips' / f'{n:02d}-body.mp4'
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', body])
    dur = max(duration(body), need)
    if voice:
        ain = ['-i', voice]
        af = f'[1:a]adelay={int(LEAD_IN * 1000)}:all=1,apad,atrim=0:{dur:.3f},aformat=sample_rates=48000:channel_layouts=stereo[a]'
    else:
        ain = ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
        af = f'[1:a]atrim=0:{dur:.3f}[a]'
    run(['ffmpeg', '-y', '-v', 'error', '-i', body, *ain, '-filter_complex', f'[0:v]tpad=stop_mode=clone:stop_duration={dur:.3f}[v];{af}',
         '-map', '[v]', '-map', '[a]', '-t', f'{dur:.3f}', *X264, *AAC, out])


def crossfade(segs, out):
    """Join the shots with a soft cross-fade instead of hard cuts. The fade sits inside the
    silent margins around each line, so voices never overlap."""
    if len(segs) == 1:
        shutil.copyfile(segs[0], out)
        return
    durs = [duration(s) for s in segs]
    inputs = []
    for s in segs:
        inputs += ['-i', str(s)]
    parts, v, a, t = [], '[0:v]', '[0:a]', durs[0]
    for i in range(1, len(segs)):
        t -= XFADE
        nv, na = f'[v{i}]', f'[a{i}]'
        parts.append(f'{v}[{i}:v]xfade=transition=fade:duration={XFADE}:offset={t:.3f}{nv}')
        parts.append(f'{a}[{i}:a]acrossfade=d={XFADE}:c1=tri:c2=tri{na}')
        v, a, t = nv, na, t + durs[i]
    graph = build_dir_file(out, 'xfade.txt')
    graph.write_text(';'.join(parts))
    run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex_script', graph, '-map', v, '-map', a, *X264, *AAC, out])


def build_dir_file(out, name):
    return Path(out).with_name(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--script', default='script.json')
    ap.add_argument('--footage', default='footage')
    ap.add_argument('--out', default='build/video.mp4')
    ap.add_argument('--build', default='build')
    a = ap.parse_args()
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool):
            sys.exit(f'{tool} is not installed: run scripts/setup.sh')
    script = json.loads(Path(a.script).read_text())
    size = tuple(script.get('size', [1920, 1080]))
    cfg = script.get('voice', {})
    build = Path(a.build).resolve()
    (build / 'clips').mkdir(parents=True, exist_ok=True)
    (build / 'segs').mkdir(parents=True, exist_ok=True)
    foot = Footage([Path(p) for p in a.footage.split(',')])
    segs = []
    for n, it in enumerate(script['timeline']):
        voice = None
        if it.get('line'):
            voice, engine = speak(it['line'], cfg, build)
            if cfg.get('engine', 'auto') in ('auto', 'azure') and engine != 'azure':
                fallbacks.append((n, engine))
        seg = build / 'segs' / f'seg-{n:02d}.mp4'
        segment(foot, n, it, voice, size, build, seg)
        segs.append(seg)
        print(f'  seg {n:02d}  {duration(seg):5.1f}s  {", ".join(it["beats"])}')
    joined = build / 'joined.mp4'
    crossfade(segs, joined)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    run(['ffmpeg', '-y', '-v', 'error', '-i', joined, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-c:v', 'copy', *AAC, '-movflags', '+faststart', out])
    print(f'done: {out}  ({duration(out):.0f}s)')
    if fallbacks:
        print('NOTE: these segments used a fallback voice, not Azure: ' + ', '.join(f'{n} ({e})' for n, e in fallbacks))


if __name__ == '__main__':
    main()
