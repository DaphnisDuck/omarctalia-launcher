# Release maintenance

The owner has requested that GitHub version tags be maintained whenever a new version is released.

- Treat `manifest.json` as the version source of truth. Use annotated tags named `v<version>` (for example, `v1.2.1`).
- For a release, update the manifest, README version, and changelog; complete relevant validation before committing.
- Tag the exact release commit and push both the branch and that specific tag to `origin` as part of publishing the version. Verify the remote tag resolves to the intended commit.
- Never move, replace, or delete an existing published tag. Corrections that change released code require a new version.
- Documentation-only maintenance does not require a version bump or a new tag.
- Tags describe source releases, not marketplace approval. Track marketplace verification separately.

See RELEASES.md for the tagging convention and historical baseline.
