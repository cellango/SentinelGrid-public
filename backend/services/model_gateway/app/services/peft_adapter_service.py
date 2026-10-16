"""
PEFT Adapter Service
Handles actual LoRA adapter loading and merging using PEFT library
"""

import logging
import os
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from peft import PeftModel, PeftConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    logger.warning("PEFT library not available. Install with: pip install peft transformers")


class PEFTAdapterService:
    """Service for loading and managing PEFT/LoRA adapters."""
    
    def __init__(self, base_model_path: Optional[str] = None):
        self.base_model_path = base_model_path or os.getenv("BASE_MODEL_PATH")
        self.base_model = None
        self.base_tokenizer = None
        self.loaded_adapters: Dict[str, Any] = {}  # Cache of merged models
        
        if not PEFT_AVAILABLE:
            logger.warning("PEFT not available. Adapter loading will be mocked.")
    
    def load_base_model(self, model_name: Optional[str] = None):
        """
        Load the base model for adapter merging.
        
        Args:
            model_name: Model name (if different from default)
        """
        if not PEFT_AVAILABLE:
            logger.warning("PEFT not available. Skipping base model loading.")
            return
        
        try:
            model_name = model_name or os.getenv("BASE_MODEL_NAME", "cybergpt-7b")
            
            logger.info(f"Loading base model: {model_name}")
            
            # Load tokenizer
            self.base_tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            
            if self.base_tokenizer.pad_token is None:
                self.base_tokenizer.pad_token = self.base_tokenizer.eos_token
            
            # Load model
            # Use device_map="auto" for GPU, or "cpu" for CPU
            device_map = os.getenv("MODEL_DEVICE_MAP", "auto")
            
            self.base_model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map=device_map,
                torch_dtype="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            logger.info(f"Base model loaded: {model_name}")
            
        except Exception as e:
            logger.error(f"Error loading base model: {e}")
            raise
    
    def load_adapter(
        self,
        adapter_path: str,
        tenant_id: str,
        merge: bool = False
    ) -> Tuple[Any, Optional[Any]]:
        """
        Load a LoRA adapter.
        
        Args:
            adapter_path: Path to adapter directory
            tenant_id: Tenant ID for caching
            merge: If True, merge adapter weights into base model
            
        Returns:
            Tuple of (model, tokenizer)
        """
        if not PEFT_AVAILABLE:
            logger.warning("PEFT not available. Returning base model without adapter.")
            return self.base_model, self.base_tokenizer
        
        try:
            # Check cache
            cache_key = f"{tenant_id}:{adapter_path}"
            if cache_key in self.loaded_adapters:
                logger.info(f"Using cached adapter for tenant {tenant_id}")
                return self.loaded_adapters[cache_key]
            
            # Load base model if not loaded
            if self.base_model is None:
                self.load_base_model()
            
            # Load adapter
            logger.info(f"Loading adapter from: {adapter_path}")
            
            # Verify adapter exists
            adapter_path_obj = Path(adapter_path)
            if not adapter_path_obj.exists():
                logger.warning(f"Adapter path does not exist: {adapter_path}")
                return self.base_model, self.base_tokenizer
            
            # Load PEFT adapter
            adapter_model = PeftModel.from_pretrained(
                self.base_model,
                adapter_path,
                device_map=os.getenv("MODEL_DEVICE_MAP", "auto")
            )
            
            if merge:
                # Merge adapter weights into base model
                logger.info("Merging adapter weights into base model")
                merged_model = adapter_model.merge_and_unload()
                self.loaded_adapters[cache_key] = (merged_model, self.base_tokenizer)
                return merged_model, self.base_tokenizer
            else:
                # Keep adapter separate (lighter, but requires adapter at inference)
                self.loaded_adapters[cache_key] = (adapter_model, self.base_tokenizer)
                return adapter_model, self.base_tokenizer
                
        except Exception as e:
            logger.error(f"Error loading adapter from {adapter_path}: {e}")
            # Fallback to base model
            if self.base_model is None:
                self.load_base_model()
            return self.base_model, self.base_tokenizer
    
    def unload_adapter(self, tenant_id: str):
        """Unload adapter from cache."""
        keys_to_remove = [k for k in self.loaded_adapters.keys() if k.startswith(f"{tenant_id}:")]
        for key in keys_to_remove:
            del self.loaded_adapters[key]
        logger.info(f"Unloaded adapter cache for tenant {tenant_id}")
    
    def get_adapter_config(self, adapter_path: str) -> Optional[Dict[str, Any]]:
        """
        Get adapter configuration without loading the model.
        
        Args:
            adapter_path: Path to adapter directory
            
        Returns:
            Adapter configuration dictionary
        """
        if not PEFT_AVAILABLE:
            return None
        
        try:
            config = PeftConfig.from_pretrained(adapter_path)
            return {
                "base_model_name": config.base_model_name_or_path,
                "task_type": config.task_type,
                "inference_mode": config.inference_mode,
                "r": getattr(config, "r", None),
                "lora_alpha": getattr(config, "lora_alpha", None),
                "lora_dropout": getattr(config, "lora_dropout", None),
                "target_modules": getattr(config, "target_modules", None),
            }
        except Exception as e:
            logger.error(f"Error reading adapter config: {e}")
            return None
    
    def save_adapter(
        self,
        model: Any,
        adapter_path: str,
        adapter_name: str = "adapter_model"
    ) -> bool:
        """
        Save a trained adapter.
        
        Args:
            model: Model with adapter (PEFT model)
            adapter_path: Directory to save adapter
            adapter_name: Name of adapter files
            
        Returns:
            True if successful
        """
        if not PEFT_AVAILABLE:
            logger.warning("PEFT not available. Cannot save adapter.")
            return False
        
        try:
            adapter_path_obj = Path(adapter_path)
            adapter_path_obj.mkdir(parents=True, exist_ok=True)
            
            # Save adapter
            if isinstance(model, PeftModel):
                model.save_pretrained(adapter_path)
            else:
                logger.warning("Model is not a PEFT model. Cannot save adapter.")
                return False
            
            logger.info(f"Saved adapter to: {adapter_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving adapter: {e}")
            return False

