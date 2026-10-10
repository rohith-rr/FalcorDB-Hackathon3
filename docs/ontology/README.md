# Viewing the Company Brain ontology in Protégé

Open `company_brain_ontology.owl` with **File → Open**. It contains 41
classes, 58 object properties and 156 data properties. The original file
loads with Protégé 5.6.9's OWLAPI 4.5.29, conforms to OWL 2 DL and passes
HermiT consistency checking with no unsatisfiable named classes.

## Repair the OWLViz layout

Two layout failures were reproduced on this Windows installation:

- The original Dot Application Path pointed to a missing Graphviz executable.
- After installing Graphviz 16.1.0, OWLViz 5.0.3 still failed because it asks
  Graphviz to read and write the same scratch file. Graphviz exits with
  `Permission denied`, but OWLViz ignores the exit code and parses the
  original file, which has no node positions. Nodes then overlap at the
  top-left corner.

The compatibility launcher `owlviz-dot.exe` runs Graphviz with a separate
temporary output file and copies the successful layout back after Graphviz
closes its input. It is already built beside the installed Graphviz binary.
The installed OWLViz renderer and parser were tested with this launcher and
the exact same-file invocation: all 42 nodes received distinct positions and
all 41 hierarchy edges received routes.

In Protégé:

1. Open **File → Preferences → OWLViz**.
2. Set **Dot Application Path** to:

   ```text
   E:\FalcorDB Hackathon\.local\tools\graphviz\Graphviz-16.1.0-win64\bin\owlviz-dot.exe
   ```

3. Apply the preference and restart Protégé to refresh the failed layout.
4. Open the OWL file, enable **Window → Tabs → OWLViz**, and use
   **Asserted hierarchy**.
5. Select **Graph entity** in the class tree and use **Show all classes** in
   the OWLViz toolbar. Hover over toolbar buttons to identify them. Use
   **Zoom out** if the complete hierarchy exceeds the view.

Use **Reasoner → HermiT → Start reasoner** before viewing **Inferred
hierarchy**. The asserted hierarchy does not require a reasoner.

OWLViz visualizes class inheritance. To inspect relationships such as
`HAS_TASK`, `DEPENDS_ON` and `DEPLOYED_TO`, enable **Window → Tabs → OntoGraf**
and expand classes with domain/range object-property relationships enabled.
See the [OWLViz documentation](https://protegewiki.stanford.edu/wiki/OWLViz)
and [OntoGraf documentation](https://protegewiki.stanford.edu/wiki/OntoGraf).

## Rebuild the compatibility launcher

The source is [tools/OwlVizDot.cs](tools/OwlVizDot.cs). From the workspace root,
run this command in Windows PowerShell 5.1 to rebuild the executable:

```powershell
& '.\docs\ontology\tools\Build-OwlVizDot.ps1'
```

For another Graphviz installation, pass `-GraphvizBin` with its `bin` folder.
The launcher must stay beside the real `dot.exe`. Calls such as `-V` and
normal rendering with separate input/output files are forwarded directly.
Failed layouts preserve the original scratch file and return Graphviz's
exit code. Generated temporary output is removed after each invocation.

## Complete hierarchy preview

Open [the SVG](company_brain_hierarchy.svg) in a browser or
[the PNG](company_brain_hierarchy.png) in an image viewer. These previews
contain all 41 named classes plus the implicit `owl:Thing` root. Arrows run
from parent to subclass; blue nodes are structural classes and orange nodes
are incident classes. The previews show inheritance, not graph edge types.

The DOT source is [company_brain_hierarchy.dot](company_brain_hierarchy.dot).
To render it again from the workspace root:

```powershell
& '.\.local\tools\graphviz\Graphviz-16.1.0-win64\bin\dot.exe' -Tsvg '.\docs\ontology\company_brain_hierarchy.dot' -o '.\docs\ontology\company_brain_hierarchy.svg'
```

Graphviz was downloaded from the 64-bit ZIP linked on the
[official download page](https://graphviz.org/download/). Its archive SHA-256
was verified against the published checksum:
`733e49626c492242eb8dca30ea627b6ead20710e207998c7933b4909d92d6abc`.
The runtime and downloaded archive are under `.local/` and stay outside Git.
