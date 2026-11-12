# Ant Standard Library: I/O Namespaces

Companion to `ant-lang.md`. The core library, which every program needs, is section 11 of the
specification. The namespaces here, and `Cmd`, a type with functions that reads like one, talk to
the world outside the program, and they follow one rule: every operation that can fail returns a
`Result` with `Error` as the error type, and nothing here panics on bad input, with these
exceptions. `Json.stringify` panics on a value that contains itself or one with no JSON form, and
`Time`, `Csv`, and `Crypto`, which are computation rather than I/O, panic where the core library
would, on an argument that cannot be, as `int8(300)` does. The comment of each such function says
when it panics. Blocking calls block only the calling goroutine (section 9).

A type a namespace declares is written through the namespace, `Json.Value` or `Http.Response`, since
a namespace that no type declares is reached only through `.` (section 10, Namespaces), and a value
of such a type reaches the namespace's functions through `.` as well, `h.writeLine(line)` for
`File.writeLine(h, line)` (section 5, Calls through `.`). A parameter with a default may be omitted
or named at the call, as for a declared function (section 6, Calling). A function that blocks takes
a context as its last parameter, `ctx: Context | null = null`, and when the context is done gives up
with `Err` and the context's reason as the message, as section 9 (Waiting) has it. A call that takes
a path, an address, or a URL names it in an `Err`'s message. A call on a handle, which may have no
path, and a context's reason name no target, so the caller adds it (section 8, Wrapping errors). The
namespaces are smaller than the Go packages behind them; a function is added when a program needs
it, and what is here is complete as written.

## File

```
type Handle                                                // opaque: an open file, a standard stream, a connection, or a buffer over one
type Info = { name: string, size: int, isDir: bool, isSymlink: bool, modified: Time.Instant, mode: int }

File.read(path: string): Result[string, Error]
File.readBytes(path: string): Result[Bytes, Error]
File.write(path: string, text: string, replace: bool = true): Result[void, Error]   // creates the file, or replaces what it held, keeping its mode
File.writeBytes(path: string, bytes: Bytes, replace: bool = true): Result[void, Error]   // likewise
File.exists(path: string): bool                            // anything at path that stat can reach, a directory included; false at a dangling link and when stat is Err for any reason
File.stat(path: string, follow: bool = true): Result[File.Info, Error]   // follow: false describes a link itself
File.chmod(path: string, mode: int): Result[void, Error]   // sets the bits in 0o7777 exactly
File.touch(path: string, time: Time.Instant | null = null): Result[void, Error]   // sets modified to time, or now; creates an empty file when missing
File.remove(path: string): Result[void, Error]             // one file, or an empty directory; Err when nothing is there
File.removeAll(path: string): Result[void, Error]          // a whole tree; Ok when nothing is there and the path could hold something; Err for . and ..
File.rename(from: string, to: string): Result[void, Error] // replaces a file at to; Err when a directory is at to, since there is no "into" form, and across file systems; Ok and nothing changes when from and to are the same file
File.copy(from: string, to: string, replace: bool = true): Result[void, Error]   // one file's contents and mode; replaces a file at to
File.copyAll(from: string, to: string): Result[void, Error]   // a file or a whole tree; to must not exist, or be an empty directory
File.mkdir(path: string): Result[void, Error]              // with its parents, each made as the path names it, so x/../y makes x too; Ok when it exists
File.tempFile(pattern: string, dir: string | null = null): Result[string, Error]   // a new empty file, mode 0o600, in dir or the host's temporary directory
File.tempDir(pattern: string, dir: string | null = null): Result[string, Error]    // a new empty directory, mode 0o700, likewise
File.symlink(target: string, link: string): Result[void, Error]   // makes link, pointing at target
File.readLink(path: string): Result[string, Error]         // a link's target, as stored
File.realPath(path: string): Result[string, Error]         // absolute and clean, with every link resolved
File.list(dir: string): Result[Array[string], Error]       // the names in dir, in lexical order
File.walk(dir: string): Result[Array[string], Error]       // every file below dir, as paths relative to it
File.glob(pattern: string, dir: string = ".", hidden: bool = false): Result[Array[string], Error]   // the paths below dir that match pattern, in lexical order

File.open(path: string): Result[File.Handle, Error]        // for reading; a directory opens, and a read of it is Err
File.create(path: string, replace: bool = true): Result[File.Handle, Error]   // for writing; truncates
File.append(path: string): Result[File.Handle, Error]      // for writing at the end; creates
File.lock(path: string, ctx: Context | null = null): Result[File.Handle, Error]   // for reading and writing, holding the file's lock; waits for it
File.tryLock(path: string): Result[File.Handle | null, Error]   // likewise; null when another handle holds the lock
File.isTerminal(f: File.Handle): bool                      // f is a terminal, as [[ -t 1 ]] asks of standard output
File.readLine(f: File.Handle, ctx: Context | null = null): Result[string | null, Error]   // the line without its \n or \r\n; null at end of file
File.readAll(f: File.Handle, ctx: Context | null = null): Result[string, Error]           // the rest of the file
File.writeLine(f: File.Handle, line: string): Result[void, Error]
File.writeText(f: File.Handle, text: string): Result[void, Error]   // writeLine without the newline
File.readChunk(f: File.Handle, max: int, ctx: Context | null = null): Result[Bytes | null, Error]   // what is there, 1 to max bytes; null at end of file
File.readExactly(f: File.Handle, n: int, ctx: Context | null = null): Result[Bytes | null, Error]   // n bytes; null at end of file; Err when it ends partway
File.writeChunk(f: File.Handle, bytes: Bytes): Result[void, Error]
File.pipe(src: File.Handle, dst: File.Handle, ctx: Context | null = null): Result[void, Error]   // copies the rest of src to dst
File.buffered(f: File.Handle, size: int = 4096): File.Handle   // a handle over f whose writes are held until full, flush or close
File.flush(f: File.Handle): Result[void, Error]            // hands what was written to f to the OS; Ok on a handle not buffered
File.close(f: File.Handle): Result[void, Error]            // a buffered handle writes out first; Ok on a standard stream and on a closed handle
```

`File.list` returns names and `File.walk` paths: `walk` descends into every directory below `dir`,
does not follow symbolic links, lists files and not directories, and returns them in lexical order.
Lexical order is the order in which strings compare, code point by code point, so `"10.txt"` comes
before `"9.txt"` and `"Zeta"` before `"apple"`. `modified` is the time of the last write, and `mode`
holds the permissions (see Modes). `isSymlink` is true only for `stat(path, follow: false)` of a
link, since `stat` otherwise describes what the link points at. `name` is the last element of
`path`, `Path.base(path)`, also when a link is followed. `size` is the length of a regular file in
bytes; for a directory, and for a link described with `follow: false`, it is what the host reports,
as is a link's own `mode`, so a program does not rely on them. `remove` refuses a directory with
entries; `removeAll` is the recursive form, named so the dangerous one is the longer name.

A path is used as written: `~` and `$NAME` are not expanded as a shell expands them, so a path under
the home directory is `Path.join([try Os.home(), ...])`. A relative path is taken against the
working directory, in every `File` function and in `Path.abs`. An empty path is `Err` in every call
that takes one; `File.exists("")` is false. Only `mkdir` creates missing directories: every other
function that creates a file, a directory or a link, `write`, `writeBytes`, `create`, `append`,
`touch`, `lock`, `tryLock`, `copy`, `copyAll` and `symlink`, is `Err` when the directory that would
hold it is missing, and those that write a file are `Err` when a directory is at the path.

`File.read`, `readLine`, and `readAll` take what they read as text, decoded as all text from outside
is (section 11 of `ant-lang.md`, String); `File.readBytes`, `readChunk`, and `readExactly` keep the
bytes as they are. The reads of a handle share one buffer, so a program can read a header line by
line and the body after it as bytes. `readChunk` returns as soon as there is anything to return, at
least one byte and at most `max`, and waits only while there is nothing; it is the read for a stream
whose pieces have no fixed size. `readExactly` waits for all `n` bytes, the read for a protocol that
announces a length, and is `Err` with the message `unexpected end of file` when the input ends after
some of them, which are discarded, since they are no whole message; `n` of 0 gives empty `Bytes`
without reading, at the end of the file too. A `max` below 1 or an `n` below 0 is `Err`.
`writeChunk` writes the bytes as they are, as `writeText` writes text as UTF-8. A read of a handle
opened only for writing, and a write to one opened only for reading, is `Err`.

A handle is also a connection from `Net`, and the reads and writes are the same. A context
interrupts a read of a connection, a pipe or a terminal, which are the handles that wait; a read of
a regular file never waits, so there the context is looked at only before the read begins. A read
the context ended loses nothing: what it had consumed is kept for the next read of the handle, which
stays open, so a line that arrives late is read whole by the read that comes next. One goroutine may
read a handle while another writes it; a second reader waits for the first and gives up on its own
context; and `File.close` from any goroutine ends a read or a write in progress with an `Err`.

A write is handed to the OS before it returns, all of its bytes or `Err`, as in Go; nothing is held
back, so nothing needs a flush. How many system calls it takes is not promised. `File.pipe` writes
each chunk as it reads it: first what `src` had read ahead, then a chunk at a time until the end of
`src`, so a source that waits, such as standard input or a connection, streams, and what it read
before its context ended it has been written. `src` and `dst` may be the same connection, which
echoes; for a file they may not, which is `Err`. `pipe` closes neither.

`File.buffered` is the opt-in for a loop of many small writes, Go's `bufio.Writer` as a handle. A
write to the handle it returns goes into a buffer of `size` bytes, which is written to `f` when a
write does not fit, at `File.flush` and at `File.close`, and at nothing else: no wait, no read and
no exit. A write to a buffered handle over a handle that cannot be written, such as one from
`File.open`, is `Err` at once and buffers nothing. A buffered handle neither flushed nor closed when
the run ends loses what its buffer holds, as a Go program that returns from `main` without `Flush`
does. A `size` below 1 gives the default. When `f` is itself buffered with a buffer of at least
`size`, `File.buffered` returns `f`. A read of the buffered handle reads `f`, through its one read
buffer, so a buffered connection can `readLine` a reply after `File.flush` sends the request.
`File.flush` writes out every layer, the handle's buffer and then that of each buffered handle under
it, so after it everything written has been handed to the OS; on a handle that is not buffered it
does nothing and is `Ok`, so a function may flush a handle without knowing what it is. The first
error from writing the buffer out is kept, and every later write and flush returns it, as does the
first close. A write to `f` itself, or a `print` while `File.buffered(Os.stdout())` holds output,
goes past the buffer and can come out before what the buffer holds.

`File.close` of a buffered handle writes the buffer out and closes `f`, and reports the first error
of the two, the kept error included; on a standard stream it writes out and leaves the stream open.
When a write or flush of the buffered handle is in progress on another goroutine, as when it waits
on a peer that stopped reading, the close does not wait behind it: it closes `f` at once, the write
ends with `Err`, and the close is `Err` when what the buffer held is lost. Over a standard stream,
which a close leaves open and which nothing can interrupt, the close waits for the write and then
writes out. A close can fail, of a file as of a buffer, so a program that promises its output checks
it, as `try File.close(output)`. A deferred close cannot report, since a deferred block's value is
discarded. So a function that writes a file ends with an explicit close, and the deferred close of
the same handle, there for the paths that leave early, then does nothing and is `Ok`, as every close
after the first is. The handle is closed even when `File.close` is `Err`, so a read or a write after
it is `Err`, as is a flush of a buffered handle, and a second close does nothing.

```ant
func writeReport(path: string, rows: Array[string]): Result[void, Error] {
  let out = File.buffered(try File.create(path))
  defer { File.close(out) }
  for row in rows { try File.writeLine(out, row) }
  File.close(out)
}
```

`File.isTerminal` is true when `f` is a terminal, as `[[ -t 1 ]]` asks of standard output, so a
program colours its output or shows progress only when a person is watching:
`File.isTerminal(Os.stdout())`. It is false for a file, a pipe and a connection, and for a closed
handle, which is no longer anything; a handle from `File.buffered` answers for the handle under it.

### Modes

`mode` holds the permission bits and the setuid, setgid and sticky bits, `0o4000`, `0o2000` and
`0o1000`, so it is a number in `0 ..= 0o7777`, written as an octal literal such as `0o644` (section
2 of `ant-lang.md`) and printed by `String.fromInt(mode, base: 8)`. What kind of file it is, `isDir`
and `isSymlink` say, not `mode`. `chmod` sets the bits exactly and is `Err` for a mode outside that
range.

A new file is created with `0o666` and a new directory with `0o777`, less the process's umask, as
the shell creates them, so under the usual umask `022` they are `0o644` and `0o755`. That is how
`write`, `writeBytes`, `create`, `append`, `mkdir`, `touch`, `lock` and `tryLock` create. A file
that exists keeps its mode when they write it, as Go's `os.WriteFile` keeps it. `chmod`, `copy`,
`tempFile` and `tempDir` set their modes exactly, without the umask.

There is no mode parameter on `write` or `create`, since it could apply only to a file that is new.
A file that must not be readable by others, such as a token, is written as a temporary file beside
its destination, which is `0o600` from the start, and renamed into place, which also means a reader
never sees it half-written:

```ant
func saveToken(path: string, token: string): Result[void, Error] {
  let tmp = try File.tempFile(".token-*", dir: Path.dir(path))
  defer { File.remove(tmp) }       // Err after the rename, and discarded
  try File.write(tmp, token)       // still 0o600, since the file exists
  File.rename(tmp, path)
}
```

These guarantees are Unix's, as Go's are. `rename` replaces `to` atomically on Unix, so a reader
sees the old file or the new one; elsewhere it is not promised to be atomic, as Go's `os.Rename` is
not. On Windows a mode is Go's reading of the read-only attribute, the only one there is: `stat`
gives a file `0o444` when it is read-only and `0o666` when not, adding `0o111` for a directory, and
`chmod` sets the attribute when `0o200` is clear and ignores the other bits. Who may read a file is
decided there by its access control list, which a new file inherits from its directory, and Ant sets
none, as Go does not. The default temporary directory on Windows is under the user's profile, so a
temporary file there is the user's alone; one made elsewhere is as private as its directory.

There is no test of whether a file could be written. The mode cannot tell, since the owner, the
group, root, access control lists and read-only mounts decide as well, and an answer would be stale
by the time it was used. A program tries instead: `File.tempFile("probe-*", dir: dir)` is `Ok` when
it can create files in `dir`.

### Temporary files

`tempFile` and `tempDir` create a file or a directory under a name nothing else has, so only the
user can use it: the file with mode `0o600`, created only if the name is free, so a link someone
planted at the name cannot redirect it, and the directory with `0o700`. The name is `pattern` with
its last `*` replaced by a random string, or with the random string appended when there is no `*`,
as Go's `os.CreateTemp` names files, so `"report-*.csv"` keeps its extension. A `pattern` that holds
a path separator is `Err`. `dir` is the host's temporary directory when null: `$TMPDIR`, or `/tmp`
when that is unset, on Unix, and `%TEMP%` on Windows. Both return the path. Nothing removes what
they make, at exit or later, so the program removes it, usually as `defer { File.removeAll(dir) }`,
and before `Os.exit`, which runs no deferred block.

### Not replacing

`write`, `writeBytes`, `create` and `copy` replace what is at the path. With `replace: false` they
create the file only if nothing is there, in one step the OS makes atomic, Go's `O_CREATE|O_EXCL`,
and are otherwise `Err` with the OS's message, such as `open out.txt: file exists`, having changed
nothing. Anything at the path counts, a directory and a link included, even a link that leads
nowhere, which is not followed, so a link planted at the name cannot redirect the write. It is the
shell's `noclobber` and `cp -n`, and it holds even against a program that takes no lock:

```ant
try File.write(output, report, replace: false)   // never overwrites an earlier report
```

The `Err` does not say why, as no library `Error` does, so a program that treats an existing file
differently from other failures checks `File.exists` after it. `append` never replaces, `copyAll`
and `symlink` already refuse what exists, and `tempFile` picks a free name, so they have no such
parameter; neither has `rename`, since Go has no rename that refuses to replace.

### Copies

`copy` copies one regular file: its contents, and then its mode, exactly. A source that is not one,
such as a FIFO or a device, is `Err`, and is not opened, since opening a FIFO waits for a writer and
`/dev/zero` never ends. It replaces a file at `to`, as `write` and `rename` do, and is `Err` when
`to` is a directory, since there is no "into" form: `Path.join` says where. It follows a link at
either end: the contents copied are those of the link's target, and a link at `to` has its target
replaced, or created when the link dangles, as `write` does through it. To replace the link itself,
`remove` it first. The times are not copied, so the copy is new to a build tool, and the copy is not
atomic: a reader can see `to` half-written, which a copy to a temporary file and a `rename` avoid.

`copyAll` is the recursive form, named so the bigger operation has the longer name. It copies a file
as `copy` does, or a whole tree: every directory and file with its mode, and every link inside the
tree as a link with the same target, not followed, as `cp -R` copies them, so a cycle cannot loop; a
link at `from` itself is followed. `to` must not exist, or, for a tree, be an empty directory, which
becomes the root of the copy and keeps its own mode, so a `tempDir` stays `0o700`. Anything else at
`to` is `Err` before anything is copied, so two trees are never merged. An error partway through
leaves what was copied.

Neither copies a thing onto itself, which would truncate the source before reading it. Before
changing anything, both are `Err` when `from` and `to` are the same file, decided by identity,
device and inode as Go's `os.SameFile` decides, not by name, so `./a` and a link at `to` that leads
to `a` are caught; and `copyAll` is `Err` when `to`, with its links resolved, lies inside `from`, as
`copyAll("src", "src/backup")` would copy its own copy.

### Links

`symlink` makes a symbolic link at `link` whose target is the text `target`, in the order of
`ln -s target link`. A relative target is relative to the link's directory, not to the working
directory, and nothing needs to exist at it. `symlink` is `Err` when anything is at `link`. On
Windows it makes a directory link when `target` is an existing directory and a file link otherwise,
and is `Err` without Developer Mode or administrator rights. `readLink` returns a link's target as
stored, and is `Err` when `path` is not a link. `realPath` returns the path absolute and clean with
every link along it resolved, and is `Err` when the path, or a link on the way, leads nowhere;
`Path.abs`, by contrast, looks only at the text.

What each function does at a link:

| Function                                                                                   | At a link                                                                                                       |
| ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `read`, `write`, `open`, `create`, `append`, `chmod`, `touch`, `lock`, both ends of `copy` | follows it; with `replace: false`, a link at the path, dangling or not, is `Err`                                |
| `exists`                                                                                   | follows it, so a dangling link is `false`                                                                       |
| `stat`                                                                                     | follows it, unless `follow` is `false`                                                                          |
| `remove`, `rename`                                                                         | acts on the link, not on its target                                                                             |
| `removeAll`                                                                                | removes the link, never what it points at                                                                       |
| `list`, `walk`                                                                             | follow it at `dir`; inside, `list` lists its name and `walk` does not descend through it and lists it as a file |
| `mkdir`                                                                                    | follows it, so a link to a directory is `Ok` and a dangling link is `Err`                                       |
| `glob`                                                                                     | `**` does not descend through it; another element of the pattern goes through it                                |
| `copyAll`                                                                                  | copies it as a link inside the tree; follows it at `from`                                                       |
| `realPath`, `readLink`                                                                     | resolves it, or reads it                                                                                        |

### Globs

`glob` returns the files and directories below `dir` whose path relative to `dir` matches `pattern`
(see Path for the syntax), as paths relative to `dir`, so `Path.join([dir, p])` reaches each, as
`walk`'s do. `dir` is a parameter and not part of the pattern so that a directory whose name holds
`*` or `[` needs no escaping. An absolute pattern ignores `dir` and gives absolute paths, as does
one with a root and no volume on Windows, `\x`, which is on the drive of the working directory.

```ant
for path in try File.glob("*.txt") { println(path) }        // a.txt, b.txt; not .notes.txt
let tests = try File.glob("**/*_test.ant", dir: root)
let dirs = try File.glob("*/")                              // directories only: src/, tests/
```

The paths are cleaned, each comes once, and they are in lexical order element by element, the order
of `walk`, so `a/x` comes before `a-b/x`. A pattern that ends in a separator matches directories
only, a link to one included, and each path keeps the separator, as `src/`. Nothing matching is `Ok`
with an empty array, never the pattern back as the shell gives it. `glob` reads only the directories
the pattern leads into: `src/*/main.ant` reads `src` and its subdirectories, not the rest of `dir`.

An element without wildcards is looked up as it is, through a link, and the path that comes back is
spelled as the pattern spells it, so on a file system that ignores case `README.MD` finds
`README.md` and returns `README.MD`. A wildcard element reads the directory and matches each name,
going through a link to a directory to the next element, as `ls link/*` does. `**` does not descend
through a link, as `walk` does not, and matches the link by its name. A dangling link is matched by
its name. An element `..` steps back on the text, as `Path.join` does, so `link/../x` is `x` below
`dir`, not beside the link's target, as Go's `filepath.Glob` has it.

`glob` is `Err` on a malformed pattern before it reads anything, when `dir` is not a directory, and
when a directory the pattern leads into cannot be read, as `walk` is; a directory missing below
`dir`, as `missing/*.txt` asks for, is no match.

### Times

`touch` sets a file's modified time, and its access time with it, to `time`, or to now when `time`
is null, and creates an empty file when nothing is at `path`, as the shell's `touch` does; it never
truncates. A stamp file is `try File.touch(stamp)`, and `modified` from `stat` reads it back,
rounded as the file system keeps times: to 2 seconds on FAT, to the second on HFS+, to the
nanosecond on ext4 and APFS. The access time is not in `File.Info`, since many systems are mounted
not to keep it.

### Locks

`lock` and `tryLock` let one process at a time do something, such as a script that cron starts again
while its last run is still going. Each opens `path` for reading and writing, creating it empty when
it is missing and never truncating it, and takes an exclusive lock on the whole file. `lock` waits
until no other handle holds the lock, or until `ctx` is done, and is then `Err` with the context's
reason; `tryLock` does not wait, and is `Ok(null)` when another handle holds it. `Err` is left for a
real failure, such as a directory that cannot be written.

```ant
let lock = try File.tryLock(Path.join([try Os.cacheDir(), "backup.lock"]))
if lock == null {
  eprintln("backup: already running")
  Os.exit(1)
}
```

The lock belongs to the handle. A second handle on the same file conflicts with it even in the same
process, so a lock orders goroutines too. Closing the handle releases it, and the OS releases it
when the process ends, however it ends, a crash and `kill -9` included, so a lock is never left
stale, as a pid file is. A child process that another goroutine starts as the handle closes holds a
copy of it until the child's program has started, so the release can come a moment after the close;
a program that locks again at once uses `lock`, which waits, rather than `tryLock`. Closing is the
one release, so there is no unlock, and a `File.buffered` over the handle writes out at its close
before the lock goes. The file stays after the close, since removing it would race with a process
that has just opened it to lock it, and the next lock reuses it. A program may write its pid into
the file for people to read; whether the lock is held is what `tryLock` answers, not what the file
says. The lock is `flock`'s on Unix and `LockFileEx`'s on Windows: advisory on Unix, so it keeps out
only processes that lock too, and mandatory on Windows, where other processes cannot read or write
the file while it is held.

## Http

```
type Response = { status: int, headers: Map[string, string], body: string, bytes: Bytes }
type Request = { method: string, path: string, query: string, headers: Map[string, string],
                 body: string, bytes: Bytes, remote: string }
type Reply = { status: int, headers: Map[string, string], body: string | Bytes }

Http.request(method: string, url: string, body: string | Bytes = "",
             headers: Map[string, string] = Map{}, timeout: Time.Duration | null = null,
             ctx: Context | null = null): Result[Http.Response, Error]
Http.get(url: string, headers: Map[string, string] = Map{}, timeout: Time.Duration | null = null,
         ctx: Context | null = null): Result[Http.Response, Error]                // request("GET", url, "", headers, timeout, ctx)
Http.post(url: string, body: string | Bytes, headers: Map[string, string] = Map{},
          timeout: Time.Duration | null = null, ctx: Context | null = null): Result[Http.Response, Error]
                                                                                  // request("POST", url, body, headers, timeout, ctx)
Http.serve(l: Net.Listener, handler: func(Http.Request): Http.Reply,
           ctx: Context | null = null): Result[void, Error]                       // panics on a response status outside 200 to 599, or on header names that differ only in case, in the handler's goroutine
```

`request` sends one request with `method` as given, `GET`, `PUT`, `DELETE`, or any other token,
`body` as its body, and `headers` as its headers, and reads the whole response. A response of any
status is `Ok` with that `status`, a redirect included: no redirect is followed, so a 3xx comes back
with its `Location` header, and a program that wants the next page asks for it. `Err` is a failure
to get one: a malformed `url`, an empty `method`, two header names that differ only in case, which
name one header, no connection, the timeout, or the context. The response's headers hold one string
per name, a repeated header joined with `, `. `get` and `post` are `request` with the method filled
in.

A body is sent as given: a string as its UTF-8, `Bytes` as they are. A body that arrives, in a
`Response` or in a `Request`, is there twice: as received in `bytes`, and in `body` as text, decoded
as all text from outside is (section 11 of `ant-lang.md`, String). When the bytes are UTF-8 the two
share one copy, so a program reads whichever it needs at no cost: `body` for JSON or HTML, `bytes`
for an image, or for a signature computed over what was sent. A handler returns an `Http.Reply`,
whose body is a string or `Bytes`, so a proxy passes `bytes` on unchanged.

`timeout` bounds the whole call, from connecting to the end of the body, and when it passes the
result is `Err` with the message `timeout`. The duration is taken as `Time.total` takes one without
a `relativeTo`: hours and smaller units are exact and a day is 24 hours, while years, months, and
weeks have no fixed length, so a duration with any of them is `Err` before anything is sent. A zero
or negative duration is `Err` too, since a request that has already timed out is a mistake. A
duration beyond what the host can wait, about 292 years, is taken as that. `null` sets no deadline
of its own; a run the host cancels ends the call regardless. These are `Err` and not panics because
`Http` is I/O and follows the rule above. `ctx` bounds the call as well, and when both are given the
earlier wins: a one-off bound is a `timeout`, a bound shared with other work is a context.

`serve` answers every request that arrives on `l` by calling `handler` on a goroutine of its own, as
section 9's goroutines, and returns `Ok` once `ctx` is done and the requests in flight have
finished, waiting at most five seconds for them before it closes their connections; with `null` it
serves until the run is cancelled. The listener is closed once `serve` returns. It is `Err` when the
listener is closed under it. A handler's panic is reported as a goroutine's panic is, and the client
gets status 500 with an empty body; a response whose status is outside 200 to 599 is a panic in the
handler's goroutine, which takes the same path, since a status below 200 is an interim response and
cannot be sent as the final one. So is a reply with two header names that differ only in case, which
name one header, as `request` is `Err` on them. The `Http.Reply` is sent as given, with
`Content-Length` from the body. In the `Request`, `path` is decoded and `query` is raw, for
`Url.parseQuery`; the headers hold one string per name, `Host` among them, a repeated header joined
with `, `; `remote` is `ip:port`. Bodies are read whole, as the client reads them. Taking a listener
rather than an address is what lets a program know its port, run the server on a goroutine, and talk
to it:

```ant
func handle(req: Http.Request): Http.Reply {
  if req.path == "/health" { Http.Reply{ status: 200, headers: Map{}, body: "ok" } }
  else { Http.Reply{ status: 404, headers: Map{}, body: "no ${req.path}" } }
}

var listener = Result.unwrap(Net.listen(":8080"))
println("listening on ${Net.address(listener)}")
var stop = Os.interrupt()
var served = Http.serve(listener, handle, stop)
println("stopped: ${Context.reason(stop) ?? "?"}")
```

## Net

```
type Listener                                                    // opaque: a listening TCP socket

Net.listen(addr: string): Result[Net.Listener, Error]            // "host:port"; ":0" takes any free port
Net.address(l: Net.Listener): string                             // the address it listens on, "127.0.0.1:50321"
Net.accept(l: Net.Listener, ctx: Context | null = null): Result[File.Handle, Error]   // the next connection; Err when closed, or with ctx's reason
Net.close(l: Net.Listener): void                                 // pending and later accepts return Err; nothing twice
Net.dial(addr: string, ctx: Context | null = null): Result[File.Handle, Error]        // a connection to "host:port"
Net.peer(f: File.Handle): string | null                          // the other end of a connection, "ip:port"; null for a file or a stream
```

A connection is a `File.Handle`, so `File.readLine`, `readAll`, `writeLine`, `writeText`, `pipe` and
`close` need nothing new, and a line protocol is a loop over `readLine`. Several goroutines may
`accept` on one listener, each with a context of its own, and each connection goes to one of them.
TCP only: there is no TLS, UDP or Unix socket.

## Path

Pure functions over paths in the host's convention: `/` on Unix, `\` and drive letters on Windows.

```
Path.join(parts: Array[string]): string          // joins with the separator and cleans the result
Path.base(p: string): string                     // the last element; "." for ""
Path.dir(p: string): string                      // all but the last element; "." when there is none
Path.ext(p: string): string                      // ".ant", or "" when there is none
Path.clean(p: string): string                    // the shortest equivalent path
Path.isAbs(p: string): bool
Path.abs(p: string): Result[string, Error]       // against the working directory
Path.rel(base: string, target: string): Result[string, Error]   // target as a path from base
Path.match(pattern: string, path: string, hidden: bool = false): Result[bool, Error]   // path matches the glob pattern; Err when the pattern is malformed
```

`Path.join` of no parts, or of empty ones only, is `.`, as `Path.clean("")` is.

`Path.rel` works on the text, cleaned, and is `Err` when no relative path leads from `base` to
`target`: when one is absolute and the other is not, when they are on different Windows volumes, or
when `base` climbs out with `..` further than `target` does, as from `../a` to `b`.

`Path.match` matches the whole of `path` against a glob pattern, the syntax `File.glob` takes. Both
are split into elements at the separator, and each element of the pattern matches one element of the
path, except `**`:

| Pattern  | Matches                                                                             |
| -------- | ----------------------------------------------------------------------------------- |
| `*`      | any run of code points within one element, the empty one included                   |
| `?`      | one code point                                                                      |
| `[abc]`  | one code point of the set; `[a-z]` a range of code points                           |
| `[^a-z]` | one code point not in the set; `[!a-z]` is the same                                 |
| `\*`     | `*` itself, and likewise any code point, on Unix; on Windows `\` is a separator     |
| `**`     | as a whole element, zero or more elements; as the last, one or more; elsewhere, `*` |
| other    | itself                                                                              |

This is the syntax of Go's `filepath.Match` with `**` and `[!...]` added. In a set, `-` and `]` are
written `\-` and `\]` on Unix; a set left open, an empty set, a range whose end comes before its
start, and a `\` at the end of an element are malformed. On Windows both `/` and `\` separate, so a
pattern written with `/` works on every system, and brackets escape instead: `[*]`, `[?]`, `[[]`.
`**/*.ant` matches `a.ant` and `x/y/a.ant`; `src/**` matches everything below `src`, but not `src`.

A wildcard does not match a `.` that begins an element: `*` matches `a.txt` and not `.env`, `?ab`
does not match `.ab`, and `**` does not take an element that begins with `.`, so it does not descend
into `.git`. An element of the pattern that begins with a literal `.`, as `.*`, matches them, and
`hidden: true` lifts the rule. The elements `.` and `..` are matched only by themselves. Wildcards
compare code points exactly on every system, as Go's do, so `*.TXT` does not match `a.txt`.

`Path.match` looks only at the text, as the other `Path` functions do, and does not clean `path`:
`Path.match("*.txt", "./a.txt")` is `Ok(false)`, and a name alone is `Path.match(p, Path.base(x))`.
A pattern that ends in a separator matches a path that does.

## Time

Dates and times follow JavaScript's Temporal: exact time and wall-clock time are different types, a
zone is named and carried, calendar arithmetic and exact arithmetic are different operations, and
nothing assumes UTC or the machine's zone. The seven types are opaque, immutable, always valid, and
compared by value. Unlike the other namespaces, `Time` is computation and panics where the core
library would: a field that cannot be panics, as `int8(300)` does, while text from the world goes
through the `parse` functions, which return `Result`.

- `Instant` is a moment on the time line: nanoseconds since the Unix epoch, with no zone and no
  calendar.
- `ZonedDateTime` is an instant seen in a zone, the only type that answers "what time is it here".
- `PlainDate`, `PlainTime` and `PlainDateTime` are what a calendar or a clock shows, with no zone: a
  birthday, an alarm, a meeting before its zone is known.
- `Zone` is a zone of the IANA database, such as `Europe/Stockholm`, or a fixed offset, such as
  `+05:30`.
- `Duration` is years, months, weeks, days, hours, minutes, seconds, milliseconds, microseconds and
  nanoseconds, all of one sign, kept as given: 90 minutes stays 90 minutes until `roundDuration`
  balances it.

Dates are in the ISO 8601 calendar, the proleptic Gregorian calendar extended to year 0 and negative
years: a year is a leap year when it is divisible by 4, except a century year not divisible by 400,
so 2000 and 0 are and 1900 is not; February has 29 days in a leap year and 28 otherwise.

Four unions name the types a function serves, and three enumerations name its options; `Time.Hour{}`
and `Time.Later{}` are values of them. Every time type has its own tag, so a union of them is legal
and `t is Time.PlainDate` narrows it (`ant-lang.md`, sections 4 and 5). A type parameter bounded by
one of the unions stands for a single member, so a value typed `Time.Dated` passes to `Time.year`
but not to `Time.add` until an `is` test narrows it:

```ant
func bump(t: Time.Dated): Time.Dated {
  let day = Time.duration(days: 1)
  if t is Time.ZonedDateTime { Time.add(t, day) }
  else if t is Time.PlainDate { Time.add(t, day) }
  else { Time.add(t, day) }
}
```

```
type Zone
type Instant
type ZonedDateTime
type PlainDate
type PlainTime
type PlainDateTime
type Duration
type Point = Instant | ZonedDateTime | PlainDate | PlainTime | PlainDateTime
type Wall = ZonedDateTime | PlainDate | PlainTime | PlainDateTime      // the types with fields
type Dated = ZonedDateTime | PlainDate | PlainDateTime                 // the types with a date
type Timed = ZonedDateTime | PlainTime | PlainDateTime                 // the types with a time
type Unit = Year | Month | Week | Day | Hour | Minute | Second | Millisecond | Microsecond | Nanosecond
type Disambiguation = Compatible | Earlier | Later
type RoundingMode = Ceil | Floor | Expand | Trunc | HalfCeil | HalfFloor | HalfExpand | HalfTrunc | HalfEven
```

**Zones.**

```
Time.utc: Time.Zone                                 // the named zone UTC, so not == to the offset zone +00:00
Time.zone(id: string): Result[Time.Zone, Error]     // a name of the IANA database in any case, or an offset
Time.localZone(): Time.Zone                         // the host's zone
Time.zoneId(z: Time.Zone): string                   // "Europe/Stockholm", "+05:30"
```

`Time.zone` accepts a name of the IANA database in any letter case, including an alias such as
`Asia/Calcutta`, and an offset `±HH:MM`, `±HHMM` or `±HH` below 24 hours, as Temporal allows;
anything else, the empty string included, is `Err`. `zoneId` returns the name as the database spells
it, or the offset as `±HH:MM`, with `+` for a zero offset, so `-00:00` gives `+00:00`. Two named
zones are equal when they are aliases of one zone in Unicode's CLDR, so `Time.zone("Asia/Calcutta")`
equals `Time.zone("Asia/Kolkata")` and `US/Eastern` equals `America/New_York`, while
`Europe/Stockholm` stays apart from `Europe/Berlin` although the IANA database has merged their
rules since 1970, as Temporal's implementations have it; two offset zones are equal when their
offsets are; a named zone never equals an offset zone. `Time.localZone()` is the zone the host's
configuration names, from the `TZ` environment variable first, with a leading `:` dropped as POSIX
allows, and the system's setting second. Each counts only when it names a zone of the database, so
an offset in `TZ`, which POSIX reads as west of UTC, is passed over; when neither does, it is the
fixed offset the host reports at the moment of the call.

**Now, and the epoch.**

```
Time.now(): Time.Instant
Time.nowIn(z: Time.Zone): Time.ZonedDateTime
Time.sleep(d: Time.Duration, ctx: Context | null = null): void   // blocks the calling goroutine; returns early when ctx is done; panics on years, months or weeks
Time.ticker(d: Time.Duration, ctx: Context | null = null): Channel[Time.Instant]   // the time, every d; panics if d is zero or negative or has years, months or weeks
Time.monotonic(): int                               // milliseconds from an arbitrary origin, for measuring
Time.fromEpochMillis(ms: int): Time.Instant         // panics on a value outside the range
Time.fromEpochNanos(ns: int): Time.Instant
Time.epochMillis(t: Time.Instant | Time.ZonedDateTime): int      // rounded down
Time.epochNanos(t: Time.Instant | Time.ZonedDateTime): int       // panics on a time outside 1677-09-21 to 2262-04-11
```

`sleep` and `ticker` take a span as `Context.new` and `Http.request` do, so every wait in the
library is a `Time.Duration`: hours and smaller units are exact and a day is 24 hours, while years,
months, and weeks have no fixed length and make it panic here, since `Time` is computation, as they
are in `Context.new`. A span beyond what the host can wait, about 292 years, is taken as that. A
zero or negative sleep returns at once. `Time.monotonic` stays an `int` of milliseconds, since it is
a reading that a program subtracts, not a span it passes. `Time.now` and `nowIn` read the wall
clock, which the host may set forward or back, so two readings can go backwards. `Time.monotonic`
reads a clock that changes to the wall clock do not affect: a later reading in the same run, on any
goroutine, is never smaller than an earlier one, and a `sleep` of `d` adds at least the whole
milliseconds of `d`. Its origin is fixed for the run.

`ticker` is Go's ticker: a channel that receives the time every `d`, counted from the call, so a
slow reader does not shift the beat. It holds one tick; a tick that finds it full is dropped, so a
reader that falls behind gets one tick and not a burst. It stops when `ctx` is done, or when the run
ends without one, as Go's `Ticker.Stop`: once the context is done no receive gets a tick, not even
the one held, and `Channel.length` is 0. The channel is never closed, so a receive or a `select`
clause on it waits for the next tick or for the context. Only the ticker sends on it, as Go's is
receive-only, so `Channel.send` and `Channel.close` on it panic. A ticker is a `select` clause like
any channel: `var at = Channel.receive(ticks) { ... }`.

Every type holds nanoseconds, and an `Instant` spans 100 million days each way from the epoch, about
270,000 years, as Temporal's does; the plain types span a day more each way. A result beyond the
range of its type panics wherever it arises, in `add`, `with`, `round`, `toZoned` and the rest, as
Temporal's RangeError is. `epochNanos` as an `int` reaches only 1677 to 2262 and panics outside,
while `epochMillis` always fits.

**Construction.**

```
Time.plainDate(year: int, month: int, day: int): Time.PlainDate                 // panics if there is no such date
Time.plainTime(hour: int = 0, minute: int = 0, second: int = 0, millisecond: int = 0,
               microsecond: int = 0, nanosecond: int = 0): Time.PlainTime      // panics if a field is out of range: hour 0 to 23, minute and second 0 to 59, the subsecond fields 0 to 999
Time.plainDateTime(date: Time.PlainDate, time: Time.PlainTime): Time.PlainDateTime
Time.duration(years: int = 0, months: int = 0, weeks: int = 0, days: int = 0, hours: int = 0,
              minutes: int = 0, seconds: int = 0, milliseconds: int = 0, microseconds: int = 0,
              nanoseconds: int = 0): Time.Duration           // panics on mixed signs, or if out of range
```

A constructor rejects what it cannot build: `Time.plainDate(2026, 13, 1)` and
`Time.plainDate(2026, 2, 30)` panic, where `with` and `add` below constrain. A program holding a
year, a month and a day from the world checks the month against 1 to 12 and the day against
`Time.daysInMonth(Time.plainDate(year, month, 1))` before it constructs, or hands the text it was
given to `parsePlainDate`. A `Duration` is bounded as Temporal's: years, months, weeks and days each
below 2^32 in magnitude, and the time part, days included at 24 hours, below 2^53 seconds in all.
Each field is an `int`, which holds less than that bound in the small units, so a function that
would give a duration with a field beyond an `int` panics: `until`, `since` or `roundDuration`
balancing a long span into nanoseconds, and `negate`, `abs` or `subtract` given a field of −2^63.

**Text.** Every value renders as its RFC 9557 string, which is ISO 8601 with the zone in brackets,
and parses back from it; `String.from`, string interpolation and `Json.stringify`, which writes a
time value as a JSON string, all use that form. The value parsed back is equal to the one rendered,
except that a `Duration` parses back with its fraction spread as below:
`Time.duration(milliseconds: 1500)` renders as `PT1.5S` and parses back as 1 second and 500
milliseconds, which `Time.compareDuration` finds equal and `==` does not.

```
Time.parseInstant(s: string): Result[Time.Instant, Error]            // 2026-10-22T14:03:05Z
Time.parseZoned(s: string, disambiguation: Time.Disambiguation = Time.Compatible{}):
    Result[Time.ZonedDateTime, Error]                                // 2026-10-22T16:03:05+02:00[Europe/Stockholm]
Time.parsePlainDate(s: string): Result[Time.PlainDate, Error]        // 2026-10-22
Time.parsePlainTime(s: string): Result[Time.PlainTime, Error]        // 14:03:05.123
Time.parsePlainDateTime(s: string): Result[Time.PlainDateTime, Error]   // 2026-10-22T14:03:05
Time.parseDuration(s: string): Result[Time.Duration, Error]          // P1Y2M3DT4H5M6.5S, -PT1H, PT0S
```

The forms: an `Instant` is `2026-10-22T14:03:05.5Z`; a `ZonedDateTime` is
`2024-11-03T01:00:00-04:00[America/New_York]`, offset and zone both, so the exact moment survives a
round trip even where the wall-clock time is ambiguous, with the offset rounded to the minute, since
RFC 9557 has no seconds in it, where `Time.offset` keeps the seconds of a historical offset; a
`PlainDate` is `2026-10-22`, a `PlainTime` `14:03:05`, a `PlainDateTime` `2026-10-22T14:03:05`; a
`Duration` is `P1Y2M3DT4H5M6.5S` with the fields as given, the subsecond fields folded into the
seconds, a sign in front when negative, and `PT0S` when zero; a `Zone` is its identifier. The
fractional second is written to its last nonzero digit and omitted when zero, and a year outside 0
to 9999 as a sign and six digits.

Parsing takes the date `YYYY-MM-DD`, or `±YYYYYY-MM-DD` with a sign and six digits of year, the form
a year outside 0 to 9999 renders in, the time `HH:MM`, `HH:MM:SS` or `HH:MM:SS.F` with up to nine
digits of fraction, `T` or a space between them, `Z` or an offset `±HH:MM`, a zone in brackets and
then `[u-ca=iso8601]`, each where its type needs it. Other spellings of ISO 8601 and RFC 9557 are
`Err`: a lowercase `t` or `z`, a comma before the fraction, an offset `±HH` or `±HHMM`, an offset
with seconds `±HH:MM:SS`, a `T` before a time with no date, the critical flag `[!...]`, an
annotation other than the zone and `[u-ca=iso8601]`, the calendar in capitals, and a leap second
`:60`. `parseInstant` needs a date, a time and `Z` or an offset, and ignores a bracketed zone.
`parseZoned` needs a bracketed zone, which is read as `Time.zone` reads a name, in any letter case,
and renders as the database spells it; with a date alone it is the start of that day in the zone, as
`startOfDay` is; with no offset it resolves the wall-clock time by `disambiguation`, with `Z` it
takes the exact moment and shows it in the zone, and with an offset that is not the zone's at that
time, rounded to the minute as the string has it, it is `Err`. The plain parsers accept any of the
forms above and keep their own part: the whole string must still be well formed, with a date that
exists, a time in range and a valid offset, while the name in a bracketed zone is not looked up. So
`parsePlainDate` accepts a bare date or a full zoned string, `parsePlainTime` a bare time or a date
and time, and `parsePlainDateTime` a date and time; `"2026-10-22 trailing"` and `"2026-02-30T10:00"`
are `Err` to all three, and none accepts `Z` without a bracketed zone, since `Z` names a moment, not
a wall-clock time. `parseDuration` takes ISO 8601's `PnYnMnWnDTnHnMnS` with an optional leading
sign, in capitals, where only the last time component may carry a fraction, after a point and of up
to nine digits; lowercase letters and a comma are `Err`, as above. A fraction is spread into the
smaller fields, as Temporal does: `PT1.5H` is `PT1H30M`, and a fraction of a second goes to
milliseconds, microseconds and nanoseconds, three digits each, so `PT1.5S` is 1 second and 500
milliseconds. A string in another calendar is `Err`.

**Conversion.**

```
Time.inZone(t: Time.Instant, z: Time.Zone): Time.ZonedDateTime
Time.withZone(t: Time.ZonedDateTime, z: Time.Zone): Time.ZonedDateTime      // the same instant in another zone
Time.toZoned(t: Time.PlainDateTime, z: Time.Zone,
             disambiguation: Time.Disambiguation = Time.Compatible{}): Time.ZonedDateTime
Time.possibleInstants(t: Time.PlainDateTime, z: Time.Zone): Array[Time.Instant]   // 0 in a gap, 2 in an overlap, else 1; earliest first
Time.toInstant(t: Time.ZonedDateTime): Time.Instant
Time.toPlainDate(t: Time.ZonedDateTime | Time.PlainDateTime): Time.PlainDate
Time.toPlainTime(t: Time.ZonedDateTime | Time.PlainDateTime): Time.PlainTime
Time.toPlainDateTime(t: Time.ZonedDateTime): Time.PlainDateTime
Time.startOfDay(t: Time.ZonedDateTime): Time.ZonedDateTime                  // the first instant of its date
Time.zoneOf(t: Time.ZonedDateTime): Time.Zone
Time.offset(t: Time.ZonedDateTime): string                                  // "+02:00"; with seconds when there are some
Time.offsetSeconds(t: Time.ZonedDateTime): int
Time.hoursInDay(t: Time.ZonedDateTime): float64                             // 23.0, 24.0 or 25.0; 23.5 or 24.5 on Lord Howe Island
Time.nextTransition(t: Time.ZonedDateTime): Time.ZonedDateTime | null       // the next change of offset after t
Time.previousTransition(t: Time.ZonedDateTime): Time.ZonedDateTime | null   // the last one before t
```

A wall-clock time in a zone has one instant, none when a daylight-saving change skipped it, or two
when a change repeated it. `disambiguation` says which to take. In a gap there is no instant, so the
time is read with the offset from before the change for `Later` and `Compatible`, which moves it
forward by the length of the gap, and with the offset from after it for `Earlier`, which moves it
back: 02:30 in New York on the spring change is 03:30 by `Later` and 01:30 by `Earlier`. In an
overlap `Compatible` and `Earlier` take the earlier instant and `Later` the later. `Compatible` is
what the common libraries do. A program that wants to refuse an ambiguous time tests the length of
`possibleInstants`. `startOfDay` is the first instant of the date in the zone, which is not midnight
on a day whose midnight falls in a gap. `nextTransition` is the earliest moment after `t` at which
the zone's offset changes, in the same zone, or `null` when there is none, as for an offset zone or
a zone that has stopped changing; `previousTransition` is the latest before `t`.

**Fields.**

```
Time.year(t: Time.Dated): int
Time.month(t: Time.Dated): int                      // 1 to 12
Time.day(t: Time.Dated): int
Time.dayOfWeek(t: Time.Dated): int                  // 1 Monday to 7 Sunday, as ISO 8601
Time.dayOfYear(t: Time.Dated): int                  // 1 to 365, or 366 in a leap year
Time.weekOfYear(t: Time.Dated): int                 // the ISO week, 1 to 53
Time.yearOfWeek(t: Time.Dated): int                 // the year of that week, which differs around New Year
Time.daysInMonth(t: Time.Dated): int                // 28 to 31
Time.daysInYear(t: Time.Dated): int                 // 365 or 366
Time.inLeapYear(t: Time.Dated): bool
Time.hour(t: Time.Timed): int
Time.minute(t: Time.Timed): int
Time.second(t: Time.Timed): int
Time.millisecond(t: Time.Timed): int
Time.microsecond(t: Time.Timed): int
Time.nanosecond(t: Time.Timed): int

Time.with[T: Time.Wall](t: T, year: int | null = null, month: int | null = null,
                        day: int | null = null, hour: int | null = null, minute: int | null = null,
                        second: int | null = null, millisecond: int | null = null,
                        microsecond: int | null = null, nanosecond: int | null = null,
                        disambiguation: Time.Disambiguation = Time.Compatible{}): T
                                                    // panics on a field the type lacks, or a month or day below 1
```

`with` returns `t` with the named fields replaced and the rest kept, and constrains the result:
`month: 13` is December and `day: 31` in April is April 30, as Temporal's `overflow: "constrain"`
has it. A month or a day below 1 panics, as Temporal throws there, while a time field below 0 is
constrained to 0, as Temporal's is. A `PlainDate` takes the three date fields and a `PlainTime` the
six time fields; another field panics. On a `ZonedDateTime` the new wall-clock time is placed in the
zone with the value's own offset when the zone has that offset at the new time, and by
`disambiguation` otherwise, so `Time.with(t, day: 3)` from November 2 in New York keeps `-04:00` and
from November 4 keeps `-05:00`, each a valid offset for the repeated hour of November 3; the plain
types ignore `disambiguation`.

**Arithmetic.**

```
Time.add[T: Time.Point](t: T, d: Time.Duration): T       // panics on years, months, weeks or days on an Instant
Time.subtract[T: Time.Point](t: T, d: Time.Duration): T  // add(t, negate(d))
Time.until[T: Time.Point](from: T, to: T, largestUnit: Time.Unit | null = null): Time.Duration
                                                         // panics on a unit the type lacks, or Day or larger across zones
Time.since[T: Time.Point](t: T, other: T, largestUnit: Time.Unit | null = null): Time.Duration
                                                         // negate(until(t, other)); panics as until does
Time.round[T: Time.Instant | Time.Timed](t: T, smallestUnit: Time.Unit, increment: int = 1,
                                         mode: Time.RoundingMode = Time.HalfExpand{}): T
                                                         // panics on Year, Month or Week; on Day for an Instant or a
                                                         // PlainTime; an increment that does not fit
Time.compare[T: Time.Point](a: T, b: T): int             // -1, 0 or 1
```

Years, months, weeks and days are calendar units and move the wall clock; hours and smaller are
exact units and move the instant. `add` applies the calendar part first, years then months with the
day constrained, so August 31 plus a month is September 30, then weeks and days, and the exact part
after. On a `ZonedDateTime` the wall-clock result of the calendar part is placed in the zone by
`Compatible` before the exact part is added, so a day added to noon on the Saturday before a change
in New York is noon on the Sunday, 23 or 25 hours later, a day added to 02:30 on the Saturday before
the spring change is 03:30 on the Sunday, since the change skips 02:30, and an hour added is the
next hour of the time line, whatever the clock shows. An `Instant` has no calendar, so a duration
with years, months, weeks or days panics. A `PlainDate` takes the exact part as whole days of 24
hours and drops the remainder; a `PlainTime` ignores the calendar part and wraps around the clock; a
`PlainDateTime` takes everything with days of 24 hours.

`until` is the duration from `from` to `to`, negative when `to` is earlier, with its fields balanced
up to `largestUnit`: `Day` gives days and smaller, `Month` gives months, days and smaller. The
default is `Second` for an `Instant`, `Hour` for a `ZonedDateTime` or a `PlainTime`, and `Day`
otherwise. Years and months are counted from `from`: a month has passed when the target's day of the
month reaches the day of `from`, compared as written, so January 31 until February 28 is `P28D`
although January 31 plus a month is February 28; the rest is days from the constrained date, as
Temporal has it. `since(t, other)` is `negate(until(t, other))`, the duration from `other` to `t`
counted from `t`, and the two differ for calendar units because the anchor does: with `Month` as the
largest unit, `Time.since(mar31, feb29)` is `P1M` and `Time.until(feb29, mar31)` is `P1M2D`. An
`Instant` or a `PlainTime` has units up to `Hour` and a `PlainDate` units down to `Day`; another
`largestUnit` panics, as does `Day` or larger between two `ZonedDateTime`s in different zones, whose
days do not line up. Between two `ZonedDateTime`s in one zone, days are the zone's real days.

`round` rounds to a multiple of `increment` of `smallestUnit` by `mode`, the number rounded being
the nanoseconds since the start of the day for the wall-clock types and since the epoch for an
`Instant`. A result of 24 hours is the start of the next day: a `PlainTime` wraps to `00:00:00`, as
in `add`, and the other wall-clock types move to the next date. For the wall-clock types `increment`
must be positive, divide the count of `smallestUnit` in the next larger unit, 24 hours, 60 minutes,
60 seconds or 1000 of a subsecond unit, and be smaller than it; for `Day` it is 1. For an `Instant`
it must be positive and divide the count of `smallestUnit` in a day, 24 hours, 1440 minutes and so
on, and may be all of it, as in Temporal's `Instant.round`, so `Time.round(i, Time.Hour{}, 24)`
rounds to a midnight of UTC. On a `ZonedDateTime` rounding to `Day` chooses between the start of its
day and the start of the next by the fraction of the real day that has passed; rounding to a smaller
unit works on the wall clock and places the result in the zone as `with` does, keeping the offset
when the zone has it.

`compare` orders by instant for `Instant` and `ZonedDateTime`, so two zoned values at one moment in
different zones compare as `0` though they are not `==`, and by fields for the plain types. `<` and
the other comparison operators do not apply to time values (section 5); `Time.compare` is the
ordering.

**Durations.**

```
Time.part(d: Time.Duration, unit: Time.Unit): int   // the field as given
Time.sign(d: Time.Duration): int                    // -1, 0 or 1
Time.negate(d: Time.Duration): Time.Duration
Time.abs(d: Time.Duration): Time.Duration
Time.addDuration(a: Time.Duration, b: Time.Duration): Time.Duration     // panics on years, months or weeks in either
Time.compareDuration(a: Time.Duration, b: Time.Duration, relativeTo: Time.Dated | null = null): int
                                                    // panics on years, months or weeks without relativeTo
Time.total(d: Time.Duration, unit: Time.Unit, relativeTo: Time.Dated | null = null): float64
                                                    // panics on years, months or weeks, in d or as unit, without relativeTo
Time.roundDuration(d: Time.Duration, smallestUnit: Time.Unit | null = null,
                   largestUnit: Time.Unit | null = null, increment: int = 1,
                   mode: Time.RoundingMode = Time.HalfExpand{},
                   relativeTo: Time.Dated | null = null): Time.Duration
                                                    // panics if no unit is given, if largestUnit is smaller than smallestUnit, if increment is below 1, or on years, months or weeks without relativeTo
```

Years, months and weeks have no fixed length, so a function that must know theirs takes a
`relativeTo` point and counts from it, a week being 7 days of the calendar and a month and a year
counted as `add` counts them, and panics without one; a day is 24 hours unless `relativeTo` is a
`ZonedDateTime`, whose days have their daylight-saving hours. A `PlainDateTime` given as
`relativeTo` counts as its date; its time is ignored, as in Temporal. `addDuration` sums two
durations without years, months or weeks, days at 24 hours, and balances the result up to the larger
of the two largest units given, so `PT90M` plus `PT30M` is `PT120M` and `P1D` plus `PT25H` is
`P2DT1H`. `compareDuration` orders by signed length, so a negative duration is before zero and
before any positive one; two durations with the same fields are `0` without `relativeTo`, as in
Temporal. `total` is the whole duration in `unit` as a number with a fraction, `PT1H30M` in hours
being `1.5`. `roundDuration` balances `d` so that no field below `largestUnit` exceeds its next
unit, and rounds the result to a multiple of `increment` of `smallestUnit` by `mode`, dropping the
smaller fields: `largestUnit` alone balances, `PT90M` to `Hour` being `PT1H30M`; `smallestUnit`
alone rounds; `largestUnit` defaults to the larger of `d`'s largest nonzero unit and `smallestUnit`.
For a time unit `increment` follows the rule of `round` for the wall-clock types; for a day or a
calendar unit any positive increment is allowed when `largestUnit` is `smallestUnit`, so a duration
rounds to a multiple of seven days or of two months, and panics otherwise. The rounding modes are
Temporal's nine: `Ceil` toward positive infinity, `Floor` toward negative, `Expand` away from zero,
`Trunc` toward zero, the four `Half` forms to the nearest multiple with a tie resolved as the plain
form says, and `HalfEven` to the nearest with a tie to the even multiple; `HalfExpand`, the default,
is what `Math.round` does.

Two durations are `==` when their ten fields are, as given, so `PT90M` and `PT1H30M` are not. For
the other types `==` is the same moment for an `Instant`, the same moment and zone for a
`ZonedDateTime`, the same fields for a plain value, and the same zone for a `Zone`, as above. Time
values are immutable and serve as map keys.

## Os

```
type Pipe = { read: File.Handle, write: File.Handle }

Os.args(): Array[string]              // the arguments after the program path: `ant run main.ant a b` gives ["a", "b"]
Os.program(): string                  // the program path: `ant run main.ant a b` gives "main.ant"; "" in the REPL
Os.platform(): string                 // the operating system: "darwin", "linux", "windows", ...
Os.arch(): string                     // the processor architecture: "arm64", "amd64", ...
Os.env(name: string): string | null   // null when name is not set; "" when it is set empty
Os.environ(): Map[string, string]     // every variable
Os.cwd(): Result[string, Error]       // the working directory, absolute
Os.home(): Result[string, Error]      // the user's home directory
Os.configDir(): Result[string, Error] // where the user's programs keep their configuration
Os.cacheDir(): Result[string, Error]  // where they keep what can be made again
Os.pid(): int                         // this process's id
Os.uid(): int | null                  // the effective user id, 0 for root; null on Windows
Os.hostname(): Result[string, Error]  // the name the host's kernel reports, as hostname prints it
Os.exit(status: int): never           // ends the process at once; no deferred block runs, in any goroutine
Os.stdin(): File.Handle               // the program's standard input
Os.stdout(): File.Handle              // its standard output, which print and println write to as well
Os.stderr(): File.Handle              // its standard error, which eprint and eprintln write to as well
Os.interrupt(): Context               // done when the process is interrupted; the same context at every call
Os.openPipe(): Result[Os.Pipe, Error] // what is written to write is read from read
Os.which(program: string): string | null   // the path a Cmd naming program starts; null when none
```

`Os.openPipe` returns two handles the program closes, as it closes a file: a read of `read` waits
for data and a context ends it. `read` is at end of file once every copy of `write` is closed, the
program's included, so after `Cmd.start` the program closes its copy of each writing end it gave
away. A write to `write` waits while the pipe is full, so the program reads it on another goroutine,
or gives it to a child, before writing much. A write once every copy of `read` is closed is `Err`
with the message `broken pipe`, and the program goes on: only the standard streams end it. A pipe
joins what `Cmd.pipe` does not: a child's output read as it comes, a child's input written a piece
at a time, or both outputs watched apart:

```ant
var out = try Os.openPipe()
var make = try Cmd.start(Cmd.new("make"), stdout: out.write)
try File.close(out.write)
var line = try File.readLine(out.read)   // each line as make writes it, null at the end
```

`Os.args` and `Os.environ` return a new array and a new map at each call, which the caller may
change: neither changes the program's arguments or environment, so a later `Os.env`, and a child
without `env`, see them as they were. In the REPL `Os.args()` is `[]`. `Os.environ()` holds the
variables in the host's order, which is no order to rely on.

`Os.program()` is the path of the program's root module as the command was given it, as a shell's
`$0` is, so a usage line names the script as it was run: `./tool.ant` when a `#!` line runs it from
the working directory, `tool.ant` after `ant run tool.ant`. A host that embeds Ant gives the path it
loaded. `Os.platform()` and `Os.arch()` are Go's names for the host's operating system and
architecture, `GOOS` and `GOARCH`, so they are lower case and macOS is `"darwin"`. A script that
differs by platform tests them rather than running `uname`:

```ant
if len(Os.args()) == 0 {
  eprintln("usage: ${Path.base(Os.program())} <file>...")
  Os.exit(2)
}
var opener = if Os.platform() == "darwin" { "open" } else { "xdg-open" }
```

`Os.home`, `Os.configDir` and `Os.cacheDir` are Go's `os.UserHomeDir`, `os.UserConfigDir` and
`os.UserCacheDir`. The home directory is `$HOME` on Unix and `%USERPROFILE%` on Windows. The
configuration directory is `$XDG_CONFIG_HOME`, or `$HOME/.config` when that is unset or empty, on
Unix, `$HOME/Library/Application Support` on macOS, and `%AppData%` on Windows; the cache directory
is `$XDG_CACHE_HOME` or `$HOME/.cache`, `$HOME/Library/Caches`, and `%LocalAppData%`. Each is `Err`
when the variable it rests on is unset or empty, or an XDG variable holds a relative path. The
directory need not exist. They are roots shared by every program, so a script keeps its files under
a directory of its own name, made with `File.mkdir`, which makes the root too, and a fixed path
belongs there rather than in the shared temporary directory, where someone else can take the name
first. Variable names are matched as the host matches them: exactly on Unix, and ignoring case on
Windows. An empty name, or one holding `=`, names no variable, and `Os.env` gives null for it.

`Os.pid` is this process's id, as `Cmd.pid` is a child's. `Os.uid` is the effective user id, the one
that decides what the process may touch, so `Os.uid() == 0` asks what `[[ $EUID -eq 0 ]]` asks;
Windows has no user ids, and there it is null. `Os.hostname` is Go's `os.Hostname`: the host's own
name, not looked up in DNS, so it may or may not hold a domain; it is `Err` only when the host
cannot report one.

`Os.cwd` is the working directory the `ant` command was started in, or the host's for an embedded
run, not the directory of the script, and nothing in Ant changes it. It is `Err` when the host
cannot name it, as when it has been removed.

`Os.exit` hands its status to the host as Go's `os.Exit` does. A Unix parent sees it modulo 256, so
`Os.exit(256)` reads as success and `Os.exit(-1)` as 255; a portable program exits with 0 to 125.

### Interrupts

An interrupt is Ctrl-C, SIGINT, and SIGTERM where the host has it. A program that has not called
`Os.interrupt()` is ended by the first one, as `ant-lang.md` section 9 says of the host ending a
run. A program that has called it receives the first one instead: the context is done with the
reason `interrupt`, the program's waits end, and the program goes on, to drain a server or write
what it has, and exits when it is ready. A second interrupt ends the run, and so does the first
after the program cancelled the context itself, since the interrupt it asked for has then been
handled. When an interrupt ends the run the `ant` command prints nothing and ends by that signal,
SIGINT or SIGTERM, so the shell that started it sees what a signal ended, `130` or `143`, and a
shell loop running it stops too. Where the host has no signals it exits with 130.

While a goroutine waits in `Cmd.run`, the `ant` command holds back every SIGINT and SIGQUIT it
receives: the terminal sends the keyboard's signal to the children too, and they decide. When the
child, or a pipeline's last stage, exits because of a signal held back meanwhile, the program
receives it then, as if it had arrived: a SIGINT is an interrupt, and a SIGQUIT does what it does
without a child. When the child exits otherwise, as `less` and `vim` do on Ctrl-C, the held signal
is dropped. Held signals do not queue, so several presses while one child runs are one interrupt. So
a loop of `Cmd.run` calls stops at Ctrl-C, and a pager quit with Ctrl-C does not end the script.
SIGTERM is not held back. Holding back is process-wide, as signals are, so a server that waits for
`Os.interrupt()` does not call `Cmd.run`. An `ant` started with SIGINT ignored, as `nohup` starts
it, keeps it ignored, and so do its children. A host that embeds Ant owns its process's signals, and
there `Cmd.run` shares the streams and holds nothing back.

### Streams

The three streams are handles, so `File.readLine(Os.stdin())`, `File.readAll(Os.stdin())`,
`File.writeLine(Os.stderr(), msg)` and `File.pipe(Os.stdin(), Os.stdout())` need nothing new. The
streams are not buffered, so what `print`, `eprint`, `Os.stdout()`, `Os.stderr()` and the program's
children write comes out in the order it was written, and a prompt is seen before the read that
follows it. A program that writes much buffers it: `File.buffered(Os.stdout())`. A write to standard
output or standard error whose reader has gone, a broken pipe, ends the program as SIGPIPE ends a Go
program, whichever function made it, a buffered handle's flush too; a shell reports status 141.
Where no signal comes, on Windows or under a host that gives the program its own writer, `print`,
`println`, `eprint` and `eprintln` end the program with status 141, and the `File` functions return
`Err`. `File.close` on a stream does nothing and is `Ok`. In the REPL standard input belongs to the
REPL, and `Os.stdin()` is at end of file, as is a child's standard input under `Cmd.run`.
`Os.stdin()` is open for reading only, and `Os.stdout()` and `Os.stderr()` for writing only,
whatever the descriptor under them allows. A read of standard input reads the stream only while a
read waits, and takes what is there, which may be more than the line it returns; what it took stays
the program's, for its next read, and only input that arrives after it is left to a child the stream
is handed to. A script that reads a header and hands the rest to a child reads the rest itself and
gives it as `input`. A read that its context ended goes on waiting for the stream, which nothing can
interrupt, and what it then reads is the program's, for its next read, not a child's.

## Cmd

```
type Cmd = { program: string, args: Array[string] = [], dir: string | null = null,
             env: Map[string, string] | null = null }
type Pipeline = { cmds: Array[Cmd] }
type Output = { status: int, statuses: Array[int], stdout: string, stderr: string,
                stdoutBytes: Bytes, stderrBytes: Bytes }
type Process                          // opaque: a command started by Cmd.start

Cmd.new(program: string, args: Array[string] = [], dir: string | null = null,
        env: Map[string, string] | null = null): Cmd
Cmd.pipe(cmds: Array[Cmd]): Cmd.Pipeline   // each one's output the next one's input; panics if cmds is empty
Cmd.string(c: Cmd | Cmd.Pipeline): string  // shell-quoted, for a log; env and dir left out

Cmd.run(c: Cmd | Cmd.Pipeline, ctx: Context | null = null): Result[int, Error]
                                      // in the foreground, with the program's three streams; Ok of its status
Cmd.read(c: Cmd | Cmd.Pipeline, input: string | Bytes = "", ctx: Context | null = null): Result[string, Error]
                                      // standard output without one final newline; Err on a nonzero status
Cmd.readBytes(c: Cmd | Cmd.Pipeline, input: string | Bytes = "", ctx: Context | null = null): Result[Bytes, Error]
Cmd.capture(c: Cmd | Cmd.Pipeline, input: string | Bytes = "", ctx: Context | null = null): Result[Cmd.Output, Error]
Cmd.start(c: Cmd | Cmd.Pipeline, stdin: File.Handle | null = null, stdout: File.Handle | null = Os.stdout(),
          stderr: File.Handle | null = Os.stderr(), ctx: Context | null = null): Result[Cmd.Process, Error]
                                      // in the background, in a process group of its own; null is the null device
Cmd.wait(p: Cmd.Process, ctx: Context | null = null): Result[int, Error]    // its status once it has exited
Cmd.kill(p: Cmd.Process, signal: string = "SIGTERM"): Result[void, Error]   // to its process group; Ok when it has exited
Cmd.stop(p: Cmd.Process, grace: Time.Duration = Time.duration(seconds: 5)): Result[int, Error]
                                      // SIGTERM, then SIGKILL after grace, or SIGKILL alone when it is zero or negative; its status; panics on a grace with years, months or weeks
Cmd.pid(p: Cmd.Process): int          // the last stage's
```

`Cmd` is a type with functions, as `Panic` is, rather than a namespace only: a `Cmd` value says what
to run, and a function of `Cmd` says how. A command is built once and run, logged, or passed to a
helper like any record:

```ant
var build = Cmd.new("go", ["build"], dir: root)
if verbose { Array.push(build.args, "-v") }
Array.push(build.args, "./...")
println("running ${Cmd.string(build)}")
var status = try Cmd.run(build)
```

`Cmd.new` is the literal with its defaults, `Cmd{ program: "go", args: ["build"] }`. `Cmd.string`
writes the program and its arguments as a POSIX shell would need them quoted, `git commit -m 'a b'`,
and a pipeline's stages joined by `|` with a space on each side, `git log | wc -l`. A word is left
bare when it is not empty and is only ASCII letters, digits and `_@%+=:,./-`, `=` excepted in the
program's word; any other word is put in single quotes, with each `'` in it written `'\''`, so `''`
is the empty word and a line break stays inside the quotes. It leaves out `env` and `dir`, unlike
the record's own rendering, so the environment's secrets stay out of a log.

### Processes

A command's `program` is started with `args` as its arguments and no shell between: `args` arrive as
they are. A `program` with no path separator is looked up in the program's own `PATH`,
`Os.env("PATH")`, never in the `PATH` of `env`, and an entry of `PATH` that is not absolute, `.`
included, finds nothing; `Os.which` returns what that lookup finds. A `program` with a separator is
taken as it is, relative to `dir` when it is relative; given one, `Os.which` returns it unchanged
when it names an executable file, taken against the working directory as a `Cmd` without `dir` takes
it, and null otherwise. The child inherits the parent's working directory and environment unless
`dir` or `env` is given; `env` is the child's whole environment, so a program that adds one variable
starts from `Os.environ()`.

The functions differ in what they do with the command's streams and how long they wait:

| A script wants                                          | Function                               |
| ------------------------------------------------------- | -------------------------------------- |
| to run a program the user watches or types into         | `Cmd.run`                              |
| one value a program prints                              | `Cmd.read`, or `Cmd.readBytes` exactly |
| the status and both outputs, without failing on nonzero | `Cmd.capture`                          |
| the output as it comes, a file, or a server             | `Cmd.start`, `Os.openPipe`, `Cmd.wait` |

`Cmd.run` gives the command the program's own standard input, output and error, handed over as they
are, so a pager, an editor or `ssh` uses the terminal, and the command stays in the program's
process group, which the terminal treats as the foreground. What the program has read ahead from
standard input stays the program's. The call blocks until the command exits and is `Ok` of its
status, nonzero included.

`Cmd.capture` captures both outputs whole and keeps each twice, as an HTTP body is: as bytes in
`stdoutBytes` and `stderrBytes`, and as text in `stdout` and `stderr`, one copy when the output is
UTF-8. `input` is what the command reads, a string as its UTF-8 and `Bytes` as they are. A nonzero
exit is `Ok` with its `status`, and `statuses` holds each stage's own. `Cmd.read` does the same and
returns standard output as text with one final `\n` or `\r\n` removed, and no other white space, as
a shell's `$(...)` does; this differs from `File.read`, which returns a file exactly, and
`Cmd.readBytes` returns the output as it was written. For both, a nonzero status is `Err` with the
message `<program>: exit status <n>`, followed by `: ` and standard error with its trailing white
space removed when it wrote any. All three stay in the program's process group, as `$(...)` does, so
a command that opens the terminal itself can use it.

`Cmd.start` starts the command and returns once it is running. Each of `stdin`, `stdout` and
`stderr` is a handle or `null`, the null device; the outputs default to the program's and the input
to `null`, as a shell's `cmd &` has it. A terminal as `stdin` is `Err` and nothing is started: a
child outside the foreground that reads the terminal would be stopped by it. The command's stages
share a process group of their own, so the terminal's Ctrl-C does not reach them and `Cmd.kill`,
`Cmd.stop` and the context signal what they started too; on Windows a signal reaches each stage
alone. `Cmd.wait` blocks until every stage has exited, and may be called any number of times, from
any goroutine, each getting the same outcome. A child that writes into a pipe nobody reads blocks
once the pipe is full, so a program reads a child's pipe while it waits, before the wait or on
another goroutine. Every child is reaped when it exits, waited for or not. `Cmd.pid` is the id the
last stage started with, and stays so after it exits; once it has been reaped the system may give
that id to another process, so a program does not signal it by id. `Cmd.kill` sends a signal by
name: `SIGTERM`, `SIGKILL`, `SIGINT`, `SIGHUP`, `SIGQUIT`, `SIGUSR1` or `SIGUSR2`; an unknown name,
or one the host lacks, is `Err`. `Cmd.stop` sends SIGTERM, waits up to `grace`, sends SIGKILL if a
stage still runs, and returns the status. On a command that has exited both send nothing. A command
still running when the script ends is left running, as in Go; a program that wants it gone stops it
in a deferred block.

A handle given to `Cmd.start` is lent: the child gets its own copy, and the handle stays open and
the program's. A buffered handle given as an output is flushed first and its `f` handed over, so a
header the program wrote comes before the child's output. A file with nothing read ahead, a pipe
end, and a standard stream are handed over as they are; anything else, such as a file the program
has read part of or a connection, goes through a copy the runtime runs, which ends a second after
the child exits at the latest, and the program does not read that handle while the child runs. A
child has only the three streams it was given. The same handle may be given twice:
`stdout: p.write, stderr: p.write` merges the outputs, as `2>&1` does.

A context bounds a wait, and the context of a call that starts a command bounds its life:

| What happens                                         | Outcome                                                                                                        |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| The call's context is done before the command starts | `Err` with the context's reason; nothing is started                                                            |
| The call's context ends while the command runs       | Every stage, and for `Cmd.start` its group, is killed; the call, or every `Cmd.wait`, is `Err` with the reason |
| The command exits before the kill is sent            | Its status, as if there were no context                                                                        |
| A `Cmd.wait` context ends first                      | That wait is `Err` with the reason; the command goes on running                                                |
| The program ends it with `Cmd.kill` or `Cmd.stop`    | `Ok` of its status                                                                                             |
| The host cancels the run, or an interrupt ends it    | Every command still running is killed                                                                          |

Contexts end when the run ends (`ant-lang.md` section 9), so a command started with a context is
killed then too. The other calls are `Err` only when the command could not be started or run to its
end: a program is not found, `dir` does not exist, a copy failed.

Where the host has signals, a child ended by signal `n` has the status `128 + n`, as a shell reports
it: SIGKILL is `137` and Ctrl-C `130`. On Windows the status is the exit code, and a child that
`Cmd.kill`, `Cmd.stop` or a context ended has status 1.

### Pipelines

`Cmd.pipe` joins commands as a shell's `|` does, and every function that runs a `Cmd` runs a
`Cmd.Pipeline` too:

```ant
var fixes = try Cmd.read(Cmd.pipe([
  Cmd.new("git", ["log", "--oneline"]),
  Cmd.new("grep", ["fix"]),
  Cmd.new("wc", ["-l"]),
]))
```

The pipeline holds a copy of the array, so changing the array later changes no pipeline. The stages
run at once. The first reads the pipeline's standard input: `input` for `Cmd.read`, `Cmd.readBytes`
and `Cmd.capture`, the `stdin` handle for `Cmd.start`, and the terminal for `Cmd.run`, where only
the first stage reads it. The last writes the pipeline's standard output, and each stage's output is
the next one's input, joined by OS pipes with no copy between. Every stage writes standard error
where the call sends it; where it is captured, the stages' lines interleave as they arrive, and no
order between stages is promised. Each stage keeps its own `dir` and `env`.

The pipeline's status is that of the rightmost stage that failed, or 0 when none did, as under
bash's `pipefail`, so `false | cat` fails. A stage before the last that SIGPIPE ended does not
count, since only a later stage that stopped reading ends it so: `yes | head -n 1` succeeds, where
bash's `pipefail` gives 141. Its own status in `statuses` is still 141. A stage that ignores SIGPIPE
and exits nonzero on the failed write counts, and on Windows, which has no SIGPIPE, every nonzero
stage does. `Cmd.read`'s `Err` names the program of the stage that set the status, followed by
`(stage <i>)`, counting from 1, when another stage runs the same program:
`grep (stage 3): exit status 1`.

The stages of `Cmd.start` share one process group, so one signal reaches them all, and `Cmd.pid` is
the last stage's, as a shell's `$!` is. When a stage cannot be started, those already started are
killed and the call is `Err`. Under `Cmd.run` a Ctrl-C reaches every stage, and the last stage
decides whether it is the program's interrupt (Os, Interrupts): in `git log | less`, Ctrl-C ends
`git`, `less` handles it and goes on, and so does the script. A pipeline of no commands, which a
literal `Cmd.Pipeline{ cmds: [] }` can make, panics wherever it is run or given to `Cmd.string`, as
`Cmd.pipe` does.

## Json

```
type Value = null | bool | float64 | string | Array[Value] | Map[string, Value]

Json.parse(text: string): Result[Json.Value, Error]
Json.stringify[T](value: T, indent: string = ""): string   // records as objects without their tag, as String.from would; a set as an array of its members; a time value as its string; panics on a cyclic value, on one with no JSON form, or on a map key that is not a string
```

`Json.Value` is a recursive alias through an array and a map, which section 4 allows. Numbers parse
as `float64`; a program that needs integers converts with `Math.toInt`, which returns `null`
wherever `int(x)` would panic: a fraction, a value outside the `int` range such as `1e30`, `NaN`, or
an infinity. A decoder into records is a function per type: narrow the tree with `is`, build the
record, and propagate errors with `try`, passing the path along so an error can say
`$.servers[2].port`. Typed decoding and encoding are library code over reflection (`ant-lang.md`,
section 11, Reflect): a walk of the type's shape that builds the value with the builders, or reads
it with the readers, with the format's own policy for unions, missing fields, and numbers.

`parse` reads one JSON text as RFC 8259 defines it, with white space around the value and nothing
else. An object that repeats a key is a map with the key in its first place and its last value, so
`{"a": 1, "b": 2, "a": 3}` is `Map{ "a": 3.0, "b": 2.0 }`. Arrays and objects nest at most 10000
deep, which no document needs, and deeper nesting is `Err`, as is a number too large for a
`float64`, such as `1e400`; a number too small for one is `0.0` or the nearest value it has. The
message of a text that stops before its value does is `unexpected end of JSON input`; of one that
goes on after its value, `unexpected text after the JSON value`; and of any other malformed text,
what was expected and what was found, with the line and column where it was found.

A `\u` escape of a surrogate pair in a JSON string is the one code point the pair encodes, and a
surrogate escape outside a pair, which encodes no text, becomes U+FFFD, as text from outside does
(section 11 of `ant-lang.md`, String).

`Json.stringify` renders numbers as `String.from` does, so `1e21` is `1e+21`. `NaN` and the
infinities have no JSON form, and `Json.stringify` panics on them, as Go's `encoding/json` refuses
them, with `Json.stringify: NaN has no JSON form` or `Json.stringify: Infinity has no JSON form`
(each of its panic messages begins `Json.stringify: `); writing `null`, as JavaScript does, gives
text that reads back as something else. A value that contains itself has no JSON form, so
`Json.stringify` panics with `cyclic value` where `String.from` would print `...`. Nor has `Bytes`,
which JSON carries only in an encoding its reader must know, so `Json.stringify` panics on it and a
program writes `Encoding.toBase64(b)` in its place. Nor has `Html`, which a program renders with
`String.from` first. Nor has a function, `void`, a type, or a reference such as a channel, a
`Random`, a `Mutex`, or a `File.Handle`, whose state JSON cannot carry, and `Json.stringify` panics
on each wherever it is in the value, with a message that names it, such as
`Channel has no JSON form`.

A map becomes an object, and a JSON property name is a string, so every key of a map must be a
`string` or a named primitive over `string`, written without its tag as its values are:
`Map{ UserId("u-1"): 1 }` is `{"u-1":1}`. Any other key panics with
`a map key must be a string, got int`, naming the key's type, since turning `1` into `"1"` or `[1]`
into `"[1]"` gives text that `Json.parse` reads back as something else; a program converts the keys
itself, to the strings it means. Two keys that give one name, `UserId("a")` and `"a"` in a map keyed
by `UserId | string`, panic too, with
`map keys UserId("a") and "a" both give the property name "a"`, so the text never repeats a property
name.

With an empty `indent`, the default, the text is one line with nothing between its tokens. With any
other, each member of an array or object goes on a line of its own, indented by `indent` once per
level of nesting, the closing bracket goes on a line of its own at its opening bracket's level, and
`": "` follows a property name. An empty array or object stays `[]` or `{}`, and the text ends
without a newline, as in JavaScript and Go. `indent` is a string so that a tab can be one, and
`Json.stringify` panics on one that is not all spaces and tabs, since anything else would not be
JSON.

```ant
Json.stringify(Map{ "id": "x1", "tags": ["a"] }, indent: "  ")
// {
//   "id": "x1",
//   "tags": [
//     "a"
//   ]
// }
```

## Csv

```
Csv.parse(text: string, sep: string = ","): Result[Array[Array[string]], Error]   // rows of fields, as many per row as written; panics if sep is not a separator
Csv.stringify(rows: Array[Array[string]], sep: string = ","): string             // a line per row, ending in \n; panics if sep is not a separator
```

The format is RFC 4180 with the separator as given. A row ends at `\n` or `\r\n`; a field that holds
the separator, a quote, or a line break is quoted, and a quote inside a quoted field is doubled.
`parse` keeps every row as written, with its own number of fields, a quoted field across lines
included, trims nothing, reads a line break inside a quoted field as `\n` whichever it was, drops an
empty line, and is `Err` on a quote inside an unquoted field or a quoted field that never closes,
naming the line. `stringify` quotes a field when it holds the separator, a quote, or a line break,
or begins with white space, and ends every row with `\n`; a row of one empty field is written `""`,
since an empty line is no row to `parse`. A separator is one code point other than `"`, `\r`, `\n`,
U+0000, and U+FFFD. It is part of the program, not of the data, so another value panics in both
functions, checked before any row is read or written. With a separator, `stringify` cannot fail,
since it writes to a string, so it returns a `string`.

## Encoding

```
Encoding.toBase64(bytes: Bytes, url: bool = false): string                      // the standard alphabet, padded; url: the URL-safe one
Encoding.fromBase64(s: string, url: bool = false): Result[Bytes, Error]          // padding present or absent; Err on another character
Encoding.toHex(bytes: Bytes): string                                            // two lower-case digits per byte
Encoding.fromHex(s: string): Result[Bytes, Error]                               // either case; Err on an odd length or another character
```

Bytes go in and text comes out, with `String.toBytes` and `String.fromBytes` between them and
strings, so the hex digest of a string is `Crypto.sha256(String.toBytes(s)) | Encoding.toHex()`.
`toBase64` writes RFC 4648's standard alphabet with `+` and `/`, or with `url` the URL-safe one with
`-` and `_`, padded with `=` either way. `fromBase64` reads the alphabet `url` names, with the
padding present or absent, and ignores `\r` and `\n`; any other character, or a length the alphabet
cannot have produced, is `Err`.

## Url

```
type Parts = { scheme: string, opaque: string, user: string, host: string, port: string,
               path: string, query: string, fragment: string }

Url.parse(s: string): Result[Url.Parts, Error]                   // an absolute or a relative reference; absent parts are ""
Url.stringify(parts: Url.Parts): string                          // the reference the parts make
Url.escape(s: string): string                                    // for one query key or value: %XX, a space as +
Url.unescape(s: string): Result[string, Error]                   // the reverse; Err on a bad %XX or on escapes that are not UTF-8
Url.parseQuery(query: string): Result[Map[string, Array[string]], Error]   // keys in order of first appearance
Url.stringifyQuery(params: Map[string, Array[string]]): string             // k=v joined with &, in the map's order
```

`Parts` divides a reference as RFC 3986 does. `scheme` is the scheme in lower case, without its
colon. `opaque` is what follows `scheme:` when it does not start with `/`:
`mailto:alice@example.com` parses with `scheme` `mailto`, `opaque` `alice@example.com`, and an empty
`path`, and without `opaque` that reference would lose its content. A single `/` after the colon
starts the path, as RFC 3986 says: `x:/a` and `file:/etc/hosts` have an empty authority and `path`
`/a` and `/etc/hosts`. `user` is the userinfo as written, a password included. `host` and `port` are
the two halves of the authority, `port` empty when there is none. `path` is decoded, `%20` read as a
space, but for `%2F` and `%25`, which stay as written: a `/` that is not a separator and a `%` that
is no escape keep the path's meaning through a round trip, as `/a%2Fb` and `/a/b` are different
paths. `query` is the raw text after `?`, without it, so `parseQuery` can read it; `fragment` is
decoded. `parse` is `Err` on a malformed reference, such as a bad `%XX`, escapes in `path` or
`fragment` that do not decode to UTF-8, or a space in the host. `stringify` assembles the parts,
escaping what needs it in every part but `query` and `opaque`, which are raw and written as they
are, and in `path` writing `%2F` and `%25` as they are and escaping any other `%`, so a program
changes a URL by parsing it, replacing a field, and writing it back. It writes `//` before an
authority that is not empty, one with a `user`, `host` or `port`, and after `scheme:` before an
empty one when the scheme is one whose references always have an authority, `http`, `https`, `ws`,
`wss`, `ftp` or `file`, in any case, or when `path` starts with `//`, which would otherwise read as
an authority. So `x:/a`, `file:///etc/hosts`, and `http://h/p` come back as written, while `x:///a`
comes back as `x:/a`, which RFC 3986 takes for the same reference.

`escape` makes a string safe as one key or value of a query: every character but the unreserved ones
becomes `%XX`, and a space becomes `+`. `parseQuery` reads `k=v&k=v`, each key and value decoded as
`unescape` does, with a key's values in order and a repeated key such as `tag=a&tag=b` kept as
`Map{ "tag": ["a", "b"] }`; a key without `=` has the value `""`. Escapes that decode to bytes that
are not UTF-8, such as `%FF`, are `Err` in `unescape` and `parseQuery`, since no string can hold
them. `stringifyQuery` writes the map back in its order, each key and value escaped, so the two
round-trip, and a request that is signed over its query has a known order. A one-value query is
`Map{ "q": ["ant"] }`.

## Crypto

```
Crypto.sha256(bytes: Bytes): Bytes                          // 32 bytes
Crypto.sha512(bytes: Bytes): Bytes                          // 64 bytes
Crypto.sha1(bytes: Bytes): Bytes                            // 20 bytes; not collision resistant; for formats that still use it
Crypto.md5(bytes: Bytes): Bytes                             // 16 bytes; likewise
Crypto.hmacSha1(key: Bytes, message: Bytes): Bytes          // 20 bytes
Crypto.hmacSha256(key: Bytes, message: Bytes): Bytes        // 32 bytes
Crypto.hmacSha512(key: Bytes, message: Bytes): Bytes        // 64 bytes
Crypto.equal(a: Bytes, b: Bytes): bool                      // in time that depends on the lengths only
Crypto.randomBytes(n: int): Bytes                           // from the host's secure source; panics if n < 0 or n is above 2^31 − 1
Crypto.uuid(): string                                       // a random UUID, version 4, lower case with hyphens
```

Digests, message authentication, and random bytes: what a program needs to check a webhook, sign a
request, or make a token. Encryption, signatures with keys, and key exchange are left out. A digest
is bytes, so a hex digest is `Crypto.sha256(String.toBytes(s)) | Encoding.toHex()`. `sha1` and `md5`
are broken against collisions and are here for the formats that still use them, as git and TOTP do.
`equal` compares two byte sequences in time that depends on their lengths and not on their contents,
for a received signature against a computed one; sequences of different lengths are unequal.
`randomBytes` and `uuid` read the operating system's source of randomness, which does not fail, and
are not seeded by anything a program can see.
