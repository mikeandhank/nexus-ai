# GPU Setup Guide for NexusOS

## Overview

Enable GPU acceleration for Ollama and vLLM inference for faster, larger models.

## Hardware Requirements

| GPU | VRAM | Models |
|-----|------|--------|
| NVIDIA T4 | 16GB | Llama 2 7B, Mistral 7B |
| NVIDIA L4 | 24GB | Llama 2 13B, CodeLlama 34B |
| NVIDIA A10G | 24GB | Llama 2 70B (quantized) |
| NVIDIA A100 | 40-80GB | Llama 2 70B, Mixtral 8x7B |

## Prerequisites

### 1. Install NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit

sudo systemctl restart docker
```

### 2. Verify GPU Access

```bash
# On host
nvidia-smi

# In Docker
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

## NexusOS GPU Deployment

### Option 1: GPU-Enabled Docker Compose

```bash
cd /data/.openclaw/workspace/nexusos-v2
docker compose -f docker-compose.gpu.yml up -d
```

### Option 2: Add GPU to Existing Deployment

Edit your `docker-compose.yml`:

```yaml
services:
  nexusos-ollama:
    # ... existing config ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all  # or specific number like "1"
              capabilities: [gpu]
```

### Option 3: Docker Run Command

```bash
docker run -d \
  --name nexusos-ollama \
  --gpus all \
  -p 11434:11434 \
  -v ollama-data:/root/.ollama \
  ollama/ollama:latest
```

## Verify GPU Acceleration

```bash
# Check Ollama sees GPU
curl http://localhost:11434/api/tags

# Check model loading
docker exec nexusos-ollama nvidia-smi

# Run a benchmark
# See /app/gpu_inference.py for benchmarking tools
python /app/gpu_inference.py --benchmark
```

## Troubleshooting

### "NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver"

```bash
# Reinstall NVIDIA driver
sudo apt-get install --reinstall nvidia-driver-525
reboot
```

### "could not select device driver "nvidia" with capabilities: [[gpu]]"

```bash
# Verify Container Toolkit installation
nvidia-container-toolkit --version

# Restart Docker
sudo systemctl restart docker
```

### GPU Memory Out of Memory (OOM)

```bash
# Reduce context size in Ollama
# Edit /etc/ollama/ollama.conf:
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
```

## Performance Tuning

### Ollama GPU Settings

```yaml
# docker-compose.yml
services:
  nexusos-ollama:
    environment:
      - OLLAMA_NUM_PARALLEL=1
      - OLLAMA_MAX_LOADED_MODELS=1
      - CUDA_VISIBLE_DEVICES=0
```

### vLLM Settings

```bash
# For T4 (16GB)
--max-model-len 4096
--gpu-memory-utilization 0.9

# For A100 (40GB)
--max-model-len 8192
--gpu-memory-utilization 0.95
```

## Monitoring

### Prometheus Metrics

GPU metrics available at:
- `/metrics` endpoint (see observability.py)
- NVIDIA DCGM exporter for detailed metrics

### Grafana Dashboard

Import the NVIDIA DCGM dashboard:
https://grafana.com/grafana/dashboards/12239-nvidia-dcgm-exporter-dashboard/