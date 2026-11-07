# OmenDB-Releases

Published OmenDB distribution bundles for OmenBuilder. This repo holds no source: its GitHub
Releases hold the bundles, and two files route apps to them. Content updates are published by the
maintainer.

## Files

- **`channels/stable.json`**: the channel index apps fetch. One entry per compatibility key
  `(epoch, schemaVersion, resourceModelRevision, mechanicsContractDigest)`, pointing at the newest
  release's `manifest.json`, with its content hash, archive commit and store SHA-256. Apps accept
  only an exact key match. The channel can hold entries for several keys and several epochs at
  once: an app reads only the entry whose key matches its own and ignores entries for another
  epoch, and an app that finds only a newer key is told to update the app.
- **`omendb-contracts.json`**: the contracts still supported. Each entry names the contract
  digest and the commit that produces it: a bundle for a contract is built with that commit's
  `omendb-build`. Delete an entry to retire an app build's contract. Every digest in
  `channels/stable.json` has an entry here.

### Contracts

`omenBuilderRev` is a commit of the private workspace repository, built from its builder directory.
The three oldest entries (`ecf6a693`, `3d4b99bb`, `3d1d4738`) are commits of the retired builder
repository and don't exist in the workspace repository. Releases don't rebuild them; their channel
entries keep the last release built. To rebuild one, check out that commit from the archived builder
repository by hand, with the sibling checkouts its own workspace lock names, and run its
`omendb-build` the way the runbook describes. The next contract added is always a commit of the workspace repository.

## Releases

A release is tagged `omendb/<contract8>/<archive-date>-<content8>` and holds:

| Asset | Contents |
|---|---|
| `omendb-<contract8>-<content8>.store` | The compacted SQLite store |
| `manifest.json` | Compatibility key, archive provenance, counts, the store's SHA-256 and size |
| `LICENSE.md` | OmenArchive's license notices (ORC) |
| `records.txt` | Every record's identity path, used for "removed records" in the next release's notes |

The release notes list the count changes and the records removed since the previous release of
the same contract. Saved characters that used removed records lose those selections.

## Publishing

The maintainer builds and publishes releases by hand, with the monorepo's `omen-dev omendb-release`
commands (`check-bundle`, `tag`, `notes`, `update-channel`, `prune`); there is no Python here and no
hosted CI. Builds run on macOS (SwiftData), from a clean archive only. Nothing is published unless
every build succeeds. `prune` drops channel entries for contracts no longer listed, keeping the
newest three; the maintainer then deletes those contracts' releases.

Apps read the channel from
`https://raw.githubusercontent.com/phynics/OmenDB-Releases/main/channels/stable.json`.
