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

import { useCallback, useMemo, useState } from 'react'
import { Group, Panel, Separator } from 'react-resizable-panels'
import { type OnConnect, type OnSelectionChangeParams } from '@xyflow/react'

import { withLooseArtifactsHidden, type CanvasNode, type HuntFlowEdge } from '../model/flow'
import { activeView } from '../model/workspace'
import { CommandRail } from './CommandRail'
import { MenuBar } from './MenuBar'
import { PanelRegion } from './PanelRegion'
import { TabBar } from './TabBar'
import { Viewport } from './Viewport'
import { useGraphStore } from './graphStore'
import { useWorkspaceStore } from './workspaceStore'
import { useSelectionStore } from './selectionStore'
import { usePersistence } from './usePersistence'
import { useUndoRedo } from './useUndoRedo'
import { useKeyboardShortcuts } from './useKeyboardShortcuts'
import type { CommandId } from './commands'
import './shell.css'

export function Shell() {
  // Graph state lives in the store (so it's undoable); subscribe to it here.
  const nodes = useGraphStore((s) => s.nodes)
  const edges = useGraphStore((s) => s.edges)
  const onNodesChange = useGraphStore((s) => s.onNodesChange)
  const onEdgesChange = useGraphStore((s) => s.onEdgesChange)
  const detachEdges = useGraphStore((s) => s.detachEdges)
  const connectNodes = useGraphStore((s) => s.connectNodes)

  // Undo/redo come from the temporal store. The methods are stable (read once); the
  // can-undo/can-redo flags are subscribed so the buttons enable/disable reactively.
  // The workspace channel (views/tabs/active tab) lives in its own store now (so panels can
  // subscribe to it directly); the active view's switch/create logic lives there too.
  const workspace = useWorkspaceStore((s) => s.workspace)
  const selectTab = useWorkspaceStore((s) => s.selectTab)
  const createTab = useWorkspaceStore((s) => s.createTab)
  const deleteTab = useWorkspaceStore((s) => s.deleteTab)
  const previewTab = useWorkspaceStore((s) => s.previewTab)
  // The tab being hover-previewed (or null). The canvas shows this tab when set, else the
  // active tab — so hovering a tab previews exactly what clicking it would show.
  const previewTabId = useWorkspaceStore((s) => s.previewTabId)
  const setActiveViewport = useWorkspaceStore((s) => s.setActiveViewport)

  // Selection lives in its own store so panels read it by subscribing (like the graph/workspace);
  // the canvas writes it through this setter.
  const setSelection = useSelectionStore((s) => s.setSelection)

  // Self-contained behaviors live in their own hooks: load/save + dirty (seeds the stores on
  // mount), undo/redo (temporal-store flags + actions), and the global keyboard chords wiring
  // both together.
  const { saveState, isDirty, onSave } = usePersistence()
  const { canUndo, canRedo, onUndo, onRedo } = useUndoRedo()
  useKeyboardShortcuts({ onSave, onUndo, onRedo })

  // Non-undoable UI state.
  const [activeCommandId, setActiveCommandId] = useState<CommandId | null>('graph')

  const handleSelectionChange = useCallback(
    ({ nodes: sn, edges: se }: OnSelectionChangeParams<CanvasNode, HuntFlowEdge>) => {
      if (sn.length > 0) setSelection({ kind: 'node', id: sn[0].id })
      else if (se.length > 0) setSelection({ kind: 'edge', id: se[0].id })
      else setSelection(null)
    },
    [setSelection],
  )

  // React Flow reports a finished node→node drag as a Connection; turn it into an edge.
  const handleConnect = useCallback<OnConnect>(
    (c) => {
      if (c.source && c.target) connectNodes(c.source, c.target)
    },
    [connectNodes],
  )

  // Clicking the active command again closes its panel.
  const onSelectCommand = useCallback((id: CommandId) => {
    setActiveCommandId((current) => (current === id ? null : id))
  }, [])

  const active = workspace ? activeView(workspace) : undefined
  // Framing belongs to the tab now: the camera comes from a tab, the drawn arrangement from
  // its view. The *displayed* tab is the previewed one while hovering, else the active tab —
  // the store reprojects its view's positions; here we feed its id + camera to the Viewport.
  const displayedTabId = previewTabId ?? workspace?.active_tab ?? null
  const displayedTab = workspace?.tabs.find((t) => t.id === displayedTabId)
  // What the canvas actually draws: a projection of the store nodes that honors the *displayed*
  // view's per-view "show unplaced?" flag (the previewed view while hovering, else the active
  // one — so a hover-preview of a hide-pool view previews it hidden). The store/save always keep
  // the full set; this only changes what's rendered. See withLooseArtifactsHidden.
  const showUnplaced = displayedTab ? (workspace?.views[displayedTab.view]?.show_unplaced ?? true) : true
  const displayNodes = useMemo(
    () => withLooseArtifactsHidden(nodes, !showUnplaced),
    [nodes, showUnplaced],
  )

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
            onCreate={createTab}
            onClose={deleteTab}
            onPreview={previewTab}
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
                    />
                  </Panel>
                  <Separator className="resize-handle" />
                </>
              )}
              <Panel id="canvas">
                <Viewport
                  nodes={displayNodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onEdgesDelete={detachEdges}
                  onConnect={handleConnect}
                  onSelectionChange={handleSelectionChange}
                  activeTabId={displayedTab?.id}
                  viewport={displayedTab?.viewport}
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
