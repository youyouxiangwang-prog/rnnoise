#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "rnnoise.h"

#define FRAME_SIZE 480

typedef struct {
  float *data;
  size_t capacity;
  size_t size;
  size_t read_pos;
  size_t write_pos;
} RingBuffer;

static int ring_buffer_init(RingBuffer *buffer, size_t capacity) {
  buffer->data = (float *)malloc(sizeof(float) * capacity);
  if (!buffer->data) {
    return 0;
  }
  buffer->capacity = capacity;
  buffer->size = 0;
  buffer->read_pos = 0;
  buffer->write_pos = 0;
  return 1;
}

static void ring_buffer_free(RingBuffer *buffer) {
  free(buffer->data);
  buffer->data = NULL;
  buffer->capacity = 0;
  buffer->size = 0;
  buffer->read_pos = 0;
  buffer->write_pos = 0;
}

static size_t ring_buffer_write(RingBuffer *buffer, const float *input, size_t count) {
  size_t written = 0;
  while (written < count && buffer->size < buffer->capacity) {
    buffer->data[buffer->write_pos] = input[written];
    buffer->write_pos = (buffer->write_pos + 1) % buffer->capacity;
    buffer->size++;
    written++;
  }
  return written;
}

static size_t ring_buffer_read(RingBuffer *buffer, float *output, size_t count) {
  size_t read_count = 0;
  while (read_count < count && buffer->size > 0) {
    output[read_count] = buffer->data[buffer->read_pos];
    buffer->read_pos = (buffer->read_pos + 1) % buffer->capacity;
    buffer->size--;
    read_count++;
  }
  return read_count;
}

int main(int argc, char **argv) {
  FILE *input_file;
  FILE *output_file;
  DenoiseState *state;
  RNNModel *model = NULL;
  RingBuffer buffer;
  const size_t chunk_size = 160;
  short input_samples[160];
  float input_float[160];
  float frame[FRAME_SIZE];
  short output_samples[FRAME_SIZE];
  int warmup = 1;

  if (argc < 3 || argc > 4) {
    fprintf(stderr, "usage: %s <noisy.pcm> <denoised.pcm> [model.bin]\n", argv[0]);
    return 1;
  }

  input_file = fopen(argv[1], "rb");
  if (!input_file) {
    fprintf(stderr, "failed to open input file\n");
    return 1;
  }

  output_file = fopen(argv[2], "wb");
  if (!output_file) {
    fprintf(stderr, "failed to open output file\n");
    fclose(input_file);
    return 1;
  }

  if (argc == 4) {
    model = rnnoise_model_from_filename(argv[3]);
    if (!model) {
      fprintf(stderr, "failed to load model\n");
      fclose(input_file);
      fclose(output_file);
      return 1;
    }
  }

  state = rnnoise_create(model);
  if (!state) {
    fprintf(stderr, "failed to create rnnoise state\n");
    if (model) {
      rnnoise_model_free(model);
    }
    fclose(input_file);
    fclose(output_file);
    return 1;
  }

  if (!ring_buffer_init(&buffer, FRAME_SIZE * 4)) {
    fprintf(stderr, "failed to allocate ring buffer\n");
    rnnoise_destroy(state);
    if (model) {
      rnnoise_model_free(model);
    }
    fclose(input_file);
    fclose(output_file);
    return 1;
  }

  while (1) {
    size_t read_count = fread(input_samples, sizeof(short), chunk_size, input_file);
    if (read_count == 0) {
      break;
    }
    for (size_t sample_index = 0; sample_index < read_count; sample_index++) {
      input_float[sample_index] = (float)input_samples[sample_index];
    }
    ring_buffer_write(&buffer, input_float, read_count);

    while (buffer.size >= FRAME_SIZE) {
      size_t frame_count = ring_buffer_read(&buffer, frame, FRAME_SIZE);
      if (frame_count < FRAME_SIZE) {
        break;
      }
      rnnoise_process_frame(state, frame, frame);
      if (!warmup) {
        for (size_t sample_index = 0; sample_index < FRAME_SIZE; sample_index++) {
          output_samples[sample_index] = (short)frame[sample_index];
        }
        fwrite(output_samples, sizeof(short), FRAME_SIZE, output_file);
      }
      warmup = 0;
    }
  }

  if (buffer.size > 0) {
    size_t remaining = ring_buffer_read(&buffer, frame, buffer.size);
    for (size_t sample_index = remaining; sample_index < FRAME_SIZE; sample_index++) {
      frame[sample_index] = 0.0f;
    }
    rnnoise_process_frame(state, frame, frame);
    if (!warmup) {
      for (size_t sample_index = 0; sample_index < remaining; sample_index++) {
        output_samples[sample_index] = (short)frame[sample_index];
      }
      fwrite(output_samples, sizeof(short), remaining, output_file);
    }
  }

  ring_buffer_free(&buffer);
  rnnoise_destroy(state);
  if (model) {
    rnnoise_model_free(model);
  }
  fclose(input_file);
  fclose(output_file);

  return 0;
}
