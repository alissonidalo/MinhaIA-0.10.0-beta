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


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
            plan_info = BillingService.get_current_plan_info(tenant_id)
            logger.debug(f"Detalhes do plano para tenant_id {tenant_id}: {plan_info}")

            features.billing.enabled = plan_info["billing"]["enabled"]
            features.billing.subscription.plan = plan_info["billing"]["subscription"]["plan"]

            features.members.size = plan_info["members"]["size"]
            features.members.limit = plan_info["members"]["limit"]

            features.apps.size = plan_info["apps"]["size"]
            features.apps.limit = plan_info["apps"]["limit"]

            features.vector_space.size = plan_info["vector_space"]["size"]
            features.vector_space.limit = plan_info["vector_space"]["limit"]

            features.documents_upload_quota.size = plan_info["documents_upload_quota"]["size"]
            features.documents_upload_quota.limit = plan_info["documents_upload_quota"]["limit"]

            features.annotation_quota_limit.size = plan_info["annotation_quota_limit"]["size"]
            features.annotation_quota_limit.limit = plan_info["annotation_quota_limit"]["limit"]

            features.docs_processing = plan_info["docs_processing"]
            features.can_replace_logo = plan_info["can_replace_logo"]
            features.model_load_balancing_enabled = plan_info["model_load_balancing_enabled"]
            features.dataset_operator_enabled = plan_info["dataset_operator_enabled"]

        except KeyError as e:
            logger.error(f"Erro ao preencher informações do plano: chave ausente {e}")

    @classmethod
    def _fulfill_params_from_enterprise(cls, features):
        enterprise_info = EnterpriseService.get_info()

        features.sso_enforced_for_signin = enterprise_info["sso_enforced_for_signin"]
        features.sso_enforced_for_signin_protocol = enterprise_info["sso_enforced_for_signin_protocol"]
        features.sso_enforced_for_web = enterprise_info["sso_enforced_for_web"]
        features.sso_enforced_for_web_protocol = enterprise_info["sso_enforced_for_web_protocol"]
