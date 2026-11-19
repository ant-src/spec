# `ant check`

Draft 0.1 · November 2026

`ant check` runs the checker over a program and reports what it finds. Which files it reads, and
what the checker accepts, are defined by the language (`ant-lang.md` section 4, Checking and
running): every rule of that document that mentions a type is a checker rule. This document covers
the command's output: the diagnostics it reports, the codes that name their rules, and its exit
status.

## 1. Command

```
ant check [-json] [path ...]
ant check -explain code
```

| Flag            | Meaning                                                                               |
| --------------- | ------------------------------------------------------------------------------------- |
| `-json`         | Write each diagnostic as a JSON object on standard output instead of the text report  |
| `-explain code` | Print what the code means, an example that has it, and the example fixed, then exit 0 |

`-explain` takes no path. An unknown code is a usage error.

## 2. Diagnostics

A diagnostic is one thing the checker reports. It has:

| Field                    | Meaning                                                                                                                                      |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `path`, `line`, `column` | Where it is reported. `line` and `column` are `0` for a diagnostic about a whole file, such as one that cannot be read                       |
| `start`, `end`           | For a diagnostic at a position, the span it is about, each a `line` and a `column`, with `end` just past the span                            |
| `severity`               | `"error"`                                                                                                                                    |
| `code`                   | The rule it enforces, from the catalog (section 3)                                                                                           |
| `message`                | What is wrong, as one sentence that names types and code as the program writes them. Its wording is not part of this contract; its `code` is |

Lines and columns count from 1, and columns count bytes. Diagnostics are reported in order of path,
then line, then column.

**Text.** Without `-json`, the command writes each diagnostic to standard error: a first line
`path:line:column: message [code]`, then, for a diagnostic at a position, the source lines of its
span, numbered, with the span marked. A blank line separates two diagnostics, and a last line gives
their count, as `1 error` or `3 errors`. When there is no diagnostic, it writes nothing.

**JSON.** With `-json`, the command writes each diagnostic to standard output as a JSON object on a
line of its own, with the fields above, and writes nothing else. `start` and `end` are left out when
there is no span.

## 3. Codes

A code names a rule. Several messages may share a code, and a message may be reworded without its
code changing. A code is never reused for another rule. A code may be split into finer ones: the old
code is then retired, listed here with the codes that replace it, and never reused.

| Code                | Rule                                                                                                                                                                                        |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `syntax`            | The source does not parse: a token, a keyword, a reserved word, an escape, or a construct out of place (section 2)                                                                          |
| `missing-module`    | A module given or imported cannot be read (section 10)                                                                                                                                      |
| `import`            | An import that is not allowed: an import cycle, or an import of a script, a declaration file, or, outside a test file, a test file (section 10)                                             |
| `undefined`         | A name, type, or member of a namespace is not declared                                                                                                                                      |
| `not-exported`      | A name is used outside its module without `export`, or an export names a private type in its signature                                                                                      |
| `redeclared`        | A name is declared twice in one scope, takes a prelude name, or shares its name with a field                                                                                                |
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
| `invalid-union`     | A union, written or formed by substitution, breaks a rule of unions: two members `is` cannot tell apart (section 4, Unions)                                                                 |
| `type-declaration`  | A `type` declaration the language does not allow: an alias that names itself, a recursion that never ends, or a second tag for one type                                                     |
| `record-literal`    | A record literal or spread is malformed: a field given twice, or a spread of something that is not a record of the right type                                                               |
| `missing-field`     | A record literal leaves out a field that has no default                                                                                                                                     |
| `missing-else`      | An `if` without `else` is used where a value is needed, including a chain of `is` tests that does not cover a union                                                                         |
| `try`               | `try` on a value that is not a `Result`, or where the enclosing function does not return a compatible `Result`                                                                              |
| `assign`            | An assignment to a `let`, an import, or something else that cannot be assigned                                                                                                              |
| `lambda`            | A lambda `{ ... }` whose shape does not fit its expected type, or that has no expected type                                                                                                 |
| `is-test`           | An `is` test the checker cannot carry out: of an interface, an alias, or a type whose type arguments the value does not fix                                                                 |
| `useless-test`      | A test whose result is known, or an `else` that cannot run                                                                                                                                  |
| `duration-equality` | `==` or `!=` between two duration literals of the same length and different fields (section 2)                                                                                              |
| `markup`            | Markup holds a value or an attribute that it does not take (section 5, HTML expressions)                                                                                                    |
| `conversion`        | A conversion to a type it does not apply to                                                                                                                                                 |
| `void-value`        | `_` is read, or a call that returns `void` is bound                                                                                                                                         |
| `reflect`           | `type(...)` is used where it cannot be (section 11, Reflect)                                                                                                                                |
| `internal`          | The checker failed. This is a bug in the implementation                                                                                                                                     |

`ant check -explain code` prints a code's entry from the documentation of `ant check`, which gives
the same rule as this table, an example that has the diagnostic, and the example fixed. This table
is normative; an explanation that disagrees with it is a bug in the explanation.

## 4. Exit status

| Status | When                                                                                                           |
| ------ | -------------------------------------------------------------------------------------------------------------- |
| `0`    | No diagnostic was reported, or `-explain` printed an explanation                                               |
| `1`    | A diagnostic was reported, and every file could be loaded                                                      |
| `2`    | A file could not be loaded (section 4, Checking and running), or the usage is wrong, including an unknown code |
