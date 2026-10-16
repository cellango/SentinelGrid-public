"""
Model Service
Combines base model with tenant LoRA adapters for personalized inference
"""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Some features may not work.")

from app.services.base_model_service import BaseModelService
from app.services.adapter_manager import AdapterManager
from app.services.peft_adapter_service import PEFTAdapterService


class ModelService:
    """Service that combines base model with tenant adapters."""
    
    def __init__(self):
        self.base_model_service = BaseModelService()
        self.adapter_manager = AdapterManager(
            adapter_storage_path=os.getenv("ADAPTER_STORAGE_PATH", "/models/adapters")
        )
        self.peft_service = PEFTAdapterService()  # PEFT adapter service
        self._adapter_cache: Dict[str, Any] = {}  # Cache merged models
    
    def generate_with_adapter(
        self,
        tenant_id: str,
        prompt: str,
        adapter_version: Optional[str] = None,
        **generation_kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using base model + tenant adapter.
        
        Args:
            tenant_id: Tenant ID
            prompt: Input prompt
            adapter_version: Adapter version (defaults to latest)
            **generation_kwargs: Generation parameters
            
        Returns:
            Generated text with metadata
        """
        # Load base model if not loaded
        if not self.base_model_service.model_loaded:
            self.base_model_service.load_base_model()
        
        # Load tenant adapter
        adapter_info = self.adapter_manager.load_adapter(tenant_id, adapter_version)
        
        # Check if we have a cached merged model
        cache_key = f"{tenant_id}:{adapter_version or 'latest'}"
        
        # Load adapter using PEFT if available
        if adapter_info and adapter_info.get("path"):
            try:
                model, tokenizer = self.peft_service.load_adapter(
                    adapter_path=adapter_info["path"],
                    tenant_id=tenant_id,
                    merge=False  # Keep adapter separate for efficiency
                )
                
                # Generate using adapter model
                result = self._generate_with_model(model, tokenizer, prompt, **generation_kwargs)
            except Exception as e:
                logger.error(f"Error using adapter model: {e}. Falling back to base model.")
                result = self.base_model_service.generate(prompt, **generation_kwargs)
        else:
            # No adapter, use base model
            result = self.base_model_service.generate(prompt, **generation_kwargs)
        
        # Add metadata
        result["tenant_id"] = tenant_id
        result["adapter_used"] = adapter_info is not None
        result["adapter_version"] = adapter_info.get("version") if adapter_info else None
        result["model_name"] = self.base_model_service.base_model_name
        result["generated_at"] = datetime.utcnow().isoformat()
        
        return result
    
    def _generate_with_model(
        self,
        model: Any,
        tokenizer: Any,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using a loaded model and tokenizer.
        
        Args:
            model: Loaded model (base or with adapter)
            tokenizer: Tokenizer
            prompt: Input prompt
            **kwargs: Generation parameters
            
        Returns:
            Generated text with metadata
        """
        try:
            if tokenizer is None or model is None:
                raise ValueError("Model or tokenizer not loaded")
            
            # Tokenize input
            inputs = tokenizer(prompt, return_tensors="pt")
            
            # Move to same device as model
            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                    **kwargs
                )
            
            # Decode output
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Remove input prompt from output
            response_text = generated_text[len(prompt):].strip()
            
            return {
                "text": response_text,
                "tokens": outputs.shape[1] - inputs["input_ids"].shape[1],
                "finish_reason": "stop"
            }
            
        except Exception as e:
            logger.error(f"Error generating with model: {e}")
            raise
