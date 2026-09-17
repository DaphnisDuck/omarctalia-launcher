# Release tags

Every released manifest version receives an annotated Git tag named `v<version>`, pushed to GitHub. Tags identify immutable source snapshots; they do not imply Omarchy marketplace approval.

## Publishing a new version

1. Update `manifest.json`, the README version, and CHANGELOG.md.
2. Run the checks appropriate to the changes, including the launcher tests and Omarchy manifest validation for code releases.
3. Commit the tested release changes.
4. Create an annotated `v<version>` tag on that exact commit.
5. Push the branch and that specific tag to `origin`, then verify the remote tag's commit.

Never move a published tag. Use a new version for corrections to released code. Documentation-only changes can follow a release without moving its tag.

## Historical tags

| Tag | Commit |
| --- | --- |
| v1.0.0 | 7b4acb1 |
| v1.1.0 | c62d429 |
| v1.1.1 | 828e696 |
| v1.1.2 | 944d523 |
| v1.1.3 | 9c1bf0c |
| v1.2.0 | 11575db |
| v1.2.1 | 20940af |

The original local v1.0.0 tag was preserved. Later README, licensing, and screenshot additions are not retroactively included in that snapshot. Historical tags record earlier states and do not incorporate subsequent fixes.
