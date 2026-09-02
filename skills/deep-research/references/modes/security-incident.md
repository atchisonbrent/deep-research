# Security incident

## Choose this mode when

The subject is a breach, intrusion, vulnerability disclosure, supply-chain compromise, or outage where technical forensics, attribution, and impact scope dominate. Use `event-assessment` for non-technical events; use `state-of-practice` for how to defend against a class of incident.

## Evidence hierarchy

1. primary technical artifacts: advisories with CVE identifiers, patches and commits, indicators of compromise, published forensic reports with method;
2. first-party disclosures from the affected organization, with version and date (attributed, interested);
3. vendor and CERT advisories;
4. independent incident-response and threat-intelligence reports that disclose method and evidence;
5. regulator filings and breach notifications;
6. reporting with named technical sources;
7. attribution claims, grouped by the evidence they rest on; unsupported attribution is a claim, not a finding.

## Decomposition pattern

Separate: vulnerability or vector; timeline (introduction, exploitation, detection, disclosure, remediation); scope of access and data affected; attribution with its evidence class; impact; and remediation state. Write the leading account, alternative accounts, and the insufficient-evidence possibility for cause and attribution.

## Mode gates

- Scope claims (records, systems, users) carry the disclosing party's exact wording and date; expansions in later disclosures are tracked.
- Attribution cites the artifacts it rests on and names the confidence; overlapping tooling is not proof of a single actor.
- Remediation state distinguishes patched, mitigated, and unaddressed, by version.

## Output sections

- Bottom line
- Vector and vulnerability
- Timeline
- Scope and impact
- Attribution and its evidence
- Remediation state
- Competing accounts and forecast
- Gaps and falsifiers

## Completion criteria

The timeline rests on dated artifacts; scope and attribution claims are attributed with confidence ranges; remediation state is version-specific; competing accounts are present for cause and attribution.

## Pitfalls

- Reporting the first disclosed scope as the final scope.
- Attributing on tooling overlap alone.
- Describing "patched" without saying which versions.
