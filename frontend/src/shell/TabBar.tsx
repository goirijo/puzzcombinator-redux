// The top tab bar: one button per open *tab*. A tab is a window showing a *view* (a drawing
// of a graph); its label is the view's title. Switching the active tab switches what the
// viewport draws. Driven entirely by the workspace state handed down from the shell — so
// creating/closing tabs later is a state change there, not a rewire here.

import type { TabDTO, ViewDTO } from '../model/workspace'

interface TabBarProps {
  tabs: TabDTO[]
  views: Record<string, ViewDTO>
  activeTabId: string | null
  onSelect: (tabId: string) => void
}

export function TabBar({ tabs, views, activeTabId, onSelect }: TabBarProps) {
  return (
    <div className="tab-bar" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className="tab-bar__tab"
          role="tab"
          aria-selected={tab.id === activeTabId}
          data-active={tab.id === activeTabId}
          onClick={() => onSelect(tab.id)}
        >
          {views[tab.view]?.title ?? tab.view}
        </button>
      ))}
    </div>
  )
}
