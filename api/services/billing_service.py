import os
import stripe
import logging
import json  # Adicionar json para formatar os logs

from flask import url_for
from extensions.ext_database import db
from models.account import TenantAccountJoin, TenantAccountRole

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Se você estiver executando com o Gunicorn, ele pode precisar disso
for handler in logger.handlers:
    handler.setLevel(logging.DEBUG)

logger.info("Forçando o nível de log para DEBUG")

# Checklist de funcionamento das funções

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


class BillingService:
    # Lê as variáveis de ambiente para a chave da API do Stripe
    stripe.api_key = os.environ.get("STRIPE_API_SECRET_KEY")

    @classmethod
    def create_checkout_session(cls, email, tenant_id, plan, interval="month", success_url=None, cancel_url=None):
        """
        Cria uma sessão de Checkout do Stripe para redirecionar o usuário e coletar o método de pagamento.
        Somente para planos pagos.
        """
        if plan == "sandbox":
            logger.info(f"O plano '{plan}' não requer checkout.")
            return None  # Não precisa de checkout para o plano gratuito

        try:
            price_id = cls.get_price_id(plan, interval)
            log_checklist(
                check_name="Verificação do Price ID",
                success=bool(price_id),
                error=f"Price ID não encontrado para o plano {plan} com intervalo {interval}",
                solution="Verifique se os preços estão corretamente cadastrados no Stripe para o plano e intervalo."
            )
            
            if not price_id:
                raise ValueError(f"Price ID não encontrado para o plano {plan} com intervalo {interval}")

            # URLs de sucesso e cancelamento
            if not success_url:
                success_url = url_for('checkout_success', _external=True)
            if not cancel_url:
                cancel_url = url_for('checkout_cancel', _external=True)

            # Criar a sessão de checkout no Stripe
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                customer_email=email,
                line_items=[{
                    'price': price_id,
                    'quantity': 1
                }],
                mode='subscription',
                metadata={"tenant_id": tenant_id},
                success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel_url
            )

            logger.info(f"Sessão de checkout criada com sucesso. Session ID: {session.id}")
            return session.url

        except stripe.error.CardError as e:
            logger.error(f"Erro de cartão: {str(e)}")
            return {"error": "Problema com o cartão."}
        except stripe.error.RateLimitError as e:
            logger.error(f"Erro de limite de taxa: {str(e)}")
            return {"error": "Muitas solicitações ao Stripe."}
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Erro de requisição inválida: {str(e)}")
            return {"error": "Parâmetros incorretos na requisição."}
        except Exception as e:
            logger.error(f"Erro inesperado ao criar sessão de checkout para {email}: {str(e)}")
            return {"error": f"Erro inesperado: {str(e)}"}  
    
    @classmethod
    def create_and_associate_subscription(cls, email, tenant_id, plan, interval="month"):
        """
        Cria um cliente no Stripe e, se for um plano pago, redireciona para o Checkout.
        """
        logger.info(f"Iniciando criação de assinatura para {email} com plano {plan} e intervalo {interval}")

        if plan == "sandbox":
            # Processar plano Sandbox sem pagamento
            return cls.associate_plan_to_customer_without_checkout(email, tenant_id, plan)

        try:
            # Criar sessão de checkout para planos pagos
            session_url = cls.create_checkout_session(email, tenant_id, plan, interval)
            log_checklist(
                check_name="Criação de Sessão de Checkout",
                success=bool(session_url),
                error=f"Falha ao redirecionar para o checkout do Stripe para {email}",
                solution="Verifique os detalhes do plano e o Stripe."
            )

            if session_url:
                logger.info(f"Redirecionando para o checkout do Stripe: {session_url}")
                return {"checkout_url": session_url}

            return {"message": "Plano gratuito ativado com sucesso."}

        except Exception as e:
            logger.error(f"Erro inesperado ao criar e associar assinatura para {email}: {str(e)}")
            return {"error": f"Erro inesperado ao criar assinatura: {str(e)}"}

    @classmethod
    def associate_plan_to_customer_without_checkout(cls, email, tenant_id, plan):
        """
        Associa diretamente o plano sandbox ao cliente, sem necessidade de pagamento.
        """
        try:
            # Criar o cliente no Stripe
            customer = cls.create_stripe_customer(email=email, tenant_id=tenant_id)
            log_checklist(
                check_name="Criação de Cliente no Stripe",
                success=bool(customer),
                error=f"Erro ao criar cliente no Stripe para {email}",
                solution="Verifique as credenciais da API do Stripe e os dados do cliente."
            )

            if not customer:
                logger.error(f"Erro ao criar cliente no Stripe para {email}")
                return {"error": "Erro ao criar cliente no Stripe."}

            # Associa o plano gratuito diretamente
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": cls.get_price_id(plan, "month")}],
                metadata={"tenant_id": tenant_id}
            )

            logger.info(f"Assinatura do plano {plan} criada com sucesso para o cliente {email}")
            return {"message": "Assinatura do plano sandbox criada com sucesso.", "subscription": subscription}

        except Exception as e:
            logger.error(f"Erro ao associar plano gratuito: {str(e)}")
            return {"error": "Erro ao associar plano gratuito."}

    @classmethod
    def create_stripe_customer(cls, email, tenant_id, name=None):
        """
        Cria um cliente no Stripe e associa o tenant_id como metadado. Verifica duplicação.
        """
        try:
            # Verificar se o cliente já existe
            existing_customer = cls.get_customer_by_email(email)
            if existing_customer:
                logger.info(f"Cliente existente encontrado para {email}")
                return existing_customer

            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"tenant_id": tenant_id}
            )
            logger.info(f"Cliente criado no Stripe para tenant {tenant_id}")
            return customer
            
        except Exception as e:
            logger.error(f"Erro ao criar cliente no Stripe: {str(e)}")
            return None

    @classmethod
    def get_customer_by_email(cls, email):
        """
        Obtém o cliente do Stripe pelo email.
        """
        try:
            customers = stripe.Customer.list(email=email).data
            if customers:
                return customers[0]
            return None

        except Exception as e:
            logger.error(f"Erro ao obter cliente do Stripe: {str(e)}")
            return None

    @classmethod
    def associate_plan_to_customer(cls, customer_id, plan, interval, tenant_id):
        """
        Associa um plano de assinatura a um cliente no Stripe e adiciona o tenant_id como metadado.
        """
        try:
            # Busca o price_id com base no plano e intervalo
            price_id = cls.get_price_id(plan, interval)
            if not price_id:
                raise ValueError(f"Price ID não encontrado para o plano {plan} com intervalo {interval}")

            # Criação da assinatura no Stripe
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                expand=["latest_invoice.payment_intent", "plan"],  # Expansão para mais informações
                metadata={"tenant_id": tenant_id}
            )

            logger.debug(f"Assinatura criada: {json.dumps(subscription, indent=2)}")

            # Verifica se o plano foi corretamente retornado
            plan_info = subscription['items']['data'][0]['plan']
            if not plan_info:
                logger.error(f"Plano da assinatura não encontrado após criação para o cliente {customer_id}")
                return {"error": "Plano da assinatura não encontrado."}

            logger.info(f"Assinatura criada com sucesso para o cliente {customer_id}. Plano: {plan_info['id']}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Erro ao associar plano ao cliente {customer_id}: {str(e)}")
            return {"error": "Erro ao associar plano ao cliente."}

        except Exception as e:
            logger.error(f"Erro inesperado ao associar plano ao cliente {customer_id}: {str(e)}")
            return {"error": f"Erro inesperado: {str(e)}"}

    @classmethod
    def get_price_id(cls, plan: str, interval: str) -> str:
        """
        Obtém o price_id do Stripe para um plano e intervalo específicos com base no mapeamento local.
        """
        try:
            logger.debug(f"Obtendo price_id para plano: {plan}, intervalo: {interval}")
            if not plan or not interval:
                log_checklist(
                    check_name="Verificação de Parâmetros de Preço",
                    success=False,
                    error=f"Parâmetro inválido: plano={plan}, intervalo={interval}",
                    solution="Certifique-se de que os parâmetros do plano e intervalo estão corretos."
                )
                logger.error(f"Parâmetro inválido: plano={plan}, intervalo={interval}")
                raise ValueError("Plano e intervalo não podem ser nulos.")
            
            # Valida intervalos suportados
            if interval not in ['month', 'year', 'oneTime']:
                raise ValueError(f"Intervalo inválido: {interval}. Os valores válidos são 'month', 'year' ou 'oneTime'.")

            plan_info = STRIPE_PLANS.get(plan)
            log_checklist(
                check_name="Verificação de Configuração do Plano",
                success=bool(plan_info),
                error=f"Plano '{plan}' não encontrado na configuração local.",
                solution="Verifique se o plano está corretamente configurado no Stripe."
            )
            if not plan_info:
                logger.error(f"Plano '{plan}' não encontrado na configuração local.")
                raise ValueError(f"Plano '{plan}' não encontrado.")

            price_id = plan_info['prices'].get(interval)
            log_checklist(
                check_name="Verificação de Price ID",
                success=bool(price_id),
                error=f"Price ID não encontrado para o plano '{plan}' com o intervalo '{interval}'.",
                solution="Verifique a configuração do intervalo para o plano no Stripe."
            )
            
            if not price_id:
                logger.error(f"Price ID não encontrado para o plano '{plan}' com o intervalo '{interval}'.")
                raise ValueError(f"O plano '{plan}' não suporta o intervalo '{interval}'.")

            logger.info(f"Price ID encontrado: {price_id} para plano '{plan}' e intervalo '{interval}'")
            return price_id

        except Exception as e:
            logger.error(f"Erro ao buscar Price ID para plano '{plan}' e intervalo '{interval}': {str(e)}")
            raise

    @classmethod
    def find_customer_by_email_and_tenant(cls, email, tenant_id):
        """
        Busca um cliente no Stripe usando o e-mail e valida o tenant_id nos metadados.
        """
        try:
            customers = stripe.Customer.list(email=email).auto_paging_iter()
            for customer in customers:
                if customer.metadata.get("tenant_id") == tenant_id:
                    return customer
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente no Stripe: {str(e)}")
            return None

    @classmethod
    def update_stripe_customer_metadata(cls, customer_id, tenant_id):
        """
        Atualiza os metadados de um cliente no Stripe para associar o tenant_id.
        """
        try:
            stripe.Customer.modify(
                customer_id,
                metadata={"tenant_id": tenant_id}
            )
            logger.info(f"Cliente {customer_id} atualizado com tenant_id {tenant_id}")
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente no Stripe: {str(e)}")

    @classmethod
    def get_info(cls, tenant_id: str):
        """Obtém as informações de assinatura do locatário."""
        try:
            logger.debug(f"Obtendo informações de assinatura para tenant_id: {tenant_id}")
            if not tenant_id:
                raise ValueError("Tenant ID é necessário para buscar as informações de assinatura.")

            # Expandindo 'plan' para garantir que os dados do plano venham completos
            subscriptions = stripe.Subscription.list(limit=10, expand=["data.plan"])

            logger.debug(f"Assinaturas obtidas do Stripe: {subscriptions}")

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

            plan_info = subscription.plan
            if not plan_info:
                logger.error(f"Plano da assinatura está None para tenant_id {tenant_id}")
                return {
                    "id": subscription.id,
                    "status": subscription.status,
                    "current_period_end": subscription.current_period_end,
                    "customer": subscription.customer,
                    "enabled": False,
                    "message": "Plano não encontrado na assinatura"
                }

            # Fallback robusto para o campo `name` ou `nickname`
            plan_name = getattr(plan_info, 'name', None) or getattr(plan_info, 'nickname', None) or f"Plano ID: {plan_info.id}"
            logger.debug(f"Plan name resolved as: {plan_name}")

            billing_info = {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "customer": subscription.customer,
                "enabled": subscription.status == "active",
                "subscription": {
                    "plan": plan_name,  # Utilizando o fallback
                    "interval": plan_info.interval
                }
            }

            logger.debug(f"Informações de billing extraídas: {billing_info}")
            return billing_info

        except stripe.error.StripeError as e:
            logger.error(f"Erro ao obter as informações de assinatura: {e}")
            return {
                "id": None,
                "status": "error",
                "message": "Erro ao obter as informações de assinatura"
            }

    @classmethod
    def reprocess_subscription(cls, email, tenant_id):
        """
        Reprocessa a assinatura de um cliente no Stripe para garantir que os dados corretos estão sendo capturados.
        Se já houver uma assinatura ativa, ela será atualizada; caso contrário, uma nova assinatura será criada.
        """
        try:
            logger.info(f"Iniciando reprocessamento de assinatura para o cliente {email}")

            # Recupera a assinatura ativa do cliente no Stripe com base no email e tenant_id
            subscription_info = cls.get_subscription(email=email, tenant_id=tenant_id)

            if not subscription_info or subscription_info.get("error"):
                logger.error(f"Erro ao obter assinatura existente para reprocessamento: {subscription_info.get('error', 'Erro desconhecido')}")
                raise ValueError("Erro ao obter informações de assinatura para reprocessamento.")

            # Verifica se já existe uma assinatura ativa
            if subscription_info.get("id"):
                logger.info(f"Assinatura existente encontrada para o cliente {email}. ID da assinatura: {subscription_info['id']}")
                return {"message": "Assinatura existente reprocessada com sucesso.", "subscription": subscription_info}

            # Se não há uma assinatura ativa, cria uma nova
            current_plan = subscription_info.get("plan", 'sandbox')  # Define o plano padrão ou usa o existente
            current_interval = subscription_info.get("interval", 'month')  # Define o intervalo padrão ou usa o existente

            logger.info(f"Reprocessando nova assinatura para o plano {current_plan} com intervalo {current_interval}")

            subscription_data = cls.create_and_associate_subscription(
                email=email,
                tenant_id=tenant_id,
                plan=current_plan,
                interval=current_interval
            )

            if subscription_data.get("error"):
                logger.error(f"Erro ao reprocessar assinatura: {subscription_data['error']}")
            else:
                logger.info(f"Reprocessamento da assinatura realizado com sucesso para {email}")

            return subscription_data

        except Exception as e:
            logger.error(f"Erro ao reprocessar assinatura para {email}: {str(e)}")
            raise e

        except Exception as e:
            logger.error(f"Erro ao reprocessar assinatura para {email}: {str(e)}")
            raise e

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
            subscriptions = stripe.Subscription.list(customer=customer.id, expand=["data.plan"])

            # Filtra assinaturas com base no plano e intervalo, se fornecidos
            for subscription in subscriptions.data:
                plan_info = subscription.plan
                if plan and plan_info.name != plan:
                    continue
                if interval and plan_info.interval != interval:
                    continue

                # Usando fallback para o nome do plano
                plan_name = getattr(plan_info, 'name', None) or getattr(plan_info, 'nickname', None) or f"Plano ID: {plan_info.id}"

                return {
                    "id": subscription.id,
                    "status": subscription.status,
                    "current_period_end": subscription.current_period_end,
                    "plan": plan_name,
                    "interval": plan_info.interval
                }

            return {"message": "Nenhuma assinatura encontrada para este cliente com o plano e intervalo fornecidos."}

        except Exception as e:
            logger.error(f"Erro ao buscar assinatura: {str(e)}")
            return {"error": f"Erro ao buscar assinatura: {str(e)}"}
    
    @staticmethod
    def get_product_metadata(product_id: str):
        try:
            # Verifica se o product_id não está vazio ou não é um fallback inválido
            if product_id == "fallback_sandbox_product_id":
                logger.warning(f"Product ID é um fallback e não será buscado no Stripe: {product_id}")
                return {
                    "members_limit": 1,  # valores padrão
                    "apps_limit": 10,
                    "vector_space_limit": 5,
                    "documents_upload_limit": 50,
                    "annotation_quota_limit": 10,
                    "docs_processing": "standard",
                    "can_replace_logo": False,
                    "model_load_balancing_enabled": False,
                    "dataset_operator_enabled": False
                }

            # Busca os metadados do produto no Stripe
            product = stripe.Product.retrieve(product_id)
            if not product:
                logger.error(f"Produto com ID {product_id} não encontrado no Stripe.")
                raise ValueError(f"Produto com ID {product_id} não encontrado.")
            
            logger.debug(f"Metadados do produto: {product.metadata}")
            return product.metadata

        except stripe.error.StripeError as e:
            logger.error(f"Erro ao buscar metadados do produto no Stripe: {e}")
            raise

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
        billing_info = cls.get_info(tenant_id)
        logger.debug(f"billing_info obtido: {billing_info}")

        # Verificação se o billing_info é válido e contém a chave 'subscription'
        if not billing_info or "subscription" not in billing_info:
            logger.error("Erro: billing_info é None ou não contém 'subscription'.")
            return {"error": "Informações de assinatura ausentes."}

        # Se o billing não estiver habilitado, retornar plano padrão
        if not billing_info.get("enabled", False):
            logger.warning(f"Billing não habilitado para tenant_id: {tenant_id}, retornando plano padrão.")
            return cls._default_plan_info(billing_info["enabled"])

        # Recuperar informações do plano e intervalo
        plan = billing_info["subscription"].get("plan", "sandbox")
        interval = billing_info["subscription"].get("interval", "month")
        product_id = billing_info["subscription"].get("product_id", "fallback_sandbox_product_id")
        logger.debug(f"Plano: {plan}, Intervalo: {interval}, Product ID: {product_id} para tenant_id: {tenant_id}")

        try:
            price_id = cls.get_price_id(plan, interval)
            logger.debug(f"Price ID obtido para plano '{plan}' e intervalo '{interval}': {price_id}")

            plan_details = cls.get_plan_details(price_id)
            logger.debug(f"Detalhes do plano obtidos: {plan_details}")

            return {
                "billing": {
                    "enabled": billing_info["enabled"],
                    "subscription": {
                        "plan": plan,
                        "interval": interval,
                        "product_id": product_id
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

        except Exception as e:
            logger.error(f"Erro ao processar informações do plano para tenant {tenant_id}: {str(e)}")
            raise RuntimeError(f"Erro ao processar informações do plano: {e}")

    @classmethod
    def _default_plan_info(cls, billing_enabled: bool) -> dict:
        """Retorna informações padrão do plano quando o billing está desabilitado ou há um erro."""
        plan = "standard"
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
                "enabled": billing_enabled,
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

    @classmethod
    def get_plan_details(cls, price_id: str) -> dict:
        """Recupera os detalhes do plano a partir dos metadados do Stripe usando o price_id."""
        logger.debug(f"Obtendo detalhes do plano para price_id: {price_id}")
        try:
            # Recupera o preço e o produto associados no Stripe
            price = stripe.Price.retrieve(price_id)
            product = stripe.Product.retrieve(price.product)
            logger.debug(f"Produto obtido para price_id '{price_id}': {product}")

            # Verificação e recuperação dos metadados do produto
            metadata = product.metadata

            plan_details = {
                "members_limit": int(metadata.get("members_limit", 0)),
                "apps_limit": int(metadata.get("apps_limit", 0)),
                "vector_space_limit": int(metadata.get("vector_space_limit", 0)),
                "documents_upload_quota_limit": int(metadata.get("documents_upload_quota_limit", 0)),
                "annotation_quota_limit": int(metadata.get("annotation_quota_limit", 0)),
                "docs_processing": metadata.get("docs_processing", "standard"),
                "can_replace_logo": metadata.get("can_replace_logo", "false").lower() == "true",
                "model_load_balancing_enabled": metadata.get("model_load_balancing_enabled", "false").lower() == "true",
                "dataset_operator_enabled": metadata.get("dataset_operator_enabled", "false").lower() == "true",
                "support": metadata.get("support", "communityForums"),
                "rag_api_request": int(metadata.get("rag_api_request", 0)),
                "logs_history": int(metadata.get("logs_history", 0))
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