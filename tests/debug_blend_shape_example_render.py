"""Check the open BlendShapeExample's hold frames and subframe cuts via TiXL debug bridge.

Run with Python + Pillow while the generated BlendShapeExample home is open and paused.
Captures stay in the example's ignored cache; restores the original playhead.
"""
import argparse
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tixl_blender_bridge' / 'source'))
from tixl_bridge import call

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=9042)
args = parser.parse_args()
context = call('getContext', args.port)
assert 'BlendShapeExample' in context.get('compositionName', ''), context
assert not context['time']['isPlaying'], 'Pause before running render validation'
out = ROOT / 'examples' / '.tixl_cache' / 'BlendShapeExample' / 'validation' / 'render_smoke'
out.mkdir(parents=True, exist_ok=True)
frames = {}

def capture(t):
    call('setTime', args.port, timeInSecs=t)
    call('pumpFrames', args.port, count=3)
    path = out / f'{t:.6f}.png'
    call('screenshot', args.port, path=str(path))
    im = Image.open(path).convert('RGB')
    blue = sum(b > 40 and b > r * 1.4 and b > g * 1.05
               for r, g, b in im.getdata())
    assert blue > 20000, f'Mesh missing at {t:.6f}s: {blue} blue pixels'
    frames[t] = im

try:
    times = {i / 4 for i in range(64)}
    times.update(t + offset for t in (4, 8, 12) for offset in (-0.001, 0, 0.001))
    times.update((15.999, 0.001, 2.001, 6.001, 10.001, 14.001))
    for t in sorted(times):
        capture(t)
    for start in (0, 4, 8, 12):
        error = sum(ImageStat.Stat(ImageChops.difference(frames[start], frames[start + 2])).mean) / 3
        assert error < 0.01, f'Hold shading changed in world at {start}s: {error}'
    for cut in (4, 8, 12):
        error = sum(ImageStat.Stat(ImageChops.difference(frames[cut - 0.001], frames[cut])).mean) / 3
        assert error < 1, f'Discontinuous shading/geometry at {cut}s: {error}'
    print(f'BLEND_SHAPE_EXAMPLE_RENDER_OK: {len(times)} frames; stable holds and continuous subframe cuts')
finally:
    call('setTime', args.port, timeInSecs=context['time']['timeInSecs'])
