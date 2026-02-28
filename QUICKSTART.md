# Quick Start - Multi-Format Audio Denoising

## Prerequisites

- FFmpeg installed (`apt-get install ffmpeg` or `brew install ffmpeg`)
- RNNoise compiled (see main README)

## Method 1: Wrapper Script (Recommended)

```bash
# Convert any audio format to raw PCM
./scripts/audio_converter.sh input.mp3 converted.raw

# Denoise the audio
./examples/rnnoise_demo converted.raw denoised.raw

# Convert back to WAV for playback
ffmpeg -f s16le -ar 48000 -ac 1 -i denoised.raw -acodec pcm_s16le denoised.wav
```

## Method 2: Docker (No Installation Required)

```bash
# Build Docker image
docker build -t rnnoise-multiformat .

# Run tests
docker run --rm -v $(pwd)/test:/test rnnoise-multiformat test_denoise

# Process your audio
docker run --rm \
  -v $(pwd)/audio:/workspace \
  rnnoise-multiformat \
  bash -c "audio_converter /workspace/input.mp3 /workspace/converted.raw && \
           /rnnoise/examples/rnnoise_demo /workspace/converted.raw /workspace/denoised.raw"
```

## Supported Formats

✅ AAC, MP3, M4A, WAV, OGG, FLAC

## Example Workflow

```bash
# 1. Convert podcast episode
./scripts/audio_converter.sh podcast_episode.mp3 podcast.raw

# 2. Denoise
./examples/rnnoise_demo podcast.raw podcast_denoised.raw

# 3. Convert back to MP3 for distribution
ffmpeg -f s16le -ar 48000 -ac 1 -i podcast_denoised.raw \
       -acodec libmp3lame -b:a 192k podcast_denoised.mp3
```

## Testing

```bash
# Run automated test suite
./scripts/test_denoise.sh

# Or in Docker
docker run --rm -v $(pwd)/test:/test rnnoise-multiformat test_denoise
```

See `docs/MULTI_FORMAT.md` for complete documentation.
