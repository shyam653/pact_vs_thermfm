# patches/ — Fixes Applied to Stock Chipyard

## 0001-fix-dead-sbt-antlr4-dependency.patch

**Problem:** chipyard's `project/plugins.sbt` (at commit e602d917, the commit
this work started from) pins `sbt-antlr4` version `0.8.2`. This exact version
was only ever published to Bintray/JCenter, which shut down permanently in
2021. It does not exist on Maven Central, or any mirror of it (including
internal Artifactory mirrors), at any date after 2021. **This is a real,
reproducible bug in stock chipyard as of this commit — not an artifact of
this environment's network/proxy setup.**

Confirmed via direct HTTP requests to an Artifactory Maven Central mirror:
- `sbt-antlr4-0.8.2.jar` / `.pom` → 404 Not Found
- `sbt-antlr4-0.8.1.jar` / `.pom` → 404 Not Found
- `sbt-antlr4-0.8.3.jar` / `.pom` → 200 OK

**Fix:** bump to `0.8.3`, the next available published version. This is a
patch-level bump of a Chisel-side ANTLR grammar-parsing plugin (used by one
specific tool subproject, not core RTL) — verified compatible, no further
build issues after applying.

**To apply:** `git apply 0001-fix-dead-sbt-antlr4-dependency.patch` from the
chipyard repo root, or manually edit `project/plugins.sbt` as shown in the
diff.

**Upstream status:** not yet reported/fixed upstream as of this writing —
worth filing an issue against ucb-bar/chipyard if this hasn't already been
addressed by the time you read this (check current `project/plugins.sbt` on
the `main` branch first; it may have moved on already).

## sbt-repositories-override.txt

**Not a code patch** — this is a config file that must be placed at
`<chipyard-checkout>/.sbt/repositories` (note: inside the chipyard checkout
itself, NOT your `$HOME/.sbt/` — chipyard's build system points sbt's global
base directly at `<chipyard_dir>/.sbt`, see docs/CHIPYARD_SOC_BUILD_REFERENCE.txt
section 4.4c for why this distinction matters).

**Purpose:** redirects sbt's dependency resolution away from the public
Maven Central / Sonatype / Typesafe / scala-sbt.org repos (all blocked by
the TI corporate proxy with a 403 "DataCenterBlock" — not a cert issue, a
policy block with no client-side fix) and toward this organization's own
internal Artifactory instance, which mirrors Maven Central and IS reachable.

**Before using this file elsewhere:** the repo URLs
(`https://artifactory.itg.ti.com/artifactory/maven-central/` and
`.../plugins-release/`) are specific to this TI corporate network. If
reproducing this build on a different network/organization, first check
`<your-artifactory>/api/repositories` for the equivalent internal mirror
of Maven Central, and substitute the URL accordingly. If your network has
no such restriction at all (i.e. repo1.maven.org is directly reachable),
you likely don't need this file at all — try without it first.

**Companion requirement:** this only works together with a custom Java
truststore that trusts your proxy's injected TLS certificate chain (if your
proxy does TLS interception like TI's does) AND the JVM system properties
`-Dsbt.override.build.repos=true -Dsbt.repository.config=<path-to-this-file>`
passed via `JAVA_TOOL_OPTIONS` on every sbt/java invocation. See
docs/CHIPYARD_SOC_BUILD_REFERENCE.txt section 4.4 for the full cert-chain
capture and truststore-building steps.
