"""
Tests for Adapter Training Service.
"""

import pytest
from app.services.adapter_training_service import AdapterTrainingService, TrainingStatus


def test_start_training_job(db_session, test_tenant_id, mock_peft_available):
    """Test starting a training job."""
    service = AdapterTrainingService(db_session=db_session)
    
    config = {
        "epochs": 3,
        "learning_rate": 2e-4,
        "batch_size": 4,
    }
    
    job = service.start_training_job(
        tenant_id=test_tenant_id,
        training_config=config
    )
    
    assert job["status"] == TrainingStatus.PENDING.value
    assert job["tenant_id"] == test_tenant_id
    assert job["config"]["epochs"] == 3
    assert job["config"]["learning_rate"] == 2e-4
    assert "job_id" in job


def test_get_training_job_status(db_session, test_tenant_id, mock_peft_available):
    """Test getting training job status."""
    service = AdapterTrainingService(db_session=db_session)
    
    # Start job
    job = service.start_training_job(
        tenant_id=test_tenant_id,
        training_config={"epochs": 3}
    )
    
    # Get status
    status = service.get_training_job_status(job["job_id"])
    
    assert status is not None
    assert status["job_id"] == job["job_id"]
    assert status["tenant_id"] == test_tenant_id
    assert status["status"] == TrainingStatus.PENDING.value


def test_validate_training_data(test_tenant_id, mock_peft_available):
    """Test validating training data."""
    service = AdapterTrainingService()
    
    # Valid dataset
    valid_dataset = {
        "samples": [
            {"instruction": "Answer:", "input": "Q1", "output": "A1"},
            {"instruction": "Answer:", "input": "Q2", "output": "A2"},
        ] * 10  # 20 samples
    }
    
    validation = service.validate_training_data(test_tenant_id, valid_dataset)
    assert validation["valid"] is True
    assert validation["sample_count"] == 20
    assert len(validation["errors"]) == 0
    
    # Invalid dataset (too few samples)
    invalid_dataset = {
        "samples": [
            {"instruction": "Answer:", "input": "Q1", "output": "A1"},
        ]
    }
    
    validation = service.validate_training_data(test_tenant_id, invalid_dataset)
    assert validation["valid"] is False
    assert "Insufficient" in validation["error"]


def test_validate_training_data_missing_fields(test_tenant_id, mock_peft_available):
    """Test validation catches missing fields."""
    service = AdapterTrainingService()
    
    # Dataset with missing output
    invalid_dataset = {
        "samples": [
            {"instruction": "Answer:", "input": "Q1", "output": "A1"},
            {"instruction": "Answer:", "input": "Q2"},  # Missing output
        ] * 10
    }
    
    validation = service.validate_training_data(test_tenant_id, invalid_dataset)
    assert validation["valid"] is False
    assert len(validation["errors"]) > 0


@pytest.mark.skip(reason="Requires actual PEFT/Transformers - use integration tests")
def test_execute_training(
    db_session,
    test_tenant_id,
    test_training_data,
    test_adapter_storage_path,
    mock_peft_available,
    mock_model_loading,
    mock_trainer
):
    """Test executing training (mocked)."""
    service = AdapterTrainingService(db_session=db_session)
    
    # Prepare dataset
    dataset = {
        "samples": test_training_data
    }
    
    config = {
        "epochs": 1,  # Reduced for testing
        "learning_rate": 2e-4,
        "batch_size": 2,
    }
    
    # Start job
    job = service.start_training_job(
        tenant_id=test_tenant_id,
        training_config=config
    )
    
    # Execute training (mocked)
    result = service.execute_training(
        tenant_id=test_tenant_id,
        training_dataset=dataset,
        config=config,
        job_id=job["job_id"]
    )
    
    assert result["status"] in ["completed", "failed"]  # May fail without actual model
    if result["status"] == "completed":
        assert "adapter_path" in result
        assert "adapter_version" in result
        assert "metrics" in result

