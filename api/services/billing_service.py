import os
import stripe
import logging
from extensions.ext_database import db
from models.account import TenantAccountJoin, TenantAccountRole

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BillingService:
    # Lê as variáveis de ambiente para a chave da API do Stripe
    stripe.api_key = os.environ.get("STRIPE_API_SECRET_KEY")
    
    @classmethod
    def find_customer_by_email_and_tenant(cls, email, tenant_id):
        """
        Busca um cliente no Stripe usando o e-mail e valida o tenant_id nos metadados.
        """
        try:
            customers = stripe.Customer.list(email=email)
            for customer in customers.auto_paging_iter():
                if customer.metadata.get("tenant_id") == tenant_id:
                    return customer
            return None
        except Exception as e:
            logging.error(f"Erro ao buscar cliente no Stripe: {str(e)}")
            return None

    @classmethod
    def update_stripe_customer_metadata(cls, customer_id, tenant_id):
        """
        Atualiza os metadados de um cliente no Stripe para associar o tenant_id.
        """
        try:
            stripe.Customer.modify(
                customer_id,
                metadata={
                    "tenant_id": tenant_id
                }
            )
            logging.info(f"Cliente {customer_id} atualizado com tenant_id {tenant_id}")
        except Exception as e:
            logging.error(f"Erro ao atualizar cliente no Stripe: {str(e)}")

    @classmethod
    def get_info(cls, tenant_id: str):
        """Obtém as informações de assinatura do locatário."""
        logger.debug(f"Obtendo informações de assinatura para tenant_id: {tenant_id}")
        
        if not tenant_id:
            raise ValueError("Tenant ID é necessário para buscar as informações de assinatura.")
        
        try:
            # Adiciona um filtro direto para tenant_id na chamada de listagem
            subscriptions = stripe.Subscription.list(limit=10, expand=["data.plan"])

            logger.debug(f"Assinaturas obtidas: {subscriptions}")

            # Verificar se há uma correspondência exata para tenant_id nos metadados
            subscription = next((s for s in subscriptions.data if s.metadata.get('tenant_id') == tenant_id), None)

            if not subscription:
                logger.warning(f"Nenhuma assinatura encontrada para tenant_id: {tenant_id}")
                return {
                    "id": None,
                    "status": "not_found",
                    "current_period_end": None,
                    "customer": None,
                    "enabled": False,
                    "message": "Nenhuma assinatura encontrada para o tenant"
                }

            billing_info = {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "customer": subscription.customer,
                "enabled": subscription.status == "active",
                "subscription": {
                    "plan": subscription.plan.nickname,
                    "interval": subscription.plan.interval
                }
            }

            logger.debug(f"billing_info: {billing_info}")
            return billing_info

        except stripe.error.StripeError as e:
            logger.error(f"Erro ao obter as informações de assinatura: {e}")
            return {
                "id": None,
                "status": "error",
                "message": "Erro ao obter as informações de assinatura"
            }

    @classmethod
    def get_subscription(cls, email, tenant_id, plan=None, interval=None):
        """
        Recupera a assinatura ativa de um cliente no Stripe com base no email e tenant_id.
        Opcionalmente filtra por plano e intervalo.
        """
        try:
            # Busca o cliente no Stripe baseado no e-mail
            customers = stripe.Customer.list(email=email)
            customer = None

            # Verifica se o cliente possui o tenant_id nos metadados
            for c in customers.auto_paging_iter():
                if c.metadata.get("tenant_id") == tenant_id:
                    customer = c
                    break

            if not customer:
                return {"error": "Cliente não encontrado para o email e tenant_id fornecidos."}

            # Busca as assinaturas do cliente
            subscriptions = stripe.Subscription.list(customer=customer.id)

            # Filtra assinaturas com base no plano e intervalo, se fornecidos
            for subscription in subscriptions.data:
                if plan and subscription.plan.nickname != plan:
                    continue
                if interval and subscription.plan.interval != interval:
                    continue

                return {
                    "id": subscription.id,
                    "status": subscription.status,
                    "current_period_end": subscription.current_period_end,
                    "plan": subscription.plan.nickname,
                    "interval": subscription.plan.interval
                }

            return {"message": "Nenhuma assinatura encontrada para este cliente com o plano e intervalo fornecidos."}

        except Exception as e:
            logging.error(f"Erro ao buscar assinatura: {str(e)}")
            return {"error": f"Erro ao buscar assinatura: {str(e)}"}
    
    @classmethod
    def get_invoices(cls, email, tenant_id):
        """
        Recupera as faturas de um cliente no Stripe com base no email e no tenant_id.
        """
        try:
            # Busca o cliente no Stripe pelo email e tenant_id
            customer = cls.find_customer_by_email_and_tenant(email, tenant_id)

            if not customer:
                return {"error": "Cliente não encontrado para o email e tenant_id fornecidos."}
            
            # Busca as faturas no Stripe para o customer_id encontrado
            invoices = stripe.Invoice.list(customer=customer.id, limit=10)

            # Processa e retorna as faturas
            if not invoices.data:
                return {"message": "Nenhuma fatura encontrada para este cliente."}

            invoice_data = []
            for invoice in invoices.data:
                invoice_data.append({
                    "id": invoice.id,
                    "status": invoice.status,
                    "amount_paid": invoice.amount_paid,
                    "amount_due": invoice.amount_due,
                    "period_start": invoice.period_start,
                    "period_end": invoice.period_end
                })

            return {"invoices": invoice_data}

        except Exception as e:
            logger.error(f"Erro ao buscar faturas: {str(e)}")
            return {"error": f"Erro ao buscar faturas: {str(e)}"}


    @classmethod
    def get_current_plan_info(cls, tenant_id: str) -> dict:
        """Obtém as informações completas do plano atual para o tenant, sincronizado com o front-end."""
        logger.debug(f"Obtendo informações do plano atual para tenant_id: {tenant_id}")
        logger.debug(f"Chamando get_info para tenant_id: {tenant_id}")
        
        billing_info = cls.get_info(tenant_id)
        logger.debug(f"billing_info obtido: {billing_info}")

        # Verificação se o billing_info é válido e contém a chave 'subscription'
        if billing_info is None or "subscription" not in billing_info:
            logger.error("Erro: billing_info é None ou não contém 'subscription'.")
            return {"error": "Informações de assinatura ausentes."}

        if not billing_info["enabled"]:
            logger.warning(f"Billing não habilitado para tenant_id: {tenant_id}, retornando plano padrão.")
            plan = "standard"  # Defina um plano padrão para quando o billing estiver desabilitado
            plan_details = {
                "members_limit": 0,
                "apps_limit": 10,
                "vector_space_limit": 5,
                "annotation_quota_limit": 10,
                "documents_upload_quota_limit": 50,
                "docs_processing": "standard",
                "can_replace_logo": False,
                "model_load_balancing_enabled": False,
                "dataset_operator_enabled": False
            }
            return {
                "billing": {
                    "enabled": billing_info["enabled"],
                    "subscription": {
                        "plan": plan
                    }
                },
                "members": {"size": 0, "limit": plan_details["members_limit"]},
                "apps": {"size": 0, "limit": plan_details["apps_limit"]},
                "vector_space": {"size": 0, "limit": plan_details["vector_space_limit"]},
                "annotation_quota_limit": {"size": 0, "limit": plan_details["annotation_quota_limit"]},
                "documents_upload_quota": {"size": 0, "limit": plan_details["documents_upload_quota_limit"]},
                "docs_processing": plan_details["docs_processing"],
                "can_replace_logo": plan_details["can_replace_logo"],
                "model_load_balancing_enabled": plan_details["model_load_balancing_enabled"],
                "dataset_operator_enabled": plan_details["dataset_operator_enabled"]
            }

        plan = billing_info["subscription"]["plan"]
        interval = billing_info["subscription"]["interval"]
        logger.debug(f"Plano: {plan}, Intervalo: {interval} para tenant_id: {tenant_id}")

        price_id = cls.get_price_id(plan, interval)
        logger.debug(f"price_id obtido para plano '{plan}' e intervalo '{interval}': {price_id}")

        plan_details = cls.get_plan_details(price_id)
        logger.debug(f"Detalhes do plano obtidos: {plan_details}")

        return {
            "billing": {
                "enabled": billing_info["enabled"],
                "subscription": {
                    "plan": plan
                }
            },
            "members": {"size": 0, "limit": plan_details.get("members_limit", 0)},
            "apps": {"size": 0, "limit": plan_details.get("apps_limit", 0)},
            "vector_space": {"size": 0, "limit": plan_details.get("vector_space_limit", 0)},
            "annotation_quota_limit": {"size": 0, "limit": plan_details.get("annotation_quota_limit", 0)},
            "documents_upload_quota": {"size": 0, "limit": plan_details.get("documents_upload_quota_limit", 0)},
            "docs_processing": plan_details.get("docs_processing", "standard"),
            "can_replace_logo": plan_details.get("can_replace_logo", False),
            "model_load_balancing_enabled": plan_details.get("model_load_balancing_enabled", False),
            "dataset_operator_enabled": plan_details.get("dataset_operator_enabled", False)
        }


    @classmethod
    def get_price_id(cls, plan: str, interval: str) -> str:
        """Obtém o price_id do Stripe para um plano e intervalo específicos."""
        logger.debug(f"Obtendo price_id para plano: {plan}, intervalo: {interval}")
        try:
            products = stripe.Product.list(limit=100)
            logger.debug(f"Produtos obtidos do Stripe: {products}")

            price_id = None

            for product in products.data:
                if product.name.lower() == plan.lower():
                    prices = stripe.Price.list(product=product.id, limit=10)
                    logger.debug(f"Preços obtidos para o produto '{product.name}': {prices}")
                    for price in prices.data:
                        if price.recurring and price.recurring.interval == interval:
                            price_id = price.id
                            logger.info(f"price_id encontrado: {price_id} para plano '{plan}' e intervalo '{interval}'")
                            break

            if not price_id:
                logger.error(f"Price ID não encontrado para plano '{plan}' e intervalo '{interval}'.")
                raise ValueError(f"Price ID não encontrado para o plano '{plan}' e intervalo '{interval}'.")

            return price_id

        except stripe.error.StripeError as e:
            logger.error(f"Erro ao buscar informações de preços para plano '{plan}', intervalo '{interval}': {e}")
            raise RuntimeError(f"Erro ao buscar informações de preços: {e}")

    @classmethod
    def get_plan_details(cls, price_id: str) -> dict:
        """Recupera os detalhes do plano a partir dos metadados do Stripe usando o price_id."""
        logger.debug(f"Obtendo detalhes do plano para price_id: {price_id}")
        try:
            price = stripe.Price.retrieve(price_id)
            product = stripe.Product.retrieve(price.product)
            logger.debug(f"Produto obtido para price_id '{price_id}': {product}")

            plan_details = {
                "members_limit": int(product.metadata.get("members_limit", 0)),
                "apps_limit": int(product.metadata.get("apps_limit", 0)),
                "vector_space_limit": int(product.metadata.get("vector_space_limit", 0)),
                "documents_upload_quota_limit": int(product.metadata.get("documents_upload_quota_limit", 0)),
                "annotation_quota_limit": int(product.metadata.get("annotation_quota_limit", 0)),
                "docs_processing": product.metadata.get("docs_processing", "standard"),
                "can_replace_logo": product.metadata.get("can_replace_logo", "false").lower() == "true",
                "model_load_balancing_enabled": product.metadata.get("model_load_balancing_enabled", "false").lower() == "true",
                "dataset_operator_enabled": product.metadata.get("dataset_operator_enabled", "false").lower() == "true"
            }

            logger.debug(f"Detalhes do plano obtidos: {plan_details}")
            return plan_details

        except stripe.error.StripeError as e:
            logger.error(f"Erro ao buscar detalhes do plano no Stripe para price_id '{price_id}': {e}")
            raise RuntimeError(f"Erro ao buscar detalhes do plano no Stripe: {e}")

    @staticmethod
    def is_tenant_owner_or_admin(current_user):
        """Verifica se o usuário atual é o proprietário ou administrador do locatário."""
        tenant_id = current_user.current_tenant_id
        logger.debug(f"Verificando se o usuário é proprietário ou administrador para tenant_id: {tenant_id}")

        join = (
            db.session.query(TenantAccountJoin)
            .filter(TenantAccountJoin.tenant_id == tenant_id, TenantAccountJoin.account_id == current_user.id)
            .first()
        )

        if not join or not TenantAccountRole.is_privileged_role(join.role):
            logger.error(f"Usuário não autorizado para tenant_id: {tenant_id}")
            raise ValueError("Somente o proprietário ou administrador do time pode realizar esta ação")

        logger.info(f"Usuário autorizado para tenant_id: {tenant_id}")
