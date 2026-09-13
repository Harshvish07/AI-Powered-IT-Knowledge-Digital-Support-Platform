> **DEMO COMPANY DOCUMENTATION** — this is fictional, illustrative content generated for a
> demo/portfolio deployment. It does not describe any real company's actual systems, vendors,
> or procedures.

# GitHub Access Policy

This policy describes how engineering staff are granted, use, and eventually have revoked
access to the company's GitHub organization.

## Requesting access

New engineering hires are added to the GitHub organization by their manager during onboarding,
using the employee's company email address. Access requests for existing employees who need
elevated permissions (for example, admin rights on a specific repository) should be submitted
through the internal access-request form and require manager approval.

## Account requirements

All members of the organization must:

- Use a GitHub account secured with two-factor authentication. Accounts without 2FA enabled
  are automatically removed from the organization after a 14-day grace period.
- Use an account email that can be verified as belonging to the employee, either their company
  email or a personal email added as a verified secondary address.
- Avoid sharing accounts between multiple people under any circumstances, even temporarily.

## Repository access levels

Access is granted using the principle of least privilege:

- **Read** access is the default for most organization members, sufficient for browsing code,
  raising issues, and reviewing pull requests.
- **Write** access is granted to engineers actively contributing to a specific repository and
  allows pushing branches and merging approved pull requests.
- **Admin** access is reserved for repository maintainers and is reviewed quarterly to confirm
  it's still needed.

## Branch protection

All production repositories require pull request review before merging to the main branch, and
direct pushes to main are disabled organization-wide. At least one approving review is required
before a merge, and status checks (tests, linting) must pass.

## Offboarding

When an employee leaves the company, their GitHub organization membership is revoked as part of
the standard offboarding checklist, on their last working day. Any personal access tokens or
SSH keys associated with their account should be assumed compromised for company purposes and
are not transferred to anyone else.

## Third-party integrations

Connecting third-party apps or OAuth integrations to the organization (CI tools, bots, code
quality services) requires approval from engineering leadership, since these integrations often
receive broad read/write access across every repository.
