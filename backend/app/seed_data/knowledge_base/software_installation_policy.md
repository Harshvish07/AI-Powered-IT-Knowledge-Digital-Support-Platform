> **DEMO COMPANY DOCUMENTATION** — this is fictional, illustrative content generated for a
> demo/portfolio deployment. It does not describe any real company's actual systems, vendors,
> or procedures.

# Software Installation Policy

This policy explains what software employees can install on company-managed devices, and how
to request software that isn't already pre-approved.

## Pre-approved software

The internal software portal (`portal.demo-corp.example/software`) lists software that any
employee can install without additional approval — this includes common productivity tools,
browsers, communication apps, and standard developer tooling for engineering roles. Installing
from the portal is the fastest path, since it's already vetted for security and licensing.

## Requesting new software

If you need something not on the pre-approved list:

1. Submit a request through the software-request form, including the tool's name, a link to
   its vendor page, and a short justification for why it's needed.
2. IT security reviews the request for security posture (data handling, permissions requested,
   vendor reputation) and IT procurement reviews licensing cost and terms.
3. Most requests are resolved within 3 business days. Requests involving access to sensitive
   company data (source code, customer data, financial systems) may take longer due to
   additional security review.

## Software employees should never install without approval

- Any tool that requires disabling antivirus, firewall, or endpoint protection to function.
- Browser extensions that request broad permissions to read and modify all web page data,
  unless specifically approved for a role that needs them.
- Cracked, pirated, or unlicensed copies of any commercial software, under any circumstances.
- Cryptocurrency mining or "system optimizer" utilities, which are common vectors for malware.

## Personal use of company devices

Company laptops are provided for work purposes. Light personal use (checking personal email,
reading the news) is generally acceptable, but installing personal games, streaming software,
or other non-work applications is discouraged and may be removed during routine device
compliance checks without prior notice.

## Open-source and developer dependencies

Engineers adding new open-source dependencies to company codebases should follow the
engineering team's existing dependency-review process rather than this policy — that process
already covers license compatibility and supply-chain security scanning for packages pulled
into build pipelines, which is a different concern from installing standalone desktop software.

## Enforcement

Devices are periodically scanned for compliance with this policy as part of routine security
maintenance. Non-compliant software is typically flagged to the employee for voluntary removal
first; repeated or willful violations are escalated to the employee's manager.
