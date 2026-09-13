> **DEMO COMPANY DOCUMENTATION** — this is fictional, illustrative content generated for a
> demo/portfolio deployment. It does not describe any real company's actual systems, vendors,
> or procedures.

# Password Reset Procedure

This document explains how to reset your company account password, both when you remember
your current password and want to change it, and when you've forgotten it entirely and are
locked out.

## Password requirements

Company account passwords must be at least 12 characters long and include a mix of uppercase,
lowercase, digits, and symbols. Passwords cannot reuse any of your last 5 passwords, and they
expire every 180 days. You'll receive an email reminder seven days before your password
expires.

## Resetting a password you remember

1. Go to `account.demo-corp.example/security`.
2. Sign in with your current credentials.
3. Select "Change password" and follow the prompts. You will be signed out of all other active
   sessions once the change is confirmed, so save any work in progress first.

## Resetting a forgotten password

If you're locked out and can't sign in at all:

1. Go to `account.demo-corp.example/forgot-password`.
2. Enter your company email address. You'll receive a reset link valid for 30 minutes.
3. Follow the link and choose a new password meeting the requirements above.
4. If you don't receive the email within a few minutes, check your spam folder before
   contacting IT support — the reset emails are sometimes filtered by aggressive spam rules on
   personal email providers.

## If you no longer have access to your recovery email

Contact IT support directly. For security, password resets requested this way require identity
verification — be ready to confirm your employee ID and answer a couple of account security
questions. IT support will never ask for your current password over email, chat, or phone; if
someone asks you for it, do not provide it and report the request immediately.

## Account lockouts

After 5 failed login attempts within 15 minutes, the account is temporarily locked for 30
minutes as a brute-force protection measure. This is automatic and does not require IT
intervention — simply wait and try again, or use the forgot-password flow to reset immediately
instead of waiting out the lockout.
