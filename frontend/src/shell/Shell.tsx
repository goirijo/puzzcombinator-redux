// The shell: the stable skeleton of regions (menu bar, command rail, tab bar, swappable
// panel, viewport) plus the home of UI state and I/O. The *graph* lives in the zundo-backed
// graph store (graphStore.ts) so it can be undone/redone; this file owns the non-undoable UI
// state (selection, active command, save status, the workspace), wires the regions, and
// drives global Save/Undo/Redo. The pure transforms (fuse-on-load, split-on-save, active-view
// lookup) live in the model layer; this file only orchestrates them.
//
// Two persisted channels arrive together (model/api.ts): the graph (hunt data) and the
// workspace (UI state). For now the workspace lives here as plain state, and node positions
// ride the graph store's React Flow nodes during editing — split apart only at save. A second
// store for independent move-undo is deferred until it has a UI.

import { useCallback, useEffect, useState } from 'react'
import { Group, Panel, Separator } from 'react-resizable-panels'
import { type OnSelectionChangeParams } from '@xyflow/react'
import { useStore } from 'zustand'

import { buildSaveRequest, fetchGraph, saveGraph, toFlowGraph } from '../model/api'
import type { HuntFlowEdge, HuntFlowNode } from '../model/flow'
import { activeView } from '../model/workspace'
import { CommandRail } from './CommandRail'
import { MenuBar } from './MenuBar'
import { PanelRegion } from './PanelRegion'
import { TabBar } from './TabBar'
import { Viewport } from './Viewport'
import { useGraphStore } from './graphStore'
import { useWorkspaceStore } from './workspaceStore'
import type { CommandId } from './commands'
import type { SaveState, Selection } from './types'
import './shell.css'

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

  // The workspace channel (views/tabs/active tab) lives in its own store now (so panels can
  // subscribe to it directly); the active view's switch/create logic lives there too.
  const workspace = useWorkspaceStore((s) => s.workspace)
  const loadWorkspace = useWorkspaceStore((s) => s.loadWorkspace)
  const selectTab = useWorkspaceStore((s) => s.selectTab)
  const setActiveViewport = useWorkspaceStore((s) => s.setActiveViewport)

  // Non-undoable UI state.
  const [selection, setSelection] = useState<Selection>(null)
  const [activeCommandId, setActiveCommandId] = useState<CommandId | null>('graph')
  const [saveState, setSaveState] = useState<SaveState>({ status: 'idle' })
  // The serialized save payload as of the last load/save; null until first load. Drives `isDirty`.
  const [savedSnapshot, setSavedSnapshot] = useState<string | null>(null)

  useEffect(() => {
    fetchGraph()
      .then((res) => {
        loadWorkspace(res.workspace)
        const { nodes: n, edges: e } = toFlowGraph(res)
        loadGraph(n, e)
        // The initial load shouldn't be undoable, and is the clean baseline.
        useGraphStore.temporal.getState().clear()
        setSavedSnapshot(JSON.stringify(buildSaveRequest(n, e, res.workspace)))
      })
      .catch((err) => console.error('failed to load graph', err))
  }, [loadGraph, loadWorkspace])

  const handleSelectionChange = useCallback(
    ({ nodes: sn, edges: se }: OnSelectionChangeParams<HuntFlowNode, HuntFlowEdge>) => {
      if (sn.length > 0) setSelection({ kind: 'node', id: sn[0].id })
      else if (se.length > 0) setSelection({ kind: 'edge', id: se[0].id })
      else setSelection(null)
    },
    [],
  )

  const onSave = useCallback(async () => {
    if (!workspace) return
    // Read straight from the store so we always serialize the latest graph.
    const { nodes: n, edges: e } = useGraphStore.getState()
    const body = buildSaveRequest(n, e, workspace)
    setSaveState({ status: 'saving' })
    try {
      await saveGraph(body)
      setSavedSnapshot(JSON.stringify(body))
      setSaveState({ status: 'saved' })
    } catch (err) {
      setSaveState({ status: 'error', message: err instanceof Error ? err.message : String(err) })
    }
  }, [workspace])

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

  const active = workspace ? activeView(workspace) : undefined
  const isDirty =
    workspace !== null &&
    savedSnapshot !== null &&
    JSON.stringify(buildSaveRequest(nodes, edges, workspace)) !== savedSnapshot
  const panelProps = { nodes, edges, selection, updateNode }

  return (
    <div className="app">
      <MenuBar
        title={`Puzzcombinator${active ? ` · ${active.view.title}` : ''}`}
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
          <TabBar
            tabs={workspace?.tabs ?? []}
            views={workspace?.views ?? {}}
            activeTabId={workspace?.active_tab ?? null}
            onSelect={selectTab}
          />
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
                <Viewport
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onSelectionChange={handleSelectionChange}
                  activeViewId={active?.id}
                  viewport={active?.view.viewport}
                  onViewportChange={setActiveViewport}
                />
              </Panel>
            </Group>
          </div>
        </div>
      </div>
    </div>
  )
}
