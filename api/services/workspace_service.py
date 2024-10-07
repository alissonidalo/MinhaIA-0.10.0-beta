import logging
from flask_login import current_user
from configs import dify_config
from extensions.ext_database import db
from models.account import Tenant, TenantAccountJoin, TenantAccountJoinRole
from services.account_service import TenantService
from services.feature_service import FeatureService

# Configurando logs
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkspaceService:
    @classmethod
    def get_tenant_info(cls, tenant: Tenant):
        if not tenant:
            logger.error("Tenant não fornecido.")
            return None
        
        logger.debug(f"Obtendo informações do tenant: {tenant.id}")

        # Inicializa as informações básicas do tenant
        tenant_info = {
            "id": tenant.id,
            "name": tenant.name,
            "plan": "unknown",  # Definido inicialmente como desconhecido até que seja obtido do FeatureService
            "status": "inactive",  # Definido inicialmente como inativo até que o status seja confirmado
            "created_at": tenant.created_at,
            "in_trail": True,
            "trial_end_reason": None,
            "role": "normal",
        }

        # Obter função do usuário no tenant
        tenant_account_join = (
            db.session.query(TenantAccountJoin)
            .filter(TenantAccountJoin.tenant_id == tenant.id, TenantAccountJoin.account_id == current_user.id)
            .first()
        )

        if tenant_account_join:
            tenant_info["role"] = tenant_account_join.role
            logger.debug(f"Função do usuário no tenant: {tenant_info['role']}")
        else:
            logger.warning(f"Usuário não possui função associada ao tenant: {tenant.id}")
            tenant_info["role"] = "none"

        # Verifica se o faturamento está habilitado e sincroniza o plano com o FeatureService
        try:
            features = FeatureService.get_features(tenant.id)
            tenant_info["plan"] = features.billing.subscription.plan
            tenant_info["status"] = "active" if features.billing.enabled else "inactive"
            logger.info(f"Plano do tenant {tenant.id}: {tenant_info['plan']}, Status: {tenant_info['status']}")
        except Exception as e:
            logger.error(f"Erro ao obter informações de faturamento para o tenant {tenant.id}: {e}")
            tenant_info["plan"] = "unknown"
            tenant_info["status"] = "inactive"
            tenant_info["error_message"] = "Erro ao sincronizar com o faturamento."

        # Verifica se o usuário pode substituir o logo do workspace
        can_replace_logo = features.can_replace_logo if features else False

        if can_replace_logo and TenantService.has_roles(tenant, [TenantAccountJoinRole.OWNER, TenantAccountJoinRole.ADMIN]):
            base_url = dify_config.FILES_URL
            replace_webapp_logo = (
                f"{base_url}/files/workspaces/{tenant.id}/webapp-logo"
                if tenant.custom_config_dict.get("replace_webapp_logo")
                else None
            )
            remove_webapp_brand = tenant.custom_config_dict.get("remove_webapp_brand", False)

            tenant_info["custom_config"] = {
                "remove_webapp_brand": remove_webapp_brand,
                "replace_webapp_logo": replace_webapp_logo,
            }
            logger.debug(f"Configurações customizadas do tenant {tenant.id}: {tenant_info['custom_config']}")
        else:
            logger.debug(f"Usuário não tem permissão para substituir o logo no tenant {tenant.id} ou feature não habilitada.")

        logger.info(f"Informações completas do tenant {tenant.id}: {tenant_info}")
        return tenant_info