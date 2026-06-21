// The left command rail: one button per registry entry, plus a toggle that collapses the
// rail to a sliver to recover space. A dumb container — it reads the COMMANDS list and
// reports clicks up; it holds no feature logic, only its own collapsed flag.

import { useState } from 'react'

import { COMMANDS, type CommandId } from './commands'

interface CommandRailProps {
  activeCommandId: CommandId | null
  onSelect: (id: CommandId) => void
}

export function CommandRail({ activeCommandId, onSelect }: CommandRailProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <nav className="command-rail" data-collapsed={collapsed}>
      <button
        className="command-rail__toggle"
        onClick={() => setCollapsed((c) => !c)}
        title={collapsed ? 'Expand rail' : 'Collapse rail'}
      >
        {collapsed ? '»' : '«'}
      </button>
      {COMMANDS.map((cmd) => (
        <button
          key={cmd.id}
          className="command-rail__btn"
          data-active={cmd.id === activeCommandId}
          title={cmd.label}
          onClick={() => onSelect(cmd.id)}
        >
          <span className="command-rail__icon">{cmd.icon}</span>
          {!collapsed && <span className="command-rail__label">{cmd.label}</span>}
        </button>
      ))}
    </nav>
  )
}
