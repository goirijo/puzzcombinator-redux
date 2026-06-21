// The app is just the shell now. All state, I/O, and layout live in <Shell>; this file
// only mounts it. (It used to hold the React Flow canvas directly — that moved into
// shell/Canvas.tsx as one region among several.)

import { Shell } from './shell/Shell'
import './theme.css'

export default function App() {
  return <Shell />
}
