// The top tab bar: one tab per view. A view is a particular drawing of a graph; switching
// the active tab switches what the canvas draws. For now the shell has a single default
// view, so this renders one tab — but it takes the full view list and an `onSelect`, so
// multiple views (the VIEW command) drop in without touching this component.

import type { View } from '../model/adapt'

interface TabBarProps {
  views: View[]
  activeViewId: string
  onSelect: (id: string) => void
}

export function TabBar({ views, activeViewId, onSelect }: TabBarProps) {
  return (
    <div className="tab-bar" role="tablist">
      {views.map((view) => (
        <button
          key={view.id}
          className="tab-bar__tab"
          role="tab"
          aria-selected={view.id === activeViewId}
          data-active={view.id === activeViewId}
          onClick={() => onSelect(view.id)}
        >
          {view.title}
        </button>
      ))}
    </div>
  )
}
