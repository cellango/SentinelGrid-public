"""
Base Model Service
Manages the base cybersecurity LLM model
"""

import logging
import os
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseModelService:
    """Service for managing the base cybersecurity LLM model."""
    
    def __init__(self):
        self.base_model_name = os.getenv("BASE_MODEL_NAME", "cybergpt-7b")
        self.model_path = os.getenv("BASE_MODEL_PATH", "/models/base")
        self.max_tokens_default = int(os.getenv("LLM_MAX_TOKENS", "128"))
        self.context_length = int(os.getenv("LLM_CONTEXT_LENGTH", "2048"))
        self.n_threads = int(os.getenv("LLM_N_THREADS", "4"))
        self.model_loaded = False
        self.model = None
        self.tokenizer = None
    
    def load_base_model(self, force_reload: bool = False):
        """
        Load the base cybersecurity model.
        
        Defaults to the launch-approved transformers runtime. llama.cpp remains
        an optional non-production path when installed manually.
        """
        if self.model_loaded and not force_reload:
            return
        
        try:
            runtime = os.getenv("LLM_RUNTIME", "transformers")  # llama_cpp, transformers, vllm
            
            if runtime == "llama_cpp":
                # CPU-optimized using llama.cpp
                try:
                    from llama_cpp import Llama
                except ImportError:
                    logger.warning("llama-cpp-python not installed. Install with: pip install llama-cpp-python")
                    logger.warning("Falling back to mock model.")
                    self.model_loaded = True
                    return
                
                # Try different GGUF file patterns
                model_file = None
                patterns = [
                    Path(self.model_path) / f"{self.base_model_name}-q4_k_m.gguf",
                    Path(self.model_path) / f"{self.base_model_name}.gguf",
                    Path(self.model_path) / "*.gguf",
                    Path(self.model_path) / "model.gguf",
                ]
                
                for pattern in patterns:
                    if "*" in str(pattern):
                        # Glob pattern
                        matches = list(pattern.parent.glob(pattern.name))
                        if matches:
                            model_file = matches[0]
                            break
                    else:
                        if pattern.exists():
                            model_file = pattern
                            break
                
                if not model_file or not model_file.exists():
                    logger.warning(f"Model file not found in {self.model_path}")
                    logger.warning("Tried patterns:")
                    for p in patterns:
                        logger.warning(f"  - {p}")
                    logger.warning("Using mock model for development.")
                    self.model_loaded = True
                    return
                
                self.model = Llama(
                    model_path=str(model_file),
                    n_ctx=self.context_length,
                    n_threads=self.n_threads,
                    verbose=False
                )
                logger.info(f"Loaded base model using llama.cpp: {model_file}")
                
            elif runtime == "transformers":
                # GPU-optimized using transformers
                from transformers import AutoModelForCausalLM, AutoTokenizer
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.base_model_name,
                    device_map="auto",
                    torch_dtype="auto"
                )
                self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
                logger.info(f"Loaded base model using transformers: {self.base_model_name}")
                
            elif runtime == "vllm":
                # High-performance GPU serving
                from vllm import LLM, SamplingParams
                
                self.model = LLM(
                    model=self.base_model_name,
                    tensor_parallel_size=int(os.getenv("VLLM_TENSOR_PARALLEL_SIZE", "1"))
                )
                logger.info(f"Loaded base model using vLLM: {self.base_model_name}")
            
            self.model_loaded = True
            
        except Exception as e:
            logger.error(f"Error loading base model: {e}")
            logger.warning("Falling back to mock model for development")
            self.model_loaded = True  # Mark as loaded to prevent retry loops
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text from the base model.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            **kwargs: Additional generation parameters
            
        Returns:
            Dictionary with generated text and metadata
        """
        if not self.model_loaded:
            self.load_base_model()
        # Cap tokens for dev friendliness
        if max_tokens is None:
            max_tokens = self.max_tokens_default
        
        try:
            runtime = os.getenv("LLM_RUNTIME", "transformers")
            
            if runtime == "llama_cpp":
                if self.model is None:
                    # Mock response for development
                    return {
                        "text": "Mock response: This is a placeholder. Load a real model to get actual responses.",
                        "tokens": 10,
                        "finish_reason": "length"
                    }
                
                result = self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    echo=False,
                    **kwargs
                )
                
                return {
                    "text": result["choices"][0]["text"],
                    "tokens": result["usage"]["completion_tokens"],
                    "finish_reason": result["choices"][0].get("finish_reason", "stop")
                }
                
            elif runtime == "transformers":
                if self.tokenizer is None or self.model is None:
                    return {
                        "text": "Model not loaded. Check configuration.",
                        "tokens": 0,
                        "finish_reason": "error"
                    }
                
                inputs = self.tokenizer(prompt, return_tensors="pt")
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs
                )
                
                generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                return {
                    "text": generated_text[len(prompt):],
                    "tokens": outputs.shape[1] - inputs.input_ids.shape[1],
                    "finish_reason": "stop"
                }
                
            elif runtime == "vllm":
                if self.model is None:
                    return {
                        "text": "Model not loaded. Check configuration.",
                        "tokens": 0,
                        "finish_reason": "error"
                    }
                
                from vllm import SamplingParams

                sampling_params = SamplingParams(
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                outputs = self.model.generate([prompt], sampling_params)
                return {
                    "text": outputs[0].outputs[0].text,
                    "tokens": len(outputs[0].outputs[0].token_ids),
                    "finish_reason": outputs[0].outputs[0].finish_reason
                }
            
            else:
                raise ValueError(f"Unsupported runtime: {runtime}")
                
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return {
                "text": f"Error generating response: {str(e)}",
                "tokens": 0,
                "finish_reason": "error"
            }
