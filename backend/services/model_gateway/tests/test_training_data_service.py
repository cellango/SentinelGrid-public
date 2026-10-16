"""
Tests for Training Data Service.
"""

import pytest
import uuid
from app.services.training_data_service import TrainingDataService, DataType


def test_store_training_data(db_session, test_tenant_id):
    """Test storing training data."""
    service = TrainingDataService(db_session=db_session)
    
    result = service.store_training_data(
        tenant_id=test_tenant_id,
        module="iam",
        data_type=DataType.QA_PAIR,
        raw_data={"question": "What is IAM?", "answer": "Identity and Access Management"},
        processed_data={"input": "What is IAM?", "output": "Identity and Access Management"},
        tags=["test", "iam"]
    )
    
    assert result["status"] == "stored"
    assert result["tenant_id"] == test_tenant_id
    assert result["module"] == "iam"
    assert result["data_type"] == "qa_pair"


def test_store_qa_pair(db_session, test_tenant_id):
    """Test storing Q&A pair."""
    service = TrainingDataService(db_session=db_session)
    
    result = service.store_qa_pair(
        tenant_id=test_tenant_id,
        module="iam",
        question="What is RBAC?",
        answer="Role-Based Access Control",
        context={"category": "access_control"},
        tags=["rbac"]
    )
    
    assert result["status"] == "stored"
    assert "processed_data" in result
    assert result["processed_data"]["input"] == "What is RBAC?"
    assert result["processed_data"]["output"] == "Role-Based Access Control"


def test_get_training_data(db_session, test_tenant_id):
    """Test retrieving training data."""
    service = TrainingDataService(db_session=db_session)
    
    # Store some data
    for i in range(5):
        service.store_qa_pair(
            tenant_id=test_tenant_id,
            module="iam",
            question=f"Question {i}?",
            answer=f"Answer {i}",
        )
    
    # Retrieve data
    data = service.get_training_data(
        tenant_id=test_tenant_id,
        module="iam",
        limit=10
    )
    
    assert len(data) == 5
    assert all(d["tenant_id"] == test_tenant_id for d in data)
    assert all(d["module"] == "iam" for d in data)


def test_prepare_training_dataset(db_session, test_tenant_id, test_training_data):
    """Test preparing training dataset."""
    service = TrainingDataService(db_session=db_session)
    
    # Store training data
    for sample in test_training_data:
        service.store_training_data(
            tenant_id=test_tenant_id,
            module="iam",
            data_type=DataType.QA_PAIR,
            raw_data=sample,
            processed_data=sample,
        )
    
    # Prepare dataset
    dataset = service.prepare_training_dataset(
        tenant_id=test_tenant_id,
        module="iam"
    )
    
    assert "samples" in dataset
    assert len(dataset["samples"]) == len(test_training_data)
    assert all("instruction" in s for s in dataset["samples"])
    assert all("input" in s for s in dataset["samples"])
    assert all("output" in s for s in dataset["samples"])


def test_tenant_isolation(db_session, test_tenant_id):
    """Test tenant data isolation."""
    service = TrainingDataService(db_session=db_session)
    
    tenant_1 = test_tenant_id
    tenant_2 = str(uuid.uuid4())
    
    # Store data for tenant 1
    service.store_qa_pair(
        tenant_id=tenant_1,
        module="iam",
        question="Tenant 1 question",
        answer="Tenant 1 answer",
    )
    
    # Store data for tenant 2
    service.store_qa_pair(
        tenant_id=tenant_2,
        module="iam",
        question="Tenant 2 question",
        answer="Tenant 2 answer",
    )
    
    # Retrieve tenant 1 data
    tenant_1_data = service.get_training_data(tenant_id=tenant_1)
    assert len(tenant_1_data) == 1
    assert tenant_1_data[0]["raw_data"]["question"] == "Tenant 1 question"
    
    # Retrieve tenant 2 data
    tenant_2_data = service.get_training_data(tenant_id=tenant_2)
    assert len(tenant_2_data) == 1
    assert tenant_2_data[0]["raw_data"]["question"] == "Tenant 2 question"
    
    # Verify isolation
    assert tenant_1_data[0]["raw_data"]["question"] != tenant_2_data[0]["raw_data"]["question"]

