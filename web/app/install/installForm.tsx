'use client'
import React, { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import Loading from '../components/base/loading'
import classNames from '@/utils/classnames'
import Button from '@/app/components/base/button'

import { createUser, createAndAssociateSubscription, CreateUserResponse } from '@/service/common';

// Regex para senha válida
const validPassword = /^(?=.*[a-zA-Z])(?=.*\d).{8,}$/

// Validação do formulário com zod
const accountFormSchema = z.object({
  email: z
    .string()
    .min(1, { message: 'login.error.emailInValid' })
    .email('login.error.emailInValid'),
  name: z.string().min(1, { message: 'login.error.nameEmpty' }),
  password: z.string().min(8, {
    message: 'login.error.passwordLengthInValid',
  }).regex(validPassword, 'login.error.passwordInvalid'),
})

// Tipos do formulário
type AccountFormValues = z.infer<typeof accountFormSchema>

const InstallForm = () => {
  const { t } = useTranslation()
  const router = useRouter()
  const [showPassword, setShowPassword] = React.useState(false)
  const [loading, setLoading] = React.useState(false) // Estado de carregamento
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null) // Estado para mensagens de erro
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AccountFormValues>({
    resolver: zodResolver(accountFormSchema),
    defaultValues: {
      name: '',
      password: '',
      email: '',
    },
  })

  const onSubmit = async (data: AccountFormValues) => {
    setLoading(true); // Exibe o carregamento ao submeter o formulário
    setErrorMessage(null); // Reseta a mensagem de erro
  
    try {
      // Criação do usuário e obtenção do tenant_id
      const userResponse: CreateUserResponse = await createUser({
        email: data.email,
        name: data.name,
        password: data.password,
      });
  
      // Verifica se o tenant_id foi retornado corretamente
      if (!userResponse?.tenant_id) {
        throw new Error('Erro ao gerar tenant_id para o novo usuário.');
      }
  
      const tenant_id = userResponse.tenant_id; // Captura o tenant_id retornado do backend
  
      // Chamada para associar o plano de pagamento
      const plan = 'sandbox'; // Plano de pagamento padrão
      const interval = 'month'; // Intervalo do plano (mensal)
  
      const subscriptionResponse = await createAndAssociateSubscription({
        email: data.email,
        tenant_id,
        plan,
        interval,
      });
  
      // Verificação do tipo de subscriptionResponse
      if (typeof subscriptionResponse === 'object' && subscriptionResponse !== null) {
        if ('error' in subscriptionResponse) {
          throw new Error(subscriptionResponse.error);
        } else if ('message' in subscriptionResponse) {
          console.log('Assinatura criada com sucesso:', subscriptionResponse.message);
          router.push('/signin'); // Redireciona para a página de login após o sucesso
        } else {
          throw new Error('Resposta inesperada do serviço de assinatura.');
        }
      } else {
        throw new Error('Resposta inesperada do serviço de assinatura.');
      }
    } catch (error: any) {
      // Detalhamento do erro
      setErrorMessage(error.message || 'Erro inesperado durante o cadastro. Tente novamente.');
      console.error('Erro ao criar usuário ou associar o plano:', error);
    } finally {
      setLoading(false); // Remover carregamento após submissão
    }
  };
  

  const handleSetting = async () => {
    handleSubmit(onSubmit)()
  }

  return (
    loading
      ? <Loading />
      : <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <h2 className="text-[32px] font-bold text-gray-900">{t('login.createAccount')}</h2>
          <p className="mt-1 text-sm text-gray-600">{t('login.createAccountDesc')}</p>
          <div className="grow mt-8 sm:mx-auto sm:w-full sm:max-w-md">
            <div className="bg-white">
              {errorMessage && <div className="text-red-400">{errorMessage}</div>} {/* Exibe mensagem de erro se existir */}
              <form onSubmit={handleSubmit(onSubmit)}>
                <div className="mb-5">
                  <label htmlFor="email" className="my-2 flex items-center justify-between text-sm font-medium text-gray-900">
                    {t('login.email')}
                  </label>
                  <div className="mt-1">
                    <input
                      {...register('email')}
                      placeholder={t('login.emailPlaceholder') || ''}
                      className="appearance-none block w-full rounded-lg pl-[14px] px-3 py-2 border border-gray-200 hover:border-gray-300 hover:shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 placeholder-gray-400 caret-primary-600 sm:text-sm"
                    />
                    {errors.email && <span className="text-red-400 text-sm">{t(`${errors.email?.message}`)}</span>}
                  </div>
                </div>

                <div className="mb-5">
                  <label htmlFor="name" className="my-2 flex items-center justify-between text-sm font-medium text-gray-900">
                    {t('login.name')}
                  </label>
                  <div className="mt-1 relative rounded-md shadow-sm">
                    <input
                      {...register('name')}
                      placeholder={t('login.namePlaceholder') || ''}
                      className="appearance-none block w-full rounded-lg pl-[14px] px-3 py-2 border border-gray-200 hover:border-gray-300 hover:shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 placeholder-gray-400 caret-primary-600 sm:text-sm pr-10"
                    />
                  </div>
                  {errors.name && <span className="text-red-400 text-sm">{t(`${errors.name.message}`)}</span>}
                </div>

                <div className="mb-5">
                  <label htmlFor="password" className="my-2 flex items-center justify-between text-sm font-medium text-gray-900">
                    {t('login.password')}
                  </label>
                  <div className="mt-1 relative rounded-md shadow-sm">
                    <input
                      {...register('password')}
                      type={showPassword ? 'text' : 'password'}
                      placeholder={t('login.passwordPlaceholder') || ''}
                      className="appearance-none block w-full rounded-lg pl-[14px] px-3 py-2 border border-gray-200 hover:border-gray-300 hover:shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 placeholder-gray-400 caret-primary-600 sm:text-sm pr-10"
                    />
                    <div className="absolute inset-y-0 right-0 flex items-center pr-3">
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="text-gray-400 hover:text-gray-500 focus:outline-none focus:text-gray-500"
                      >
                        {showPassword ? '👀' : '😝'}
                      </button>
                    </div>
                  </div>
                  <div className={classNames('mt-1 text-xs text-gray-500', { 'text-red-400 !text-sm': errors.password })}>
                    {t('login.error.passwordInvalid')}
                  </div>
                </div>

                <div>
                  <Button variant="primary" className="w-full" onClick={handleSetting}>
                    {t('login.createAccount')}
                  </Button>
                </div>
              </form>
              <div className="block w-full mt-2 text-xs text-gray-600">
                {t('login.license.tip')}
                &nbsp;
                <Link
                  className="text-primary-600"
                  target="_blank" rel="noopener noreferrer"
                  href={'https://minhaia.com/termos'}
                >
                  {t('login.license.link')}
                </Link>
              </div>
            </div>
          </div>
        </div>
  )
}

export default InstallForm
