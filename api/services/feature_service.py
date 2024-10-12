from pydantic import BaseModel, ConfigDict
import logging
from configs import dify_config
from services.billing_service import BillingService
from services.enterprise.enterprise_service import EnterpriseService

class SubscriptionModel(BaseModel):
    plan: str = "sandbox"
    interval: str = ""

class BillingModel(BaseModel):
    enabled: bool = True
    subscription: SubscriptionModel = SubscriptionModel()

class LimitationModel(BaseModel):
    size: int = 0
    limit: int = 0

class FeatureModel(BaseModel):
    billing: BillingModel = BillingModel()
    members: LimitationModel = LimitationModel(size=0, limit=1)
    apps: LimitationModel = LimitationModel(size=0, limit=10)
    vector_space: LimitationModel = LimitationModel(size=0, limit=5)
    annotation_quota_limit: LimitationModel = LimitationModel(size=0, limit=10)
    documents_upload_quota: LimitationModel = LimitationModel(size=0, limit=50)
    docs_processing: str = "standard"
    can_replace_logo: bool = False
    model_load_balancing_enabled: bool = False
    dataset_operator_enabled: bool = False

    # pydantic configs
    model_config = ConfigDict(protected_namespaces=())

class SystemFeatureModel(BaseModel):
    sso_enforced_for_signin: bool = False
    sso_enforced_for_signin_protocol: str = ""
    sso_enforced_for_web: bool = False
    sso_enforced_for_web_protocol: str = ""
    enable_web_sso_switch_component: bool = False

# Configuração de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_and_get(value, default_value, expected_type=str):
    """Valida se o valor não é None e retorna o valor convertido. Se None, retorna um valor padrão."""
    if value is None:
        return default_value
    try:
        return expected_type(value)
    except (ValueError, TypeError):
        return default_value

class FeatureService:
    @classmethod
    def get_features(cls, tenant_id: str) -> FeatureModel:
        features = FeatureModel()

        # Preencher com parâmetros do ambiente
        cls._fulfill_params_from_env(features)
        logger.debug(f"Parâmetros de ambiente preenchidos: {features}")

        # Preencher com informações de billing, se habilitado
        if dify_config.BILLING_ENABLED:
            try:
                cls._fulfill_params_from_billing_api(features, tenant_id)
                logger.debug(f"Informações de billing preenchidas: {features}")
            except Exception as e:
                logger.error(f"Erro ao preencher informações de billing para tenant_id '{tenant_id}': {e}")

        return features

    @classmethod
    def get_system_features(cls) -> SystemFeatureModel:
        system_features = SystemFeatureModel()

        if dify_config.ENTERPRISE_ENABLED:
            system_features.enable_web_sso_switch_component = True
            cls._fulfill_params_from_enterprise(system_features)

        return system_features

    @classmethod
    def _fulfill_params_from_env(cls, features: FeatureModel):
        features.can_replace_logo = dify_config.CAN_REPLACE_LOGO
        features.model_load_balancing_enabled = dify_config.MODEL_LB_ENABLED
        features.dataset_operator_enabled = dify_config.DATASET_OPERATOR_ENABLED

    @classmethod
    def _fulfill_params_from_billing_api(cls, features: FeatureModel, tenant_id: str):
        try:
            # 1. Recuperar detalhes da assinatura (pagamentos, valores)
            plan_info = BillingService.get_current_plan_info(tenant_id)
            logger.debug(f"Detalhes do plano para tenant_id {tenant_id}: {plan_info}")

            # Preenchendo as informações de billing com fallback adequado
            billing_info = plan_info.get("billing", {})
            logger.debug(f"Billing info para tenant {tenant_id}: {billing_info}")

            features.billing.enabled = billing_info.get("enabled", False)
            features.billing.subscription.plan = validate_and_get(plan_info.get("subscription", {}).get("plan"), "sandbox")
            features.billing.subscription.interval = validate_and_get(plan_info.get("subscription", {}).get("interval"), "month")

            # 2. Recuperar os metadados do produto associado à assinatura
            product_id = plan_info.get("subscription", {}).get("product_id")
            if not product_id:
                raise ValueError(f"Product ID não encontrado para tenant {tenant_id}")

            product_info = BillingService.get_product_metadata(product_id)
            logger.debug(f"Metadados do produto para tenant {tenant_id}: {product_info}")

            # Preenchendo limites de membros, apps, etc. a partir dos metadados do produto
            features.members.size = plan_info.get("members", {}).get("size", 0)
            features.members.limit = product_info.get("members_limit", 1)

            features.apps.size = plan_info.get("apps", {}).get("size", 0)
            features.apps.limit = product_info.get("apps_limit", 10)

            features.vector_space.size = plan_info.get("vector_space", {}).get("size", 0)
            features.vector_space.limit = product_info.get("vector_space_limit", 5)

            features.documents_upload_quota.size = plan_info.get("documents_upload_quota", {}).get("size", 0)
            features.documents_upload_quota.limit = product_info.get("documents_upload_limit", 50)

            features.annotation_quota_limit.size = plan_info.get("annotation_quota_limit", {}).get("size", 0)
            features.annotation_quota_limit.limit = product_info.get("annotation_quota_limit", 10)

            # Tratar docs_processing com fallback
            features.docs_processing = product_info.get("docs_processing", "standard")

            # Usando to_bool para valores booleanos, com suporte a None
            features.can_replace_logo = validate_and_get(product_info.get("can_replace_logo"), False, bool)
            logger.debug(f"can_replace_logo processado: {features.can_replace_logo}")

            features.model_load_balancing_enabled = validate_and_get(product_info.get("model_load_balancing_enabled"), False, bool)
            logger.debug(f"model_load_balancing_enabled processado: {features.model_load_balancing_enabled}")

            features.dataset_operator_enabled = validate_and_get(product_info.get("dataset_operator_enabled"), False, bool)
            logger.debug(f"dataset_operator_enabled processado: {features.dataset_operator_enabled}")

        except KeyError as e:
            logger.error(f"Erro ao preencher informações do plano: chave ausente {e}")
            raise ValueError("Informações incompletas para o tenant. Contate o administrador.")
        except Exception as e:
            logger.error(f"Erro inesperado ao preencher informações do plano: {e}")
            raise ValueError("Erro ao processar as informações do tenant. Verifique o sistema.")

    @classmethod
    def _fulfill_params_from_enterprise(cls, features: SystemFeatureModel):
        enterprise_info = EnterpriseService.get_info()

        features.sso_enforced_for_signin = enterprise_info["sso_enforced_for_signin"]
        features.sso_enforced_for_signin_protocol = enterprise_info["sso_enforced_for_signin_protocol"]
        features.sso_enforced_for_web = enterprise_info["sso_enforced_for_web"]
        features.sso_enforced_for_web_protocol = enterprise_info["sso_enforced_for_web_protocol"]
