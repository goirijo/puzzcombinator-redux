// The stand-in panel every not-yet-built command opens. It exists so the command rail can
// show the full intended command set today; replacing a command's `Panel` in commands.ts
// with a real component is the whole job of building that feature.

export function PlaceholderPanel() {
  return <p className="panel__placeholder">Not built yet.</p>
}
