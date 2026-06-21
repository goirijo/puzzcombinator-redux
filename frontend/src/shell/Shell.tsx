// The shell: the stable skeleton of regions (menu bar, command rail, tab bar, swappable
// panel, canvas) plus the home of UI state and I/O. The *graph* itself now lives in the
// zundo-backed store (store.ts) so it can be undone/redone; this file owns the non-undoable
// UI state (selection, active command, save status, views), wires the regions together,
// and drives the global Save/Undo/Redo from the menu bar.

import { useCallback, useEffect, useState } from 'react'
import { Group, Panel, Separator } from 'react-resizable-panels'
import { type OnSelectionChangeParams } from '@xyflow/react'
import { useStore } from 'zustand'

import { fetchGraph, saveGraph } from '../model/api'
import { fromFlow, toFlow, type HuntFlowEdge, type HuntFlowNode, type View } from '../model/adapt'
import { Canvas } from './Canvas'
import { CommandRail } from './CommandRail'
import { MenuBar } from './MenuBar'
import { PanelRegion } from './PanelRegion'
import { TabBar } from './TabBar'
import { useGraphStore } from './store'
import type { CommandId } from './commands'
import type { SaveState, Selection } from './types'
import './shell.css'

// The single default view until the VIEW command lands. The canvas already consumes a
// View, so adding more is a state change here, not a rewire.
const DEFAULT_VIEWS: View[] = [{ id: 'main', title: 'Main', graphId: 'main' }]

/** Serialize the graph the way Save sends it — used to detect unsaved changes. */
function serialize(nodes: HuntFlowNode[], edges: HuntFlowEdge[]): string {
  return JSON.stringify(fromFlow(nodes, edges))
}

export function Shell() {
  // Graph state lives in the store (so it's undoable); subscribe to it here.
  const nodes = useGraphStore((s) => s.nodes)
  const edges = useGraphStore((s) => s.edges)
  const loadGraph = useGraphStore((s) => s.loadGraph)
  const updateNode = useGraphStore((s) => s.updateNode)
  const onNodesChange = useGraphStore((s) => s.onNodesChange)
  const onEdgesChange = useGraphStore((s) => s.onEdgesChange)

  // Undo/redo come from the temporal store. The methods are stable (read once); the
  // can-undo/can-redo flags are subscribed so the buttons enable/disable reactively.
  const canUndo = useStore(useGraphStore.temporal, (s) => s.pastStates.length > 0)
  const canRedo = useStore(useGraphStore.temporal, (s) => s.futureStates.length > 0)

  // Non-undoable UI state.
  const [selection, setSelection] = useState<Selection>(null)
  const [activeCommandId, setActiveCommandId] = useState<CommandId | null>('graph')
  const [saveState, setSaveState] = useState<SaveState>({ status: 'idle' })
  // The serialized graph as of the last load/save; null until first load. Drives `isDirty`.
  const [savedSnapshot, setSavedSnapshot] = useState<string | null>(null)

  const [views] = useState<View[]>(DEFAULT_VIEWS)
  const [activeViewId, setActiveViewId] = useState(DEFAULT_VIEWS[0].id)
  const activeView = views.find((v) => v.id === activeViewId) ?? views[0]

  useEffect(() => {
    fetchGraph()
      .then((res) => {
        const flow = toFlow(res)
        loadGraph(flow.nodes, flow.edges)
        // The initial load shouldn't be undoable, and is the clean baseline.
        useGraphStore.temporal.getState().clear()
        setSavedSnapshot(serialize(flow.nodes, flow.edges))
      })
      .catch((err) => console.error('failed to load graph', err))
  }, [loadGraph])

  const handleSelectionChange = useCallback(
    ({ nodes: sn, edges: se }: OnSelectionChangeParams<HuntFlowNode, HuntFlowEdge>) => {
      if (sn.length > 0) setSelection({ kind: 'node', id: sn[0].id })
      else if (se.length > 0) setSelection({ kind: 'edge', id: se[0].id })
      else setSelection(null)
    },
    [],
  )

  const onSave = useCallback(async () => {
    // Read straight from the store so we always serialize the latest graph.
    const { nodes: n, edges: e } = useGraphStore.getState()
    setSaveState({ status: 'saving' })
    try {
      await saveGraph(fromFlow(n, e))
      setSavedSnapshot(serialize(n, e))
      setSaveState({ status: 'saved' })
    } catch (err) {
      setSaveState({ status: 'error', message: err instanceof Error ? err.message : String(err) })
    }
  }, [])

  const onUndo = useCallback(() => useGraphStore.temporal.getState().undo(), [])
  const onRedo = useCallback(() => useGraphStore.temporal.getState().redo(), [])

  // Keyboard shortcuts: Ctrl/⌘+S save, Ctrl/⌘+Z undo, Ctrl/⌘+Shift+Z (or Ctrl/⌘+Y) redo.
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (!ev.metaKey && !ev.ctrlKey) return
      const key = ev.key.toLowerCase()
      if (key === 's') {
        ev.preventDefault()
        void onSave()
      } else if (key === 'z' && !ev.shiftKey) {
        ev.preventDefault()
        onUndo()
      } else if ((key === 'z' && ev.shiftKey) || key === 'y') {
        ev.preventDefault()
        onRedo()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onSave, onUndo, onRedo])

  // Clicking the active command again closes its panel.
  const onSelectCommand = useCallback((id: CommandId) => {
    setActiveCommandId((current) => (current === id ? null : id))
  }, [])

  const isDirty = savedSnapshot !== null && serialize(nodes, edges) !== savedSnapshot
  const panelProps = { nodes, edges, selection, updateNode }

  return (
    <div className="app">
      <MenuBar
        title={`Puzzcombinator · ${activeView.title}`}
        isDirty={isDirty}
        saveState={saveState}
        canUndo={canUndo}
        canRedo={canRedo}
        onSave={onSave}
        onUndo={onUndo}
        onRedo={onRedo}
      />
      <div className="shell">
        <CommandRail activeCommandId={activeCommandId} onSelect={onSelectCommand} />
        <div className="shell__body">
          <TabBar views={views} activeViewId={activeViewId} onSelect={setActiveViewId} />
          <div className="shell__content">
            {/* String sizes are percentages of the group; numbers would be pixels. */}
            <Group orientation="horizontal" id="puzz-shell">
              {activeCommandId !== null && (
                <>
                  <Panel id="panel" defaultSize="26" minSize="16" maxSize="55">
                    <PanelRegion
                      activeCommandId={activeCommandId}
                      onClose={() => setActiveCommandId(null)}
                      {...panelProps}
                    />
                  </Panel>
                  <Separator className="resize-handle" />
                </>
              )}
              <Panel id="canvas">
                <Canvas
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onSelectionChange={handleSelectionChange}
                  view={activeView}
                />
              </Panel>
            </Group>
          </div>
        </div>
      </div>
    </div>
  )
}
