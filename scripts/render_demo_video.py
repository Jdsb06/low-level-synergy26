"""Render the recorded terminal events at their original times; no desktop-capture claim."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "demo/terminal-replay.mp4")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("video exists; choose a fresh output path")
    cast = ROOT / "demo/terminal.cast"
    entries = [json.loads(line) for line in cast.read_text().splitlines()]
    events = entries[1:]
    duration = events[-1][0] + 2  # Explicit final-frame hold; event timestamps are unchanged.
    width, height, fps = 1440, 900, 15
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 18)
    title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 21)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
    assert font.getlength('M' * 128) <= width - 48
    command = ['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{width}x{height}',
               '-r', str(fps), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
               '-threads', '2', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(args.output)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    text, index = '', 0
    for frame in range(math.ceil(duration * fps)):
        stamp = frame / fps
        while index < len(events) and events[index][0] <= stamp:
            assert events[index][1] == 'o'
            text += events[index][2]
            index += 1
        visible = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text).replace('\r\n', '\n').replace('\r', '')
        lines = []
        for line in visible.expandtabs(8).split('\n'):
            lines.extend(textwrap.wrap(line, width=128, replace_whitespace=False, drop_whitespace=False) or [''])
        image = Image.new('RGB', (width, height), '#0e1726')
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, 60), fill='#19334b')
        draw.text((24, 17), 'libmemctl - recorded terminal replay', font=title, fill='#e9f4fb')
        draw.text((width - 95, 23), f'{stamp:05.1f}s', font=small, fill='#a4dce5')
        for row, line in enumerate(lines[-32:]):
            draw.text((24, 78 + row * 24), line, font=font, fill='#e0e8ee')
        draw.text((24, height - 27), 'Actual PTY output | no desktop capture | source ce2e34f55760',
                  font=small, fill='#94b9ca')
        process.stdin.write(image.tobytes())
    process.stdin.close()
    errors = process.stderr.read().decode()
    if process.wait() != 0:
        raise RuntimeError(errors)
    record = dict(command=command, cast_sha256=hashlib.sha256(cast.read_bytes()).hexdigest(),
                  video_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
                  duration_seconds=duration, fps=fps, final_hold_seconds=2,
                  scope='Rendered terminal replay at recorded event times; not an unedited desktop screen capture.')
    (ROOT / 'demo/video.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
