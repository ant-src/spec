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
Json.decode[T](t: Type[T], text: string): Result[T, Error]     // type-directed, through Reflect; the root is a named type
Json.encode[T](t: Type[T], value: T): string            // the inverse, type-directed
```

`Json` is a recursive alias through an array and a map, which section 4 allows. Numbers parse as `float64`; a program that needs integers converts with `int(...)`, which panics on a fraction, so check with `Math.trunc(x) == x` first, or decode into an `int` field and let `Json.decode` report it.

`Json.decode` and `Json.encode` are ordinary library code written against `Reflect` (section 11), and other formats can follow the same shape. Their conventions: an object's keys are a record's fields, and a missing key decodes as `null` when the field's type includes `null`; extra keys are ignored; numbers convert with `Reflect.convert`, so `8080` decodes into an `int` field and `8.5` does not; a record inside a union of several records is told apart by a `"type"` key holding the type name, which `encode` writes and `decode` requires only when present or needed; maps decode only with `string` keys; a named primitive type such as `UserId` reads and writes as its bare base value; anonymous record types and functions do not decode. The error names the path, such as `$.servers[2].port`.
