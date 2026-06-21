// The swappable panel region: a titled, closeable container that renders whichever
// command's panel is active. It looks the command up in the registry and renders its
// `Panel`, forwarding the shared `PanelProps`. It knows nothing about any specific panel —
// that is the whole point: a new command shows up here for free.

import { commandById, type CommandId } from './commands'
import type { PanelProps } from './types'

interface PanelRegionProps extends PanelProps {
  activeCommandId: CommandId
  onClose: () => void
}

export function PanelRegion({ activeCommandId, onClose, ...panelProps }: PanelRegionProps) {
  const cmd = commandById(activeCommandId)
  const Body = cmd.Panel
  return (
    <aside className="panel">
      <header className="panel__header">
        <span className="panel__title">{cmd.label}</span>
        <button className="panel__close" onClick={onClose} title="Close panel">
          ×
        </button>
      </header>
      <div className="panel__body">
        <Body {...panelProps} />
      </div>
    </aside>
  )
}
