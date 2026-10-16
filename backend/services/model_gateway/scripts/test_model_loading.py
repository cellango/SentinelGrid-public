#!/usr/bin/env python3
"""
Test model loading and basic inference.

This script tests:
1. Model loading from configured path
2. Basic text generation
3. Performance benchmarking
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.base_model_service import BaseModelService
from app.core.config import settings

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_model_loading():
    """Test loading the base model."""
    logger.info("Testing model loading...")
    
    service = BaseModelService()
    
    start_time = time.time()
    service.load_base_model()
    load_time = time.time() - start_time
    
    if service.model_loaded:
        logger.info(f"✅ Model loaded successfully in {load_time:.2f}s")
        return True
    else:
        logger.error("❌ Model loading failed")
        return False


def test_inference(service: BaseModelService, prompt: str = "What is cybersecurity?"):
    """Test basic inference."""
    logger.info(f"Testing inference with prompt: '{prompt}'")
    
    start_time = time.time()
    result = service.generate(
        prompt=prompt,
        max_tokens=100,
        temperature=0.7
    )
    inference_time = time.time() - start_time
    
    logger.info(f"Response: {result.get('text', 'No response')[:200]}...")
    logger.info(f"Inference time: {inference_time:.2f}s")
    logger.info(f"Tokens generated: {result.get('tokens', 0)}")
    
    if result.get("finish_reason") == "error":
        logger.error("❌ Inference failed")
        return False
    
    logger.info("✅ Inference successful")
    return True


def benchmark_inference(service: BaseModelService, num_runs: int = 5):
    """Benchmark inference performance."""
    logger.info(f"Benchmarking inference ({num_runs} runs)...")
    
    prompts = [
        "What is IAM?",
        "Explain least privilege.",
        "What is NIST AC-2?",
        "Describe RBAC.",
        "What is MITRE ATT&CK?"
    ]
    
    times = []
    token_counts = []
    
    for i, prompt in enumerate(prompts[:num_runs]):
        logger.info(f"Run {i+1}/{num_runs}: {prompt}")
        
        start_time = time.time()
        result = service.generate(
            prompt=prompt,
            max_tokens=100,
            temperature=0.7
        )
        elapsed = time.time() - start_time
        
        times.append(elapsed)
        token_counts.append(result.get("tokens", 0))
        
        time.sleep(0.5)  # Brief pause between runs
    
    # Calculate statistics
    avg_time = sum(times) / len(times)
    avg_tokens = sum(token_counts) / len(token_counts)
    tokens_per_second = avg_tokens / avg_time if avg_time > 0 else 0
    
    logger.info("📊 Benchmark Results:")
    logger.info(f"  Average inference time: {avg_time:.2f}s")
    logger.info(f"  Average tokens generated: {avg_tokens:.1f}")
    logger.info(f"  Tokens per second: {tokens_per_second:.2f}")
    logger.info(f"  Min time: {min(times):.2f}s")
    logger.info(f"  Max time: {max(times):.2f}s")


def main():
    parser = argparse.ArgumentParser(description="Test model loading and inference")
    parser.add_argument(
        "--model-path",
        default=os.getenv("BASE_MODEL_PATH"),
        help="Path to model directory or GGUF file"
    )
    parser.add_argument(
        "--runtime",
        default=os.getenv("LLM_RUNTIME", "transformers"),
        choices=["llama_cpp", "transformers", "vllm"],
        help="LLM runtime to use"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run performance benchmark"
    )
    parser.add_argument(
        "--prompt",
        default="What is cybersecurity?",
        help="Test prompt"
    )
    
    args = parser.parse_args()
    
    # Set environment variables
    if args.model_path:
        os.environ["BASE_MODEL_PATH"] = args.model_path
    os.environ["LLM_RUNTIME"] = args.runtime
    
    logger.info(f"Model path: {args.model_path or settings.BASE_MODEL_PATH}")
    logger.info(f"Runtime: {args.runtime}")
    
    # Test loading
    if not test_model_loading():
        logger.error("Model loading failed. Check configuration.")
        sys.exit(1)
    
    # Create service
    service = BaseModelService()
    service.load_base_model()
    
    # Test inference
    if not test_inference(service, args.prompt):
        logger.error("Inference test failed.")
        sys.exit(1)
    
    # Benchmark if requested
    if args.benchmark:
        benchmark_inference(service)
    
    logger.info("✅ All tests passed!")


if __name__ == "__main__":
    main()
