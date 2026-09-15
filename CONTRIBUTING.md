# Contributing

## Delivery workflow

All changes after repository initialization arrive through one pull request at
a time. Branches and pull requests begin with `task/` or `feat/`, and titles
begin with `task:` or `feat:` respectively.

Before merge:

1. Rebase or update the branch from `main`.
2. Run all documented local checks.
3. Resolve every required CI check.
4. Review the diff against its acceptance criteria.
5. Squash-merge and delete the branch.

Do not include automated-author attribution in commits, pull requests,
documentation, or source files.
