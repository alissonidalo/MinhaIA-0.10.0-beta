import type { FC } from 'react'
import { memo } from 'react'
import type {
  ChatItem,
  VisionFile,
} from '../../types'
import { Markdown } from '@/app/components/base/markdown'
import Thought from '@/app/components/base/chat/chat/thought'
import ImageGallery from '@/app/components/base/image-gallery'

type AgentContentProps = {
  item: ChatItem
  responding?: boolean
}
const AgentContent: FC<AgentContentProps> = ({
  item,
  responding,
}) => {
  const {
    annotation,
    agent_thoughts,
  } = item

  const getImgs = (list?: VisionFile[]) => {
    if (!list)
      return []
    return list.filter(file => file.type === 'image' && file.belongs_to === 'assistant')
  }

  if (annotation?.logAnnotation)
    return <Markdown content={annotation?.logAnnotation.content || ''} />

  return (
    <div>
      {agent_thoughts?.map((thought, index) => (
        <div key={index} className='px-2 py-1'>
          {thought.thought && (
            <Markdown content={thought.thought} />
          )}
          {/* {item.tool} */}
          {/* perhaps not use tool */}
          {!!thought.tool && (
            <Thought
              thought={thought}
              isFinished={!!thought.observation || !responding}
            />
          )}

          {getImgs(thought.message_files).length > 0 && (
            <ImageGallery srcs={getImgs(thought.message_files).map(file => file.url)} />
          )}
        </div>
      ))}
    </div>
  )
}

export default memo(AgentContent)
