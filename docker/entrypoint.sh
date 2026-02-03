#!/bin/sh
set -e

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <noisy.pcm> <denoised.pcm> [model.bin]"
  echo "Set RNNOISE_MODE=demo to use rnnoise_demo (default: wrapper)."
  exit 1
fi

mode=${RNNOISE_MODE:-wrapper}

case "$mode" in
  demo)
    exec rnnoise_demo "$@"
    ;;
  wrapper)
    exec rnnoise_wrapper_demo "$@"
    ;;
  server)
    exec uvicorn server.app:APP --host 0.0.0.0 --port 8000
    ;;
  *)
    echo "Unknown RNNOISE_MODE: $mode"
    exit 1
    ;;
esac
