#!/usr/bin/env bash
# Lay the backing track under the narrated video. The music dips whenever the voice
# speaks and comes up in the pauses. Usage: ./mix.sh build/video.mp4 build/data-lens.mp4
set -euo pipefail
IN=${1:-build/video.mp4}
OUT=${2:-build/data-lens.mp4}
LEN=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
python3 music.py "$LEN" build/music.wav
ffmpeg -y -v error -i "$IN" -i build/music.wav -filter_complex \
  "[0:a]asplit=2[voice][key];[1:a]volume=0.30[m];[m][key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=600[duck];[voice][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart "$OUT"
echo "wrote $OUT ($(printf '%.0f' "$LEN") s)"
