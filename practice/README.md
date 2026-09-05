# practice/

One subfolder per build phase. Throwaway scripts/notebooks that isolate a
single technique (e.g. RRF fusion, a chunking algorithm) away from the app's
architecture, so a bug in the technique and a bug in the wiring are never
debugged at the same time. Nothing here needs to be clean — it's scratch work
that gets thrown away once the technique is understood and wired into
`project/`.
