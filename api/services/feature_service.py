from pydantic import BaseModel, ConfigDict
import logging
import json  # Adicionar json para formatar os logs
from configs import dify_config
from services.billing_service import BillingService
from services.enterprise.enterprise_service import EnterpriseService

# Definição dos modelos usados no FeatureService
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

    # Configuração do Pydantic
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

# Função de checklist para logs
def log_checklist(check_name, success, error=None, solution=None):
    """
    Função que registra logs baseados em um checklist de verificações.

    :param check_name: Nome do item do checklist.
    :param success: Booleano indicando se a verificação foi bem-sucedida.
    :param error: Detalhe do erro, caso ocorra.
    :param solution: Sugestão de solução para o erro.
    """
    if success:
        # Não gerar logs para processos bem-sucedidos
        return
    else:
        logger.error(f"[{check_name}] Falha: {error}")
        if solution:
            logger.error(f"[{check_name}] Sugestão: {solution}")

# Configuração dos planos do Stripe
STRIPE_PLANS = {
    "sandbox": {
        "productId": "prod_QsZbt0DwShON3a",
        "prices": {
            "month": "price_1Q0oSBP1Q7ODTY3xIiGwvQm3",
            "year": "price_1Q6wc0P1Q7ODTY3x2Ea8EsiH",
            "oneTime": "price_1Q8RJUP1Q7ODTY3xVWsM4Z9F"
        },
    },
    "professional": {
        "productId": "prod_QsZbK1TJoho55K",
        "prices": {
            "month": "price_1Q0oSkP1Q7ODTY3xljhmKOea",
            "year": "price_1Q8RKbP1Q7ODTY3xlNaUPy0U",
            "oneTime": None
        },
    },
    "team": {
        "productId": "prod_QsZcYAP5OuWzrr",
        "prices": {
            "month": "price_1Q7P6IP1Q7ODTY3xCfKyZyi7",
            "year": "price_1Q7P3sP1Q7ODTY3x54GP00jb",
            "oneTime": None
        },
    },
    "enterprise": {
        "productId": "prod_QsrSCBv9JZiE6D",
        "prices": {
            "month": "price_1Q8RN0P1Q7ODTY3xwhn1XfXT",
            "year": "price_1Q8RN0P1Q7ODTY3xwhn1XfXT",
            "oneTime": "price_1Q8RN0P1Q7ODTY3xwhn1XfXT"
        },
    },
}


class FeatureService:

    @classmethod
    def get_features(cls, tenant_id: str) -> FeatureModel:
        features = FeatureModel()  # Inicializa o objeto de recursos

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
                raise ValueError(f"Falha ao recuperar as informações de billing para tenant_id '{tenant_id}'. Verifique o sistema.")

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
        """Preenche as informações do ambiente no FeatureModel"""
        features.can_replace_logo = dify_config.CAN_REPLACE_LOGO
        features.model_load_balancing_enabled = dify_config.MODEL_LB_ENABLED
        features.dataset_operator_enabled = dify_config.DATASET_OPERATOR_ENABLED

    @classmethod
    def update_features_from_billing(cls, tenant_id: str):
        """Atualiza as features do sistema com base nas informações de billing"""
        try:
            features = FeatureModel()
            
            # Chama a função que preenche as informações de billing
            cls._fulfill_params_from_billing_api(features, tenant_id)

            # Verifica se as informações de subscription foram corretamente preenchidas
            log_checklist(
                check_name="Preenchimento de Subscription",
                success=features.billing.subscription.plan != "",
                error="Assinatura ausente ou inválida",
                solution="Definir plano padrão 'sandbox' para situações de fallback."
            )
            
            # Verifica se as informações de subscription foram corretamente preenchidas
            if not features.billing.subscription.plan:
                logger.warning(f"Assinatura ausente ou inválida para tenant_id {tenant_id}, utilizando fallback.")
                features.billing.subscription.plan = "sandbox"
                features.billing.subscription.interval = "month"
            
            # Validação final das features
            cls._validate_filled_features(features, tenant_id)
            
            return features
        
        except Exception as e:
            logger.error(f"Erro ao atualizar features para tenant {tenant_id}: {e}")
            raise

    @classmethod
    def _validate_filled_features(cls, features: FeatureModel, tenant_id: str):
        """Realiza validações finais sobre as features preenchidas"""
        try:
            # Verificar se as principais informações de features foram preenchidas
            log_checklist(
                check_name="Validação dos Limites de Apps e Membros",
                success=bool(features.apps.limit and features.members.limit),
                error=f"Limites de apps ou membros ausentes para o tenant {tenant_id}",
                solution="Certifique-se de que os limites de apps e membros foram corretamente atribuídos."
            )

            if not features.docs_processing:
                logger.warning(f"Processamento de documentos não definido para tenant {tenant_id}, aplicando padrão 'standard'")
                features.docs_processing = "standard"

            logger.info(f"Features validadas com sucesso para tenant {tenant_id}")
        except Exception as e:
            logger.error(f"Erro ao validar features para tenant {tenant_id}: {e}")
            raise

    @classmethod
    def _fulfill_params_from_billing_api(cls, features: FeatureModel, tenant_id: str, email: str = None):
        """Preenche as informações de billing a partir do BillingService"""
        try:
            # Se o email não foi fornecido, buscar o cliente com base no tenant_id
            if not email:
                customer = BillingService.find_customer_by_email_and_tenant(email=email, tenant_id=tenant_id)
                log_checklist(
                    check_name="Busca de Cliente pelo Tenant ID",
                    success=bool(customer and customer.email),
                    error=f"Cliente não encontrado para tenant_id {tenant_id}",
                    solution="Verifique se o tenant_id está correto e o cliente foi registrado corretamente no Stripe."
                )

                if not customer or not customer.email:
                    raise ValueError(f"Cliente não encontrado para tenant_id {tenant_id}")
                email = customer.email

            # Obter as informações de plano usando o tenant_id
            plan_info = BillingService.get_info(tenant_id=tenant_id)
            logger.debug(f"Plan info recebido do Stripe para tenant_id {tenant_id}: {json.dumps(plan_info, indent=2)}")
            log_checklist(
                check_name="Recuperação de Informações de Plano",
                success=bool(plan_info),
                error=f"Informações de plano não encontradas para o tenant {tenant_id}",
                solution="Verifique as assinaturas do cliente no Stripe e o tenant_id fornecido."
            )

            if not plan_info:
                raise ValueError(f"Informações de plano não encontradas para o tenant {tenant_id}")

            # Obter informações de subscription
            subscription_info = BillingService.get_subscription(email=email, tenant_id=tenant_id)
            logger.debug(f"Subscription info recebido do Stripe para tenant_id {tenant_id}: {json.dumps(subscription_info, indent=2)}")
            log_checklist(
                check_name="Recuperação de Assinatura",
                success=bool(subscription_info and subscription_info.get("plan")),
                error=f"Assinatura ausente para tenant_id {tenant_id}",
                solution="Verifique as assinaturas ativas do cliente e defina um plano padrão se necessário."
            )
            
            if not subscription_info or not subscription_info.get("plan"):
                logger.warning(f"Assinatura ausente para tenant_id {tenant_id}, aplicando valores padrão.")
                subscription_info = {"plan": "sandbox", "interval": "month"}  # Valores padrão

            # Preencher o modelo de billing com as informações da subscription
            features.billing.enabled = plan_info.get("billing", {}).get("enabled", False)
            features.billing.subscription.plan = subscription_info.get("plan", "sandbox")
            features.billing.subscription.interval = subscription_info.get("interval", "month")

            # Verificar o status da assinatura para saber se está ativa
            plan_status = subscription_info.get("status", "inactive")
            if plan_status == "active":
                logger.debug(f"Plano ativo para tenant {tenant_id}: {subscription_info}")
                features.billing.enabled = True
            else:
                logger.debug(f"Plano inativo para tenant {tenant_id}: {subscription_info}")
                features.billing.enabled = False

            # Verificar o plano e buscar o productId correspondente no dicionário de planos
            plan_name = subscription_info.get("plan", "sandbox")  # Exemplo: "sandbox"
            if plan_name in STRIPE_PLANS:
                product_id = STRIPE_PLANS[plan_name]["productId"]
            else:
                raise ValueError(f"Plano '{plan_name}' não encontrado nos planos configurados para o tenant {tenant_id}")

            logger.debug(f"Plan {plan_name} mapeado para product_id {product_id} para tenant_id {tenant_id}")

            # Obter os metadados do produto usando o product_id
            product_info = BillingService.get_product_metadata(product_id)
            log_checklist(
                check_name="Recuperação de Metadados do Produto",
                success=bool(product_info),
                error=f"Metadados do produto ausentes para tenant_id {tenant_id}",
                solution="Verifique se o produto correto está associado à assinatura no Stripe."
            )
            if not product_info:
                logger.warning(f"Metadados do produto ausentes para tenant_id {tenant_id}. Usando valores padrão.")
                product_info = cls._default_product_info()

            # Preenchendo limites e configurações com base nos metadados do produto
            features.members.size = plan_info.get("members", {}).get("size", 0)
            features.members.limit = int(product_info.get("members_limit", 1))

            features.apps.size = plan_info.get("apps", {}).get("size", 0)
            features.apps.limit = int(product_info.get("apps_limit", 10))

            features.vector_space.size = plan_info.get("vector_space", {}).get("size", 0)
            features.vector_space.limit = int(product_info.get("vector_space_limit", 5))

            features.documents_upload_quota.size = plan_info.get("documents_upload_quota", {}).get("size", 0)
            features.documents_upload_quota.limit = int(product_info.get("documents_upload_limit", 50))

            features.annotation_quota_limit.size = plan_info.get("annotation_quota_limit", {}).get("size", 0)
            features.annotation_quota_limit.limit = int(product_info.get("annotation_quota_limit", 10))

            features.docs_processing = product_info.get("docs_processing", "standard")
            features.can_replace_logo = bool(product_info.get("can_replace_logo", False))
            features.model_load_balancing_enabled = bool(product_info.get("model_load_balancing_enabled", False))
            features.dataset_operator_enabled = bool(product_info.get("dataset_operator_enabled", False))

        except ValueError as ve:
            logger.error(f"Erro ao preencher informações do billing para tenant_id '{tenant_id}': {ve}")
            raise
        except KeyError as e:
            logger.error(f"Erro ao preencher informações do plano: chave ausente {e}")
            raise ValueError(f"Informações incompletas para o tenant {tenant_id}.")
        except Exception as e:
            logger.error(f"Erro inesperado ao preencher informações do plano: {e}")
            raise ValueError(f"Erro ao processar as informações do tenant {tenant_id}. Verifique o sistema.")

    @classmethod
    def _default_product_info(cls):
        """Retorna valores padrão para os metadados do produto"""
        return {
            "members_limit": 1,
            "apps_limit": 10,
            "vector_space_limit": 5,
            "documents_upload_limit": 50,
            "annotation_quota_limit": 10,
            "docs_processing": "standard",
            "can_replace_logo": False,
            "model_load_balancing_enabled": False,
            "dataset_operator_enabled": False
        }

    @classmethod
    def _fulfill_params_from_enterprise(cls, features: SystemFeatureModel):
        """Preenche informações específicas de enterprise"""
        enterprise_info = EnterpriseService.get_info()
        features.sso_enforced_for_signin = enterprise_info["sso_enforced_for_signin"]
        features.sso_enforced_for_signin_protocol = enterprise_info["sso_enforced_for_signin_protocol"]
        features.sso_enforced_for_web = enterprise_info["sso_enforced_for_web"]
        features.sso_enforced_for_web_protocol = enterprise_info["sso_enforced_for_web_protocol"]

