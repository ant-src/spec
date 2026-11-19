# `ant test`

Draft 0.1 · October 2026

`ant test` finds test files, runs their tests, and reports the ones that failed. What a test is, the
`test` declaration, and when a test fails are defined by the language (`ant-lang.md` section 10,
Tests); the `Test` namespace is in section 11. This document covers the command: which files it
runs, its flags, its report, and its exit status.

## 1. Command

```
ant test [flags] [path ...]
```

- A path is a test file, whose name ends in `_test.ant`, or a directory, searched recursively for
  test files; directories whose names begin with `.` are left out. With no path, it is `.`. A file
  named directly that is not a test file is a usage error.
- Files run one after another, in the order the paths were given, and a directory's files in lexical
  order of their paths.
- Each test file runs as a program of its own: its modules are loaded and initialized for that file,
  so the module state of one file never reaches another's.
- Before any test runs, the checker runs over the test files and every module they import, as
  `ant check` runs over the same files (section 4, Checking and running), so a run that passes is a
  run of files that check. When it reports an error no test runs (Check errors, below). `-nocheck`
  leaves the check out, and the tests then run as `ant run` runs a program, with types erased.

| Flag           | Meaning                                                                                                                                                    |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `-run regexp`  | Run only the tests whose full name matches. The pattern is split on `/` into levels (Filtering, below): `-run 'parse/0x'`                                  |
| `-skip regexp` | Leave out the tests that match, the same way                                                                                                               |
| `-v`           | Print every test as it starts and ends, with its output                                                                                                    |
| `-json`        | Print events as JSON lines instead of the report                                                                                                           |
| `-failfast`    | Start no test after the first failure                                                                                                                      |
| `-nocheck`     | Run the tests without checking the test files first                                                                                                        |
| `-parallel n`  | The most tests that run at once after `Test.parallel()`; the default is the number of CPUs                                                                 |
| `-timeout d`   | End the run after `d`, read as `Time.parseDuration` reads it, such as `30s` or `10m` (the default), and report the tests still running; `0` means no limit |

**Filtering.** A part of `-run` is a regular expression (`Regex`, section 11) matched anywhere in
the name of the test at its level: the first part against a top-level test's name, the second
against its subtests' names, and so on. A test runs when each of its names matches the part at its
level, as far as the pattern has parts, so `-run parse` runs `parse` and all its subtests, and
`-run parse/0x` runs `parse` and the subtests of it whose names contain `0x`. A parent whose
subtests are left out still runs its body, which is how its subtests are found. `-skip` leaves out a
test when its full name has at least as many levels as the pattern and each matches, and with it its
subtests. A test left out is neither run nor counted.

The pattern is split on each `/` that is not escaped with a backslash and not inside brackets or
parentheses, so a name that holds a `/` is matched by `\/` or `[/]`: `-run 'a\/b/c'` runs subtest
`c` of the test `a/b`.

## 2. Output

What a test prints, with `print`, `println`, `eprint`, and `eprintln`, from its body or from any
goroutine it owns, is collected: it is shown with the test's result when the test fails, and as it
comes under `-v`. A passing test prints nothing. Other output, from a module's initialization or a
child process, goes to standard output and standard error as under `ant run`.

**The report.** For each test that fails, in the order they end:

```
--- FAIL: stack_test.ant: parse/0x10 (0.00s)
    assertion failed: parse(c.input) == c.want (0 == 16)
      c.input = "0x10"
      at test "0x10" (stack_test.ant:26:13)
```

The line names the file, as the path it was found by, and the test's full name, then the time the
test took in seconds. The lines after it are indented by four spaces: the test's collected output,
then each of its failures. A panic shows its message and its trace, from the panic to the test's
body, as the runtime reports a panic without the `panic: ` prefix (section 8); a panic in a
goroutine the test owns starts with `goroutine started at path:line:column panicked: `. An `Err` the
body returned shows its error as a script's is shown (section 10, Scripts). A parent that fails only
because a subtest did is not reported again.

The run ends with one line:

```
FAIL  1 failed, 4 passed (0.02s)
ok    4 passed, 1 skipped (0.01s)
ok    no tests (0.00s)
```

The line gives the failed count when it is not zero, then always the passed count, then the skipped
count when it is not zero: `ok    0 passed, 1 skipped` for a run whose one test skipped. A run of no
tests says `no tests`. The line starts with `ok` when the command exits with `0` and `FAIL`
otherwise, so under `-nocheck` a file that cannot be loaded makes it `FAIL`, though it adds to no
count. The counts are of tests without subtests, and of tests with subtests that failed on their
own; a test counts as without subtests when none of its subtests ran, so a parent whose subtests
`-run` or `-skip` left out all counts as one test.

**Verbose.** Under `-v`, each test also prints `=== RUN   file: name` when it starts, its output as
it comes, indented by four spaces, and when it ends `--- PASS: file: name (0.00s)`, `--- SKIP:` with
the reason on the next line, or `--- FAIL:` with its failures.

**JSON.** Under `-json`, the command writes one JSON object per line to standard output, and nothing
else; what a program prints outside a test, as it initializes, goes to standard error instead:

| `action`   | Other fields                                                    | When                           |
| ---------- | --------------------------------------------------------------- | ------------------------------ |
| `"run"`    | `file`, `test`                                                  | a test starts                  |
| `"output"` | `file`, `test`, `output`: the text of one write                 | a test prints                  |
| `"pass"`   | `file`, `test`, `elapsed`: seconds as a number                  | a test passes                  |
| `"skip"`   | `file`, `test`, `elapsed`, `reason`                             | a test is skipped              |
| `"fail"`   | `file`, `test`, `elapsed`, `message`: the failures, as reported | a test fails                   |
| `"done"`   | `passed`, `failed`, `skipped`, `elapsed`                        | the run ends, as the last line |
| `"error"`  | the fields of an `ant check -json` error                        | the checker reports an error   |

**Check errors.** When the checker reports an error, the command writes every error to standard
error as `ant check` writes them, with the count, and runs no test, so it prints no report and no
last line. Under `-json` it writes each error to standard output as an `"error"` event, with `path`,
`line`, `column`, `severity`, `code`, `message`, and `start` and `end` as `ant check -json` gives
them (`check.md` section 2), whose `severity` is always `"error"`, and no `"done"` event. A file
that cannot be loaded is one of these errors, and the other files do not run either. The checker's
warnings (`check.md` section 4) are not reported, and do not stop the run: they are `ant check`'s to
report, and the report stays the tests'.

## 3. Time limit

When `-timeout` runs out, the command writes `test timed out after d` to standard error, then
`running tests:` and the full name of each test still running, indented by four spaces, ends the run
as an interrupt does (section 9), and exits with status `1`.

## 4. Exit status

| Status | When                                                                                                                             |
| ------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `0`    | no test failed, including when tests were skipped and when there were none                                                       |
| `1`    | a test failed, the checker reported an error, or the time ran out                                                                |
| `2`    | a file could not be loaded, because of a syntax error, an import cycle, a missing module, or a bad import, or the usage is wrong |

Under `-nocheck`, a file that cannot be loaded is reported as `ant run` reports one, on standard
error, and the other files still run. A panic while a file's modules are initialized is reported as
`ant run` reports one; the file's tests do not run, and the file counts as one failed test.
`Os.exit` in a test ends the command with its status, as it ends a program.
