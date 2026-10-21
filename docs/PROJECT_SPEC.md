# ReArchive
## Definitive Project Description and Master Product Specification

**Project category:** AI-assisted legacy data recovery, deterministic decoding, verified migration, and digital preservation  
**Product form:** Evidence-first migration workbench with a reusable decoding engine  
**Initial technical focus:** Unknown binary-format recovery using a private synthetic format and a real waveform-format benchmark  
**Initial delivery model:** Local-first, offline-capable application with isolated processing workers  
**Primary design principle:** AI proposes interpretations; deterministic tests and independent evidence determine what can be trusted.

---

# 1. Executive definition

ReArchive is a software platform for recovering, interpreting, validating, and migrating data trapped in obsolete, proprietary, undocumented, or partially understood file formats.

Organizations frequently retain valuable historical data long after the software required to interpret it has become unavailable, unsupported, unlicensed, or incompatible with current systems. The files themselves may still exist, but their structure, encoding, metadata, units, timestamps, relationships, or original application behavior may no longer be understood.

Conventional data migration generally assumes that the source format is known and that a suitable parser or converter exists. ReArchive addresses the earlier and more difficult problem: what happens when the format, its semantics, or the correctness of an existing conversion cannot be trusted?

The platform combines AI-assisted reverse engineering with deterministic decoding, explicit evidence provenance, independent validation, resumable batch processing, and portable verification reports. Its purpose is not simply to produce a readable file. It is to establish, to the extent the available evidence permits, **what was recovered, how it was interpreted, which claims are supported, what was lost, and what remains unknown**.

ReArchive treats migration as an auditable engineering process rather than a one-off conversion command.

Its central workflow is:

1. Inventory and fingerprint an archive without changing the original data.
2. Identify known formats and group files that appear to share an unknown structure.
3. Investigate candidate structures using byte-level evidence and representative files.
4. Use an AI recovery agent to propose format hypotheses and declarative decoding specifications.
5. Compile and execute deterministic decoders in a controlled environment.
6. Evaluate the results against independent oracles, assertions, and reference evidence.
7. Record each interpretation, test, limitation, and decision in a provenance ledger.
8. Convert validated data into a defined open representation while preserving the original files.
9. Process large archives incrementally and resume interrupted jobs safely.
10. Export a self-verifiable evidence package showing both successful recovery and unresolved information.

ReArchive does not promise that every unknown file can be completely reconstructed. Some file structures are ambiguous; some semantic information exists only in external documentation or human knowledge; some formats contain irreversible compression or missing data; and some archives have no independent reference against which correctness can be established.

The platform must recognize those situations explicitly instead of inventing certainty.

**The product's differentiator is evidence-backed recovery, not AI-generated parsers alone.**

---

# 2. The problem ReArchive solves

## 2.1 Data survives longer than the software that created it

An organization may retain decades of scientific measurements, industrial process history, instrument captures, engineering records, telemetry, calibration results, technical documentation, or administrative data.

The original data may be stored in binary files, directory structures, proprietary project databases, instrument-specific archives, or files whose extensions no longer identify their internal structure.

Several circumstances can make that information inaccessible:

- The original application has reached end of life.
- The vendor no longer supports the software or hardware.
- License servers or activation mechanisms no longer function.
- The operating system or hardware required to run the application is unavailable.
- The organization lacks sufficient documentation for the file format.
- An existing parser supports only some versions or features.
- The available conversion preserves visible values but loses metadata or semantic information.
- The original system remains operational, but retaining it is expensive, insecure, or operationally inconvenient.
- An audit, modernization project, investigation, or system replacement requires data in a contemporary format.

These are distinct situations. ReArchive must not treat all of them as the same technical problem.

A file that is merely difficult to open is different from one whose binary structure is unknown. A file that can be decoded but whose units are unknown is different from one that has suffered irreversible information loss. A known format with an incomplete open parser is different from a proprietary format for which no usable reference implementation exists.

The first task is therefore to classify the obstacle.

## 2.2 Conventional conversion does not automatically establish correctness

A converter can produce output without establishing that the output is correct.

For example, a decoder may reconstruct a waveform but apply the wrong gain. The resulting plot may look convincing even though its numerical amplitude is incorrect.

Other examples include:

- Reading a signed integer as unsigned.
- Misinterpreting a three-byte value.
- Shifting a timestamp axis.
- Confusing relative ticks with absolute timestamps.
- Losing quality flags or calibration parameters.
- Mapping an unknown unit code to the wrong physical unit.
- Dropping a segment while reporting successful completion.
- Converting an original lossy recording into a modern representation without documenting the information already lost in the source.

The problem is not necessarily that the conversion fails visibly. The more dangerous case is that it succeeds convincingly while silently changing meaning.

ReArchive therefore separates decoding from validation. Its output is not considered trustworthy merely because it parses, renders, or resembles a reference plot.

## 2.3 Existing parsers and legacy vendors remain competitors

ReArchive should not assume that every legacy format needs to be reverse-engineered.

The practical alternatives include:

- Keeping the old machine and application running.
- Paying the original vendor or a specialist migration provider.
- Using an existing open-source or commercial converter.
- Exporting from the original application.
- Reconstructing selected records manually.
- Leaving the archive inaccessible.

Sometimes the correct decision is to use an existing, sufficiently reliable tool. ReArchive should be able to identify that situation rather than forcing an unnecessary recovery project.

Its potential value is strongest when the existing options are unavailable, incomplete, too costly, difficult to reproduce, or insufficiently trustworthy for the intended use.

---

# 3. Product thesis and design principles

ReArchive is built around ten principles.

## 3.1 AI proposes; deterministic validation decides

The AI recovery agent is responsible for generating and evaluating hypotheses. It may analyze file differences, identify candidate fields, suggest offsets and encodings, produce declarative specifications, and propose tests.

It is not the authority that determines whether a claim is correct.

Deterministic execution and independent evidence establish the status of the resulting claims. Human review remains available for ambiguous interpretations and changes that extend the decoding language.

## 3.2 Structure and meaning are different

A file may be structurally understood while its semantic interpretation remains unresolved.

For example, the platform may establish that a field is a 64-bit floating-point number and that successive values form a time axis. It may still lack evidence for the epoch, timezone, or physical interpretation of those values.

Every meaningful interpretation must therefore have a stated basis and scope.

## 3.3 Original bytes are immutable

The source archive is the preservation anchor.

ReArchive hashes and inventories input files, retains original relative paths in the protected project manifest, and writes all derived artifacts separately. Decoding, normalization, or export must never silently overwrite source files.

## 3.4 Evidence is a first-class product artifact

The platform stores claims, supporting evidence, tests, oracle versions, assumptions, limitations, reviewer decisions, and artifact identities.

These are not merely logs for developers. They are part of the deliverable.

## 3.5 Correctness must be tested independently

The decoder should not be permitted to validate its own correctness through a circular comparison.

Oracle dependencies, code lineage, shared assumptions, and reference sources must be recorded and reviewed.

## 3.6 Uncertainty must be represented explicitly

A field may be structurally recovered but semantically unresolved. A numerical conversion may be supported by a customer attestation but lack an independent physical reference. Two structural interpretations may remain consistent with the available bytes.

ReArchive should report such distinctions directly.

## 3.7 Determinism is an architectural property

When the inputs, decoder, specification, configuration, and declared runtime conditions are the same, the system should produce reproducible canonical outputs.

Determinism should not depend on the AI service being available during routine decoding or verification.

## 3.8 Migration must be resumable

Large archives should not need to restart from the beginning after a worker fails. Completed work must remain identifiable, incomplete work must remain visible, and output publication must be safe against partial writes and duplicate processing.

## 3.9 Security begins at ingestion

Legacy parsers process untrusted bytes. They must run with resource limits and a small attack surface. Offline operation reduces exposure but does not by itself guarantee security.

## 3.10 Product claims must match demonstrated capabilities

A successful synthetic test is evidence about the synthetic test. A successful real-format benchmark is evidence about the tested format, version, files, and acceptance criteria. Neither automatically demonstrates universal recoverability or commercial demand.

---

# 4. Target customers and commercial positioning

ReArchive is intended for organizations with consequential historical data that needs to remain accessible after the original software environment becomes unavailable or unsuitable.

Four industry groups are initial discovery targets.

## 4.1 Manufacturing and industrial

Potential archives include historical process recordings, data-logger captures, quality records, calibration data, old historian exports, and related batch or event information.

Possible migration triggers include retirement of legacy systems, plant modernization, equipment replacement, warranty investigations, audits, and organizational transitions.

The important acceptance questions are not limited to whether records can be parsed. They include whether values, units, timestamps, quality flags, tag identities, and business totals remain correct within defined tolerances.

## 4.2 Aerospace, defense, and electronics

Potential archives include telemetry, test-station captures, qualification evidence, engineering measurements, legacy design data, and technical records.

These environments may impose strict deployment, access, contractual, or data-handling restrictions. The initial demonstrations must therefore use synthetic or appropriately licensed public data.

ReArchive must not imply that data recovery constitutes flight qualification, certification, compliance, or approval for operational use.

Telemetry recovery and electronic-design recovery are separate domain capabilities. They may share the platform but should not be combined into the first implementation.

## 4.3 Scientific laboratories

Potential archives include instrument measurements, waveforms, spectroscopy, chromatography, experimental metadata, acquisition sequences, methods, and historical result reports.

A laboratory migration may require more than recovering the numerical samples. Method information, units, acquisition settings, sample identity, timestamps, and processing parameters may determine whether historical results can be reproduced or interpreted.

The first laboratory-oriented capability should focus on recoverable raw signals and independently testable numerical properties. Reproduction of complex instrument results should be treated as a subsequent capability with its own acceptance criteria.

## 4.4 Government and public-sector archives

Potential archives include fixed-width records, legacy database exports, registries, case files, land records, technical archives, and records originating from retired administrative systems.

Important concerns include record counts, control totals, character encodings, field layouts, relationships, provenance, documented deletion, and transfer into contemporary preservation or records-management systems.

A correct field decoder alone does not establish legal admissibility, statutory compliance, or completeness of the original institutional record.

## 4.5 What is established and what remains a hypothesis

These four groups are **prospect-discovery targets, not validated markets**.

No conclusion about market size, willingness to pay, or the most attractive initial vertical should be treated as established until conversations and concrete archive assessments supply evidence.

The first industry-specific pack will be chosen only after the prospect qualification gates have been met. The default Unknown pack and core engine support discovery across these industries; they do not replace the need to understand a real customer's actual archive.

---

# 5. The product's three-layer architecture

ReArchive has three conceptual layers: the core platform, the format or industry pack, and the prospect configuration.

## 5.1 Layer A — Core platform

The core contains capabilities that should be reusable regardless of industry or file family:

- Project and archive management.
- File inventory, manifests, hashing, and immutable input storage.
- Signature detection and unknown-format clustering.
- Byte-level inspection and structural analysis.
- Versioned decoder contracts.
- Declarative specification handling.
- Sandboxed deterministic decoding.
- Claims and evidence provenance.
- Independent validation and oracle integration.
- Mutation testing and regression testing.
- Canonical output generation and content-addressed artifacts.
- Durable job states, checkpoints, and resumability.
- Audit events and deterministic ledger replay.
- Fidelity reporting and explicit unresolved-data accounting.
- Evidence-package generation and offline verification.
- A replaceable AI recovery-agent interface.
- Offline archive triage.

The core should be implemented as a modular application with isolated worker processes. A single database and local artifact store are sufficient for the initial prototype.

## 5.2 Layer B — Format or industry pack

A pack defines the domain-specific information needed to recover and verify a particular family of data.

It includes:

- Supported format identifiers and variants.
- Decoder primitives or plugins.
- Format specifications and version mappings.
- Synthetic archive generation where applicable.
- Hidden ground truth for generated fixtures.
- Independent oracle definitions.
- Domain-specific assertions.
- Mutation operators and expected detection behavior.
- Report terminology and domain-specific sections.
- Data-handling requirements.
- A demonstration narrative.

The Unknown pack is the first reference pack and forms the initial technical benchmark. It is centered on binary waveform-like data and a private synthetic format.

Industry packs are extensions to the same core, not separate products with separate ingestion, audit, validation, and batch systems.

## 5.3 Layer C — Prospect configuration

Prospect configuration defines requirements particular to the customer and project, including:

- Archive selection and migration scope.
- Acceptance criteria.
- Numerical tolerances.
- Required metadata.
- Expected output representation.
- Reference files or legacy reports.
- Deployment and network restrictions.
- Data-residency constraints.
- Permitted processing methods.
- Required review or approval steps.

These settings must not be hard-coded into the general platform or confused with format semantics.

A pack can specify what it knows how to interpret; a prospect configuration determines what that particular migration must establish and preserve.

---

# 6. The end-to-end application workflow

## Stage 1 — Project definition

The user creates a migration project, records the intended objective, chooses the relevant pack or Unknown workflow, identifies data-handling restrictions, and defines what a successful migration would mean.

Unknown fields should remain explicitly unknown rather than being filled with guessed defaults.

## Stage 2 — Ingestion and source inventory

The application walks the selected input scope and creates a manifest of the original files.

Each manifest entry includes, as applicable:

- Stable file identifier.
- Original relative path.
- File size and content hash.
- Detected signature and extension.
- Known or candidate format and version.
- Structural observations.
- Duplicate-content relationships.
- Processing state.
- Warnings and diagnostics.

Identical files are identified but not silently removed. Malformed, truncated, empty, and unknown files remain represented in the inventory.

## Stage 3 — Triage and clustering

The platform groups files based on observable characteristics: signatures, recurring headers, apparent layouts, lengths, section patterns, and similarities across files.

The result is a set of candidate format families and variants, each accompanied by the observations that support the grouping.

An unknown format must not be declared identified just because its files share a recognizable pattern.

## Stage 4 — Format investigation

The user or recovery agent inspects the bytes through a structured investigation workspace.

Available tools should include:

- Hex and byte-offset views.
- Decoded-text views where meaningful.
- Candidate field boundaries and offsets.
- File-to-file differences.
- Byte coverage maps.
- Entropy and repeated-pattern summaries.
- Candidate numeric interpretations.
- Sample arrays and signal views where appropriate.
- Version and layout comparisons.

The objective is to turn raw bytes into explicit, testable hypotheses.

## Stage 5 — AI-assisted hypothesis generation

The recovery agent receives a controlled set of files, analysis outputs, prior decoder capabilities, and task constraints.

It may suggest:

- Header fields and section boundaries.
- Field widths and numeric encodings.
- Endianness and signedness.
- Counts, offsets, and nested sections.
- Scaling and offset relationships.
- Sample and channel layouts.
- Repeated structures or transformations.
- Metadata mappings.
- Tests that distinguish competing hypotheses.
- Minimal extensions to the declarative language.

The agent does not receive hidden ground truth during blind-recovery experiments and cannot promote a hypothesis to verified status merely because its proposed decoder runs successfully.

## Stage 6 — Specification review and compilation

Candidate structures are represented in a constrained declarative format specification.

The system validates the specification, identifies structural problems, and compiles it into an approved decoding plan or executable decoder.

Invalid specifications must fail early. The platform should reject out-of-bounds offsets, overlapping fields where overlap is not explicitly allowed, invalid counts, unsupported operations, and other statically detectable inconsistencies.

New decoding operations require review and contract tests rather than unrestricted execution of AI-generated code.

## Stage 7 — Deterministic decoding

The decoder transforms source bytes into a canonical representation.

Conceptually, the contract is:

`(source bytes, specification, configuration) → (records, claims, diagnostics)`

Decoding is deterministic and isolated. It does not use network access, the wall clock, or randomness to determine output.

The result includes parsed records, raw and derived values, provenance mappings, structural coverage, warnings, and unresolved content.

## Stage 8 — Independent validation

The validation subsystem evaluates the output under the specified acceptance policy.

It can use:

- Hidden synthetic ground truth.
- Independent analytical calculations.
- Reference implementations.
- Known calibration stimuli.
- Structural and numeric assertions.
- Cross-file invariants.
- Legacy reports or business reconciliation.
- Metadata completeness checks.
- Destination-format integrity checks.

Every claim is evaluated against the evidence appropriate to its type. A plausibility check does not count as proof of semantic correctness.

## Stage 9 — Claims and evidence review

The user can inspect each important interpretation, its evidence, its tests, its limitations, and its version history.

Conflicting evidence is retained as a conflict. Missing evidence remains missing. A human attestation is recorded with its author, time, basis, and scope rather than being represented as an independent measurement.

## Stage 10 — Export and preservation

Validated data is converted into the selected open representation. Source files remain immutable, and derived outputs are stored separately.

The export records which fields were preserved, transformed, omitted, approximated, or left unresolved.

Where the original data already contains loss, the output report must distinguish that source limitation from loss introduced by the migration.

## Stage 11 — Evidence-package generation

The application builds a portable package containing the source and output manifests, specification and decoder identities, validation results, provenance ledger, unresolved claims, limitations, and verification instructions.

The recipient can use the supplied verification tool to check package integrity and replay supported deterministic checks without relying on the original application interface.

---

# 7. The evidence model: the intellectual center of ReArchive

The claims and evidence model determines what the product is able to say about a migration.

## 7.1 Claims

A claim is an explicit statement about a source file, decoded structure, value, interpretation, or migration outcome.

Examples include:

- Bytes 16–17 represent a signed sample count.
- A field contains 2,048 sample values.
- Sample values are scaled linearly by a coefficient and offset.
- A decoded waveform matches a known amplitude within tolerance.
- A timestamp field represents relative ticks.
- A unit code maps to volts under a specified reference.
- All supported records were exported.
- A particular field could not be recovered.

Each claim should carry a stable identifier, its scope, its status, the applicable evidence, the supporting tests, and relevant limitations.

## 7.2 Claim status is separate from evidence basis

The status of a claim should not be conflated with where its evidence came from.

Recommended claim statuses are:

- `candidate`
- `supported`
- `disputed`
- `contradicted`
- `unresolved`

Evidence bases should be recorded independently, for example:

- Byte-level structural evidence.
- Hidden synthetic ground truth.
- Independent analytical oracle.
- Independent implementation.
- Vendor documentation.
- Customer or operator attestation.
- Business or physical reconciliation.
- Plausibility check.
- Self-consistency or round-trip comparison.

The schema should also record applicability scope, assumptions, tolerances, limitations, provenance, and any human review.

A claim may be supported by an attestation without being independently verified. A claim may be structurally supported while its semantic interpretation remains unresolved. A claim can be disputed after having been previously supported.

## 7.3 Evidence quality and independence

Evidence items must declare their dependencies.

Dependencies can include generator code, helper functions, reference implementation lineage, shared assumptions, calibration sources, vendor documents, and tolerance policies.

The system must identify when apparently separate checks rely on the same underlying interpretation or calculation.

For example, a waveform generated using a particular scaling function, a report created from that waveform, and an assertion that reuses the same function do not provide three independent confirmations of the scale.

At the same time, two independent readers may legitimately analyze the same input file. Sharing the test subject does not automatically make their implementations dependent.

The independence analysis must therefore distinguish shared inputs from shared interpretations and shared implementations.

Evidence counts should be presented under explicit policies. They must not be treated as a mathematical proof of truth.

## 7.4 Hidden ground truth

The private synthetic format includes a ground-truth sidecar containing known field layouts, values, units where explicitly defined, checksums, and expected outcomes.

The recovery agent must not access this sidecar during blind trials.

The validator may access the reference only through a defined oracle interface that returns the necessary comparison results without exposing the full hidden specification to the agent.

This arrangement allows objective measurement of recovery performance without turning the experiment into a test of how well the model reads its answer key.

## 7.5 Semantic anchoring

A semantic interpretation requires appropriate external evidence when it cannot be established from the bytes themselves.

For example:

- A known calibration input can support a physical amplitude interpretation.
- A companion log can help establish timing relationships.
- Instrument documentation can establish what a documented field is intended to mean.
- A customer attestation can identify a unit mapping within a declared scope.
- A reference measurement can independently check a numerical scale.

The system must record the evidence type and not silently transform an attested interpretation into an independently verified one.

---

# 8. The Unknown reference pack and synthetic-format program

The Unknown pack is the first complete implementation and the primary controlled environment for demonstrating ReArchive's capabilities.

It contains three complementary components: the private synthetic format, analytic calibration fixtures, and a real-format benchmark.

## 8.1 Private synthetic format

The private synthetic format supplies a controlled reverse-engineering problem for which the true interpretation is known but concealed from the recovery agent.

Its release ladder is designed to isolate capabilities rather than introduce every difficult feature simultaneously.

### R0 — Basic fixed-layout waveform

R0 contains:

- Little-endian signed 16-bit samples.
- One channel.
- A fixed header.
- Linear scaling using floating-point gain and offset.
- A sample interval.
- A sample count.
- A checksum or other explicitly defined integrity field.

R0 proves the ingestion-to-evidence pipeline and establishes a baseline for structural and numerical recovery.

### R1 — Signed packed int24

R1 introduces a signed three-byte integer representation.

The tests cover signedness, sign extension, byte ordering, and incorrect attempts to interpret the samples as a different width.

The decoder succeeds only when it correctly recovers the integer values and downstream numerical relationships.

### R2 — Delta encoding

R2 introduces a defined delta transform in which an initial value is explicit and later values are reconstructed from a documented encoding relationship.

Tests include incorrect cumulative sums, initial values, overflow handling, and missed block boundaries if those are part of the selected encoding.

The experiment asks whether the recovery process can identify a transformation that is not apparent from direct numeric interpretation.

### R3 — Interleaved channels

R3 introduces two channels stored in an interleaved layout.

The fixtures provide distinct known signals for each channel so that stride errors, channel swaps, and incorrect starting offsets become detectable.

### R4 — Segmented acquisition

R4 introduces multiple segments within a recording.

The decoder must identify segment boundaries, sample counts, ordering, and any supported segment-specific metadata.

Tests establish whether the structure is reconstructed correctly without introducing absolute-time assumptions.

### R5 — Tick-valued timestamps

R5 introduces relative timing information expressed in ticks.

The system should recover available timing fields and supported relative relationships while leaving the physical tick duration or absolute epoch unresolved if no suitable anchor is supplied.

### R6 — TLV metadata parsing

R6 introduces a bounded type-length-value metadata structure.

The feature tests whether the decoder can recover metadata boundaries, lengths, and stored values under a reviewed extension to the specification language.

### R7 — Vendor unit-code interpretation

R7 introduces a unit dictionary and code mappings.

It includes anchored, attested-only, and no-anchor fixtures. The expected behavior differs by evidence condition.

A unit mapping supported by an independent physical stimulus is not equivalent to a mapping supplied only by customer configuration. An unmapped code must remain unresolved rather than being assigned a guessed unit.

### Deferred format features

Further features—such as alternate header byte order, section-offset directories, additional checksums, planar channel layouts, and run-length encoding—belong in a reserve queue.

Each is admitted only through the same release process after the preceding release passes its full regression suite.

The purpose of this program is to test one meaningful capability extension at a time.

## 8.2 Release protocol

Each release follows a controlled sequence:

1. Generate the format specification, test generator, ground truth, and sealed evaluation material independently from the recovery implementation.
2. Freeze and identify the release artifacts.
3. Require the complete earlier-release regression suite to pass.
4. Give the recovery agent the permitted development files and prior decoder capabilities, but not the hidden specification or hidden ground truth.
5. Run the recovery experiment under pre-registered iteration, token, and time budgets.
6. Evaluate the result against held-out files, clean controls, and the specified oracles.
7. Record the result regardless of whether the release succeeds.
8. When a failed experiment leads to changes, retire the exposed evaluation seeds and generate fresh hidden evaluation material.
9. Add reviewed held-out fixtures into the regression corpus after they are revealed.
10. Freeze the passing release before beginning the next one.

The regression corpus must grow rather than shrink.

## 8.3 Specification-language evolution

The initial declarative language supports a deliberately small set of safe operations: fixed-width fields, supported integer and floating-point types, explicit byte order, magic constants, fixed text fields, counted arrays, bounded offsets, and linear scaling.

New capabilities require explicit, reviewed language versions.

For example, if the current specification cannot express int24 or delta decoding, the agent must identify the limitation and propose a minimal extension with a reference implementation, contract tests, and property tests.

The agent is not permitted to bypass the specification language through unrestricted executable code.

## 8.4 Analytic calibration fixtures

The calibration set contains signals with known mathematical properties, generated through code independent of the decoder.

It may include:

- Sine waves with known amplitude, frequency, and offset.
- Square waves with specified duty cycle and transition times.
- Step signals with known rise times and overshoot.
- Chirps with controlled frequency evolution.
- Signals with a defined noise floor.

These fixtures test both the decoder and the estimators used by the validator.

Estimator correctness must be established independently. An incorrectly implemented frequency estimator cannot be trusted simply because it is used to validate a decoder.

---

# 9. Validation and adversarial testing

Validation is a product subsystem rather than a collection of ad hoc assertions.

## 9.1 Seeded mutations

Seeded mutations introduce known errors into otherwise valid decoding logic. Initial classes include:

- Incorrect gain.
- Offset-sign reversal.
- Wrong endianness.
- Signed/unsigned confusion.
- Incorrect sample interval.
- Dropped samples.
- Segment-order errors.
- Missing metadata.
- Checksum or quality-flag handling errors.
- Incorrect unit-code mapping.

Each mutation must have a stated expected failure class and intended detection mechanism.

## 9.2 Held-out mutations

Held-out mutations test whether the validator generalizes beyond faults known to its author.

A separate process generates the evaluation material and does not access the validator implementation or the hidden answers. The validator is frozen before evaluation, and thresholds are recorded in advance.

Results are reported per mutation class and under the declared sampling plan. Any statistical interpretation must reflect the actual design and limitations of that plan.

## 9.3 Clean controls

Clean controls measure false rejection.

They should include legitimate edge cases, all supported release variants, unusual but valid values, and explicitly supported empty or zero-length cases.

A validator that catches every injected error by rejecting every unusual input is not a successful validator.

## 9.4 Fault-injected files

Fault-injected files exercise triage and diagnostics using truncated files, damaged blocks, invalid checksums, trailing bytes, misleading extensions, and other malformed inputs.

The expected outcome is not always a complete rejection. The system may recover a supported portion of a file, but it must identify what was rejected or left unresolved.

## 9.5 Sensitivity analysis

For numerical checks, report the range of errors the oracle can detect under specified signal, quantization, noise, and tolerance conditions.

For example, a gain-error sweep can establish the smallest detectable gain deviation for a particular anchored fixture.

That result should not be presented as a universal detection limit across all formats or data conditions.

## 9.6 Equivalent and surviving mutants

Distinguish:

- Mutations proven equivalent under the defined observable behavior.
- Mutations that are indistinguishable on the existing corpus.
- Mutations detected for the intended reason.
- Mutations that trigger a failure for the wrong reason.
- Mutations that survive without explanation.

A mutant is not proven equivalent merely because the current test set does not distinguish it.

## 9.7 Metamorphic and property-based tests

The system should test invariants that can be checked without knowing every expected output.

Examples include:

- Changing gain and inversely changing raw amplitude preserves a derived value when the specification states that relationship.
- Reversing channel order reverses decoded channel order without changing channel contents.
- Concatenating valid segments preserves expected sample accounting.
- Repeated decoding under identical declared conditions produces identical canonical values.
- A change to a validation policy invalidates validation artifacts without unnecessarily invalidating unchanged decoded output.

Each property must be defined carefully enough to ensure that the transformation and expected relationship are mathematically valid.

## 9.8 Fuzzing and malformed-input security

Decoder plugins and the specification compiler should be tested with malformed inputs and resource exhaustion cases.

The system records crashes, hangs, resource violations, and diagnostic failures. Parsing workers have execution limits, restricted filesystem access, no network access by default, and no permission to modify the original archive.

---

# 10. Determinism, artifacts, and event ledger

## 10.1 Canonical output representation

The platform requires a canonical serialization contract so that semantically identical decoded results have consistent representations.

The contract must define field ordering, numeric encoding, treatment of missing values, timestamps, text encoding, and any floating-point normalization rules that affect reproducibility.

Byte-identical output hashes are a release criterion under specified runtime conditions, not a guarantee that every arbitrary environment will behave identically without controlling dependencies.

## 10.2 Content-addressed artifact identity

Artifacts are addressed using inputs and versions relevant to their creation.

**Ingestion artifacts** use source content hashes.

**Decoded artifacts** incorporate source identity, decoder identity and version, specification hash, canonical configuration, output-schema version, and runtime or dependency-lock identity.

**Validation artifacts** incorporate decoded artifact identity, validator version, oracle set and inputs, tolerance policy, and test-suite version.

**Evidence packages** incorporate the manifest of their included artifacts.

This enables selective recomputation. A new validator should trigger revalidation and repackaging without forcing the decoder to be rerun unnecessarily, provided the decoded artifact remains valid under the new validation contract.

## 10.3 Event-sourced ledger

The ledger is an append-only sequence of events describing ingestion, decoding, validation, decisions, errors, specification changes, and export.

Each event records its sequence, type, payload identity, and previous-event hash.

Per-file statuses and project views are projections of that history. The ledger supports deterministic replay and the reconstruction of how a migration reached its recorded result.

The exported package includes the ledger head hash. Because a hash chain alone does not prevent an actor from rewriting an entire chain, stronger tamper-evidence arrangements can be considered for later deployments, where customer requirements justify them.

## 10.4 Batch state and resumability

Each file has a persistent state machine. A conceptual progression is:

`queued → inspected → decoded → validated → exported`

Additional states include:

- `failed`
- `needs_review`
- `skipped_with_reason`

Completed work can be reused only when the relevant artifact identity matches. Partial artifacts must not be published as complete. A restarted worker must distinguish completed, incomplete, invalidated, and failed work.

The batch engine should support controlled cancellation, checkpointing, retry policies, and failure isolation.

Chaos testing later verifies that randomly interrupted executions preserve the expected job state, output manifest, and ledger consistency.

---

# 11. The offline triage CLI

The triage CLI is a small, data-minimizing utility intended to help potential customers evaluate their archives without sending the underlying files to ReArchive.

It runs locally, without AI or network access, and uses read-only access to the selected directory.

Its functions are to:

- Inventory files and calculate hashes.
- Record sizes, extensions, and known signatures.
- Group files using observable structural similarities.
- Identify supported, potentially unknown, and obviously malformed inputs.
- Produce a complete local report.
- Produce a separately redacted summary for sharing.

The shared summary omits paths and identifiers by default and allows the customer to select which information to disclose. Optional salted hashes may reduce some correlation risks, but they do not guarantee anonymity.

The CLI should not silently upload files, recursively unpack archives by default, or execute arbitrary legacy programs.

Because the tool processes untrusted input, it still needs resource limits, timeouts, restricted behavior, and a minimal dependency footprint.

The triage CLI is not the complete recovery platform. Its purpose is to remove the first practical obstacle to a commercial assessment: understanding the archive well enough to decide what to do next.

---

# 12. The real-format benchmark

The initial real-format benchmark is a documented LeCroy-style `.trc` waveform variant, conditional on a formal feasibility review.

Its purpose is to test the core engine on genuine format data and compare its output against reference evidence.

Before integration, the project must establish:

- The exact supported format variant.
- Access to suitable, legally usable sample files.
- Documentation and implementation availability.
- Reference-reader feature coverage.
- Source lineage of candidate readers.
- Oracle independence and shared assumptions.
- Comparison methodology and tolerances.
- Unsupported features and known ambiguities.

Distinct project names do not establish independent implementation lineage. If the available readers share the same upstream implementation or assumptions, their agreement counts as a single underlying evidence source for the relevant claims.

Analytic calibration oracles can provide additional evidence where appropriate.

The real-format benchmark is not the blind-discovery benchmark. The private synthetic format is the controlled environment for blind trials because it has hidden ground truth and can be designed to prevent prior-format familiarity from determining the result.

A successful LeCroy benchmark demonstrates capability on the tested data and features. It does not demonstrate that LeCroy data is commercially underserved or that ReArchive can decode every legacy waveform format.

---

# 13. Migration outputs, fidelity, and honest reporting

ReArchive should never compress migration quality into a single opaque accuracy score.

The report keeps these dimensions separate.

## 13.1 Structural coverage

Which supported fields, structures, and records were correctly reconstructed?

## 13.2 Value recovery

Which decoded values match ground truth or an applicable reference within the defined tolerance?

## 13.3 Semantic verification

Which interpretations are supported under the stated evidence policy, and what is the evidence basis for each?

## 13.4 Semantic overreach

How often does the system promote semantic interpretations that the available evidence does not justify?

## 13.5 Correct abstention

When the evidence is insufficient or genuinely ambiguous, does the system correctly leave the claim unresolved?

## 13.6 Anchored-claim resolution

When sufficient evidence is available, does the system successfully resolve the interpretation rather than refusing unnecessarily?

## 13.7 False rejection

How frequently are legitimate files or valid data incorrectly rejected?

## 13.8 Reproducibility

Do repeated runs produce the expected identical canonical artifacts under the declared execution conditions?

## 13.9 Batch resilience

Do interrupted runs preserve file accounting, artifact integrity, and ledger consistency?

## 13.10 Security robustness

What crashes, hangs, malformed-input failures, or resource-limit violations are observed?

## 13.11 Generalization and reuse

How well does the recovery workflow perform on unseen files and later format variants, and how much effort does it save on subsequent variants?

## 13.12 Explicit outcome states

A migration or file should receive a transparent outcome, such as:

- `semantically_reconciled`
- `documented_lossy`
- `incomplete`
- `unverified`
- `failed`

The exact outcome follows documented criteria.

A file can be structurally recovered yet remain semantically unverified. A lossy source can be migrated correctly while retaining its source limitations. A byte-identical copy establishes byte preservation, not interpretation correctness.

Unresolved items must appear prominently in the report.

---

# 14. The evidence package

The evidence package is one of ReArchive's principal deliverables.

It should contain, as applicable:

1. Project scope and acceptance criteria.
2. Immutable input manifest and source hashes.
3. File classification and format hypotheses.
4. Specification, decoder, and runtime identities.
5. Claims ledger and provenance information.
6. Test, oracle, and mutation results.
7. Structural and numerical coverage.
8. Semantic anchoring and evidence dependencies.
9. Reference reconciliation outcomes.
10. Documented losses and unresolved items.
11. Failures, exclusions, and warnings.
12. Output manifest and hashes.
13. Ledger history and head hash.
14. Verification instructions and limitations.

Use a documented packaging convention and include a verification CLI that can run offline.

The verifier should distinguish package integrity, deterministic replay, semantic reconciliation, and external reference verification. These are not interchangeable.

A package whose hashes are valid has demonstrated integrity of its packaged bytes. It has not, by that fact alone, proved that a decoded unit or timestamp interpretation is correct.

Where verification depends on proprietary external software, the package should document that dependency and preserve whatever reference outputs can lawfully be included. It must not imply that an external check can be rerun entirely offline unless the required tools and evidence are actually available.

---

# 15. Security and data-handling model

Security is built into the processing architecture rather than deferred to the final interface.

The initial system should:

- Treat all input files as untrusted.
- Preserve source files as immutable inputs.
- Run decoding workers in isolated, no-network-by-default environments.
- Apply CPU, memory, file-size, and execution-time limits.
- Restrict filesystem access to the relevant project artifacts.
- Avoid executing arbitrary embedded content.
- Keep secrets out of logs and reports.
- Separate customer files from any external AI-processing channel.
- Require authorization and an appropriate data-handling arrangement before customer content is sent to an external model.
- Record the deployment and processing profile in the project evidence.
- Provide an offline path for the deterministic decoding and verification workflow.

An air-gapped execution claim is justified only if the complete relevant workflow actually works without network access. The existence of an offline triage CLI alone does not demonstrate that the AI-assisted recovery process works air-gapped.

The first version should demonstrate honest local execution boundaries without building a large enterprise control plane.

---

# 16. The user interface

The interface is an evidence-first migration workbench, not a chatbot with a file-upload button.

It should provide:

### Project overview

Scope, acceptance criteria, data-handling constraints, project state, and major unresolved issues.

### Archive explorer

File manifests, hashes, duplicate relationships, format clusters, anomalies, and file-level processing status.

### Byte and structure inspector

Byte ranges, candidate field boundaries, alternate interpretations, text decoding, and unexplained regions.

### Hypothesis workspace

AI suggestions, their evidence, proposed tests, reviewer decisions, and specification changes.

### Decoder and specification view

The current supported format version, declarative field definitions, compile or lint errors, and version history.

### Validation workspace

Assertions, oracle results, mutation outcomes, reference disagreements, false rejections, and unresolved claims.

### Batch monitoring

File-level progress, checkpoints, failure reasons, retries, and resume history.

### Evidence report

Claim-level traceability, outcome states, reconciliation results, coverage, documented loss, unresolved items, and verification instructions.

Every meaningful statement in the interface should lead to its supporting evidence or identify the absence of such evidence.

The AI agent's suggestions remain visibly provisional until the necessary checks and decisions have occurred.

The interface must not hide important unresolved items behind an aggregate percentage or a visually impressive success indicator.

---

# 17. Demonstration design

The first demonstration should show one complete, credible recovery rather than several shallow industry scenarios.

The seven-beat narrative is:

**1. Triage.** Open a mixed archive and show the inventory, hashes, format clusters, and malformed files.

**2. Recovery.** Show a candidate format structure and an AI-generated decoding hypothesis supported by observable evidence.

**3. Deliberate error.** Introduce a known incorrect gain or another carefully chosen mutation that produces plausible output but fails the designated independent check.

**4. Batch resilience.** Interrupt a running job, restart it, and demonstrate that completed work is safely reused while failed and incomplete items remain explicit.

**5. Evidence export.** Generate the evidence package and show verified claims, unresolved fields, reference disagreements, and documented limitations.

**6. Capability reuse.** Apply the same engine to a new supported variant and measure the effort required to reach the same acceptance criteria.

**7. Prospect archive.** Explain the intake process for a real customer archive and the reference evidence required for a scoped assessment.

The demo should include a no-anchor file where the system refuses to claim an unsupported unit or absolute time origin. That demonstration is important: it shows that the product knows when the evidence is insufficient.

The AI reasoning may be replayed from a recorded run if necessary for reliable timing, but the deterministic decoder, validation results, artifact hashes, and evidence generation shown as live must genuinely execute. Any replayed component must be identified honestly.

---

# 18. Prospect qualification and selection of the first industry pack

ReArchive should pursue only one industry-specific pack after a prospect passes the commercial and deployment gates.

## 18.1 The eight-factor scorecard

Each candidate receives a 0–2 score for each criterion.

**Trigger:** Is there a concrete event making migration necessary?

**Consequence:** What is the operational, financial, scientific, contractual, or preservation impact of leaving the archive inaccessible?

**Ownership:** Who owns the archive and the budget?

**Alternative:** Can the organization retain the old machine, pay the vendor, use an existing converter, or leave the data inaccessible? What does that status quo cost?

**Acceptance:** Who can establish that the recovered information is usable, and what independent reference evidence is available?

**Access:** Can representative files and relevant reference artifacts be supplied under appropriate permission?

**Path:** Is there a plausible route to a paid assessment, migration project, or ongoing service?

**Deployment:** Can the data legally and technically be processed under the customer's constraints?

Scores mean:

- **0:** absent or unknown.
- **1:** plausible but not evidenced.
- **2:** confirmed by a concrete artifact, named owner, or explicit commitment.

Record evidence supporting each score of 2 and review stale assessments after approximately 60 days.

## 18.2 Staged gates

**G1 — Continue discovery.** Requires a credible trigger and a named owner.

**G2 — Perform triage or a scoped assessment.** Requires at least plausible archive access and deployment feasibility, plus explicit permission before operating in the prospect's environment.

**G3 — Commit to the industry-specific pack.** Requires confirmed access, confirmed acceptance criteria and evidence, confirmed deployment feasibility, a credible migration trigger, and a plausible commercial path.

A high score justifies further investigation, not an assumption of willingness to pay.

A paid assessment, approved budget, or concrete procurement step is stronger evidence of demand than positive feedback about a technical demo.

## 18.3 The purpose of the Unknown pack

The Unknown pack is the shared technical foundation used while a prospective customer's format family and migration needs are still being investigated.

The triage CLI should make it easier for prospects to share carefully selected archive summaries without transferring the archive itself. A subsequent assessment can determine whether the required evidence exists and whether the work is commercially justified.

The Unknown pack does not imply that ReArchive can immediately handle arbitrary archives in every industry. It establishes the reusable discovery and recovery workflow from which a targeted pack can be developed.

---

# 19. Implementation plan and release gates

## Phase 0 — Contracts and evidence foundation

**Deliverables:**

- Repository skeleton.
- Core data models.
- Claim and evidence schemas.
- Decoder interface.
- Initial declarative specification language.
- Canonical serialization rules.
- Artifact identities.
- Append-only event ledger and replay.
- Contract-test suite.

**Exit criteria:** Schemas validate, the no-op decoder passes its contract tests, canonicalization rules are tested, and ledger replay works deterministically.

## Phase 1 — R0 end to end

**Deliverables:**

- Private synthetic R0 generator.
- Hidden ground-truth sidecar and oracle interface.
- Deterministic R0 decoder.
- Claims ledger.
- Basic validation.
- Evidence package.
- Offline verification CLI.
- Minimal offline triage CLI.

**Exit criteria:** Structural and anchored numerical results match the defined reference; semantic claims are correctly classified; offline verification succeeds; and canonical output hashes agree across the declared test environments.

## Phase 2 — Validation rigor

**Deliverables:**

- Independent oracle suite.
- Evidence-dependency graph and independence policies.
- Seeded mutations.
- Held-out mutation procedure.
- Clean controls.
- Fault-injected file corpus.
- Sensitivity sweeps.
- False-rejection measurements.

**Exit criteria:** The preregistered tests meet the declared thresholds; the evidence-independence meta-tests work; and results, limitations, and detection classes are recorded.

## Phase 3 — Capability extensions

**Deliverables:**

- R1 through subsequent releases, one at a time.
- Reviewed declarative-language extensions where required.
- Development/test corpus splits.
- Blind recovery trials.
- Measured generalization, reuse, and semantic-overreach results.

**Exit criteria:** Each new release passes the entire previous regression corpus and its own pre-registered entry and exit gates.

## Phase 4 — Batch resilience

**Deliverables:**

- Persistent file states.
- Durable checkpoints.
- Content-addressed memoization.
- Atomic output publication.
- Restart and resume behavior.
- Random interruption and chaos-test suite.

**Exit criteria:** Repeated interrupted runs preserve file accounting, expected output hashes, artifact validity, and ledger consistency.

## Phase 5 — Real-format benchmark

**Deliverables:**

- Completed format feasibility review.
- Approved sample fixtures.
- Reference-reader lineage audit.
- LeCroy-style benchmark integration.
- Analytical and reference reconciliation.

**Exit criteria:** The supported variants and limitations are documented; reconciliation disagreements are visible; and the benchmark does not claim more independence or coverage than the evidence provides.

## Phase 6 — Workbench and demonstration hardening

**Deliverables:**

- Evidence-first UI.
- Report templates.
- Claim-to-evidence navigation.
- Reliable demo orchestration.
- Clean-install testing.
- User-facing limitations and verification instructions.

**Exit criteria:** The entire demo can be repeated without hidden-state repairs, the reported claims are traceable, and the evidence package can be inspected independently.

Prospect discovery runs in parallel from the beginning. The first industry-specific pack remains gated by G3.

---

# 20. Business model and commercial hypotheses

ReArchive's likely initial commercial path is assessment-led rather than a self-serve universal converter.

A possible progression is:

**Archive assessment.** Inventory a defined archive, identify recoverable formats and variants, establish feasible reference evidence, and estimate the effort and expected limitations.

**Verified migration engagement.** Recover the selected format or archive, convert the agreed scope, reconcile results against the customer's acceptance criteria, and deliver the evidence package.

**Ongoing legacy-data continuity.** Where recurring archive creation or multiple legacy systems justify it, maintain reusable format knowledge, versioned decoding specifications, regression suites, and repeatable migration procedures.

This is a proposed commercial model, not validated revenue evidence.

The platform's economics depend on how much effort can be reused across format variants and customer engagements. The project should therefore track the time, AI cost, engineering iterations, and acceptance effort required to extend an existing decoder.

If each archive requires a completely bespoke investigation that cannot be reused, ReArchive may function primarily as a specialist migration service rather than a scalable software platform. That could still be commercially viable, but it would be a different business model.

The project should measure the reuse achieved instead of assuming that a common engine automatically eliminates bespoke work.

---

# 21. Scope boundaries and non-goals

The initial ReArchive prototype is **not** intended to be:

- A universal converter for all historical data formats.
- An AI chatbot that guarantees a readable output for every file.
- A replacement for every existing parser or migration vendor.
- A system that infers all physical units, epochs, and business semantics from bytes alone.
- A complete implementation of four industry packs.
- A multi-tenant enterprise cloud platform.
- A fully distributed microservices system.
- A replacement for customer-specific validation or expert acceptance.
- A source of legal admissibility, regulatory compliance, airworthiness, or certification guarantees.
- A tool for accessing live industrial control systems or bypassing protections on locked or restricted projects.
- A promise that lossy or missing source information can be reconstructed exactly.
- A demonstration that the market is commercially attractive merely because the synthetic benchmark succeeds.

These limitations are deliberate. They protect the credibility of the product and prevent the first prototype from becoming a collection of loosely related features.

---

# 22. The principal technical and commercial risks

## Risk 1 — The system learns the examples rather than the format

**Mitigation:** Separate development and held-out corpora, hide ground truth, seal evaluation files, and measure generalization to new files and supported variants.

## Risk 2 — Correct structure is mistaken for correct semantics

**Mitigation:** Separate claim status, evidence basis, and scope. Include anchored, attested-only, and no-anchor conditions.

## Risk 3 — The validator shares assumptions with the decoder

**Mitigation:** Use independent implementations and analytical oracles where available, track dependency lineage, and test the independence model itself.

## Risk 4 — The mutation suite creates false confidence

**Mitigation:** Use a documented held-out sampling plan, freeze the validator before evaluation, test clean controls, report per-class outcomes, and qualify any statistical claims.

## Risk 5 — The synthetic format becomes a research project in itself

**Mitigation:** Introduce one feature per release, require every prior release to pass its regression suite, and defer unnecessary format complexity.

## Risk 6 — The real-format benchmark is mistaken for market proof

**Mitigation:** Label it as a technical capability benchmark and conduct prospect discovery independently.

## Risk 7 — The system rejects too much or guesses too much

**Mitigation:** Measure false rejection, correct abstention, anchored-claim resolution, and semantic overreach separately.

## Risk 8 — Reproducibility depends on undocumented runtime behavior

**Mitigation:** Pin dependencies, canonicalize configuration and outputs, version validation inputs, and test across declared environments.

## Risk 9 — Batch interruption corrupts provenance or artifacts

**Mitigation:** Use durable states, content-addressed artifacts, atomic publication, deterministic replay, and randomized interruption testing.

## Risk 10 — Customer data cannot legally or safely be accessed

**Mitigation:** Build offline triage, explicit permission gates, data-minimizing reports, isolation, and customer-specific deployment constraints into the workflow.

## Risk 11 — A technically successful prototype has no paying customer

**Mitigation:** Begin discovery immediately, quantify the status quo, require a concrete migration trigger, and commit to an industry pack only when the G3 requirements are met.

---

# 23. Definitive definition of success

The initial prototype is successful when it demonstrates one complete recovery under controlled conditions and one credible real-format reconciliation experiment.

The synthetic recovery must show that:

1. An archive can be ingested and preserved immutably.
2. The recovery agent can analyze permitted development material without accessing hidden ground truth.
3. A deterministic decoder can be derived from a reviewed specification.
4. Correct structural and numerical claims match the known reference.
5. Incorrect but plausible decoding hypotheses are detected by the intended independent checks.
6. Claims that lack necessary semantic anchors remain unresolved.
7. The system reports semantic overreach, false rejection, and correct abstention separately.
8. Repeated runs reproduce canonical outputs under the declared conditions.
9. Interrupted jobs resume without silent loss, duplication, or corruption.
10. The evidence package is internally verifiable and explicitly describes which checks require external references.
11. The complete system has a documented security and data-handling boundary.

The real-format experiment must establish a credible comparison against its supported reference implementations and analytical checks, document shared lineage and unsupported features, and avoid claiming a commercial gap that has not been demonstrated.

Commercial validation is a separate requirement. A paying assessment or a concrete, qualified migration opportunity must eventually establish that the problem matters enough for a customer to act.

---

# 24. Final product statement

ReArchive is an evidence-first platform for recovering data from legacy formats whose interpretation is unknown, incomplete, or no longer dependable.

It uses AI to help discover and formalize the structure of historical files, but places deterministic decoding, independent validation, explicit provenance, and reproducible outputs at the center of the migration process. It preserves original bytes, separates structural recovery from semantic interpretation, records the evidence supporting each claim, and exposes rather than hides unresolved information.

Its core is a reusable recovery and verification engine. Format and industry packs supply domain-specific decoders, data generators, validation oracles, assertions, mutations, and report profiles. Prospect configuration defines the migration's scope, acceptance criteria, tolerances, deployment constraints, and required evidence.

The initial Unknown pack uses a private synthetic binary format with hidden ground truth, a gated release ladder, analytic calibration data, adversarial testing, and a real waveform-format benchmark. An offline triage CLI allows potential customers to assess their archives without automatically transferring the underlying files.

The platform's engineering discipline is built around deterministic execution, content-addressed artifacts, a replayable provenance ledger, independent testing, resumable batch processing, and portable evidence packages. Its reports distinguish verified structure, anchored semantics, attested assumptions, documented loss, and unresolved claims.

The commercial strategy is intentionally narrower than the architecture: qualify a real customer, establish the archive's migration trigger and independent acceptance evidence, verify deployment feasibility, and then build exactly one industry-specific pack around a demonstrable need.

**ReArchive's central promise is not that it can reconstruct everything. It is that it can recover what the evidence supports, prove the extent of that recovery, preserve the distinction between knowledge and assumption, and leave the customer with a result that can be independently examined and reproduced.**