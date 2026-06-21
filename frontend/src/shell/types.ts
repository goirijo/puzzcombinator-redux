// The shared contracts the shell hands to its features. Keeping them in one tiny file
// (rather than scattered through components) is what lets a new panel "fill a slot": it
// receives `PanelProps` and nothing else, and never reaches into shell internals.

import type { HuntFlowEdge, HuntFlowNode, NodeFields } from '../model/adapt'

/** What is currently selected on the canvas — the datum the canvas writes and the GRAPH
 *  panel reads. `null` when nothing is selected. */
export type Selection =
  | { kind: 'node'; id: string }
  | { kind: 'edge'; id: string }
  | null

/** Where a save attempt currently stands — drives the menu bar's Save button. */
export type SaveState =
  | { status: 'idle' }
  | { status: 'saving' }
  | { status: 'saved' }
  | { status: 'error'; message: string }

/**
 * The uniform contract every command panel receives. Add a panel by writing a component
 * that takes these props and registering it in `commands.ts` — no shell edits. Panels are
 * pure views over this data + callbacks; they hold no graph state of their own.
 *
 * Note: saving is *not* here. It's a global action that lives in the menu bar (it commits
 * the whole graph), not a per-panel concern — so panels never see `onSave`/`saveState`.
 */
export interface PanelProps {
  nodes: HuntFlowNode[]
  edges: HuntFlowEdge[]
  selection: Selection
  /** Patch the editable fields (label/action/notes) of one node. */
  updateNode: (id: string, patch: Partial<NodeFields>) => void
}
