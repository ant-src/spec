# Ant Standard Library: I/O Namespaces

Companion to `ant-lang.md`. The core library, which every program needs, is section 11 of the specification. The namespaces here talk to the world outside the program, and they follow one rule: every operation that can fail returns a `Result` with `Error` as the error type, and nothing here panics on bad input. Blocking calls block only the calling goroutine (section 9).

This file is a sketch of shape, not a finished API.

## File

```
File.read(path: string): Result[string, Error]
File.readBytes(path: string): Result[Array[byte], Error]
File.write(path: string, text: string): Result[void, Error]
File.writeBytes(path: string, bytes: Array[byte]): Result[void, Error]
File.exists(path: string): bool
File.remove(path: string): Result[void, Error]
File.list(dir: string): Result[Array[string], Error]
File.open(path: string): Result[File, Error]
File.create(path: string): Result[File, Error]
File.readLine(f: File): Result[string | null, Error]       // null at end of file
File.writeLine(f: File, line: string): Result[void, Error]
File.pipe(src: File, dst: File): Result[void, Error]
File.close(f: File): void
```

## Http

```
type Response = { status: int, headers: Map[string, string], body: string }

Http.get(url: string): Result[Response, Error]
Http.post(url: string, body: string, headers: Map[string, string]): Result[Response, Error]
```

## Time

```
Time.now(): int                   // milliseconds since the Unix epoch
Time.sleep(ms: int): void         // blocks the calling goroutine
Time.monotonic(): int             // milliseconds from an arbitrary origin, for measuring
```

## Os

```
Os.args(): Array[string]
Os.env(name: string): string | null
Os.exit(status: int): never
```

## Json

```
type Json = null | bool | float64 | string | Array[Json] | Map[string, Json]

Json.parse(text: string): Result[Json, Error]
Json.stringify[T](value: T): string                     // records as objects without their tag, as String.from would
```

`Json` is a recursive alias through an array and a map, which section 4 allows. Numbers parse as `float64`; a program that needs integers converts with `Math.toInt`, which returns `null` wherever `int(x)` would panic: a fraction, a value outside the `int` range such as `1e30`, `NaN`, or an infinity. A decoder into records is a function per type: narrow the tree with `is`, build the record, and propagate errors with `try`, passing the path along so an error can say `$.servers[2].port`; `tests/ok/json_decoder.ant` in the specification repository is the pattern. Typed decoding through reflection is deferred; the design is in the repository history at commit 81525d2.

