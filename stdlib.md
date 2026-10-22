# Ant Standard Library: I/O Namespaces

Companion to `ant-lang.md`. The core library, which every program needs, is section 11 of the
specification. The namespaces here talk to the world outside the program, and they follow one rule:
every operation that can fail returns a `Result` with `Error` as the error type, and nothing here
panics on bad input; the one ◆ is `Json.stringify` on a value that contains itself. Blocking calls
block only the calling goroutine (section 9).

This file is a sketch of shape, not a finished API. A type a namespace declares is written through
the namespace, `Json.Value` or `Http.Response`, since a namespace is a record like an imported
module and the bare name would collide with it.

## File

```
File.read(path: string): Result[string, Error]
File.readBytes(path: string): Result[Array[byte], Error]
File.write(path: string, text: string): Result[void, Error]
File.writeBytes(path: string, bytes: Array[byte]): Result[void, Error]
File.exists(path: string): bool
File.remove(path: string): Result[void, Error]
File.list(dir: string): Result[Array[string], Error]
type Handle                                                // opaque: an open file

File.open(path: string): Result[File.Handle, Error]
File.create(path: string): Result[File.Handle, Error]
File.readLine(f: File.Handle): Result[string | null, Error]   // null at end of file
File.writeLine(f: File.Handle, line: string): Result[void, Error]
File.pipe(src: File.Handle, dst: File.Handle): Result[void, Error]
File.close(f: File.Handle): void
```

## Http

```
type Response = { status: int, headers: Map[string, string], body: string }

Http.get(url: string): Result[Http.Response, Error]
Http.post(url: string, body: string, headers: Map[string, string]): Result[Http.Response, Error]
```

## Time

```
Time.now(): int                   // milliseconds since the Unix epoch
Time.sleep(ms: int): void         // blocks the calling goroutine
Time.monotonic(): int             // milliseconds from an arbitrary origin, for measuring
```

## Os

```
Os.args(): Array[string]              // the arguments after the program path: `ant run main.ant a b` gives ["a", "b"]
Os.env(name: string): string | null
Os.exit(status: int): never           // ends the process at once; no deferred block runs, in any goroutine
```

## Json

```
type Value = null | bool | float64 | string | Array[Value] | Map[string, Value]

Json.parse(text: string): Result[Json.Value, Error]
Json.stringify[T](value: T): string                     // records as objects without their tag, as String.from would; ◆ cyclic value
```

`Json.Value` is a recursive alias through an array and a map, which section 4 allows. Numbers parse
as `float64`; a program that needs integers converts with `Math.toInt`, which returns `null`
wherever `int(x)` would panic: a fraction, a value outside the `int` range such as `1e30`, `NaN`, or
an infinity. A decoder into records is a function per type: narrow the tree with `is`, build the
record, and propagate errors with `try`, passing the path along so an error can say
`$.servers[2].port`. Typed decoding through reflection is deferred; the design is in the repository
history at commit 81525d2.

`Json.stringify` renders numbers as `String.from` does, so `1e21` is `1e+21`, and `NaN` and the
infinities, which JSON cannot carry, as `null`. A value that contains itself has no JSON form, so
`Json.stringify` panics with `cyclic value` where `String.from` would print `...`.
