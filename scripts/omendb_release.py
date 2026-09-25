#!/usr/bin/env python3
"""Release tooling for OmenDB distribution bundles (ticket 0099, proposal F).

Subcommands:
  check-bundle  <bundle-dir>                      fail unless the bundle is complete and clean
  tag           <bundle-dir> --archive-date DATE  print the release tag for a bundle
  notes         <bundle-dir> [--previous DIR]     print release notes (counts diff, removed records)
  update-channel <channel.json> <manifest.json> --manifest-url URL
                                                  point the bundle's compatibility key at URL
  prune         <contracts.json> <channel.json> [--keep N]
                                                  drop channel entries for unsupported contracts,
                                                  keeping the newest N extra (default 3)

Only the standard library is used, so it runs on a stock macOS runner.
"""
import argparse
import hashlib
import json
import pathlib
import sys

CHANNEL_FORMAT = 1


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def dump(path, value):
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    pathlib.Path(path).write_text(text, encoding="utf-8")


def compatibility_key(manifest):
    return {
        "schemaVersion": manifest["schemaVersion"],
        "resourceModelRevision": manifest["resourceModelRevision"],
        "mechanicsContractDigest": manifest["mechanicsContractDigest"],
    }


def contract8(digest):
    # Matches OmenDBBundleBuilder: the first 8 hex digits of SHA-256 over the digest string.
    return hashlib.sha256(digest.encode("utf-8")).hexdigest()[:8]


def fail(message):
    print(f"omendb_release: {message}", file=sys.stderr)
    sys.exit(1)


def check_bundle(args):
    bundle = pathlib.Path(args.bundle)
    manifest = load(bundle / "manifest.json")
    if manifest.get("formatVersion") != 1:
        fail(f"unsupported manifest formatVersion {manifest.get('formatVersion')}")
    if manifest["archive"]["dirty"]:
        fail("the bundle was built from an archive with uncommitted changes; dirty bundles are never published")
    store = bundle / manifest["store"]["file"]
    data = store.read_bytes()
    if hashlib.sha256(data).hexdigest() != manifest["store"]["sha256"] or len(data) != manifest["store"]["bytes"]:
        fail(f"{store.name} doesn't match the manifest's SHA-256 and size")
    for name in (manifest["licenseNotices"], manifest["recordIndex"]):
        if not (bundle / name).is_file():
            fail(f"the bundle is missing {name}")
    for suffix in ("-wal", "-shm"):
        if (bundle / (store.name + suffix)).exists():
            fail(f"the bundle has a {suffix} file; the store must be a single file")
    print(f"ok {store.name} {manifest['store']['sha256']}")


def tag(args):
    manifest = load(pathlib.Path(args.bundle) / "manifest.json")
    content8 = manifest["archive"]["contentHash"][:8]
    print(f"omendb/{contract8(manifest['mechanicsContractDigest'])}/{args.archive_date}-{content8}")


def notes(args):
    bundle = pathlib.Path(args.bundle)
    manifest = load(bundle / "manifest.json")
    lines = [
        "OmenDB distribution bundle",
        "",
        f"- Archive: `{manifest['archive']['gitSHA']}`, content hash `{manifest['archive']['contentHash']}`",
        f"- Contract: `{manifest['mechanicsContractDigest']}` (schema {manifest['schemaVersion']}, "
        f"resource model {manifest['resourceModelRevision']})",
        f"- Store: `{manifest['store']['file']}`, SHA-256 `{manifest['store']['sha256']}`, {manifest['store']['bytes']} bytes",
        "",
        "| Family | Records | Change |",
        "|---|---|---|",
    ]
    previous = None
    if args.previous:
        previous = load(pathlib.Path(args.previous) / "manifest.json")
    families = sorted(set(manifest["counts"]) | set(previous["counts"] if previous else []))
    for family in families:
        count = manifest["counts"].get(family, 0)
        change = ""
        if previous is not None:
            delta = count - previous["counts"].get(family, 0)
            change = f"{delta:+d}" if delta else ""
        lines.append(f"| {family} | {count} | {change} |")
    unsupported = manifest.get("unsupportedRecords", [])
    if unsupported:
        lines += ["", f"{len(unsupported)} records are imported without rules no translator supports yet."]
    if previous is not None:
        current_paths = set((bundle / manifest["recordIndex"]).read_text(encoding="utf-8").split())
        previous_paths = set((pathlib.Path(args.previous) / previous["recordIndex"]).read_text(encoding="utf-8").split())
        removed = sorted(previous_paths - current_paths)
        added = len(current_paths - previous_paths)
        lines += ["", f"{added} records added, {len(removed)} removed since `{previous['archive']['gitSHA'][:12]}`."]
        if removed:
            lines += ["", "Removed records (saved characters that use them lose those selections):", ""]
            lines += [f"- `{path}`" for path in removed]
    print("\n".join(lines))


def update_channel(args):
    manifest = load(args.manifest)
    if manifest["archive"]["dirty"]:
        fail("refusing to publish a dirty bundle to the channel")
    channel_path = pathlib.Path(args.channel)
    channel = load(channel_path) if channel_path.exists() else {"formatVersion": CHANNEL_FORMAT, "entries": []}
    key = compatibility_key(manifest)
    entry = dict(key)
    entry.update({
        "manifestURL": args.manifest_url,
        "contentHash": manifest["archive"]["contentHash"],
        "archiveGitSHA": manifest["archive"]["gitSHA"],
        "storeSHA256": manifest["store"]["sha256"],
        "builtAt": manifest["builtAt"],
    })
    others = [existing for existing in channel["entries"] if {k: existing[k] for k in key} != key]
    channel["entries"] = sorted(others + [entry], key=lambda item: (
        item["mechanicsContractDigest"], item["schemaVersion"], item["resourceModelRevision"]))
    dump(channel_path, channel)
    print(f"channel: {contract8(manifest['mechanicsContractDigest'])} -> {args.manifest_url}")


def prune(args):
    contracts = load(args.contracts)
    supported = {entry["digest"] for entry in contracts["contracts"]}
    channel = load(args.channel)
    unsupported = [entry for entry in channel["entries"] if entry["mechanicsContractDigest"] not in supported]
    unsupported.sort(key=lambda entry: entry["builtAt"], reverse=True)
    keep = unsupported[: args.keep]
    channel["entries"] = sorted(
        [entry for entry in channel["entries"] if entry["mechanicsContractDigest"] in supported] + keep,
        key=lambda item: (item["mechanicsContractDigest"], item["schemaVersion"], item["resourceModelRevision"]))
    dump(args.channel, channel)
    dropped = len(unsupported) - len(keep)
    print(f"pruned {dropped} channel entries for unsupported contracts, kept {len(keep)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("check-bundle"); command.add_argument("bundle"); command.set_defaults(run=check_bundle)
    command = commands.add_parser("tag"); command.add_argument("bundle"); command.add_argument("--archive-date", required=True)
    command.set_defaults(run=tag)
    command = commands.add_parser("notes"); command.add_argument("bundle"); command.add_argument("--previous")
    command.set_defaults(run=notes)
    command = commands.add_parser("update-channel"); command.add_argument("channel"); command.add_argument("manifest")
    command.add_argument("--manifest-url", required=True); command.set_defaults(run=update_channel)
    command = commands.add_parser("prune"); command.add_argument("contracts"); command.add_argument("channel")
    command.add_argument("--keep", type=int, default=3); command.set_defaults(run=prune)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
