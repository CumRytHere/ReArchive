meta:
  id: tier0
  title: ReArchive synthetic tier-0 waveform (format v1)
  file-extension: bin
  endian: le
  license: CC0-1.0
doc: |
  Tier-0 synthetic format, as defined in docs/STATUS.md "Tier-0 format v1".
  48-byte header, then sample_count signed 16-bit little-endian raw codes.
  Structure only: gain/offset scaling and the meaning of unit_code live in
  tier0.rearchive.yaml and in claims, never here.
seq:
  - id: magic
    contents: "RAT0"
  - id: version
    type: u2
    valid: 1
  - id: unit_code
    type: u2
    doc: Vendor unit code. Its meaning is NOT derivable from the file.
  - id: sample_count
    type: u4
    valid:
      min: 1
      max: 1048576
  - id: sample_interval
    type: f8
  - id: gain
    type: f8
  - id: offset
    type: f8
  - id: crc32
    type: u4
    doc: zlib CRC-32 of the raw sample block.
  - id: reserved
    contents: [0, 0, 0, 0, 0, 0, 0, 0]
  - id: samples_raw
    size: sample_count * 2
    doc: Raw sample block; decoded by the sidecar's `view` op, never element by element here.
