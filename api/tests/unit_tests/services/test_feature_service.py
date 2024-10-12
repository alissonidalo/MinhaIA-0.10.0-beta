# test for api/services/feature_service.py
import pytest
from unittest.mock import patch
from services.feature_service import FeatureService, FeatureModel

@patch('services.billing_service.BillingService.get_current_plan_info')
def test_fulfill_params_from_billing_api(mock_get_current_plan_info):
    # Simulação de retorno da API de billing
    mock_get_current_plan_info.return_value = {
        "billing": {
            "enabled": True,
            "subscription": {"plan": "team"}
        },
        "members": {"size": 5, "limit": 10},
        "apps": {"size": 2, "limit": 10},
        "vector_space": {"size": 3, "limit": 5},
        "can_replace_logo": "true",
        "model_load_balancing_enabled": "true",
        "dataset_operator_enabled": "false"
    }
    
    tenant_id = "test-tenant-id"
    features = FeatureService.get_features(tenant_id)
    
    assert features.billing.enabled is True
    assert features.billing.subscription.plan == "team"
    assert features.members.size == 5
    assert features.apps.size == 2
    assert features.vector_space.size == 3
    assert features.can_replace_logo is True
    assert features.model_load_balancing_enabled is True
    assert features.dataset_operator_enabled is False

@patch('services.billing_service.BillingService.get_current_plan_info')
def test_fulfill_params_with_invalid_data(mock_get_current_plan_info):
    # Simulação de retorno da API com dados faltantes
    mock_get_current_plan_info.return_value = {}

    tenant_id = "test-tenant-id"
    features = FeatureService.get_features(tenant_id)

    assert features.billing.enabled is False
    assert features.billing.subscription.plan == "sandbox"
    assert features.members.size == 0
    assert features.apps.size == 0
    assert features.vector_space.size == 0
    assert features.can_replace_logo is False
    assert features.model_load_balancing_enabled is False
    assert features.dataset_operator_enabled is False
