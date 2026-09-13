> **DEMO COMPANY DOCUMENTATION** — this is fictional, illustrative content generated for a
> demo/portfolio deployment. It does not describe any real company's actual systems, vendors,
> or procedures.

# Wi-Fi Configuration Guide

This guide covers connecting company devices to office Wi-Fi networks and troubleshooting the
most common connectivity issues.

## Available networks

Each office has two Wi-Fi networks:

- **DemoCorp-Secure** — the primary network for company-owned laptops and phones. It uses
  certificate-based authentication tied to your company account, so there's no shared password
  to type in; your device authenticates automatically once enrolled.
- **DemoCorp-Guest** — an internet-only network for visitors and personal devices. It has no
  access to internal systems and is isolated from the corporate network entirely. The password
  is displayed on posters near reception and rotates monthly.

## Enrolling a company laptop on DemoCorp-Secure

New laptops are enrolled automatically during initial setup by IT before they're handed out.
If you need to re-enroll a device (for example, after a factory reset), open the company
device-management app and select "Enroll in Wi-Fi" — this pushes the required certificate to
your device without you needing to configure anything manually.

## Enrolling a personal phone for company email

Personal devices used to check company email over Wi-Fi should still connect to
DemoCorp-Guest, not DemoCorp-Secure — DemoCorp-Secure is reserved for company-managed hardware
only. Company email access from personal devices goes through the mobile email app, which
handles its own authentication independently of which Wi-Fi network you're on.

## Troubleshooting

**Device won't connect to DemoCorp-Secure at all:** this is almost always an expired or missing
enrollment certificate. Re-run the enrollment step above.

**Connects but has no internet access:** try forgetting the network and reconnecting. If that
doesn't help, check whether other people nearby are having the same issue — this can indicate
an access point outage rather than a problem with your specific device.

**Frequent disconnections in certain parts of the building:** some office areas have weaker
signal coverage. Report the specific location to IT so it can be included in the next access
point placement review; in the meantime, moving closer to a shared space or conference room
usually resolves it.

## Security note

Never connect company laptops to unknown or unsecured public Wi-Fi networks without also
connecting the VPN client (see the VPN Setup Guide). Public Wi-Fi at cafes, airports, and
hotels should always be treated as untrusted.
