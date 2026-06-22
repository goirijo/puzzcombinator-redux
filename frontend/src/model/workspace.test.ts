import { describe, expect, it } from 'vitest'

import { activeView, type WorkspaceDTO } from './workspace'

const WS: WorkspaceDTO = {
  views: {
    v1: { graph: 'main', title: 'Main', positions: { a: { x: 1, y: 2 } } },
    v2: { graph: 'main', title: 'Cellar', positions: {} },
  },
  tabs: [
    { id: 't1', view: 'v1', viewport: { x: 0, y: 0, zoom: 1 } },
    { id: 't2', view: 'v2', viewport: { x: 0, y: 0, zoom: 1 } },
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
