# Week 13 implementation decisions

1. Preserve the existing root Flutter template layout. Add backend, docs and evidence directories instead of moving working Flutter tooling.
2. The project source is preserved under docs/specification, with paragraph and table extraction in project-extracted.txt. The instructor course module is not present in the searched local folders. Implementation follows the supplied AGENTS.md academic requirements and Chapter 11; independent confirmation against Module 13 remains blocked until supplied.
3. Use actual MySQL only. An isolated development instance may be bootstrapped outside the repository; no live registrar or real student data is authorized.
4. No registration, service editor, recovery screen, later assessment portfolio or production deployment is included. Controlled seeded staff use an operator-chosen non-temporary test password, with must_change_password=false, to avoid adding an unrelated account-management milestone. This is an explicit controlled-demo exception to the specification's temporary staff provisioning rule, not permission for production provisioning.
5. Published service versions and submitted revisions are immutable through both ORM guards and absence of mutation routes. Correction submissions are complete snapshots; only correction targets may change. Responses and endpoints follow Chapter 6 for implemented operations.
6. Exactly one separate APScheduler 3.x process owns schedules. MySQL stores claims, attempts, durable pending work and deduplication keys. No scheduler starts inside FastAPI.
