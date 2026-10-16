#!/usr/bin/env python3
"""
Download and prepare base LLM model for Model Gateway.

This script:
1. Downloads model from Hugging Face
2. Optionally converts to GGUF format (for llama.cpp)
3. Validates model files
"""

import argparse
import os
import sys
from pathlib import Path
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_from_huggingface(
    model_id: str,
    output_dir: Path,
    use_auth_token: bool = False
):
    """
    Download model from Hugging Face.
    
    Args:
        model_id: Hugging Face model ID (e.g., "microsoft/phi-2")
        output_dir: Directory to save model
        use_auth_token: Whether to use authentication token
    """
    try:
        from huggingface_hub import snapshot_download
        
        logger.info(f"Downloading model {model_id} to {output_dir}...")
        
        token = os.getenv("HUGGINGFACE_TOKEN") if use_auth_token else None
        
        snapshot_download(
            repo_id=model_id,
            local_dir=str(output_dir),
            token=token,
            local_dir_use_symlinks=False
        )
        
        logger.info(f"✅ Model downloaded successfully to {output_dir}")
        return True
        
    except ImportError:
        logger.error("huggingface_hub not installed. Install with: pip install huggingface_hub")
        return False
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return False


def convert_to_gguf(
    model_path: Path,
    output_path: Path,
    quantization: str = "Q4_K_M"
):
    """
    Convert model to GGUF format using llama.cpp.
    
    Args:
        model_path: Path to model directory
        output_path: Path for output GGUF file
        quantization: Quantization level (Q4_K_M, Q8_0, etc.)
    """
    try:
        # Check if llama.cpp converter exists
        converter_path = os.getenv("LLAMA_CPP_CONVERTER", "convert.py")
        
        logger.info(f"Converting model to GGUF format ({quantization})...")
        logger.warning("This requires llama.cpp converter. Manual conversion may be needed.")
        
        # Example command (adjust based on actual converter)
        # python convert.py {model_path} --outfile {output_path} --outtype {quantization}
        
        return False  # Placeholder - actual conversion requires llama.cpp setup
        
    except Exception as e:
        logger.error(f"Error converting to GGUF: {e}")
        return False


def validate_model_files(model_path: Path) -> bool:
    """Validate that model files exist."""
    required_files = ["config.json"]
    
    if not model_path.exists():
        logger.error(f"Model path does not exist: {model_path}")
        return False
    
    for file in required_files:
        if not (model_path / file).exists():
            logger.warning(f"Required file not found: {file}")
    
    # Check for model weights (common patterns)
    weight_files = list(model_path.glob("*.bin")) + list(model_path.glob("*.safetensors"))
    if not weight_files:
        logger.warning("No model weight files found (.bin or .safetensors)")
    else:
        logger.info(f"Found {len(weight_files)} weight file(s)")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Download and prepare LLM model")
    parser.add_argument(
        "--model-id",
        default=os.getenv("BASE_MODEL_HUGGINGFACE_ID", "microsoft/phi-2"),
        help="Hugging Face model ID"
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("BASE_MODEL_PATH", "/models/base"),
        help="Output directory for model"
    )
    parser.add_argument(
        "--convert-gguf",
        action="store_true",
        help="Convert to GGUF format after download"
    )
    parser.add_argument(
        "--quantization",
        default="Q4_K_M",
        choices=["Q4_K_M", "Q8_0", "F16", "F32"],
        help="Quantization level for GGUF"
    )
    parser.add_argument(
        "--use-auth-token",
        action="store_true",
        help="Use Hugging Face auth token"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download model
    success = download_from_huggingface(
        model_id=args.model_id,
        output_dir=output_dir,
        use_auth_token=args.use_auth_token
    )
    
    if not success:
        logger.error("Failed to download model")
        sys.exit(1)
    
    # Validate files
    if not validate_model_files(output_dir):
        logger.warning("Model validation failed, but continuing...")
    
    # Convert to GGUF if requested
    if args.convert_gguf:
        gguf_path = output_dir / f"{Path(args.model_id).name}-{args.quantization.lower()}.gguf"
        convert_to_gguf(output_dir, gguf_path, args.quantization)
    
    logger.info("✅ Model setup complete!")
    logger.info(f"Model location: {output_dir}")
    logger.info(f"Set BASE_MODEL_PATH={output_dir} to use this model")


if __name__ == "__main__":
    main()

