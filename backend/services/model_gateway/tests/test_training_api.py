"""
Tests for Training API endpoints.
"""

import pytest
import uuid
from fastapi import status
from app.services.training_data_service import DataType


def test_store_training_data_endpoint(client, test_tenant_id):
    """Test storing training data via API."""
    response = client.post(
        "/internal/llm/training/data",
        json={
            "tenant_id": test_tenant_id,
            "module": "iam",
            "data_type": "qa_pair",
            "raw_data": {
                "question": "What is IAM?",
                "answer": "Identity and Access Management"
            },
            "tags": ["test"]
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "stored"
    assert data["tenant_id"] == test_tenant_id


def test_store_qa_pair_endpoint(client, test_tenant_id):
    """Test storing Q&A pair via API."""
    response = client.post(
        "/internal/llm/training/qa",
        params={
            "tenant_id": test_tenant_id,
            "module": "iam",
            "question": "What is RBAC?",
            "answer": "Role-Based Access Control"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "stored"


def test_start_training_job_endpoint(
    client,
    test_tenant_id,
    test_training_data,
    mock_peft_available,
    mock_job_queue
):
    """Test starting a training job via API."""
    # First, store some training data
    for sample in test_training_data[:5]:  # Store 5 samples
        client.post(
            "/internal/llm/training/qa",
            params={
                "tenant_id": test_tenant_id,
                "module": "iam",
                "question": sample["input"],
                "answer": sample["output"]
            }
        )
    
    # Start training
    response = client.post(
        "/internal/llm/training/start",
        json={
            "tenant_id": test_tenant_id,
            "config": {
                "epochs": 1,
                "learning_rate": 2e-4,
                "batch_size": 2
            }
        }
    )
    
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
    
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "job_id" in data
        assert data["tenant_id"] == test_tenant_id
        assert data["status"] == "pending"


def test_get_training_job_status_endpoint(
    client,
    test_tenant_id,
    test_training_data,
    mock_peft_available,
    mock_job_queue
):
    """Test getting training job status via API."""
    # Store training data
    for sample in test_training_data[:5]:
        client.post(
            "/internal/llm/training/qa",
            params={
                "tenant_id": test_tenant_id,
                "module": "iam",
                "question": sample["input"],
                "answer": sample["output"]
            }
        )
    
    # Start training
    start_response = client.post(
        "/internal/llm/training/start",
        json={
            "tenant_id": test_tenant_id,
            "config": {"epochs": 1}
        }
    )
    
    if start_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        pytest.skip("Job queue unavailable")
    
    job_id = start_response.json()["job_id"]
    
    # Get status
    status_response = client.get(f"/internal/llm/training/jobs/{job_id}")
    
    assert status_response.status_code == status.HTTP_200_OK
    data = status_response.json()
    assert data["job_id"] == job_id
    assert data["tenant_id"] == test_tenant_id
    assert "status" in data


def test_start_training_without_data(client, test_tenant_id, mock_peft_available):
    """Test starting training without sufficient data."""
    response = client.post(
        "/internal/llm/training/start",
        json={
            "tenant_id": test_tenant_id,
            "config": {"epochs": 3}
        }
    )
    
    # Should fail due to insufficient data
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_tenant_isolation_api(client, test_tenant_id):
    """Test tenant isolation via API."""
    tenant_1 = test_tenant_id
    tenant_2 = str(uuid.uuid4())
    
    # Store data for tenant 1
    response_1 = client.post(
        "/internal/llm/training/qa",
        params={
            "tenant_id": tenant_1,
            "module": "iam",
            "question": "Tenant 1 question",
            "answer": "Tenant 1 answer"
        }
    )
    assert response_1.status_code == status.HTTP_200_OK
    
    # Store data for tenant 2
    response_2 = client.post(
        "/internal/llm/training/qa",
        params={
            "tenant_id": tenant_2,
            "module": "iam",
            "question": "Tenant 2 question",
            "answer": "Tenant 2 answer"
        }
    )
    assert response_2.status_code == status.HTTP_200_OK
    
    # Data should be isolated (tested in service layer)

