// The TESTING rail command: a scratch playground for in-progress editor features. It is NOT
// part of the command design — it exists to force each new feature to be a self-contained
// <Section> that subscribes to the stores it needs, so once a feature settles it can be lifted
// wholesale into its real command (EDIT, …) with no rewiring. Deliberately clunky: bare
// buttons, no polish yet.

import { ArtifactCreateSection } from './ArtifactCreateSection'
import { NodeCreateSection } from './NodeCreateSection'

export function TestingPanel() {
  return (
    <div className="testing-panel">
      <NodeCreateSection />
      <ArtifactCreateSection />
    </div>
  )
}
