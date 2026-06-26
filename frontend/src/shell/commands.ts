// The command registry: the single list the command rail and the panel region read from.
// Each command is a self-contained descriptor pairing an id/label/icon with the panel
// component it opens. The rail renders one button per entry; the panel region renders the
// active entry's `Panel`. Neither names a specific command — so adding one later (or
// turning a placeholder into a real feature) is editing THIS list and nothing else.

import type { FC } from 'react'

import { GraphInspector } from '../panels/GraphInspector'
import { PlaceholderPanel } from '../panels/PlaceholderPanel'
import { ViewPanel } from '../panels/ViewPanel'
import type { PanelProps } from './types'

/** The commands from the design (`frontend/design/ideas.txt`). */
export type CommandId =
  | 'view'
  | 'graph'
  | 'puzzle'
  | 'saveload'
  | 'bind'
  | 'arrange'
  | 'manage'

export interface CommandDescriptor {
  id: CommandId
  label: string
  /** A single glyph for the rail button (kept text-only until we add real icons). */
  icon: string
  Panel: FC<PanelProps>
}

// GRAPH and VIEW have real panels; the rest open a placeholder, so the rail already matches the
// design and "build the feature" is swapping its `Panel` here. A panel may take PanelProps
// (GraphInspector) or subscribe to stores directly and ignore them (ViewPanel) — both satisfy
// `FC<PanelProps>`, so the registry stays uniform either way.
export const COMMANDS: CommandDescriptor[] = [
  { id: 'view', label: 'View', icon: '▤', Panel: ViewPanel },
  { id: 'graph', label: 'Graph', icon: '◆', Panel: GraphInspector },
  { id: 'puzzle', label: 'Puzzle', icon: '✦', Panel: PlaceholderPanel },
  { id: 'saveload', label: 'Save / Load', icon: '🖫', Panel: PlaceholderPanel },
  { id: 'bind', label: 'Bind', icon: '❒', Panel: PlaceholderPanel },
  { id: 'arrange', label: 'Arrange', icon: '⊞', Panel: PlaceholderPanel },
  { id: 'manage', label: 'Manage', icon: '☰', Panel: PlaceholderPanel },
]

export function commandById(id: CommandId): CommandDescriptor {
  const cmd = COMMANDS.find((c) => c.id === id)
  if (!cmd) throw new Error(`unknown command: ${id}`)
  return cmd
}
