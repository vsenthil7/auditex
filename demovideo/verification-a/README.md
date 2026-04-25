# verification-a/ - Option A: Structural review

Re-runs the same demo flow as Option 1 but with **hard assertions** at each scene gate.
No video frame inspection - this is logic-level checking. If every assertion passes, the
recorded video has by-construction shown all the right states.

## What it asserts (8 gates per scene, 3 scenes = 24 assertions total)

1. Dashboard reachable, form visible
2. Form accepts task type / document / criteria inputs
3. POST /api/v1/tasks returns 201 with valid task_id
4. Task appears in list, reaches COMPLETED
5. Detail panel renders all 5 pipeline steps
6. Step 2 executor block has model + recommendation
7. Step 3 review panel shows 3 reviewers
8. Step 4 vertex hash visible

## Run
```powershell
.\demovideo\verification-a\run-verify-a.ps1
```

Outputs:
- Pass/fail summary in the console.
- Full report at `verification-a/reports/structural-review-{timestamp}.txt`.
