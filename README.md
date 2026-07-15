# claude-skills

Personal Claude Code / Cowork plugin marketplace. `marketplace.json` at this root lists each
plugin below by path — add new, unrelated plugins as sibling folders with their own
`.claude-plugin/plugin.json`, and add an entry for them to `marketplace.json`. Don't mix
unrelated skills into an existing plugin folder.

## Plugins

- **[FAIR-science](./FAIR-science)** — reproducible/FAIR data-analysis tooling for computational
  biology (setup-repo, env-audit, reproduce, fair-audit).

## Install a plugin from this marketplace

```
/plugin marketplace add mschechter/claude-skills
/plugin install FAIR-science
```
