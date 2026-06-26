import { describe, expect, it } from 'vitest'

import {
  activeTab,
  activeView,
  createView,
  deleteView,
  renameView,
  setActiveTabView,
  type WorkspaceDTO,
} from './workspace'

const VP = { x: 0, y: 0, zoom: 1 }
const WS: WorkspaceDTO = {
  views: {
    v1: { graph: 'main', title: 'Main', positions: { a: { x: 1, y: 2 } }, viewport: VP },
    v2: { graph: 'main', title: 'Cellar', positions: {}, viewport: VP },
  },
  tabs: [
    { id: 't1', view: 'v1' },
    { id: 't2', view: 'v2' },
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
    const view = { graph: 'main', title: 'Attic', positions: {}, viewport: VP }
    const { workspace, viewId } = createView(WS, view)
    expect(workspace.views[viewId]).toEqual(view)
    expect(Object.keys(workspace.views)).toHaveLength(3)
    expect(workspace.tabs).toEqual(WS.tabs) // create does not switch
    expect(workspace.active_tab).toBe('t2')
  })

  it('generates distinct ids on repeated calls', () => {
    const view = { graph: 'main', title: 'x', positions: {}, viewport: VP }
    expect(createView(WS, view).viewId).not.toBe(createView(WS, view).viewId)
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
