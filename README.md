# OmenDB-Releases

To publish a content update, follow the runbook in the omen-project workspace,
`docs/runbooks/omendb-release.md`.

Published OmenDB distribution bundles for OmenBuilder (proposal F, tickets 0098–0102 in the
omen-project workspace). This repo holds no source: its GitHub Releases hold the bundles, and
two files route apps to them.

## Files

- **`channels/stable.json`**: the channel index apps fetch. One entry per compatibility key
  `(schemaVersion, resourceModelRevision, mechanicsContractDigest)`, pointing at the newest
  release's `manifest.json`, with its content hash, archive commit and store SHA-256. Apps accept
  only an exact key match.
- **`omendb-contracts.json`**: the contracts still supported. Each entry names the contract
  digest and the OmenBuilder commit that produces it: a bundle for a contract is built with that
  commit's `omendb-build`. Delete an entry to retire an app build's contract.

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

## Workflows

- **`publish.yml`** builds and publishes. It runs on:
  - `repository_dispatch` `archive-release`, which OmenArchive sends when a release is published
    (payload `archive_ref`). It builds every supported contract from that tag.
  - `repository_dispatch` `app-contract` (payload `omenbuilder_rev`, optional `archive_ref`). It
    builds one OmenBuilder commit from the latest archive release and adds its contract.
  - `workflow_dispatch` with the same inputs.

  Builds run on macOS (SwiftData), from a clean archive only. Nothing is published unless every
  build succeeds.
- **`prune.yml`** runs weekly. It drops channel entries for contracts no longer listed, keeping
  the newest three, and deletes those contracts' releases.

## Setup (owner)

1. Create the GitHub repo `phynics/OmenDB-Releases` and push this directory.
2. Add the secret `OMEN_CI_READ_TOKEN`: read access to OmenBuilder (`phynics/Scribe_Omens`),
   OmenCore, ADUtilities, OmenArchiveKit and OmenArchive.
3. In OmenArchive, add the secret `OMENDB_RELEASES_DISPATCH_TOKEN`, a token that can send
   `repository_dispatch` events to this repo. Its `notify-omendb-releases.yml` workflow uses it.
4. Run `publish.yml` once by hand to publish the first bundle and fill the channel.

Apps read the channel from
`https://raw.githubusercontent.com/phynics/OmenDB-Releases/main/channels/stable.json`.
