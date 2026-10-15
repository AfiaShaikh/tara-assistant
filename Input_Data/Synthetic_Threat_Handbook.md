# Synthetic automotive threat handbook

Original educational data. No proprietary standards text. Not expert-approved.

## KB-01 - Firmware authenticity

Firmware authenticity requires checking the update package signature against an authorized trust anchor before installation. A failed signature check must reject the package and leave the current firmware unchanged. This synthetic guidance does not assert that this control exists in the architecture.

## KB-02 - Rollback prevention

Rollback protection rejects older firmware versions below the authorized minimum version. Maintain protected version state and test attempted downgrade after successful update. A valid signature alone does not prevent installation of an old vulnerable version.

## KB-03 - Signing key protection

Signing key confidentiality protects the ability to authorize firmware. Limit signing access, separate development and production keys, and use protected key storage. A leaked signing key can make malicious firmware appear authentic.

## KB-04 - Diagnostic authorization

Diagnostic access requires authentication and authorization for privileged operations. Restrict programming operations to permitted diagnostic sessions and log rejected attempts. The presence of a diagnostic interface does not prove that it is exploitable.

## KB-05 - Gateway isolation

Gateway segmentation limits communication between external interfaces and internal ECU networks. Use explicit message allowlists and validate message length, state and origin. Connectivity alone is not evidence of a feasible attack path.

## KB-06 - Service availability

Availability controls for an update service include request rate limits, resource quotas and recovery behavior. Flooding an exposed update endpoint may delay legitimate updates; impact depends on operational context.

## KB-07 - Transport protection

Update transport confidentiality and integrity can use authenticated encrypted connections with certificate validation. Secure transport complements package signature verification; neither control is evidence that the other is implemented.

## KB-08 - Audit evidence

Security audit logs record update acceptance, rejection, actor identity, timestamp and package version. Protect log integrity and access, and retain evidence according to the project policy.

## KB-09 - Risk method

The DEMO-RISK-v1 educational matrix uses impact and attack feasibility, each rated 1 to 4 by a reviewer. Product scores 1 to 3 are Low, 4 to 7 Medium, 8 to 11 High, and 12 to 16 Critical. This is a synthetic teaching method, not the ISO/SAE 21434 risk method. Missing ratings mean Unassessed.

## KB-10 - Assessment boundaries

An item definition describes functions, components, operational context, external interfaces and assumptions. An asset is something whose cybersecurity properties matter. A damage scenario describes an adverse consequence; a threat scenario describes a potential cause of that consequence.

## KB-11 - Review and uncertainty

Candidate threats need engineering review. Unknown controls are not absent controls. Record assumptions and evidence separately. An accepted finding is accepted for the project register, not vehicle release or regulatory approval.

## KB-12 - Change reassessment

Architecture changes can invalidate earlier assessments. Compare components, interfaces, controls and trust boundaries, then trace dependencies to affected assets and tests. Mark affected reviews stale; do not silently reuse a previous approval.