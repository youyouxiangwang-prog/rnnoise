# RNNoise Multi-Format Audio Support

This extension adds support for multiple audio input formats to RNNoise, which natively only accepts raw 16-bit PCM files at 48kHz.

## Supported Formats

✅ **Input Formats:**
- AAC (.aac, .m4a)
- MP3 (.mp3)
- M4A (.m4a)
- WAV (.wav)
- WMA (.wma)
- OGG (.ogg)
- FLAC (.flac)
- AIFF (.aiff)

✅ **Output Format:**
- Raw 16-bit signed PCM, mono, 48kHz (RNNoise native format)

## Quick Start

### Option 1: Using the Wrapper Script

```bash
# Convert any supported format to raw PCM
./scripts/audio_converter.sh input.mp3 output.raw

# Denoise the converted file
./examples/rnnoise_demo output.raw denoised.raw
```

### Option 2: Using Docker (Recommended for Testing)

```bash
# Build the Docker image
docker build -t rnnoise-multiformat .

# Run the test suite
docker run --rm -v $(pwd)/test:/test rnnoise-multiformat test_denoise

# Interactive session for manual testing
docker run --rm -it -v $(pwd)/audio:/workspace rnnoise-multiformat
```

### Option 3: Direct Integration (Advanced)

For developers who want to integrate format conversion directly into their applications:

```c
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libswresample/swresample.h>

// See examples/rnnoise_demo_extended.c for a complete example
// This version links against FFmpeg libraries for direct format support
```

## Technical Details

### Conversion Pipeline

```
[Input Audio] → [FFmpeg Decode] → [Resample to 48kHz] → [Downmix to Mono] 
→ [Convert to 16-bit PCM] → [RNNoise Denoise] → [Output Raw PCM]
```

### Audio Specifications

**Input (Any Format):**
- Sample Rate: Any (automatically resampled to 48kHz)
- Channels: Any (automatically downmixed to mono)
- Bit Depth: Any (automatically converted to 16-bit)

**Output (RNNoise Compatible):**
- Format: Raw PCM (no header)
- Sample Rate: 48kHz
- Channels: 1 (mono)
- Bit Depth: 16-bit signed integer
- Endianness: Little-endian

### Performance

| Operation | Speed (relative to realtime) |
|-----------|------------------------------|
| Format Conversion | 2-5x |
| RNNoise Denoising | 10-20x (with AVX2) |
| Combined Pipeline | 2-4x |

*Performance varies based on input format, CPU capabilities, and file size.*

## Testing

### Automated Test Suite

```bash
# Inside Docker container
test_denoise

# Or manually
./scripts/test_denoise.sh
```

The test suite:
1. Generates test audio samples in all supported formats
2. Adds controlled noise (~10dB SNR)
3. Converts each format to raw PCM
4. Processes with RNNoise
5. Validates output integrity
6. Generates a comprehensive test report

### Manual Testing

```bash
# Test with your own audio file
./scripts/audio_converter.sh your_audio.mp3 converted.raw
./examples/rnnoise_demo converted.raw denoised.raw

# Convert denoised raw back to WAV for playback
ffmpeg -f s16le -ar 48000 -ac 1 -i denoised.raw -acodec pcm_s16le denoised.wav
```

## Docker Usage

### Build

```bash
docker build -t rnnoise-multiformat:latest .
```

### Run Tests

```bash
docker run --rm \
  -v $(pwd)/test:/test \
  rnnoise-multiformat:latest \
  test_denoise
```

### Interactive Development

```bash
docker run --rm -it \
  -v $(pwd)/audio:/workspace \
  rnnoise-multiformat:latest \
  /bin/bash
```

### Production Deployment

```bash
docker run --rm \
  -v /path/to/audio:/input \
  -v /path/to/output:/output \
  rnnoise-multiformat:latest \
  bash -c "audio_converter /input/input.mp3 /tmp/converted.raw && \
           /rnnoise/examples/rnnoise_demo /tmp/converted.raw /output/denoised.raw"
```

## File Structure

```
rnnoise/
├── Dockerfile                          # Docker build configuration
├── scripts/
│   ├── audio_converter.sh             # Format conversion wrapper
│   ├── test_denoise.sh                # Automated test suite
│   └── generate_test_report.sh        # Report generation
├── examples/
│   ├── rnnoise_demo.c                 # Original demo (raw PCM only)
│   └── rnnoise_demo_extended.c        # Extended version with FFmpeg
└── docs/
    └── MULTI_FORMAT.md                # This file
```

## Dependencies

### Build Dependencies
- GCC/Clang
- Autoconf, Automake, Libtool
- FFmpeg development libraries:
  - libavformat-dev
  - libavcodec-dev
  - libavutil-dev
  - libswresample-dev

### Runtime Dependencies
- FFmpeg (for audio conversion)
- RNNoise libraries

### Docker Dependencies
- Docker Engine 20.10+
- Docker Compose (optional)

## Troubleshooting

### Common Issues

**1. "ffmpeg not found"**
```bash
# Install FFmpeg
apt-get install ffmpeg
# or
brew install ffmpeg  # macOS
```

**2. "Unsupported codec"**
- Some formats may not be supported by your FFmpeg build
- Check supported formats: `ffmpeg -formats | grep "^DE"`

**3. "Output file too small"**
- Input file may be corrupted or DRM-protected
- Verify input file plays correctly in media player

**4. "Memory allocation failed"**
- File may be too large for available memory
- Try processing in chunks or use a machine with more RAM

### Debug Mode

Enable verbose output for troubleshooting:

```bash
# Conversion debug
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 48000 -ac 1 -f s16le output.raw -loglevel debug

# RNNoise debug
strace -e trace=file ./examples/rnnoise_demo input.raw output.raw
```

## API Reference

### audio_converter.sh

**Usage:**
```bash
audio_converter.sh <input_file> <output_file>
```

**Parameters:**
- `input_file`: Path to input audio file (any supported format)
- `output_file`: Path to output raw PCM file

**Exit Codes:**
- `0`: Success
- `1`: Error (file not found, conversion failed, etc.)

**Example:**
```bash
./scripts/audio_converter.sh podcast.mp3 podcast.raw
if [ $? -eq 0 ]; then
    echo "Conversion successful"
else
    echo "Conversion failed"
fi
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new formats
4. Update documentation
5. Submit a pull request

### Adding New Format Support

1. Verify FFmpeg supports the format
2. Add format to test suite (`test_denoise.sh`)
3. Update documentation
4. Test with various bitrates and sample rates

## License

This extension follows the same license as RNNoise (BSD-2-Clause).

FFmpeg libraries are licensed under LGPL/GPL - ensure compliance with your use case.

## Acknowledgments

- RNNoise: Jean-Marc Valin and Mozilla
- FFmpeg: FFmpeg developers
- Test audio samples: Generated using FFmpeg lavfi

## Contact

For issues or questions, please open an issue on the repository.

---

*Last updated: 2026-02-28*
