# Model Gateway Scripts

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


Utility scripts for model management and testing.

## Scripts

### `download_model.py`

Download and prepare base LLM model from Hugging Face.

**Usage:**
```bash
# Download default model
python scripts/download_model.py

# Download specific model
python scripts/download_model.py \
  --model-id microsoft/phi-2 \
  --output-dir /models/base

# Download and convert to GGUF
python scripts/download_model.py \
  --model-id microsoft/phi-2 \
  --output-dir /models/base \
  --convert-gguf \
  --quantization Q4_K_M

# With authentication token
export HUGGINGFACE_TOKEN=your_token_here
python scripts/download_model.py --use-auth-token
```

**Requirements:**
```bash
pip install huggingface_hub
```

### `test_model_loading.py`

Test model loading and basic inference.

**Usage:**
```bash
# Basic test
python scripts/test_model_loading.py

# With custom model path
python scripts/test_model_loading.py \
  --model-path /models/base/cybergpt-7b-q4_k_m.gguf \
  --runtime llama_cpp

# With benchmark
python scripts/test_model_loading.py --benchmark

# Custom prompt
python scripts/test_model_loading.py \
  --prompt "What is NIST AC-2?"
```

**Requirements:**
```bash
# For llama.cpp
pip install llama-cpp-python

# For transformers
pip install transformers torch

# For vLLM
pip install vllm
```

## Model Recommendations

### For CPU (Recommended for Development)

**Model:** CyberGPT-7B or Qwen2.5-Coder-7B-Instruct  
**Runtime:** llama.cpp  
**Quantization:** Q4_K_M (~4GB RAM)

```bash
# Download and convert to GGUF
python scripts/download_model.py \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct \
  --output-dir /models/base \
  --convert-gguf \
  --quantization Q4_K_M
```

### For GPU

**Model:** CyberGPT-7B or SecGPT-7B  
**Runtime:** transformers or vLLM  
**Quantization:** FP16 or BF16

```bash
# Download model
python scripts/download_model.py \
  --model-id microsoft/phi-2 \
  --output-dir /models/base

# Set runtime
export LLM_RUNTIME=transformers
python scripts/test_model_loading.py
```

## Model Paths

### Default Locations

- **Base Models:** `/models/base/`
- **Adapters:** `/models/adapters/`
- **GGUF Files:** `/models/base/{model-name}-{quantization}.gguf`

### Environment Variables

```bash
export BASE_MODEL_NAME=cybergpt-7b
export BASE_MODEL_PATH=/models/base
export LLM_RUNTIME=llama_cpp
export ADAPTER_STORAGE_PATH=/models/adapters
```

## Testing Checklist

1. **Download Model:**
   ```bash
   python scripts/download_model.py
   ```

2. **Test Loading:**
   ```bash
   python scripts/test_model_loading.py
   ```

3. **Benchmark:**
   ```bash
   python scripts/test_model_loading.py --benchmark
   ```

4. **Test with Service:**
   ```bash
   # Start Model Gateway service
   docker-compose -f docker-compose.dev.yml up model_gateway
   
   # Test API
   curl http://localhost:8002/health
   ```

## Troubleshooting

### Model Not Found

**Error:** `Model file not found`

**Solution:**
1. Check `BASE_MODEL_PATH` environment variable
2. Verify model files exist
3. For GGUF, ensure file name matches pattern: `{model-name}-{quantization}.gguf`

### Out of Memory

**Error:** `CUDA out of memory` or `Cannot allocate memory`

**Solution:**
1. Use quantization (Q4_K_M for CPU, FP16 for GPU)
2. Reduce context window: `export LLM_N_CTX=2048`
3. Use CPU runtime: `export LLM_RUNTIME=llama_cpp`

### Import Errors

**Error:** `No module named 'llama_cpp'`

**Solution:**
```bash
pip install llama-cpp-python
# Or for GPU support:
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
```

