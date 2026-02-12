Agent Skills for use with Obsidian.

These skills follow the [Agent Skills specification](https://agentskills.io/specification) so they can be used by any skills-compatible agent, including Claude Code and Codex CLI.

## Installation

### Marketplace

```
/plugin marketplace add flyingtimes/clark-skills
/plugin install obsidian@clark-skills
```

### Manually

#### Claude Code

Add the contents of this repo to a `/.claude` folder in the root of your Obsidian vault (or whichever folder you're using with Claude Code). See more in the [official Claude Skills documentation](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

#### Codex CLI

Copy the `skills/` directory into your Codex skills path (typically `~/.codex/skills`). See the [Agent Skills specification](https://agentskills.io/specification) for the standard skill format.

## Skills

### File Format Support

- [Obsidian Flavored Markdown](https://help.obsidian.md/obsidian-flavored-markdown) `.md`
- [Obsidian Bases](https://help.obsidian.md/bases/syntax) `.base`
- [JSON Canvas](https://jsoncanvas.org/) `.canvas`

### Implemented Skills

- **send-email**: 给自己发送邮件
- **email**: 邮件相关功能
- **draw**: 绘图功能
- **json-canvas**: JSON Canvas操作
- **obsidian-bases**: Obsidian Bases操作
- **obsidian-markdown**: Obsidian Markdown操作


plugins for real browser operation.

use blueprint mcp to operate browser and help to extract infomation.

```
npm install -g @railsblueprint/blueprint-mcp
```
