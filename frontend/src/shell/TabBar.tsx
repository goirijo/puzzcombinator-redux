// The top tab bar: one button per open *tab*. A tab is a window showing a *view* (a drawing
// of a graph); its label is the view's title. Switching the active tab switches what the
// viewport draws. Driven entirely by the workspace state handed down from the shell.
//
// Browser-like behaviour: a persistent "+" opens a new tab, each tab has a "×" to close it
// (hidden when only one remains — a workspace always keeps one tab), and hovering a tab
// previews it (the shell reverts on mouse-out). Tabs size in CSS (fixed width, shrinking
// uniformly when they crowd) — see `.tab-bar__*` in shell.css.
//
// Closing-freeze: while you close tabs, the row's widths are pinned to their current pixel
// size (the `data-frozen` flag + `--tab-frozen-width`), so the *next* tab's × slides under
// the cursor instead of the row resizing mid-click. The freeze releases when the pointer
// leaves the bar (mouse-out), exactly like a browser's tab strip.

import { useState, type CSSProperties, type MouseEvent } from 'react'

import type { TabDTO, ViewDTO } from '../model/workspace'

interface TabBarProps {
  tabs: TabDTO[]
  views: Record<string, ViewDTO>
  activeTabId: string | null
  onSelect: (tabId: string) => void
  onCreate: () => void
  onClose: (tabId: string) => void
  /** Preview a tab while hovering it (pass null on mouse-out to revert). */
  onPreview: (tabId: string | null) => void
}

export function TabBar({
  tabs,
  views,
  activeTabId,
  onSelect,
  onCreate,
  onClose,
  onPreview,
}: TabBarProps) {
  const closable = tabs.length > 1 // never close the last tab
  // The pinned tab width while closing, or null when the row is free to resize.
  const [frozenWidth, setFrozenWidth] = useState<number | null>(null)

  function handleClose(tabId: string, e: MouseEvent<HTMLButtonElement>) {
    e.stopPropagation() // don't let the close click also select the tab underneath it
    // Pin the current width on the first close of this pass so the row doesn't reflow.
    if (frozenWidth === null) {
      const tab = e.currentTarget.closest('.tab-bar__tab')
      if (tab) setFrozenWidth(tab.getBoundingClientRect().width)
    }
    onClose(tabId)
  }

  // Leaving the bar ends both the closing-freeze (resize now) and any hover-preview.
  function handleBarLeave() {
    setFrozenWidth(null)
    onPreview(null)
  }

  const style =
    frozenWidth !== null ? ({ '--tab-frozen-width': `${frozenWidth}px` } as CSSProperties) : undefined

  return (
    <div
      className="tab-bar"
      role="tablist"
      data-frozen={frozenWidth !== null}
      style={style}
      onMouseLeave={handleBarLeave}
    >
      {tabs.map((tab) => (
        <div
          key={tab.id}
          className="tab-bar__tab"
          data-active={tab.id === activeTabId}
          onMouseEnter={() => onPreview(tab.id)}
        >
          <button
            type="button"
            className="tab-bar__label"
            role="tab"
            aria-selected={tab.id === activeTabId}
            onClick={() => onSelect(tab.id)}
          >
            {views[tab.view]?.title ?? tab.view}
          </button>
          {closable && (
            <button
              type="button"
              className="tab-bar__close"
              aria-label="Close tab"
              title="Close tab"
              onClick={(e) => handleClose(tab.id, e)}
            >
              ×
            </button>
          )}
        </div>
      ))}
      <button
        type="button"
        className="tab-bar__new"
        aria-label="New tab"
        title="New tab"
        // The + isn't a tab, so reaching it ends any tab hover-preview.
        onMouseEnter={() => onPreview(null)}
        onClick={onCreate}
      >
        +
      </button>
    </div>
  )
}
