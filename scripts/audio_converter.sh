#!/bin/bash
# Audio Converter - Convert any supported audio format to raw PCM (RNNoise compatible)
# Usage: audio_converter.sh <input_file> <output_file>

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <input_file> <output_file>"
    echo "Converts any supported audio format to raw 16-bit PCM, mono, 48kHz"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file not found: $INPUT_FILE"
    exit 1
fi

# Convert to raw PCM: 16-bit signed, mono, 48kHz, little-endian
ffmpeg -i "$INPUT_FILE" \
    -acodec pcm_s16le \
    -ar 48000 \
    -ac 1 \
    -f s16le \
    -y \
    "$OUTPUT_FILE" 2>/dev/null

echo "Converted: $INPUT_FILE -> $OUTPUT_FILE"
