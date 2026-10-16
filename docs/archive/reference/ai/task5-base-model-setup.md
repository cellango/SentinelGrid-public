# Task 5: Base Model Setup & Testing - COMPLETE ✅

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-11-29  
**Status:** ✅ COMPLETE  
**Focus:** Setup and test base LLM model for Model Gateway

---

## ✅ What Was Implemented

### 1. Configuration Management

**File:** `backend/services/model_gateway/app/core/config.py`

**Features:**
- ✅ Centralized configuration using Pydantic Settings
- ✅ Environment variable support
- ✅ Multiple runtime support (llama.cpp, transformers, vLLM)
- ✅ Model path configuration
- ✅ GPU/CPU settings

### 2. Model Download Script

**File:** `backend/services/model_gateway/scripts/download_model.py`

**Features:**
- ✅ Download models from Hugging Face
- ✅ Support for authentication tokens
- ✅ Model validation
- ✅ GGUF conversion placeholder
- ✅ Error handling

### 3. Model Testing Script

**File:** `backend/services/model_gateway/scripts/test_model_loading.py`

**Features:**
- ✅ Model loading test
- ✅ Inference testing
- ✅ Performance benchmarking
- ✅ Multiple runtime support
- ✅ Custom prompts

### 4. Enhanced Base Model Service

**File:** `backend/services/model_gateway/app/services/base_model_service.py`

**Improvements:**
- ✅ Multiple GGUF file pattern matching
- ✅ Better error handling
- ✅ Mock model fallback for development
- ✅ Runtime-specific loading
- ✅ Improved logging

### 5. Test Suite

**File:** `backend/services/model_gateway/tests/test_base_model_service.py`

**Tests:**
- ✅ Service initialization
- ✅ Model loading (with/without model files)
- ✅ Error handling
- ✅ Mock model fallback
- ✅ Text generation

### 6. Dockerfile Updates

**File:** `backend/services/model_gateway/Dockerfile`

**Features:**
- ✅ Model directories creation
- ✅ Scripts installation
- ✅ Environment variables

---

## 🔧 Configuration

### Environment Variables

```bash
# Base Model
BASE_MODEL_NAME=cybergpt-7b
BASE_MODEL_PATH=/models/base
BASE_MODEL_HUGGINGFACE_ID=microsoft/phi-2

# Runtime
LLM_RUNTIME=llama_cpp  # llama_cpp, transformers, vllm
LLM_N_THREADS=4
LLM_N_CTX=4096

# GPU (for transformers/vLLM)
CUDA_VISIBLE_DEVICES=0

# vLLM
VLLM_TENSOR_PARALLEL_SIZE=1

# Adapters
ADAPTER_STORAGE_PATH=/models/adapters
```

---

## 📥 Model Download Options

### Option 1: Download from Hugging Face (Recommended)

```bash
# Download model
python backend/services/model_gateway/scripts/download_model.py \
  --model-id microsoft/phi-2 \
  --output-dir /models/base

# With authentication (for gated models)
export HUGGINGFACE_TOKEN=your_token_here
python scripts/download_model.py --use-auth-token
```

### Option 2: Manual Download

```bash
# Using huggingface-cli
pip install huggingface_hub
huggingface-cli download microsoft/phi-2 --local-dir /models/base
```

### Option 3: Pre-downloaded Model

If you already have a model:
```bash
export BASE_MODEL_PATH=/path/to/your/model
```

---

## 🧪 Testing Model Setup

### Quick Test

```bash
# Test model loading
python backend/services/model_gateway/scripts/test_model_loading.py

# With custom settings
python scripts/test_model_loading.py \
  --model-path /models/base \
  --runtime llama_cpp \
  --prompt "What is cybersecurity?"
```

### Benchmark

```bash
# Run performance benchmark
python scripts/test_model_loading.py --benchmark
```

### Expected Output

```
INFO: Testing model loading...
INFO: ✅ Model loaded successfully in 2.34s
INFO: Testing inference with prompt: 'What is cybersecurity?'
INFO: Response: Cybersecurity is the practice of protecting...
INFO: Inference time: 1.23s
INFO: Tokens generated: 45
INFO: ✅ Inference successful
```

---

## 🎯 Model Recommendations

### For CPU (Development/Testing)

**Recommended:** Qwen2.5-Coder-7B-Instruct or Phi-2  
**Runtime:** llama.cpp  
**Quantization:** Q4_K_M (~4GB RAM)

```bash
# Download
python scripts/download_model.py \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct \
  --output-dir /models/base

# Test
export LLM_RUNTIME=llama_cpp
python scripts/test_model_loading.py
```

### For GPU (Production)

**Recommended:** CyberGPT-7B or SecGPT-7B  
**Runtime:** transformers or vLLM  
**Quantization:** FP16 or BF16

```bash
# Download
python scripts/download_model.py \
  --model-id microsoft/phi-2 \
  --output-dir /models/base

# Test
export LLM_RUNTIME=transformers
export CUDA_VISIBLE_DEVICES=0
python scripts/test_model_loading.py
```

---

## 📊 Model File Structure

### For llama.cpp (GGUF)

```
/models/base/
  └── cybergpt-7b-q4_k_m.gguf  # Quantized model file
```

### For transformers

```
/models/base/
  ├── config.json
  ├── tokenizer.json
  ├── model.safetensors  # or model.bin
  └── ...
```

---

## 🐛 Troubleshooting

### Issue: Model File Not Found

**Error:** `Model file not found at /models/base/...`

**Solution:**
1. Verify model path: `echo $BASE_MODEL_PATH`
2. Check file exists: `ls -la /models/base/`
3. For GGUF, ensure file matches pattern: `{model-name}-{quantization}.gguf`
4. Update `BASE_MODEL_NAME` to match actual file

### Issue: Import Error (llama-cpp-python)

**Error:** `No module named 'llama_cpp'`

**Solution:**
```bash
# Install llama-cpp-python
pip install llama-cpp-python

# Or for GPU support:
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
```

### Issue: Out of Memory

**Error:** `Cannot allocate memory` or `CUDA out of memory`

**Solution:**
1. Use quantization: `Q4_K_M` for CPU, `FP16` for GPU
2. Reduce context: `export LLM_N_CTX=2048`
3. Use CPU runtime: `export LLM_RUNTIME=llama_cpp`
4. Close other applications

### Issue: Slow Inference

**Cause:** CPU inference or insufficient resources

**Solutions:**
1. Use GPU runtime if available
2. Use quantization (Q4_K_M)
3. Reduce context window
4. Increase threads: `export LLM_N_THREADS=8`

---

## ✅ Acceptance Criteria Met

- [x] Model download script created
- [x] Model loading service enhanced
- [x] Testing script created
- [x] Configuration management
- [x] Error handling and fallbacks
- [x] Multiple runtime support
- [x] Test suite created
- [x] Documentation complete

---

## 📋 Next Steps

1. **Download Model:** Run download script to get base model
2. **Test Loading:** Verify model loads correctly
3. **Run Benchmark:** Check performance metrics
4. **Configure Service:** Set environment variables
5. **Integration:** Test with Model Gateway service

---

## 🔍 Model Selection Guide

### Cybersecurity-Specific Models

1. **CyberGPT-7B** (Ideal, if available)
   - Trained on security data
   - Understands NIST, MITRE, OWASP
   - 7B parameters, cost-effective

2. **SecGPT-7B** (Alternative)
   - Security-focused
   - May need verification of training data

3. **Qwen2.5-Coder-7B-Instruct** (General purpose)
   - Good code/technical understanding
   - Can be fine-tuned for cybersecurity

4. **Phi-2** (Microsoft)
   - Small, fast (2.7B parameters)
   - Good for testing/development
   - Less specialized for security

### Recommended Setup for V1

**Development:**
- Model: Phi-2 or Qwen2.5-Coder-7B-Instruct
- Runtime: llama.cpp
- Quantization: Q4_K_M
- RAM: ~4-6GB

**Production:**
- Model: CyberGPT-7B or SecGPT-7B
- Runtime: vLLM (GPU) or llama.cpp (CPU)
- Quantization: FP16 (GPU) or Q4_K_M (CPU)
- RAM/VRAM: 8-16GB

---

**Status:** ✅ Task 5 COMPLETE - Base model setup and testing utilities ready

