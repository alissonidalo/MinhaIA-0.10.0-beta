from flask_login import current_user
from flask_restful import Resource, reqparse
from controllers.console import api
from controllers.console.setup import setup_required
from controllers.console.wraps import account_initialization_required, only_edition_cloud
from libs.login import login_required
from services.billing_service import BillingService


class Subscription(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @only_edition_cloud
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("plan", type=str, required=True, location="args", choices=["professional", "team"])
        parser.add_argument("interval", type=str, required=True, location="args", choices=["month", "year"])
        args = parser.parse_args()

        BillingService.is_tenant_owner_or_admin(current_user)

        return BillingService.get_subscription(
            args["plan"], args["interval"], current_user.email, current_user.current_tenant_id
        )


class Invoices(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @only_edition_cloud
    def get(self):
        BillingService.is_tenant_owner_or_admin(current_user)
        return BillingService.get_invoices(current_user.email, current_user.current_tenant_id)


# Nova classe para criar e associar assinaturas
class CreateSubscriptionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @only_edition_cloud
    def post(self):
        # Parsing dos parâmetros esperados na requisição
        parser = reqparse.RequestParser()
        parser.add_argument("email", type=str, required=True, location="json")
        parser.add_argument("tenant_id", type=str, required=True, location="json")
        parser.add_argument("plan", type=str, required=True, location="json")
        parser.add_argument("interval", type=str, required=False, default="month", location="json")
        args = parser.parse_args()

        email = args["email"]
        tenant_id = args["tenant_id"]
        plan = args["plan"]
        interval = args["interval"]

        # Chamando o serviço para criar e associar a assinatura
        try:
            result = BillingService.create_and_associate_subscription(
                email=email, 
                tenant_id=tenant_id, 
                plan=plan, 
                interval=interval
            )

            # Se houver erro no resultado, retorne erro apropriado
            if "error" in result:
                return {"error": result["error"]}, 400

            # Adiciona a URL de redirecionamento correta no resultado
            if result.get("checkout_url"):
                return {"checkout_url": result["checkout_url"]}, 201

            return {"message": result.get("message")}, 201

        except Exception as e:
            logging.error(f"Erro inesperado ao criar a assinatura: {str(e)}")
            return {"error": "Erro inesperado ao processar a assinatura."}, 500


# Adicionando as rotas à API
api.add_resource(Subscription, "/billing/subscription")  # Mantém a rota para obter assinaturas
api.add_resource(Invoices, "/billing/invoices")  # Mantém a rota para listar faturas
api.add_resource(CreateSubscriptionApi, "/billing/create-subscription")  # Nova rota adicionada para criar assinaturas

