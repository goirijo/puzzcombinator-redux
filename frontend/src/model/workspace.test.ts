import { describe, expect, it } from 'vitest'

import {
  activeTab,
  activeView,
  createTab,
  createView,
  deleteTab,
  deleteView,
  renameView,
  setActiveTabView,
  setShowUnplaced,
  type WorkspaceDTO,
} from './workspace'

const VP = { x: 0, y: 0, zoom: 1 }
const WS: WorkspaceDTO = {
  views: {
    v1: { graph: 'main', title: 'Main', positions: { a: { x: 1, y: 2 } }, show_unplaced: true },
    v2: { graph: 'main', title: 'Cellar', positions: {}, show_unplaced: false },
  },
  tabs: [
    { id: 't1', view: 'v1', viewport: VP },
    { id: 't2', view: 'v2', viewport: VP },
  ],
  active_tab: 't2',
}

describe('activeView', () => {
  it('returns the view the active tab points at, with its id', () => {
    expect(activeView(WS)).toEqual({ id: 'v2', view: WS.views.v2 })
  })

  it('is undefined when no tab is active', () => {
    expect(activeView({ ...WS, active_tab: null })).toBeUndefined()
  })

  it('is undefined when the active tab points at a missing view', () => {
    expect(activeView({ ...WS, views: { v1: WS.views.v1 } })).toBeUndefined()
  })
})

describe('activeTab', () => {
  it('returns the active tab object', () => {
    expect(activeTab(WS)).toEqual(WS.tabs[1])
  })

  it('is undefined when no tab is active', () => {
    expect(activeTab({ ...WS, active_tab: null })).toBeUndefined()
  })
})

describe('setActiveTabView', () => {
  it('repoints only the active tab at the new view, leaving others untouched', () => {
    const next = setActiveTabView(WS, 'v1') // active tab is t2
    expect(next.tabs.find((t) => t.id === 't2')!.view).toBe('v1')
    expect(next.tabs.find((t) => t.id === 't1')!.view).toBe('v1') // unchanged (already v1)
  })

  it('does not mutate the input', () => {
    setActiveTabView(WS, 'v1')
    expect(WS.tabs.find((t) => t.id === 't2')!.view).toBe('v2')
  })

  it('is a no-op on tabs when nothing is active', () => {
    expect(setActiveTabView({ ...WS, active_tab: null }, 'v1').tabs).toEqual(WS.tabs)
  })
})

describe('createView', () => {
  it('adds the view under a fresh id without touching existing views or tabs', () => {
    const view = { graph: 'main', title: 'Attic', positions: {}, show_unplaced: true }
    const { workspace, viewId } = createView(WS, view)
    expect(workspace.views[viewId]).toEqual(view)
    expect(Object.keys(workspace.views)).toHaveLength(3)
    expect(workspace.tabs).toEqual(WS.tabs) // create does not switch
    expect(workspace.active_tab).toBe('t2')
  })

  it('generates distinct ids on repeated calls', () => {
    const view = { graph: 'main', title: 'x', positions: {}, show_unplaced: true }
    expect(createView(WS, view).viewId).not.toBe(createView(WS, view).viewId)
  })
})

describe('setShowUnplaced', () => {
  it('flips only the named view’s flag', () => {
    const next = setShowUnplaced(WS, 'v1', false)
    expect(next.views.v1.show_unplaced).toBe(false)
    expect(next.views.v2).toEqual(WS.views.v2) // untouched
  })

  it('does not mutate the input', () => {
    setShowUnplaced(WS, 'v1', false)
    expect(WS.views.v1.show_unplaced).toBe(true)
  })

  it('is a no-op for a missing view (returns the input unchanged)', () => {
    expect(setShowUnplaced(WS, 'nope', false)).toBe(WS)
  })
})

describe('renameView', () => {
  it('retitles only the named view', () => {
    const next = renameView(WS, 'v1', 'Renamed')
    expect(next.views.v1.title).toBe('Renamed')
    expect(next.views.v2).toEqual(WS.views.v2) // untouched
  })

  it('does not mutate the input', () => {
    renameView(WS, 'v1', 'Renamed')
    expect(WS.views.v1.title).toBe('Main')
  })

  it('returns the input unchanged for a missing view', () => {
    expect(renameView(WS, 'nope', 'x')).toBe(WS)
  })
})

describe('deleteView', () => {
  it('removes the view', () => {
    const next = deleteView(WS, 'v1')
    expect(next.views).not.toHaveProperty('v1')
    expect(Object.keys(next.views)).toEqual(['v2'])
  })

  it('repoints tabs that showed the deleted view at a survivor', () => {
    const next = deleteView(WS, 'v1') // t1 showed v1; v2 is the only survivor
    expect(next.tabs.find((t) => t.id === 't1')!.view).toBe('v2')
    expect(next.tabs.find((t) => t.id === 't2')!.view).toBe('v2') // unchanged
  })

  it('refuses to delete the last view (returns input unchanged)', () => {
    const one: WorkspaceDTO = { ...WS, views: { v1: WS.views.v1 } }
    expect(deleteView(one, 'v1')).toBe(one)
  })

  it('returns the input unchanged for a missing view', () => {
    expect(deleteView(WS, 'nope')).toBe(WS)
  })

  it('does not mutate the input', () => {
    deleteView(WS, 'v1')
    expect(WS.views).toHaveProperty('v1')
    expect(WS.tabs.find((t) => t.id === 't1')!.view).toBe('v1')
  })
})

describe('createTab', () => {
  it('appends a tab on the given view with its viewport, without switching', () => {
    const { workspace, tabId } = createTab(WS, 'v1', VP)
    expect(workspace.tabs).toHaveLength(3)
    expect(workspace.tabs[2]).toEqual({ id: tabId, view: 'v1', viewport: VP })
    expect(workspace.active_tab).toBe('t2') // create does not switch
  })

  it('generates distinct ids on repeated calls', () => {
    expect(createTab(WS, 'v1', VP).tabId).not.toBe(createTab(WS, 'v1', VP).tabId)
  })

  it('does not mutate the input', () => {
    createTab(WS, 'v1', VP)
    expect(WS.tabs).toHaveLength(2)
  })
})

describe('deleteTab', () => {
  it('removes the tab and leaves its view intact', () => {
    const next = deleteTab(WS, 't1') // background tab (active is t2)
    expect(next.tabs.map((t) => t.id)).toEqual(['t2'])
    expect(next.views).toHaveProperty('v1') // view survives the window closing
  })

  it('leaves active_tab alone when closing a background tab', () => {
    expect(deleteTab(WS, 't1').active_tab).toBe('t2')
  })

  it('lands on the next tab when the active one is closed', () => {
    const three: WorkspaceDTO = {
      ...WS,
      tabs: [...WS.tabs, { id: 't3', view: 'v1', viewport: VP }],
      active_tab: 't2',
    }
    expect(deleteTab(three, 't2').active_tab).toBe('t3') // next by position
  })

  it('falls back to the previous tab when the closed active tab was last', () => {
    expect(deleteTab(WS, 't2').active_tab).toBe('t1') // t2 was last → previous
  })

  it('refuses to remove the last tab (returns input unchanged)', () => {
    const one: WorkspaceDTO = { ...WS, tabs: [WS.tabs[0]], active_tab: 't1' }
    expect(deleteTab(one, 't1')).toBe(one)
  })

  it('returns the input unchanged for a missing id', () => {
    expect(deleteTab(WS, 'nope')).toBe(WS)
  })

  it('does not mutate the input', () => {
    deleteTab(WS, 't2')
    expect(WS.tabs).toHaveLength(2)
    expect(WS.active_tab).toBe('t2')
  })
})
