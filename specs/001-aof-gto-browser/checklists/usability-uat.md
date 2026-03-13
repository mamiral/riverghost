# Usability UAT Checklist: AoF GTO Browser Control Discoverability

## Objective
Validate SC-004: at least 90% of participants can correctly identify selected position, action, and metric without assistance.

## Test Setup
- Minimum participants: 10
- Environment: Windows desktop, venv active, app launched from `python/`
- Build: Current feature branch implementation

## Participant Tasks
- [ ] Open standalone AoF browser.
- [ ] Identify currently selected position.
- [ ] Identify currently selected action.
- [ ] Identify currently selected metric.
- [ ] Switch to `BB`, `all-in`, and `EQR`.
- [ ] Confirm all three active selections are visible simultaneously.

## Pass/Fail Recording
- [ ] Record each participant as pass/fail for all three identification checks.
- [ ] Calculate pass rate = passes / total participants.
- [ ] SC-004 passes if pass rate >= 90%.

## Result Summary
- Total participants: 
- Participants passed: 
- Pass rate (%): 
- SC-004 status (PASS/FAIL): 
- Notes:
