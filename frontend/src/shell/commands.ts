// The command registry: the single list the command rail and the panel region read from.
// Each command is a self-contained descriptor pairing an id/label/icon with the panel
// component it opens. The rail renders one button per entry; the panel region renders the
// active entry's `Panel`. Neither names a specific command — so adding one later (or
// turning a placeholder into a real feature) is editing THIS list and nothing else.

import type { FC } from 'react'

import { GraphInspector } from '../panels/GraphInspector'
import { PlaceholderPanel } from '../panels/PlaceholderPanel'
import { TestingPanel } from '../panels/testing/TestingPanel'
import { ViewPanel } from '../panels/ViewPanel'

/** The commands from the design (`frontend/design/ideas.txt`), plus TESTING — a scratch
 *  playground for in-progress features (not in the design). Its sections graduate into real
 *  commands (e.g. EDIT) once they settle, and then it goes away. */
export type CommandId =
  | 'view'
  | 'graph'
  | 'puzzle'
  | 'saveload'
  | 'bind'
  | 'arrange'
  | 'manage'
  | 'testing'

export interface CommandDescriptor {
  id: CommandId
  label: string
  /** A single glyph for the rail button (kept text-only until we add real icons). */
  icon: string
  Panel: FC
}

// GRAPH and VIEW have real panels; the rest open a placeholder, so the rail already matches the
// design and "build the feature" is swapping its `Panel` here. Panels take no props — each
// subscribes to the stores it needs (graph / workspace / selection), so the registry stays
// uniform and the panel region just renders the active entry's `Panel`.
export const COMMANDS: CommandDescriptor[] = [
  { id: 'view', label: 'View', icon: '▤', Panel: ViewPanel },
  { id: 'graph', label: 'Graph', icon: '◆', Panel: GraphInspector },
  { id: 'puzzle', label: 'Puzzle', icon: '✦', Panel: PlaceholderPanel },
  { id: 'saveload', label: 'Save / Load', icon: '🖫', Panel: PlaceholderPanel },
  { id: 'bind', label: 'Bind', icon: '❒', Panel: PlaceholderPanel },
  { id: 'arrange', label: 'Arrange', icon: '⊞', Panel: PlaceholderPanel },
  { id: 'manage', label: 'Manage', icon: '☰', Panel: PlaceholderPanel },
  { id: 'testing', label: 'Testing', icon: '🧪', Panel: TestingPanel },
]

export function commandById(id: CommandId): CommandDescriptor {
  const cmd = COMMANDS.find((c) => c.id === id)
  if (!cmd) throw new Error(`unknown command: ${id}`)
  return cmd
}
