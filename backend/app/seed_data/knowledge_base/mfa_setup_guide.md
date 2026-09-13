> **DEMO COMPANY DOCUMENTATION** — this is fictional, illustrative content generated for a
> demo/portfolio deployment. It does not describe any real company's actual systems, vendors,
> or procedures.

# MFA Setup Guide

Multi-factor authentication (MFA) adds a second step to signing in, so a stolen or guessed
password alone isn't enough to access your account. This guide covers enrolling in MFA and
using it day to day.

## Why MFA is required

Company accounts protect access to internal systems, customer data, and source code. MFA is
mandatory for all employees, and accounts without it configured are automatically restricted
from accessing sensitive systems after a short grace period following account creation.

## Enrolling for the first time

1. Sign in to `account.demo-corp.example/security` with your normal email and password.
2. Select "Set up multi-factor authentication."
3. Choose an authenticator app (any standard TOTP app works — the specific app doesn't matter,
   since they all implement the same open standard).
4. Scan the QR code shown on screen with your chosen app.
5. Enter the 6-digit code the app generates to confirm the setup completed correctly.
6. Save the backup codes shown on the confirmation screen somewhere safe — you'll need one if
   you ever lose access to your authenticator app.

## Signing in with MFA

After entering your password, you'll be prompted for a 6-digit code from your authenticator
app. Codes refresh every 30 seconds, so enter the current one promptly — if it expires before
you submit it, just use the next code that appears.

## If you lose access to your authenticator app

Use one of the backup codes saved during enrollment to sign in, then immediately set up MFA
again on your new device so you're not relying on backup codes going forward. If you've also
lost your backup codes, contact IT support for identity verification and manual account
recovery — this process takes longer specifically because it's designed to prevent someone
else from bypassing MFA by claiming to have lost access.

## Switching to a new phone

Before wiping or replacing a phone with an authenticator app on it, transfer the MFA enrollment
to your new device first (most authenticator apps support an export/transfer feature) or
re-enroll from scratch using the steps above while you still have access to the old device.
Doing this ahead of time avoids needing the backup-code recovery process entirely.

## Hardware security keys

Employees in roles with elevated access (engineering leads, IT security, finance) are issued a
hardware security key as an additional or alternative MFA method. If you believe your role
should require one but you haven't been issued one, ask your manager to submit a request.
