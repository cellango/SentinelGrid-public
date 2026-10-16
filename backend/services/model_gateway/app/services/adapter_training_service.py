"""
Adapter Training Service
Manages training of per-tenant LoRA adapters using PEFT
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Try importing required libraries
try:
    from peft import LoraConfig, get_peft_model, TaskType, PeftModel
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling
    )
    from datasets import Dataset
    import torch
    PEFT_AVAILABLE = True
except ImportError as e:
    PEFT_AVAILABLE = False
    logger.warning(f"PEFT/Transformers not available: {e}. Install with: pip install peft transformers torch datasets")


class TrainingStatus(str, Enum):
    """Training job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AdapterTrainingService:
    """Service for training per-tenant LoRA adapters."""
    
    def __init__(self, db_session=None):
        self.base_model_name = os.getenv("BASE_MODEL_NAME", "cybergpt-7b")
        self.adapter_storage_path = Path(os.getenv("ADAPTER_STORAGE_PATH", "/models/adapters"))
        self.adapter_storage_path.mkdir(parents=True, exist_ok=True)
        self.db = db_session  # Database session (injected via dependency)
        self.training_jobs: Dict[str, Dict[str, Any]] = {}  # In-memory cache, also stored in DB
    
    def start_training_job(
        self,
        tenant_id: str,
        training_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start training a LoRA adapter for a tenant.
        
        Args:
            tenant_id: Tenant ID
            training_config: Training configuration (epochs, learning rate, etc.)
            
        Returns:
            Training job information
        """
        if not PEFT_AVAILABLE:
            raise RuntimeError("PEFT library not available. Cannot start training.")
        
        job_id = f"train-{tenant_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        config = training_config or {}
        training_job = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": TrainingStatus.PENDING.value,
            "base_model": self.base_model_name,
            "config": {
                "epochs": config.get("epochs", 3),
                "learning_rate": config.get("learning_rate", 2e-4),
                "batch_size": config.get("batch_size", 4),
                "gradient_accumulation_steps": config.get("gradient_accumulation_steps", 4),
                "lora_r": config.get("lora_r", 16),
                "lora_alpha": config.get("lora_alpha", 32),
                "lora_dropout": config.get("lora_dropout", 0.1),
                "target_modules": config.get("target_modules", None),  # Auto-detect if None
                **config
            },
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None
        }
        
        # Store in database if available
        if self.db:
            try:
                from app.models.database import AdapterTrainingJob
                db_job = AdapterTrainingJob(
                    tenant_id=tenant_id,
                    job_id=job_id,
                    status=TrainingStatus.PENDING.value,
                    training_config=training_job["config"],
                    base_model_name=self.base_model_name,
                    base_model_version="1.0.0"  # TODO: Get actual version
                )
                self.db.add(db_job)
                self.db.commit()
                self.db.refresh(db_job)
            except Exception as e:
                logger.error(f"Error storing training job in database: {e}")
                self.db.rollback()
        
        self.training_jobs[job_id] = training_job
        
        logger.info(f"Created training job {job_id} for tenant {tenant_id}")
        
        return training_job
    
    def get_training_job_status(
        self,
        job_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get status of a training job."""
        # Try database first
        if self.db:
            try:
                from app.models.database import AdapterTrainingJob
                from sqlalchemy import select
                
                stmt = select(AdapterTrainingJob).where(AdapterTrainingJob.job_id == job_id)
                db_job = self.db.execute(stmt).scalar_one_or_none()
                
                if db_job:
                    return {
                        "job_id": db_job.job_id,
                        "tenant_id": str(db_job.tenant_id),
                        "status": db_job.status,
                        "config": db_job.training_config,
                        "created_at": db_job.created_at.isoformat() if db_job.created_at else None,
                        "started_at": db_job.started_at.isoformat() if db_job.started_at else None,
                        "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None,
                        "error_message": db_job.error_message,
                        "metrics": db_job.metrics
                    }
            except Exception as e:
                logger.error(f"Error getting job status from database: {e}")
        
        # Fallback to in-memory cache
        return self.training_jobs.get(job_id)
    
    def execute_training(
        self,
        tenant_id: str,
        training_dataset: Dict[str, Any],
        config: Dict[str, Any],
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute LoRA adapter training using PEFT.
        
        This method:
        1. Loads base model
        2. Initializes LoRA adapter
        3. Formats training dataset
        4. Trains adapter
        5. Saves adapter to storage
        6. Updates database metadata
        
        Args:
            tenant_id: Tenant ID
            training_dataset: Dataset with samples (list of dicts with 'input' and 'output')
            config: Training configuration
            job_id: Optional job ID for tracking
            
        Returns:
            Dictionary with training results
        """
        if not PEFT_AVAILABLE:
            raise RuntimeError("PEFT library not available. Cannot execute training.")
        
        start_time = datetime.utcnow()
        adapter_version = f"v{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        try:
            logger.info(f"Starting LoRA training for tenant {tenant_id}, job {job_id}")
            
            # Update job status to RUNNING
            if job_id and self.db:
                self._update_job_status(job_id, TrainingStatus.RUNNING.value, started_at=start_time)
            
            # 1. Load base model and tokenizer
            logger.info(f"Loading base model: {self.base_model_name}")
            model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                device_map="auto",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            tokenizer = AutoTokenizer.from_pretrained(
                self.base_model_name,
                trust_remote_code=True
            )
            
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
                tokenizer.pad_token_id = tokenizer.eos_token_id
            
            # 2. Auto-detect target modules if not specified
            target_modules = config.get("target_modules")
            if target_modules is None:
                # Common module names for different architectures
                model_config = model.config
                if hasattr(model_config, "hidden_size"):
                    # Try to auto-detect based on model architecture
                    if "gpt" in self.base_model_name.lower() or "qwen" in self.base_model_name.lower():
                        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]
                    elif "llama" in self.base_model_name.lower():
                        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]
                    else:
                        # Default fallback
                        target_modules = ["q_proj", "v_proj"]
                        logger.warning(f"Could not auto-detect target modules. Using default: {target_modules}")
                else:
                    target_modules = ["q_proj", "v_proj"]
                    logger.warning(f"Using default target modules: {target_modules}")
            
            # 3. Configure LoRA
            logger.info(f"Configuring LoRA with r={config.get('lora_r', 16)}, alpha={config.get('lora_alpha', 32)}")
            lora_config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                r=config.get("lora_r", 16),
                lora_alpha=config.get("lora_alpha", 32),
                target_modules=target_modules,
                lora_dropout=config.get("lora_dropout", 0.1),
                bias="none",
            )
            
            # 4. Apply LoRA to model
            model = get_peft_model(model, lora_config)
            model.print_trainable_parameters()
            
            # 5. Prepare dataset
            logger.info(f"Preparing dataset with {len(training_dataset.get('samples', []))} samples")
            formatted_samples = self._format_training_samples(training_dataset.get("samples", []))
            
            if len(formatted_samples) < 10:
                raise ValueError(f"Insufficient training samples: {len(formatted_samples)}. Need at least 10.")
            
            # Tokenize dataset
            def tokenize_function(examples):
                # Combine instruction, input, and output into a single prompt
                texts = []
                for inst, inp, out in zip(examples["instruction"], examples["input"], examples["output"]):
                    if inp:
                        prompt = f"{inst}\n\nInput: {inp}\n\nOutput: {out}"
                    else:
                        prompt = f"{inst}\n\nOutput: {out}"
                    texts.append(prompt)
                
                # Tokenize
                tokenized = tokenizer(
                    texts,
                    truncation=True,
                    max_length=512,  # Adjust based on model context window
                    padding=False
                )
                
                # Create labels (same as input_ids for language modeling)
                tokenized["labels"] = tokenized["input_ids"].copy()
                
                return tokenized
            
            # Create HuggingFace Dataset
            dataset_dict = {
                "instruction": [s["instruction"] for s in formatted_samples],
                "input": [s.get("input", "") for s in formatted_samples],
                "output": [s["output"] for s in formatted_samples]
            }
            hf_dataset = Dataset.from_dict(dataset_dict)
            tokenized_dataset = hf_dataset.map(
                tokenize_function,
                batched=True,
                remove_columns=hf_dataset.column_names
            )
            
            # Split into train/validation (80/20)
            split_dataset = tokenized_dataset.train_test_split(test_size=0.2, seed=42)
            train_dataset = split_dataset["train"]
            eval_dataset = split_dataset["test"]
            
            # 6. Set up training arguments
            output_dir = str(self.adapter_storage_path / f"tenant-{tenant_id}" / adapter_version / "training")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            training_args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=config.get("epochs", 3),
                per_device_train_batch_size=config.get("batch_size", 4),
                per_device_eval_batch_size=config.get("batch_size", 4),
                gradient_accumulation_steps=config.get("gradient_accumulation_steps", 4),
                learning_rate=config.get("learning_rate", 2e-4),
                warmup_steps=10,
                logging_steps=10,
                eval_steps=50,
                save_steps=100,
                evaluation_strategy="steps",
                save_strategy="steps",
                load_best_model_at_end=True,
                metric_for_best_model="eval_loss",
                greater_is_better=False,
                fp16=torch.cuda.is_available(),
                remove_unused_columns=False,
                report_to="none",  # Disable wandb/tensorboard
            )
            
            # 7. Create data collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=tokenizer,
                mlm=False  # Causal LM, not masked LM
            )
            
            # 8. Initialize Trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                data_collator=data_collator,
            )
            
            # 9. Train
            logger.info("Starting training...")
            train_result = trainer.train()
            
            # 10. Evaluate
            logger.info("Evaluating model...")
            eval_result = trainer.evaluate()
            
            # 11. Save adapter
            adapter_path = str(self.adapter_storage_path / f"tenant-{tenant_id}" / adapter_version)
            logger.info(f"Saving adapter to: {adapter_path}")
            model.save_pretrained(adapter_path)
            tokenizer.save_pretrained(adapter_path)
            
            # Calculate adapter size
            adapter_size_mb = self._calculate_adapter_size(adapter_path)
            
            # 12. Update database metadata
            training_time = (datetime.utcnow() - start_time).total_seconds()
            
            if self.db:
                try:
                    from app.models.database import TenantModelAdapter, AdapterVersionHistory
                    from sqlalchemy import select
                    import uuid as uuid_lib
                    
                    # Check if adapter exists
                    stmt = select(TenantModelAdapter).where(TenantModelAdapter.tenant_id == uuid_lib.UUID(tenant_id))
                    existing_adapter = self.db.execute(stmt).scalar_one_or_none()
                    
                    if existing_adapter:
                        # Archive old version
                        old_version = AdapterVersionHistory(
                            tenant_id=existing_adapter.tenant_id,
                            adapter_version=existing_adapter.adapter_version,
                            adapter_path=existing_adapter.adapter_path,
                            base_model_name=existing_adapter.base_model_name,
                            base_model_version=existing_adapter.base_model_version,
                            training_data_count=existing_adapter.training_data_count,
                            training_config=existing_adapter.training_config,
                            performance_metrics=existing_adapter.performance_metrics,
                            status=existing_adapter.status,
                            trained_at=existing_adapter.trained_at
                        )
                        self.db.add(old_version)
                        
                        # Update existing
                        existing_adapter.adapter_version = adapter_version
                        existing_adapter.adapter_path = adapter_path
                        existing_adapter.status = "active"
                        existing_adapter.training_data_count = len(formatted_samples)
                        existing_adapter.training_config = config
                        existing_adapter.performance_metrics = {
                            "train_loss": train_result.training_loss,
                            "eval_loss": eval_result.get("eval_loss"),
                            "train_runtime": train_result.metrics.get("train_runtime", training_time),
                            "train_samples_per_second": train_result.metrics.get("train_samples_per_second")
                        }
                        existing_adapter.trained_at = datetime.utcnow()
                    else:
                        # Create new
                        new_adapter = TenantModelAdapter(
                            tenant_id=uuid_lib.UUID(tenant_id),
                            adapter_version=adapter_version,
                            adapter_path=adapter_path,
                            base_model_name=self.base_model_name,
                            base_model_version="1.0.0",  # TODO: Get actual version
                            training_data_count=len(formatted_samples),
                            training_config=config,
                            performance_metrics={
                                "train_loss": train_result.training_loss,
                                "eval_loss": eval_result.get("eval_loss"),
                                "train_runtime": train_result.metrics.get("train_runtime", training_time),
                                "train_samples_per_second": train_result.metrics.get("train_samples_per_second")
                            },
                            status="active",
                            trained_at=datetime.utcnow()
                        )
                        self.db.add(new_adapter)
                    
                    self.db.commit()
                    logger.info("Adapter metadata updated in database")
                    
                except Exception as e:
                    logger.error(f"Error updating adapter metadata in database: {e}")
                    self.db.rollback()
            
            # 13. Update job status
            if job_id and self.db:
                self._update_job_status(
                    job_id,
                    TrainingStatus.COMPLETED.value,
                    completed_at=datetime.utcnow(),
                    metrics={
                        "train_loss": train_result.training_loss,
                        "eval_loss": eval_result.get("eval_loss"),
                        "training_time_seconds": training_time,
                        "adapter_size_mb": adapter_size_mb
                    }
                )
            
            result = {
                "status": "completed",
                "adapter_path": adapter_path,
                "adapter_version": adapter_version,
                "adapter_size_mb": adapter_size_mb,
                "training_samples": len(formatted_samples),
                "training_time_seconds": training_time,
                "metrics": {
                    "train_loss": train_result.training_loss,
                    "eval_loss": eval_result.get("eval_loss"),
                }
            }
            
            logger.info(f"Training completed successfully for tenant {tenant_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error during training: {e}", exc_info=True)
            
            # Update job status to FAILED
            if job_id and self.db:
                self._update_job_status(
                    job_id,
                    TrainingStatus.FAILED.value,
                    error_message=str(e)
                )
            
            return {
                "status": "failed",
                "error": str(e),
                "adapter_path": None
            }
    
    def _format_training_samples(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format training samples into standard format.
        
        Expected input: List of dicts with 'input' and 'output' keys
        Output: List of dicts with 'instruction', 'input', 'output' keys
        """
        formatted = []
        for sample in samples:
            if "processed_data" in sample and sample["processed_data"]:
                # Use processed_data if available
                proc = sample["processed_data"]
                formatted.append({
                    "instruction": proc.get("instruction", "You are a cybersecurity expert. Answer the question:"),
                    "input": proc.get("input", ""),
                    "output": proc.get("output", "")
                })
            elif "input" in sample and "output" in sample:
                # Use input/output directly
                formatted.append({
                    "instruction": "You are a cybersecurity expert. Answer the question:",
                    "input": sample.get("input", ""),
                    "output": sample.get("output", "")
                })
            else:
                logger.warning(f"Skipping invalid sample: {sample}")
        
        return formatted
    
    def _calculate_adapter_size(self, adapter_path: str) -> float:
        """Calculate adapter size in MB."""
        try:
            total_size = 0
            adapter_path_obj = Path(adapter_path)
            
            if adapter_path_obj.exists():
                for file_path in adapter_path_obj.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
            
            return round(total_size / (1024 * 1024), 2)
        except Exception as e:
            logger.warning(f"Error calculating adapter size: {e}")
            return 0.0
    
    def _update_job_status(
        self,
        job_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """Update training job status in database."""
        if not self.db:
            return
        
        try:
            from app.models.database import AdapterTrainingJob
            from sqlalchemy import select
            
            stmt = select(AdapterTrainingJob).where(AdapterTrainingJob.job_id == job_id)
            job = self.db.execute(stmt).scalar_one_or_none()
            
            if job:
                job.status = status
                if started_at:
                    job.started_at = started_at
                if completed_at:
                    job.completed_at = completed_at
                if error_message:
                    job.error_message = error_message
                if metrics:
                    job.metrics = metrics
                job.updated_at = datetime.utcnow()
                
                self.db.commit()
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
            self.db.rollback()
    
    def retrain_adapter(
        self,
        tenant_id: str,
        new_training_data: Dict[str, Any],
        base_adapter_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrain adapter with new data.
        
        Can either:
        - Train new adapter from base model
        - Fine-tune existing adapter (incremental learning)
        """
        # TODO: Implement retraining logic
        # For now, just train new adapter from base
        logger.info(f"Retraining adapter for tenant {tenant_id} (from base model)")
        
        # Use default config
        config = {
            "epochs": 3,
            "learning_rate": 2e-4,
            "batch_size": 4,
        }
        
        return self.execute_training(tenant_id, new_training_data, config)
    
    def validate_training_data(
        self,
        tenant_id: str,
        dataset: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate training dataset before training."""
        samples = dataset.get("samples", [])
        
        if len(samples) < 10:
            return {
                "valid": False,
                "error": "Insufficient training data (need at least 10 samples)"
            }
        
        # Check data quality
        errors = []
        for i, sample in enumerate(samples):
            # Check if has processed_data with input/output
            if "processed_data" in sample:
                proc = sample["processed_data"]
                if "input" not in proc and "output" not in proc:
                    errors.append(f"Sample {i} missing input or output in processed_data")
            elif "input" not in sample and "output" not in sample:
                errors.append(f"Sample {i} missing input or output")
        
        return {
            "valid": len(errors) == 0,
            "sample_count": len(samples),
            "errors": errors
        }
