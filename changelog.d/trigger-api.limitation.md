- The generated SQL has not run on an IBM i yet: PUB400 does not allow
  `CREATE TRIGGER`. `Truncate`, deferrable triggers, statement-level and
  `INSTEAD OF` triggers are refused with `NotSupportedError`.
