# `ant check`

Draft 0.1 · November 2026

`ant check` runs the checker over a program and reports what it finds. Which files it reads, and
what the checker accepts, are defined by the language (`ant-lang.md` section 4, Checking and
running): every rule of that document that mentions a type is a checker rule. This document covers
the command's output: the diagnostics it reports, the codes that name their rules, the warnings it
gives about code it accepts, and its exit status.

## 1. Command

```
ant check [-json] [-strict] [path ...]
ant check -explain code
```

| Flag            | Meaning                                                                               |
| --------------- | ------------------------------------------------------------------------------------- |
| `-json`         | Write each diagnostic as a JSON object on standard output instead of the text report  |
| `-strict`       | Exit with `1` on a warning as on an error (section 5)                                 |
| `-explain code` | Print what the code means, an example that has it, and the example fixed, then exit 0 |

`-explain` takes no path. An unknown code is a usage error.

## 2. Diagnostics

A diagnostic is one thing the checker reports. It has:

| Field                    | Meaning                                                                                                                                                                                                     |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `path`, `line`, `column` | Where it is reported. `line` and `column` are `0` for a diagnostic about a whole file, such as one that cannot be read                                                                                      |
| `start`, `end`           | For a diagnostic at a position, the span it is about, each a `line` and a `column`, with `end` just past the span                                                                                           |
| `severity`               | `"error"`, or `"warning"` for a warning (section 4)                                                                                                                                                         |
| `code`                   | The rule it enforces, from the catalog (section 3)                                                                                                                                                          |
| `message`                | What is wrong, as one sentence that names types and code as the program writes them. Its wording is not part of this contract; its `code` is                                                                |
| `help`                   | Optional: one sentence on how to fix it, when the message does not say                                                                                                                                      |
| `fixes`                  | Optional: edits that would remove it, each fix a `title`, an `auto` flag, and `edits`, each edit a `path`, a `start`, an `end`, and the `text` that replaces what lies between them; `start == end` inserts |
| `related`                | Optional: other places that explain it, each a `path`, `line`, `column`, and `message`                                                                                                                      |

Lines and columns count from 1, and columns count bytes. Diagnostics are reported in order of path,
then line, then column.

**Text.** Without `-json`, the command writes each diagnostic to standard error: a first line
`path:line:column: message [code]`, with `warning: ` before the message of a warning, then, for a
diagnostic at a position, the source lines of its span, numbered, with the span marked. Under the
source come, each on a line of its own, `= help:` and the help, `= fix:` and the title of each fix,
and `= note: path:line:column: message` for each related place. A blank line separates two
diagnostics, and a last line gives their count, as `1 error`, `3 errors`, `2 warnings`, or
`1 error, 2 warnings`. When there is no diagnostic, it writes nothing.

**JSON.** With `-json`, the command writes each diagnostic to standard output as a JSON object on a
line of its own, with the fields above, and writes nothing else. `start` and `end` are left out when
there is no span, and `help`, `fixes`, and `related` when there is none.

**Help and fixes.** A fix is `auto` only when applying it removes the diagnostic, it is the only fix
offered, and no other edit could be meant: the error admits one repair. `ant code fix` applies auto
fixes without asking; an editor offers every fix. The checker offers at least these:

| Code                               | When                                                                                                                                        | Help, and fix                                                                                                     |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `no-member`                        | `x.f(...)`, where a prelude function `f` of another namespace takes `x` first and the arguments                                             | the namespace that has it; a fix that calls it as `Ns.f(x, ...)`, auto when one namespace does                    |
| `no-member`, `undefined`           | a name near one that exists, within one edit for a name of up to four characters and two for a longer one, swapping two neighbors being one | the nearest names; for a prelude namespace or type with none near, that `ant doc` lists its members               |
| `arguments`                        | `Result.ok()`                                                                                                                               | that a `Result[void, E]` holds `void`; a fix that passes it, auto when the call is expected to be such a `Result` |
| `type-mismatch`                    | a map literal's key written `[k]`                                                                                                           | that a computed key is written `(k)`; a fix that writes it so, not auto, since an array may be the key meant      |
| `syntax`                           | a reserved word                                                                                                                             | what Ant writes in its place, or, where a name was expected, to choose another                                    |
| `syntax`                           | a subtest's name that is not a string                                                                                                       | the name written as a template, `test "${...}"`                                                                   |
| `type-mismatch`, `needs-narrowing` | a field path, such as `r.x`, used after an `is` test of it in the same function                                                             | that a test narrows only a local or a parameter; the test as a related place                                      |
| `missing-else`                     | a chain of `is` tests of a local that leaves members of its union out                                                                       | the members left out                                                                                              |
| `redeclared`                       | a declaration that takes a prelude name                                                                                                     | to choose another name, and how to see the prelude's                                                              |

**Every error in one run.** A module with a syntax error is read past it: each statement or
declaration the parser can read after the error is checked as if the error were not there, and a
module that imports it is checked too. A brace on the line after the header of an `if`, `for`,
`while`, or `select` clause is read as the block the header lacks.

**Errors that follow from others.** An error is not reported when it follows only from another
error, which is reported:

- a second syntax error at the position of one, and, after the first syntax error of a file, one at
  the end of the file, which only says that what the first broke never closed;
- an error other than a syntax error on a line that has one, since the line was not read as written;
- an error whose message would name a type the checker could not determine, once any error has been
  reported;
- in a module with a syntax error, a name that is not declared, since its declaration may be in what
  the parser could not read; and a name imported from such a module that it does not declare;
- a use of a name that an import could not bind: from a module that cannot be read, from a script,
  or a name the module does not declare; a name imported without `export` is bound to its
  declaration, so its uses are checked;
- in the body of a lambda rejected for its parameters (`lambda`), a name that is not declared, since
  it is likely one of the parameters the author meant.

## 3. Codes

A code names a rule. Several messages may share a code, and a message may be reworded without its
code changing. A code is never reused for another rule. A code may be split into finer ones: the old
code is then retired, listed here with the codes that replace it, and never reused.

| Code                | Rule                                                                                                                                                                                        |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `syntax`            | The source does not parse: a token, a keyword, a reserved word, an escape, or a construct out of place (`ant-lang.md` section 2)                                                            |
| `missing-module`    | A module given or imported cannot be read (`ant-lang.md` section 10)                                                                                                                        |
| `import`            | An import that is not allowed: an import cycle, or an import of a script, a declaration file, or, outside a test file, a test file (`ant-lang.md` section 10)                               |
| `undefined`         | A name, type, or member of a namespace is not declared                                                                                                                                      |
| `not-exported`      | A name is used outside its module without `export`, or an export names a private type in its signature                                                                                      |
| `redeclared`        | A name is declared twice in one scope, a field twice in one record type, a declaration takes a prelude name, or a function on a type shares its name with a field                           |
| `declaration-order` | A name is read before it is initialized: a later top-level variable, a variable in its own initializer, or a later parameter in a default                                                   |
| `misplaced`         | A construct is outside the place it is allowed: `return` outside a function, a function on a type not declared at the top level of the module, or a local type that mentions what it cannot |
| `wrong-kind`        | A name is used as a kind of thing it is not: a namespace or a type as a value, a variable as a type, a value called that is not a function                                                  |
| `type-mismatch`     | A value's type does not fit where it is used                                                                                                                                                |
| `no-member`         | A type or namespace has no field or function of that name, or a function cannot be called on that receiver                                                                                  |
| `needs-narrowing`   | A field or function exists on some members of a union but not all, so the value must be narrowed first                                                                                      |
| `not-nullable`      | `??`, `?.`, `?.(`, or `?.[` applies to a value that cannot be `null`                                                                                                                        |
| `operands`          | An operator's operands do not fit it                                                                                                                                                        |
| `arguments`         | A call's arguments, or a type's type arguments, do not fit what it takes                                                                                                                    |
| `needs-annotation`  | The checker cannot infer a type, and asks for it to be written                                                                                                                              |
| `no-common-type`    | The branches, clauses, elements, entries, or returns of a construct have no type in common                                                                                                  |
| `bound`             | A type argument is outside its parameter's bound, or a bound does not provide what is used                                                                                                  |
| `invalid-union`     | A union, written or formed by substitution, breaks a rule of unions: two members `is` cannot tell apart (`ant-lang.md` section 4, Unions)                                                   |
| `type-declaration`  | A `type` declaration the language does not allow: an alias that names itself, a recursion that never ends, or a second tag for one type                                                     |
| `spread`            | A spread in a literal of a value it cannot spread, or of a record with a field the literal's type lacks                                                                                     |
| `missing-field`     | A record literal leaves out a field that has no default                                                                                                                                     |
| `missing-else`      | An `if` without `else` is used where a value is needed, including a chain of `is` tests that does not cover a union                                                                         |
| `try`               | `try` on a value that is not a `Result`, or where the enclosing function does not return a compatible `Result`                                                                              |
| `assign`            | An assignment to a `let`, an import, or something else that cannot be assigned                                                                                                              |
| `lambda`            | A lambda `{ ... }` whose shape does not fit its expected type, or that has no expected type                                                                                                 |
| `is-test`           | An `is` test the checker cannot carry out: of an interface, an alias, or a type whose type arguments the value does not fix                                                                 |
| `useless-test`      | A test whose result is known, or an `else` that cannot run                                                                                                                                  |
| `duration-equality` | `==` or `!=` between two duration literals of the same length and different fields (`ant-lang.md` section 2)                                                                                |
| `markup`            | Markup holds a value or an attribute that it does not take (`ant-lang.md` section 5, HTML expressions)                                                                                      |
| `conversion`        | A conversion to a type it does not apply to                                                                                                                                                 |
| `void-value`        | `_` is read, or a call that returns `void` is bound                                                                                                                                         |
| `reflect`           | `type(...)` is used where it cannot be (`ant-lang.md` section 11, Reflect)                                                                                                                  |
| `internal`          | The checker failed. This is a bug in the implementation                                                                                                                                     |

The warnings of section 4 have codes of their own: `unused-result`, `unused-import`,
`unused-variable`, and `named-interpolation`.

`ant check -explain code` prints a code's entry from the documentation of `ant check`, which gives
the same rule as this table, an example that has the diagnostic, and the example fixed. This table
is normative; an explanation that disagrees with it is a bug in the explanation.

## 4. Warnings

A warning reports code the checker accepts that is almost always a mistake. A warning is added only
when it catches a real bug, the bug happens in practice, and it rarely fires on correct code. Each
is silenced by writing what the code means, never by a comment or a setting. Warnings are reported
only for a module with no error, since a module the checker rejected was not checked as written.

| Code                  | Reported on                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Silenced by                                                                                                              |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `unused-result`       | a value whose type is a `Result` or a union with a `Result` member, which is discarded: a statement of a block other than its last; the last of a block whose value is discarded, the body of a function or lambda that returns `void`, a test, a loop, or a `go` block, or a branch of an `if` or `select` that is itself discarded; or a statement of a script's top level. Not anything in a `defer` block, whose values the language discards (`ant-lang.md` section 8) | `try`, or `_ = ` before it                                                                                               |
| `unused-import`       | a name an import binds that the module uses neither as a value nor as a type                                                                                                                                                                                                                                                                                                                                                                                                | removing it; the fix that removes it is auto while another name of the import remains, so that the module stays imported |
| `unused-variable`     | a `let` or `var` in a function, a lambda, a block, or a test, or a name of its destructuring, that the module never uses                                                                                                                                                                                                                                                                                                                                                    | removing it, or binding `_`                                                                                              |
| `named-interpolation` | a value of a named primitive type in a string's `${...}`, which shows it as its constructor, `UserId("u-1")`; markup rejects one for that reason (`ant-lang.md` section 5, HTML expressions)                                                                                                                                                                                                                                                                                | converting it to its base type, as `string(id)`, or `String.from(id)` for the constructor form                           |

`ant test` does not report warnings; its report is the tests' (`test.md` section 2).

## 5. Exit status

| Status | When                                                                                                                         |
| ------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `0`    | No error was reported, though warnings may have been, or `-explain` printed an explanation                                   |
| `1`    | An error was reported, or under `-strict` a warning, and every file could be loaded                                          |
| `2`    | A file could not be loaded (`ant-lang.md` section 4, Checking and running), or the usage is wrong, including an unknown code |
