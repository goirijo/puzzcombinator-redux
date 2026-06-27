// Small shared UI types used across the shell. Panels don't receive these as props — they
// subscribe to the stores that hold them (the graph store, the workspace store, the selection
// store); these are just the value shapes those stores and the menu bar pass around.

/** What is currently selected on the canvas — the datum the canvas writes (via the selection
 *  store) and the GRAPH panel reads. `null` when nothing is selected. */
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
