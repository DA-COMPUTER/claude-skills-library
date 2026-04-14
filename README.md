# Claude Skill Library

A community-accessible library of installable skills for [Claude](https://claude.ai) — extending what Claude can do with reusable, shareable `.skill` files.

---

## What Are Skills?

Skills are modular instruction sets that give Claude specialized capabilities. Once installed, a skill is automatically consulted by Claude when relevant — no prompting required. They can encode workflows, domain knowledge, tool usage patterns, and more.

Skills are packaged as `.skill` files and installed directly through Claude's settings.

---

## Installing a Skill

### Option 1 — Using the Skill Installer *(recommended)*

1. Download and install the [`skill-installer`](./skill-installer.skill) skill first.
2. Ask Claude: *"Show me available skills"* or *"Install the [skill-name] skill."*
3. Claude will fetch the skill and present it as a download.
4. Save the `.skill` file and go to **Claude Settings → Skills → Install from file**.

### Option 2 — Manual Download

1. Browse the [skill registry](./registry.json) or this README to find a skill.
2. Download the corresponding `.skill` file directly from this repo.
3. Go to **Claude Settings → Skills → Install from file** and select it.

---

## Available Skills

| Skill | Description |
|-------|-------------|
| `skill-installer` | Browse and install skills from this library directly through Claude. |

*More skills coming soon. Contributions welcome — see below.*

---

## Registry Format

The [`registry.json`](./registry.json) file is the machine-readable index used by the skill installer. Each entry follows this structure:

```json
[
  {
    "name": "skill-name",
    "description": "A short description of what the skill does.",
    "author": "username",
    "version": "1.0.0"
  }
]
```

---

## Contributing

Contributions are welcome. To add a skill to the library:

1. Fork this repository.
2. Add your `.skill` file to the root of the repo.
3. Add an entry for it in `registry.json`.
4. Open a pull request with a brief description of what your skill does.

Please ensure your skill does not contain malicious instructions, prompt injections, or content designed to circumvent Claude's guidelines.

---

## License

This repository is licensed under the [MIT License](./LICENSE). Individual skills may carry their own license terms — check the skill's contents if redistribution matters to you.

---

## Disclaimer

This is an unofficial, community-maintained project. It is not affiliated with or endorsed by Anthropic.
