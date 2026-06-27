// What's currently selected on the canvas, as a tiny store so any panel can read it the same
// way it reads the graph or workspace — by subscribing, not by being handed props. Selection is
// transient view state: not undoable and not saved. The canvas writes it (Viewport's
// onSelectionChange); panels that edit the selected thing read it.

import { create } from 'zustand'

import type { Selection } from './types'

interface SelectionState {
  selection: Selection
  setSelection: (selection: Selection) => void
}

export const useSelectionStore = create<SelectionState>((set) => ({
  selection: null,
  setSelection: (selection) => set({ selection }),
}))
