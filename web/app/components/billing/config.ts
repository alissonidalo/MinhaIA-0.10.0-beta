import { Plan, type PlanInfo, Priority } from '@/app/components/billing/type'

const supportModelProviders = 'OpenAI/Anthropic/Azure OpenAI/  Llama2/Hugging Face/Replicate'

export const NUM_INFINITE = 99999999
export const contractSales = 'contractSales'
export const unAvailable = 'unAvailable'

export const contactSalesUrl = 'mailto:comercial@minhaia.com'

// Stripe Product and Price IDs, agora com múltiplos priceIds por plano
export const STRIPE_PLANS = {
  sandbox: {
    productId: 'prod_QsZbt0DwShON3a',  // Produto no Stripe
    prices: {
      monthly: unAvailable,
      yearly: unAvailable,
      oneTime: 'price_1Q8RJUP1Q7ODTY3xVWsM4Z9F'
    },
  },
  professional: {
    productId: 'prod_QsZbK1TJoho55K',  // ID do produto no Stripe
    prices: {
      monthly: 'price_1Q0oSkP1Q7ODTY3xljhmKOea',
      yearly: 'price_1Q8RKbP1Q7ODTY3xlNaUPy0U',
      oneTime: unAvailable
    },
  },
  team: {
    productId: 'prod_QsZcYAP5OuWzrr',  // ID do produto no Stripe
    prices: {
      monthly: 'price_1Q7P6IP1Q7ODTY3xCfKyZyi7',
      yearly: 'price_1Q7P3sP1Q7ODTY3x54GP00jb',
      oneTime: unAvailable
    },
  },
  enterprise: {
    productId: 'prod_QsrSCBv9JZiE6D',  // ID do produto no Stripe
    prices: {
      monthly: 'price_1Q8RN0P1Q7ODTY3xwhn1XfXT',
      yearly: 'price_1Q8RN0P1Q7ODTY3xwhn1XfXT',
      oneTime: 'price_1Q8RN0P1Q7ODTY3xwhn1XfXT'
    },
  },
}

export const ALL_PLANS: Record<Plan, PlanInfo> = {
  sandbox: {
    stripeProductId: STRIPE_PLANS.sandbox.productId,  // ID do produto
    stripePrices: STRIPE_PLANS.sandbox.prices,  // Preços com múltiplos intervalos
    level: 1,
    price: 0,
    modelProviders: supportModelProviders,
    teamMembers: 1,
    buildApps: 10,
    vectorSpace: 5,
    documentsUploadQuota: 50,
    documentProcessingPriority: Priority.standard,
    logHistory: 30,
    customTools: unAvailable,
    messageRequest: {
      en: '200 messages',
      zh: '200 条信息',
    },
    annotatedResponse: 10,
  },
  professional: {
    stripeProductId: STRIPE_PLANS.professional.productId,  // ID do produto
    stripePrices: STRIPE_PLANS.professional.prices,  // Preços com múltiplos intervalos
    level: 2,
    price: 59,
    modelProviders: supportModelProviders,
    teamMembers: 3,
    buildApps: 50,
    vectorSpace: 200,
    documentsUploadQuota: 500,
    documentProcessingPriority: Priority.priority,
    logHistory: NUM_INFINITE,
    customTools: 10,
    messageRequest: {
      en: '5,000  mensagens/mês',
      zh: '5,000  mensagens/mês',
    },
    annotatedResponse: 2000,
  },
  team: {
    stripeProductId: STRIPE_PLANS.team.productId,  // ID do produto
    stripePrices: STRIPE_PLANS.team.prices,  // Preços com múltiplos intervalos
    level: 3,
    price: 159,
    modelProviders: supportModelProviders,
    teamMembers: NUM_INFINITE,
    buildApps: NUM_INFINITE,
    vectorSpace: 1000,
    documentsUploadQuota: 1000,
    documentProcessingPriority: Priority.topPriority,
    logHistory: NUM_INFINITE,
    customTools: NUM_INFINITE,
    messageRequest: {
      en: '10,000  mensagens/mês',
      zh: '10,000  mensagens/mês',
    },
    annotatedResponse: 5000,
  },
  enterprise: {
    stripeProductId: STRIPE_PLANS.enterprise.productId,  // ID do produto
    stripePrices: STRIPE_PLANS.enterprise.prices,  // Preços com múltiplos intervalos
    level: 4,
    price: 0,
    modelProviders: supportModelProviders,
    teamMembers: NUM_INFINITE,
    buildApps: NUM_INFINITE,
    vectorSpace: NUM_INFINITE,
    documentsUploadQuota: NUM_INFINITE,
    documentProcessingPriority: Priority.topPriority,
    logHistory: NUM_INFINITE,
    customTools: NUM_INFINITE,
    messageRequest: {
      en: contractSales,
      zh: contractSales,
    },
    annotatedResponse: NUM_INFINITE,
  },
}

export const defaultPlan = {
  type: Plan.sandbox,
  usage: {
    vectorSpace: 1,
    buildApps: 1,
    teamMembers: 1,
    annotatedResponse: 1,
    documentsUploadQuota: 1,
  },
  total: {
    vectorSpace: 10,
    buildApps: 10,
    teamMembers: 1,
    annotatedResponse: 10,
    documentsUploadQuota: 50,
  },
}
