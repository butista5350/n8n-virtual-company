# HR Wave 1 - Decision Record

- Request ID: hr-wave1-001
- Action type: create_file_dev
- Decision: APPROVED by the CEO via Telegram on 2026-11-26
- Executed manually on 2026-11-26 because the Telegram approval callback did not reach n8n; the CEO instructed direct execution.
- Branch: dev only. No merge to main, no seat activation.

## Scope approved
- Packages: hr-core
- Seats in wave 1: 3
- HR Manager - L1 / T1 - see wave1-seat-hr-manager.md
- Recruiting and Onboarding Specialist - L1 / T1 - see wave1-seat-recruiter.md
- Performance and Permissions Specialist - L0 / T0 - see wave1-seat-performance.md
- Request: wave1-activation-request.md

## Security checks
- Status: passed
- No secrets, no L3 actions, write scope limited to org/hr/**

## Not included in this decision
- Activating any seat, enabling workflows, or any spending. Each needs a separate CEO approval.
- Wave 1 trial window: 48 hours from activation, once activation is approved.
