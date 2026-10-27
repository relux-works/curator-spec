# Profile command PATH companion records

Unreleased JSON Schema Draft 2020-12 allocation for the
[native-first companion](../../protocol/profile-command-path.md):

- `root-receipt.schema.json`: closed `profile-command-root/1`, stored at
  `.curator-profile-command-root.json` in an active root. Binds the complete
  lock and plan to a generation, root identity and complete export/shim chains.
- `launcher-state.schema.json`: closed `launcher-path-state/1`, stored per
  native launch under `${XDG_STATE_HOME}/swarma/launcher/`. Distinguishes active,
  no-export and explicitly empty command availability, records effective PATH,
  exact fragment/receipt digests, binding and admission decisions.

Identifiers preserve the existing common identifier grammar with explicit
control-character rejection. Paths are absolute and have no parent segment.
Mode is the native POSIX permission/special-bit integer; identity values are
lossless native device/inode or volume/file strings. Windows metadata uses an
owner SID and exact native security-descriptor digest. Native access and
identity verification, command order/completeness, confinement, chain targets,
digests and PATH serialization require the published semantic procedure;
schema validity supplies no authority. POSIX symlink permission bits are not
file mutation authority: verify owner, identity and the protected parent.

Empty availability is an explicit null root/receipt decision, not a root
receipt with zero exports or an empty PATH component. These files allocate
neither a full-fragment revision nor `launch-delegated/2`. Old hosted carriers
stay closed. Independent native/hosted qualification remains required.

Run `python3 -B -m unittest discover -s tools -p 'test_profile_command_path.py' -v`
for the [closed paired corpus](../../conformance/profile-command-path/README.md).
`make validate` discovers it. Logs go in `.temp/`; no launcher executes here.
