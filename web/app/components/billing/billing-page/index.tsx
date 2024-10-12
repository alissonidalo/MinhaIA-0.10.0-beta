'use client'
import React, { FC, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import useSWR from 'swr'
import PlanComp from '../plan'
import { fetchBillingUrl } from '@/service/billing'
import { useAppContext } from '@/context/app-context'
import { useProviderContext } from '@/context/provider-context'
import { Plan } from '../type'  // Importando o enum Plan

const Billing: FC = () => {
  const { t } = useTranslation()
  const { isCurrentWorkspaceManager } = useAppContext()
  const { enableBilling, plan } = useProviderContext()

  // Usa SWR para pegar a URL de faturamento, mas apenas para planos pagos
  const { data: billingUrl } = useSWR(
    (!enableBilling || !isCurrentWorkspaceManager || plan.type === Plan.sandbox) ? null : ['/billing/invoices'],
    () => fetchBillingUrl().then(data => data.url),
  )

  useEffect(() => {
    if (billingUrl) {
      window.location.href = billingUrl
    }
  }, [billingUrl])

  return (
    <div>
      <PlanComp loc={'billing-page'} />
      {enableBilling && isCurrentWorkspaceManager && billingUrl && plan.type !== Plan.sandbox && (
        <a className='mt-5 flex px-6 justify-between h-12 items-center bg-gray-50 rounded-xl cursor-pointer' href={billingUrl} target='_blank' rel='noopener noreferrer'>
          <div className='flex items-center'>
            <div className='ml-2 text-sm font-normal text-gray-700'>{t('billing.viewBilling')}</div>
          </div>
        </a>
      )}
    </div>
  )
}

export default Billing
