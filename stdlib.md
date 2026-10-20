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
Json.decode[T](t: Type[T], text: string): Result[T, Error]     // Reflect.fromData(t, Json.toData(try Json.parse(text)))
Json.encode[T](t: Type[T], value: T): string            // the inverse: renders Reflect.toData(t, value)
Json.toData(json: Json): Reflect.Data                   // an object with a string "$type" becomes a Tagged node
Json.fromData(data: Reflect.Data): Json                 // the inverse; numbers round to float64
```

`Json` is a recursive alias through an array and a map, which section 4 allows. Numbers parse as `float64`; a program that needs integers converts with `int(...)`, which panics on a fraction, so check with `Math.trunc(x) == x` first, or decode into an `int` field and let `Json.decode` report it.

`Json.decode` and `Json.encode` are ordinary library code written against `Reflect` (section 11), and another format follows the same shape: turn its tree into a `Reflect.Data` and let `Reflect.fromData` build the value by its declaration. The conventions that are JSON's own: an object's keys are a record's fields; a `Tagged` node is an object with a `"$type"` entry holding the name, and, when its value is not an object, a `"$value"` entry holding the value, so `{"$type":"Circle","radius":2.0}` and `{"$type":"UserId","$value":"u-1"}`; the key cannot collide with a field, since `$` is not an identifier character, and `Reflect.toData` tags only where section 11 says a name is needed, so most objects carry none; numbers go through the conversion table, so `8080` decodes into an `int` field and `8.5` does not, and because every JSON number is a `float64`, a union of numeric kinds decodes as `float64` when it has that member and otherwise by the table in declaration order, so a union of integer widths does not survive JSON; a named primitive type such as `UserId` reads and writes as its bare base value unless tagged; a field declared as `Reflect.Data` keeps its subtree for a later `Reflect.fromData`. Missing and extra keys, unions, map keys, and the types that cannot be built follow `fromData`'s table. The error names the path, such as `$.servers[2].port`.

