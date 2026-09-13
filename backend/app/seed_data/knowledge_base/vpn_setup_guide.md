> **DEMO COMPANY DOCUMENTATION** — this is fictional, illustrative content generated for a
> demo/portfolio deployment. It does not describe any real company's actual systems, vendors,
> or procedures.

# VPN Setup Guide

This guide walks employees through installing and configuring the company VPN client so you
can securely access internal systems (the internal wiki, build servers, and shared drives)
from outside the office network.

## Who needs this

Anyone working remotely, traveling, or connecting from a home network needs the VPN client to
reach internal-only services. If you only use cloud tools that are already accessible from the
public internet, you do not need the VPN for day-to-day work.

## Installing the client

1. Download the VPN client for your operating system from the internal software portal
   (`portal.demo-corp.example/software/vpn`).
2. Run the installer with administrator privileges. On managed company laptops this should not
   prompt for a password, since the installer is already signed and allow-listed.
3. Restart your machine once the installation finishes, even if it doesn't explicitly ask you
   to — the network driver the client installs sometimes only loads cleanly after a reboot.

## First-time configuration

When you open the VPN client for the first time, you'll be asked for a server address. Use
`vpn.demo-corp.example` — this is the only supported endpoint for this demo environment.
Sign in with your regular company email and password. If your account has multi-factor
authentication enabled (see the MFA Setup Guide), you'll be prompted for a one-time code after
your password.

Once connected, the client icon in your system tray should turn green and show "Connected".
You can verify connectivity by opening the internal wiki at `wiki.internal.demo-corp.example`
— if it loads without the VPN, something is misconfigured, since that address is not reachable
from the public internet.

## Common issues

**"Connection timed out" errors** are almost always a local network issue — try switching from
Wi-Fi to a wired connection, or from your home network to a phone hotspot, to rule out a
firewall on your router blocking the VPN's protocol.

**Repeated authentication prompts** usually mean your password was recently changed and the
client has a cached (now-stale) credential. Fully quit the client (not just disconnect) and
reopen it to force a fresh login prompt.

**Slow speeds while connected** are expected for large file transfers, since all traffic is
routed through the VPN gateway rather than directly to the internet. For large downloads that
don't require internal access, consider disconnecting the VPN temporarily.

## Getting help

If none of the above resolves your issue, contact IT support with your operating system
version and the exact error message shown by the client. Screenshots are helpful.
