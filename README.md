# FIH Mod Catalog

The list of mods shown in [FIH Mod Manager](https://github.com/d1ll3x3/FIH_ModManager) for
**Flipping is Hard**: the Explore tab and the Speedrun tab. The manager downloads `mods.json` from this
repository on startup, so a mod added here shows up for everyone without a new version of the manager.

## Add your mod

1. Publish a GitHub release of your mod with a `.zip` or a `.dll`. The manager installs the latest
   release; a `.zip` can contain `BepInEx/plugins/...`, `plugins/...` or just the mod's folder.
2. Fork this repository and add an entry to `mods.json`:

```json
{
  "repo": "your-user/YourMod",
  "title": "Your Mod",
  "author": "YourName",
  "category": "cosmetic",
  "icon": "palette",
  "description": {
    "en": "One sentence about what it does (and its key, if it has one).",
    "es": "Optional: the same in other languages."
  }
}
```

3. Open a pull request. A check validates the file and your release; the maintainer reviews and merges it.

### Fields

| Field | Required | What |
|---|---|---|
| `repo` | yes | `owner/name` of the GitHub repository |
| `title` | yes | Name shown on the card |
| `author` | yes | Name shown under the title |
| `category` | yes | `cosmetic`, `graphics`, `practice`, `challenge`, `multiplayer` or `creation` |
| `icon` | yes | `edit`, `timer`, `palette`, `flight`, `person`, `bolt`, `link`, `visibility`, `translate`, `camera`, `chat`, `image`, `lock`, `videocam`, `brush`, `sparkle`, `brightness`, `hook`, `hanger` or `tag` |
| `description` | yes | Text per language: `en` (required), `es`, `fr`, `ru`, `pl`, `ar`, `zh`, `ko`. Missing languages show the English text |
| `explore` | no | `false` hides the mod from Explore (only for mods listed in the Speedrun tab) |
| `speedrun` | no | `{"allowed": true}` or `{"allowed": false}`, with an optional `note` per language. Only speedrun moderators can add or change it |

New categories or icons need a new version of the manager first: open an issue in the manager's repository.

## Speedrun rules

The Speedrun tab splits mods into allowed and not allowed in runs submitted to
[speedrun.com](https://www.speedrun.com/Flipping_Is_Hard). Only the users in
`.github/speedrun-moderators.txt` can add or change the `speedrun` field; the check fails if anyone else
does.

## Check it locally

```
python3 scripts/validate.py
```
