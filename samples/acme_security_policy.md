# Acme Corp — Information Security Policy

**Owner:** Raj Patel (CTO) · **Version:** 3.2 · **Effective:** January 2024

## 1. Purpose
This policy defines how Acme Corp protects customer and company data. It applies to
all employees, contractors, and systems that process Acme or customer data.

## 2. Access control
Acme enforces role-based access control (RBAC). Access to production systems follows
the principle of least privilege and is reviewed monthly by the People Ops and
Engineering leads. Multi-factor authentication (MFA) is mandatory for all accounts.
Privileged access requires hardware security keys.

Access is granted through the PolicyForge access-request workflow and is automatically
revoked when an employee changes roles or leaves the company.

## 3. Data classification
Data is classified into four levels:

1. **Public** — marketing material, public documentation.
2. **Internal** — internal wikis, non-sensitive project plans.
3. **Confidential** — source code, financial reports, employee records.
4. **Restricted** — customer data, encryption keys, credentials.

Restricted data must be encrypted at rest and in transit using DataShield Cloud, and
may never be copied to personal devices.

## 4. Passwords and secrets
Passwords must be at least 12 characters and are stored only as Argon2 hashes. Service
secrets are kept in a managed secrets vault and rotated every 90 days. Secrets must
never be committed to source control.

## 5. Incident response
Suspected security incidents must be reported to the security team within one hour of
discovery. The on-call security engineer triages the incident and, for critical events,
convenes an incident response team. A written post-mortem is required within five
business days of any incident rated high or critical.

## 6. Vendor and compliance
Acme is SOC 2 Type II certified and GDPR compliant. All vendors that handle Restricted
data must complete a security review and sign a data processing agreement before
onboarding. Annual penetration tests are performed by an independent third party.

## 7. Training
All employees complete security awareness training during onboarding and again every
year. Engineers complete an additional secure-coding course. Failure to complete
required training within 30 days results in suspended production access.
