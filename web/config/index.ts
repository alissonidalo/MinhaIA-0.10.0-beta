/* eslint-disable import/no-mutable-exports */
import { InputVarType } from '@/app/components/workflow/types'
import { AgentStrategy } from '@/types/app'
import { PromptRole } from '@/models/debug'

export let apiPrefix = ''
export let publicApiPrefix = ''

// NEXT_PUBLIC_API_PREFIX=/console/api NEXT_PUBLIC_PUBLIC_API_PREFIX=/api npm run start
if (process.env.NEXT_PUBLIC_API_PREFIX && process.env.NEXT_PUBLIC_PUBLIC_API_PREFIX) {
  apiPrefix = process.env.NEXT_PUBLIC_API_PREFIX
  publicApiPrefix = process.env.NEXT_PUBLIC_PUBLIC_API_PREFIX
}
else if (
  globalThis.document?.body?.getAttribute('data-api-prefix')
  && globalThis.document?.body?.getAttribute('data-pubic-api-prefix')
) {
  // Not build can not get env from process.env.NEXT_PUBLIC_ in browser https://nextjs.org/docs/basic-features/environment-variables#exposing-environment-variables-to-the-browser
  apiPrefix = globalThis.document.body.getAttribute('data-api-prefix') as string
  publicApiPrefix = globalThis.document.body.getAttribute('data-pubic-api-prefix') as string
}
else {
  // const domainParts = globalThis.location?.host?.split('.');
  // in production env, the host is dify.app . In other env, the host is [dev].dify.app
  // const env = domainParts.length === 2 ? 'ai' : domainParts?.[0];
  apiPrefix = 'http://localhost:5001/console/api'
  publicApiPrefix = 'http://localhost:5001/api' // avoid browser private mode api cross origin
}

export const API_PREFIX: string = apiPrefix
export const PUBLIC_API_PREFIX: string = publicApiPrefix

const EDITION = process.env.NEXT_PUBLIC_EDITION || globalThis.document?.body?.getAttribute('data-public-edition') || 'CLOUD'
export const IS_CE_EDITION = EDITION === 'CLOUD'

export const SUPPORT_MAIL_LOGIN = !!(process.env.NEXT_PUBLIC_SUPPORT_MAIL_LOGIN || globalThis.document?.body?.getAttribute('data-public-support-mail-login'))

export const TONE_LIST = [
  {
    id: 1,
    name: 'Creative',
    config: {
      temperature: 0.8,
      top_p: 0.9,
      presence_penalty: 0.1,
      frequency_penalty: 0.1,
    },
  },
  {
    id: 2,
    name: 'Balanced',
    config: {
      temperature: 0.5,
      top_p: 0.85,
      presence_penalty: 0.2,
      frequency_penalty: 0.3,
    },
  },
  {
    id: 3,
    name: 'Precise',
    config: {
      temperature: 0.2,
      top_p: 0.75,
      presence_penalty: 0.5,
      frequency_penalty: 0.5,
    },
  },
  {
    id: 4,
    name: 'Custom',
  },
]

export const DEFAULT_CHAT_PROMPT_CONFIG = {
  prompt: [
    {
      role: PromptRole.system,
      text: '',
    },
  ],
}

export const DEFAULT_COMPLETION_PROMPT_CONFIG = {
  prompt: {
    text: '',
  },
  conversation_histories_role: {
    user_prefix: '',
    assistant_prefix: '',
  },
}

export const getMaxToken = (modelId: string) => {
  return (modelId === 'gpt-4' || modelId === 'gpt-3.5-turbo-16k') ? 8000 : 4000
}

export const LOCALE_COOKIE_NAME = 'locale'

export const DEFAULT_VALUE_MAX_LEN = 48
export const DEFAULT_PARAGRAPH_VALUE_MAX_LEN = 1000

export const zhRegex = /^[\u4E00-\u9FA5]$/m
export const emojiRegex = /^[\uD800-\uDBFF][\uDC00-\uDFFF]$/m
export const emailRegex = /^[\w.!#$%&'*+\-/=?^{|}~]+@([\w-]+\.)+[\w-]{2,}$/m
const MAX_ZN_VAR_NAME_LENGTH = 8
const MAX_EN_VAR_VALUE_LENGTH = 30
export const getMaxVarNameLength = (value: string) => {
  if (zhRegex.test(value))
    return MAX_ZN_VAR_NAME_LENGTH

  return MAX_EN_VAR_VALUE_LENGTH
}

export const MAX_VAR_KEY_LENGTH = 30

export const MAX_PROMPT_MESSAGE_LENGTH = 10

export const VAR_ITEM_TEMPLATE = {
  key: '',
  name: '',
  type: 'string',
  max_length: DEFAULT_VALUE_MAX_LEN,
  required: true,
}

export const VAR_ITEM_TEMPLATE_IN_WORKFLOW = {
  variable: '',
  label: '',
  type: InputVarType.textInput,
  max_length: DEFAULT_VALUE_MAX_LEN,
  required: true,
  options: [],
}

export const appDefaultIconBackground = '#D5F5F6'

export const NEED_REFRESH_APP_LIST_KEY = 'needRefreshAppList'

export const DATASET_DEFAULT = {
  top_k: 4,
  score_threshold: 0.8,
}

export const APP_PAGE_LIMIT = 10

export const ANNOTATION_DEFAULT = {
  score_threshold: 0.9,
}

export const MAX_TOOLS_NUM = 10

export const DEFAULT_AGENT_SETTING = {
  enabled: false,
  max_iteration: 5,
  strategy: AgentStrategy.functionCall,
  tools: [],
}

export const DEFAULT_AGENT_PROMPT = {
  chat: `Responda ao humano da forma mais útil e precisa possível. 

  {{instruction}}
  
  Você tem acesso às seguintes ferramentas:
  
  {{tools}}
  
  Use um blob JSON para especificar uma ferramenta, fornecendo uma chave {{TOOL_NAME_KEY}} (nome da ferramenta) e uma chave {{ACTION_INPUT_KEY}} (entrada da ferramenta).
  Valores válidos para "{{TOOL_NAME_KEY}}": "Resposta Final" ou {{tool_names}}
  
  Forneça apenas UMA ação por $JSON_BLOB, como mostrado:
  
  \`\`\`
  {
    "{{TOOL_NAME_KEY}}": $TOOL_NAME,
    "{{ACTION_INPUT_KEY}}": $ACTION_INPUT
  }
  \`\`\`
  
  Siga este formato:
  
  Pergunta: pergunta de entrada a ser respondida
  Pensamento: considere passos anteriores e subsequentes
  Ação:
  \`\`\`
  $JSON_BLOB
  \`\`\`
  Observação: resultado da ação
  ... (repita Pensamento/Ação/Observação N vezes)
  Pensamento: Eu sei o que responder
  Ação:
  \`\`\`
  {
    "{{TOOL_NAME_KEY}}": "Final Answer",
    "{{ACTION_INPUT_KEY}}": "Final response to human"
  }
  \`\`\`
  
  Comece! Lembre-se de SEMPRE responder com um blob JSON válido de uma única ação. Use ferramentas se necessário. Responda diretamente se apropriado. O formato é Ação:\`\`\`$JSON_BLOB\`\`\`em seguida Observação:.`,
  completion: `
  Responda ao humano da forma mais útil e precisa possível. 

{{instruction}}

Você tem acesso às seguintes ferramentas:

{{tools}}

Use um bloco JSON para especificar uma ferramenta, fornecendo uma chave {{TOOL_NAME_KEY}} (nome da ferramenta) e uma chave {{ACTION_INPUT_KEY}} (entrada da ação).
Valores válidos para "{{TOOL_NAME_KEY}}": "Resposta Final" ou {{tool_names}}

Forneça apenas UMA ação por $JSON_BLOB, conforme mostrado:

\`\`\`
{{{{
  "{{TOOL_NAME_KEY}}": $TOOL_NAME,
  "{{ACTION_INPUT_KEY}}": $ACTION_INPUT
}}}}
\`\`\`

Siga este formato:

Pergunta: pergunta de entrada a ser respondida
Pensamento: considere os passos anteriores e subsequente
Ação:
\`\`\`
$JSON_BLOB
\`\`\`
Observação: resultado da ação
... (repita Pensamento/Ação/Observação N vezes)
Pensamento: Sei o que responder
Ação:
\`\`\`
{{{{
  "{{TOOL_NAME_KEY}}": "Resposta Final",
  "{{ACTION_INPUT_KEY}}": "Resposta final ao humano"
}}}}
\`\`\`

Comece! Lembre-se de SEMPRE responder com um blob JSON válido de uma única ação. Use ferramentas se necessário. Responda diretamente se apropriado. O formato é Ação:\`\`\`$JSON_BLOB\`\`\`em seguida Observação:.
Pergunta: {{query}}
Pensamento: {{agent_scratchpad}}
  `,
}

export const VAR_REGEX = /\{\{(#[a-zA-Z0-9_-]{1,50}(\.[a-zA-Z_][a-zA-Z0-9_]{0,29}){1,10}#)\}\}/gi

export let textGenerationTimeoutMs = 60000

if (process.env.NEXT_PUBLIC_TEXT_GENERATION_TIMEOUT_MS && process.env.NEXT_PUBLIC_TEXT_GENERATION_TIMEOUT_MS !== '')
  textGenerationTimeoutMs = parseInt(process.env.NEXT_PUBLIC_TEXT_GENERATION_TIMEOUT_MS)
else if (globalThis.document?.body?.getAttribute('data-public-text-generation-timeout-ms') && globalThis.document.body.getAttribute('data-public-text-generation-timeout-ms') !== '')
  textGenerationTimeoutMs = parseInt(globalThis.document.body.getAttribute('data-public-text-generation-timeout-ms') as string)

export const TEXT_GENERATION_TIMEOUT_MS = textGenerationTimeoutMs

export const DISABLE_UPLOAD_IMAGE_AS_ICON = process.env.NEXT_PUBLIC_DISABLE_UPLOAD_IMAGE_AS_ICON === 'true'
