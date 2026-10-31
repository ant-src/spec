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
- Each test file runs as a program of its own: its modules, its companion among them, are loaded and
  initialized for that file, so the module state of one file never reaches another's.
- `ant test`, like `ant run`, does not type-check (section 4, Checking and running). `ant check`
  accepts a test file and checks it with its companion and its imports.

| Flag           | Meaning                                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `-run regexp`  | Run only the tests whose full name matches. The pattern is split on `/`, and each part must match the name at its level: `-run 'parse/0x'` |
| `-skip regexp` | Leave out the tests that match, the same way                                                                                               |
| `-v`           | Print every test as it starts and ends, with its output                                                                                    |
| `-json`        | Print events as JSON lines instead of the report                                                                                           |
| `-failfast`    | Start no test after the first failure                                                                                                      |
| `-parallel n`  | The most tests that run at once after `Test.parallel()`; the default is the number of CPUs                                                 |
| `-timeout d`   | End the run after `d`, a Go duration such as `30s` or `10m` (the default), and report the tests still running; `0` means no limit          |

**Filtering.** A part of `-run` is a regular expression (`Regex`, section 11) matched anywhere in
the name of the test at its level: the first part against a top-level test's name, the second
against its subtests' names, and so on. A test runs when each of its names matches the part at its
level, as far as the pattern has parts, so `-run parse` runs `parse` and all its subtests, and
`-run parse/0x` runs `parse` and the subtests of it whose names contain `0x`. A parent whose
subtests are left out still runs its body, which is how its subtests are found. `-skip` leaves out a
test when its full name has at least as many levels as the pattern and each matches, and with it its
subtests. A test left out is neither run nor counted.

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
      c.want = 16
      at test "0x10" (stack_test.ant:24:13)
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

The counts are of tests without subtests, and of tests with subtests that failed on their own.

**Verbose.** Under `-v`, each test also prints `=== RUN   file: name` when it starts, its output as
it comes, indented by four spaces, and when it ends `--- PASS: file: name (0.00s)`, `--- SKIP:` with
the reason on the next line, or `--- FAIL:` with its failures.

**JSON.** Under `-json`, the command writes one JSON object per line to standard output, and nothing
else:

| `action`   | Other fields                                                    | When                           |
| ---------- | --------------------------------------------------------------- | ------------------------------ |
| `"run"`    | `file`, `test`                                                  | a test starts                  |
| `"output"` | `file`, `test`, `output`: the text of one write                 | a test prints                  |
| `"pass"`   | `file`, `test`, `elapsed`: seconds as a number                  | a test passes                  |
| `"skip"`   | `file`, `test`, `elapsed`, `reason`                             | a test is skipped              |
| `"fail"`   | `file`, `test`, `elapsed`, `message`: the failures, as reported | a test fails                   |
| `"done"`   | `passed`, `failed`, `skipped`, `elapsed`                        | the run ends, as the last line |

## 3. Time limit

When `-timeout` runs out, the command writes `test timed out after d` to standard error, then
`running tests:` and the full name of each test still running, indented by four spaces, ends the run
as an interrupt does (section 9), and exits with status `1`.

## 4. Exit status

| Status | When                                                                                                                             |
| ------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `0`    | no test failed, including when tests were skipped and when there were none                                                       |
| `1`    | a test failed, or the time ran out                                                                                               |
| `2`    | a file could not be loaded, because of a syntax error, an import cycle, a missing module, or a bad import, or the usage is wrong |

A file that cannot be loaded is reported as `ant run` reports one, on standard error, and the other
files still run. A panic while a file's modules are initialized is reported as `ant run` reports
one; the file's tests do not run, and the file counts as one failed test. `Os.exit` in a test ends
the command with its status, as it ends a program.

## 5. Editors and the debugger

`ant lsp` shows each top-level test, and each subtest whose name is a literal, as a document symbol
and with a code lens to run or debug it (`lsp.md`). `ant dap` launches a test file with a `-run`
pattern (`dap.md`).
