# `ant dap`

Draft 0.1 · October 2026

`ant dap` is the debugger: it speaks the Debug Adapter Protocol over standard input and standard
output, so that an editor runs a program with breakpoints, steps through it, and shows its
goroutines, stacks, and variables. This document is the contract of the command and of what it
offers an editor; section numbers in it refer to `ant-lang.md`, and `stdlib.md` defines the
standard library it mentions.

## 1. Command

```
ant dap                     serve the protocol on standard input and standard output
```

`ant dap` takes no arguments and writes nothing to standard output but protocol messages, each
framed with a `Content-Length` header as the Language Server Protocol frames them; what it logs goes
to standard error. It serves one client and one debug session, and runs one program, in its own
process.

| Exit status | When                                                       |
| ----------- | ---------------------------------------------------------- |
| `0`         | the client sent `disconnect`                               |
| `1`         | the connection ended without `disconnect`                  |
| `2`         | the usage is wrong                                         |

The exit status of the program is reported in the `exited` event, not as the command's own.

## 2. Session

A session runs in this order:

1. `initialize`. The response states the capabilities of section 7.
2. `launch`, with the attributes below. The adapter loads the program as `ant run` does (section 10),
   and answers with an error, and nothing more, if it does not load: the error is `ant run`'s
   message. A program that loads is not yet running.
3. The `initialized` event, after the response to `launch`. The client then sends its breakpoints
   (section 4) and exception filters (section 5).
4. `configurationDone`. The program starts.
5. The `exited` event with the program's exit status, as `ant run` would end with it, and then
   `terminated`, when the program ends.

| Attribute     | Meaning                                                          | Default                  |
| ------------- | ---------------------------------------------------------------- | ------------------------ |
| `program`     | the file to run, as given to `ant run`                           | required                 |
| `args`        | the program's arguments, as `Os.args()` returns them              | `[]`                     |
| `cwd`         | the working directory                                            | the program's directory  |
| `env`         | variables set in the program's environment over the adapter's    | `{}`                     |
| `stdin`       | a file whose contents are the program's standard input           | none                     |
| `stopOnEntry` | stop before the root module's first statement                    | `false`                  |

A relative `program` or `stdin` is resolved against `cwd`. `stopOnEntry` stops after the modules
the root imports have run, before the first statement of the root itself: for a script, its first
line.

**Streams.** What the program writes to standard output and standard error is sent as `output`
events of category `stdout` and `stderr`. Standard output is sent at each line break, at least every
100 milliseconds, and before every stop, so what a program wrote before it stops is shown when it
stops. With no `stdin`, standard input is at end of file. A child the program starts (`stdlib.md`,
`Cmd`) gets the same: its output goes to the same events, and it never reads or writes the
adapter's own streams. A panic the runtime reports and the error of a `Result` returned from `main`
are written to standard error as `ant run` writes them (section 8).

**Ending.** `terminate` delivers an interrupt, as the first Ctrl-C does under `ant run`: to the
context `Os.interrupt` returned, when the program asked for one and it is not done, and otherwise it
cancels the run (section 9). A second `terminate` cancels the run. A cancelled run kills the
children still running (`stdlib.md`, `Cmd`). `disconnect` cancels the run if it has not ended, waits
for it, and ends the command.

## 3. The program in protocol terms

**Positions.** Lines and columns count from 1, or from 0 when the client says so in `initialize`
(`linesStartAt1`, `columnsStartAt1`). A column counts UTF-16 code units, as editors do. A source is
the absolute path of a module's file.

**Threads.** Each goroutine is a thread. The main goroutine is thread 1, named `main`. The others
are numbered from 2 in the order they start, and named `go at <file>:<line> #<id>`, by the `go`
block that started them. A `thread` event reports each goroutine that starts and each that ends.

**Stack frames.** A goroutine's frames are those of its panic trace (section 8, Catching a panic),
innermost first: one for each call of a function or a lambda in progress, and one for each module
body that is running, with the same names. A frame's position is the statement or stage (section 4)
it is stopped at, or, below the innermost, the call it is in. The prelude is not written in Ant, so
a call of a prelude function has no frame: a lambda the prelude calls, as `Array.map` calls its
argument, is a frame directly above the one that called the prelude function.

**Scopes.** Each frame has up to three scopes:

| Scope     | Holds                                                                                    |
| --------- | ---------------------------------------------------------------------------------------- |
| `Locals`  | the bindings of the frame's body in scope at its position, innermost block first          |
| `Closure` | for a lambda or a `go` block, the bindings of the enclosing bodies it sees                |
| `Module`  | the top-level declarations of the frame's module                                         |

A binding is shown once its declaration has run: a `var` below the position, or a module variable
whose initializer has not run, is left out. A name an inner binding shadows is left out. A `defer`
block runs in the environment of the block that registered it, so its bindings, and that block's,
are its `Locals`. At a pipeline stage, `Locals` starts with `(piped)`, the value flowing into the
stage. A scope with nothing to show is left out.

**Variables.** A variable's value is written as `String.from` writes it (section 11), with a string
in double quotes, and cut to 200 characters. Its type is the value's runtime type: the record or
enum type's name for a record, a variant, `Ok`, `Err`, or a tagged primitive, and otherwise its kind
(`int`, `string`, `array`, `map`, `func`, ...). Annotations are not kept at run time (section 1,
Types are advisory), so the declared type is not shown. These values expand:

| Value       | Children                                                     |
| ----------- | ------------------------------------------------------------ |
| record      | its fields, in declaration order                             |
| array       | its elements, `[0]`, `[1]`, ...                              |
| map         | its entries, named by the key as `String.from` writes it     |
| set         | its members, `[0]`, `[1]`, ... in iteration order            |
| `Bytes`     | its bytes, `[0]`, `[1]`, ...                                 |

An array, a set, and `Bytes` report `indexedVariables`, so the client fetches their children in
pages with `start` and `count`; a map reports `namedVariables`. A value refers to itself through a
cycle as `String.from` writes it. A child is read when the client asks for it, while the program is
stopped; references are valid until the program resumes.

## 4. Stopping

**Stop points.** The program stops only at a stop point:

- before each statement of a block: a function body, a script body, a lambda, a `go` block, a
  `defer` block, a loop body, a branch of `if` or `match`, and a plain block;
- before each stage of a pipeline of two or more stages (section 5, Pipes): after the value flowing
  into the stage is computed and before the stage's arguments are. The stage's position is that of
  its `|`.

`xs | Array.sum()` is a pipeline of one stage and has no stop point of its own.

**Breakpoints.** A line breakpoint binds to the first stop point that starts on its line, in the
module of its source. A line with none binds to the next line that has one, inside the same
function, lambda, or module body; the breakpoint is reported verified on that line. A breakpoint
that binds to nothing, or whose source is not a module of the program, is reported unverified, with
a message saying why. `setBreakpoints` replaces every breakpoint of its source. A stop point a
breakpoint binds to stops each goroutine that reaches it.

**All-stop.** When one goroutine stops, for a breakpoint, a step, a pause, a panic, or the entry,
every goroutine stops: one running Ant code stops at its next stop point, and one waiting in a
blocking call (a channel operation, `select`, a lock, a sleep, I/O) stops before the call returns to
Ant code. A waiting goroutine's innermost frame is the one making the call, at the call. The
`stopped` event names the goroutine that stopped, with the reason `breakpoint`, `step`, `pause`,
`exception`, or `entry`, and `allThreadsStopped`. `continue` resumes every goroutine.

Time does not stop with the program. A sleep, a timer, or a deadline (`stdlib.md`, `Context`) that
passes while the program is stopped ends as it would have, when the program resumes.

**Stepping.** A step resumes every goroutine and stops them all when the stepping goroutine reaches
the stop point it is looking for, or ends. It looks only on its own goroutine:

| Request    | Stops at the next stop point                                              |
| ---------- | ------------------------------------------------------------------------- |
| `stepIn`   | in any frame                                                              |
| `next`     | in the current frame or a frame below it                                  |
| `stepOut`  | in a frame below the current one                                          |

A frame here is one call of a function or a lambda, or one run of a module body, wherever it sits on
the stack. A loop's body over a sequence runs inside the sequence's call of `yield`, above the
sequence's frame, but it belongs to the frame of the loop (section 12, `for x in e`): `next` in the
body goes to the next statement of the body, and then, at its end, into the next iteration. A
`defer` block belongs to the frame of the block that registered it. A goroutine a `go` block starts
is not stepped into; a breakpoint inside the block stops it. A breakpoint reached by another
goroutine during a step stops the program there, and the step ends.

**Pause.** `pause` stops every goroutine, as a breakpoint would, and the `stopped` event names the
goroutine `pause` named, or the main goroutine when that one has ended.

## 5. Panics

`setExceptionBreakpoints` takes two filters:

| Filter     | Stops at                                                       | Default |
| ---------- | -------------------------------------------------------------- | ------- |
| `uncaught` | a panic that no `Panic.catch` on its goroutine will stop       | on      |
| `all`      | every panic, including one a `Panic.catch` turns into a value  | off     |

The program stops where the panic starts, before any deferred block runs, so every frame's
variables can still be read. A panic in a deferred block replaces the one in progress (section 8),
so it is a panic of its own and stops where it starts. `Panic.raise(p)` stops at the call of
`raise`, by the same filters. `exceptionInfo` gives the panic's message as its description and its
trace as section 8 writes it, which for a raised panic is the trace it was raised with.

## 6. Requests

| Request                   | What the adapter does                                                  |
| ------------------------- | ---------------------------------------------------------------------- |
| `initialize`              | states the capabilities of section 7                                   |
| `launch`                  | loads the program (section 2)                                          |
| `setBreakpoints`          | sets the line breakpoints of a source (section 4)                      |
| `setExceptionBreakpoints` | sets the panic filters (section 5)                                     |
| `configurationDone`       | starts the program                                                     |
| `threads`                 | lists the live goroutines                                              |
| `stackTrace`              | lists a stopped goroutine's frames, paged by `startFrame` and `levels` |
| `scopes`                  | lists a frame's scopes (section 3)                                     |
| `variables`               | lists a scope's or a value's children                                  |
| `continue`                | resumes every goroutine                                                |
| `next`, `stepIn`, `stepOut` | steps the goroutine named (section 4)                                |
| `pause`                   | stops every goroutine (section 4)                                      |
| `exceptionInfo`           | describes the panic the program stopped at                             |
| `terminate`               | interrupts the program (section 2)                                     |
| `disconnect`              | ends the run and the command (section 2)                               |

A request the adapter does not serve is answered with an error. `threads`, `stackTrace`, `scopes`,
and `variables` answer with the goroutines and frames as they are when the program is stopped; while
it runs, `threads` lists the goroutines and the others answer with an error.

## 7. Capabilities

The response to `initialize` states `supportsConfigurationDoneRequest`,
`supportsTerminateRequest`, `supportsExceptionInfoRequest`, and the two `exceptionBreakpointFilters`
of section 5, and no other capability.

## 8. What `ant dap` does not do

- It does not evaluate expressions: there is no `evaluate`, so no watch, no hover value, and no
  debug console input.
- It offers no conditional, hit-count, or function breakpoints, and no logpoints.
- It does not change a variable's value.
- It does not attach to a program already running; it runs the program it launches.
- It gives the program no terminal. A program that reads its input as it is typed is run with
  `ant run`.
- It does not stop the clock while the program is stopped (section 4, All-stop).
