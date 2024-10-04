import {
  RiCloseLine,
  RiDownloadLine,
} from '@remixicon/react'
import {
  fileIsUploaded,
  getFileAppearanceType,
  getFileExtension,
} from '../utils'
import FileTypeIcon from '../file-type-icon'
import type { FileEntity } from '../types'
import cn from '@/utils/classnames'
import { formatFileSize } from '@/utils/format'
import ProgressCircle from '@/app/components/base/progress-bar/progress-circle'
import { ReplayLine } from '@/app/components/base/icons/src/vender/other'
import ActionButton from '@/app/components/base/action-button'
import Button from '@/app/components/base/button'

type FileItemProps = {
  file: FileEntity
  showDeleteAction?: boolean
  showDownloadAction?: boolean
  onRemove?: (fileId: string) => void
  onReUpload?: (fileId: string) => void
}
const FileItem = ({
  file,
  showDeleteAction,
  showDownloadAction = true,
  onRemove,
  onReUpload,
}: FileItemProps) => {
  const { id, name, type, progress } = file
  const ext = getFileExtension(name, type)
  const uploadError = progress === -1

  return (
    <div
      className={cn(
        'group relative p-2 w-[144px] h-[68px] rounded-lg border-[0.5px] border-components-panel-border bg-components-card-bg shadow-xs',
        !uploadError && 'hover:bg-components-card-bg-alt',
        uploadError && 'border border-state-destructive-border bg-state-destructive-hover',
        uploadError && 'hover:border-[0.5px] hover:border-state-destructive-border bg-state-destructive-hover-alt',
      )}
    >
      {
        showDeleteAction && (
          <Button
            className='hidden group-hover:flex absolute -right-1.5 -top-1.5 p-0 w-5 h-5 rounded-full z-10'
            onClick={() => onRemove?.(id)}
          >
            <RiCloseLine className='w-4 h-4 text-components-button-secondary-text' />
          </Button>
        )
      }
      <div className='mb-1 h-8 line-clamp-2 system-xs-medium text-text-tertiary'>
        {name}
      </div>
      <div className='flex items-center justify-between'>
        <div className='flex items-center system-2xs-medium-uppercase text-text-tertiary'>
          <FileTypeIcon
            size='sm'
            type={getFileAppearanceType(name, type)}
            className='mr-1'
          />
          {
            ext && (
              <>
                {ext}
                <div className='mx-1'>·</div>
              </>
            )
          }
          {formatFileSize(file.size || 0)}
        </div>
        {
          showDownloadAction && (
            <a href={file.url} download={true} target='_blank'>
              <ActionButton
                size='xs'
              >
                <RiDownloadLine className='w-3.5 h-3.5 text-text-tertiary' />
              </ActionButton>
            </a>
          )
        }
        {
          progress >= 0 && !fileIsUploaded(file) && (
            <ProgressCircle
              percentage={progress}
              size={12}
            />
          )
        }
        {
          uploadError && (
            <ReplayLine
              className='w-4 h-4 text-text-tertiary'
              onClick={() => onReUpload?.(id)}
            />
          )
        }
      </div>
    </div>
  )
}

export default FileItem
