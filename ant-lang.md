# Ant Language Specification

Draft 0.1 · October 2026

Ant is a general-purpose, garbage-collected language with JavaScript-like syntax, structural static types, expression-oriented control flow, and goroutine-style concurrency. This document describes the language as a programmer sees it. It does not describe the compiler or the runtime.

The name "Ant" is a placeholder.

## 1. Principles

- **One obvious way.** When two constructs would do the same job, the language keeps one.
- **No implicit coercion.** A value never changes type without a visible conversion.
- **Everything is an expression.** Blocks, `if`, `match`, and loops produce values.
- **Errors are values.** `Result` carries expected failures and `null` carries absence. `panic` is for bugs.
- **Minimal syntax.** The grammar needs one token of lookahead and no feedback from the type checker.

Section 13 lists the decisions this draft leaves open.

## 2. Lexical structure

Source files are UTF-8 text. The file extension is `.ant`.

### Comments

```ant
// line comment
/* block comment */
```

### Identifiers and keywords

An identifier starts with a letter or `_` and continues with letters, digits, or `_`. Case carries no meaning. `_` on its own is the wildcard pattern and cannot be read.

Keywords:

```
break continue defer else export false for func go if import
in match null panic return true try type var void while
```

Names such as `Array`, `Map`, and `Result` are ordinary identifiers bound by the standard library. They are not keywords.

### Literals

```ant
42          1_000_000     0xFF        0b1010    // integers
3.14        1e9           2.5e-3                // floats
"hello"     "line\nbreak" "\u{1F600}"           // strings
`total: ${count} items`                         // template strings
true        false         null
```

An integer literal takes any integer type the context requires and defaults to `int`. A float literal takes any float type and defaults to `float64`. `1` is never a float; write `1.0`.

Template strings interpolate any expression. Each `${...}` is converted with `String.from`, which is defined for every type (section 11).

### Line endings

A newline ends an expression, except when:

- the line ends with a token that cannot end an expression, such as a binary operator, `,`, `(`, `[`, `{`, `=`, or `=>`; or
- the next non-blank line starts with `.`, `?.`, or `|`.

A semicolon also ends an expression. Nothing else is inferred. The second rule exists so that pipelines, and union types, read top to bottom:

```ant
var total = orders
  | Array.filter({ x.paid })
  | Array.map({ x.amount })
  | Array.sum()
```

## 3. Variables

`var` declares a mutable binding. Every declaration has an initializer. The type is inferred from the initializer or written explicitly.

```ant
var count = 0
var name: string = "ant"
var scores: Array[int] = []
```

A name cannot be redeclared in the same scope. An inner scope may shadow an outer one. A `var` is visible from its declaration to the end of the enclosing block. Top-level `func` and `type` declarations are visible throughout the module regardless of order; top-level `var` is not.

Assignment is an expression of type `void`, so it cannot be chained or used as a condition:

```ant
count = count + 1
count += 1                // also -= *= /= %=
if (count = 5) { ... }    // compile error: void is not bool
```

There is no `++`, `--`, or `const`.

## 4. Types

Ant is statically typed. Types are checked before the program runs, and most annotations are inferred. All types are structural: two types with the same shape are the same type.

### Primitives

| Type | Values |
|---|---|
| `bool` | `true`, `false` |
| `int8` `int16` `int32` `int64` | signed integers |
| `uint8` `uint16` `uint32` `uint64` | unsigned integers |
| `float32` `float64` | IEEE 754 floats |
| `string` | immutable sequence of Unicode code points |
| `null` | the single value `null` |
| `void` | the single value `void`, which carries no information |
| `never` | the type of expressions that do not return, such as `panic(...)` or `return` |

`int` is an alias for `int64` and `byte` is an alias for `uint8`.

`void` is both a type and its only value, like `null`. A block that ends in a declaration or assignment, a loop, and a function with nothing to return all produce `void`. Write it explicitly when a value is required, as in `Result.ok(void)`.

Numeric types never mix. Convert explicitly by calling the target type as a function. Conversions that lose information panic rather than wrap or truncate silently; float-to-int conversion truncates toward zero and panics when out of range.

```ant
var n = 7
var ratio = float64(n) / 2.0      // 3.5
var small = int8(n)               // ok
var bad = int8(300)               // panic: out of range
```

### Records

A record type lists named fields. A record literal uses the same shape. Fields are mutable.

```ant
type Point = { x: float64, y: float64 }

var p: Point = { x: 1.0, y: 2.0 }
p.x = 3.0
```

A record has no dynamic access: `p["x"]` is a compile error, and `for` does not iterate a record. When the keys are data rather than part of the type, use a `Map` (next section).

Records are structural with width subtyping: a value with extra fields is accepted where fewer are required. A record *literal* written directly against a known type must match it exactly, which catches typos.

```ant
type Named = { name: string }
func greet(n: Named): string { `hi ${n.name}` }

var user = { name: "ada", age: 36 }
greet(user)                       // ok: user has a name field
greet({ name: "ada", age: 36 })   // compile error: literal has extra field age
```

The spread `...` copies all fields of a record into a new literal. Later fields win.

```ant
var moved = { ...p, x: 0.0 }
```

Records, arrays, and maps are reference values: assigning or passing one shares it, and `==` compares identity. Structural comparison is a library call (`Array.equals`, `Map.equals`, `Record.equals`). `Record.equals` compares every run-time field recursively, including fields the static type does not mention, so it agrees with `String.from` and `Json.stringify`.

### Arrays and maps

```ant
var xs: Array[int] = [1, 2, 3]
var ages: Map[string, int] = ["ada": 36, "linus": 54]
var empty: Map[string, int] = [:]
```

Square brackets always build a collection; braces always build a record, block, or lambda. `Array[T]` is dense and growable. `Map[K, V]` keys compare the way `==` does: primitives by value, everything else by identity. Section 11 covers the operations.

### Literal types

A string literal is also a type. `"circle"` is the type whose only value is `"circle"`. Literal types appear almost only inside unions, where they serve as enumerations and as tags:

```ant
type Color = "red" | "green" | "blue"

var c: Color = "green"
c = "purple"                      // compile error
```

A string literal expression has its literal type when the context expects one, and `string` otherwise. Context comes from annotations, parameter types, return types, and the expected type of an enclosing record literal. An unannotated `var` therefore holds a `string`:

```ant
var a = "red"                     // string
var b: Color = "red"              // Color
```

### Unions

`A | B` is a type whose values belong to `A` or to `B`. In a type, `|` builds a union; in an expression, it is the pipe (section 5). A union may span several lines when each continuation line starts with `|`.

```ant
type Id = int | string

func describe(id: Id): string {
  match (id) {
    n: int => `number ${n}`,
    s: string => `text ${s}`,
  }
}
```

A nullable type is written `T | null`. See section 7.

The members of a union must be distinguishable at run time. A union may contain at most one array type, one map type, and one function type. It may contain several record types only when they are tagged, as described next.

### Tagged unions

A tagged union is a union of record types that share a field whose type is a different string literal in each member. By convention the field is named `kind`. The compiler uses it to tell the members apart: matching on the record, or comparing the field with `==`, narrows the value to one member.

```ant
type Circle = { kind: "circle", radius: float64 }
type Rect = { kind: "rect", width: float64, height: float64 }
type Shape = Circle | Rect | { kind: "empty" }

var s: Shape = { kind: "circle", radius: 2.0 }

func area(s: Shape): float64 {
  match (s) {
    { kind: "circle", radius } => 3.14159 * radius * radius,
    { kind: "rect", width, height } => width * height,
    { kind: "empty" } => 0.0,
  }
}

if (s.kind == "circle") { print(s.radius) }     // s: Circle here
```

Through a value of union type, a field can be read when every member has it, and its type is the union of the members' field types. A field can never be assigned through a union type; narrow first, then assign.

`Result[T, E]` is a standard tagged union: `{ kind: "ok", value: T } | { kind: "err", error: E }`. See section 8.

### Function types

A function type lists parameter types and the return type. Parameter names are optional. When present, callers may pass those parameters by name (section 6).

```ant
type Predicate[T] = func(T): bool
type Handler = func(request: Request): Response
```

### Generics

Type parameters go in square brackets after the name. They apply to types and functions.

```ant
type Pair[A, B] = { first: A, second: B }

func swap[A, B](p: Pair[A, B]): Pair[B, A] {
  { first: p.second, second: p.first }
}
```

Type arguments are never written at a call site. They are inferred from the arguments or from the expected type. When inference has nothing to work with, annotate the result.

```ant
var xs = Array.map([1, 2, 3], { x * 2 })   // Array[int]
var ys: Array[string] = []                  // annotation needed
```

Type parameters have no constraints in this draft. `==` and `Map` keys work on every type, so most generic code needs none.

### Type declarations

`type` declares a name for a type. The name is an alias: `type UserId = int` makes `UserId` interchangeable with `int`, and `type Shape = Circle | Rect` is interchangeable with the union written out. There are no classes, interfaces, or prototypes.

### Inference

Every `var` without an annotation takes the type of its initializer. Every function parameter is annotated, except lambda parameters, which take their type from context. A function's return type is inferred from its body unless the function is recursive, in which case it must be written.

## 5. Expressions

Every construct is an expression with a type. Statements are just expressions whose value is `void`.

### Operators

From tightest to loosest binding:

| Level | Operators | Notes |
|---|---|---|
| postfix | `a.b` `a?.b` `a[i]` `f(x)` | |
| prefix | `-a` `!a` `try a` | |
| multiplicative | `*` `/` `%` | integer `/` truncates toward zero |
| additive | `+` `-` | `+` also concatenates strings |
| comparison | `<` `<=` `>` `>=` | numbers and strings |
| equality | `==` `!=` | both operands must have the same type |
| logical | `&&` then `\|\|` | short-circuit, `bool` only |
| null | `??` | cannot mix with `&&` or `\|\|` without parentheses |
| pipe | `\|` | left associative; in a type, `\|` is a union (section 4) |
| assignment | `=` `+=` `-=` `*=` `/=` `%=` | type `void` |

There is no `===`, no `+` between different types, and no truthiness: a condition must be a `bool`. Integer overflow panics. Division by zero panics for integers and follows IEEE 754 for floats.

Bitwise operations are functions in the `Bits` namespace:

```ant
var flags = Bits.or(READ, WRITE)
var high = Bits.shiftRight(word, 8)
```

### Pipes

`a | f(b, c)` means `f(a, b, c)`. The right side must be a call. The pipe replaces method chaining.

```ant
var names = users
  | Array.filter({ x.age >= 18 })
  | Array.map({ x.name })
  | Array.sort()
```

### Blocks

A block is a sequence of expressions separated by newlines or semicolons. Its value is the value of the last expression. A block that ends in a declaration or assignment has type `void`.

Braces are a block only directly after `func(...)`, `if (...)`, `else`, `for (...)`, `while (...)`, `go`, `defer`, or `=>` in a `match` arm. Anywhere else, braces are a record literal or a lambda (section 6).

So `{}` after one of those keywords is an empty block of type `void`, and elsewhere it is an empty record. A branch that produces a record literal nests it inside the block: `if (c) { { x: 1 } } else { { x: 2 } }`.

### `if`

```ant
var label = if (n < 0) { "negative" } else if (n == 0) { "zero" } else { "positive" }
```

Both branches must have the same type. An `if` without `else` has type `void`.

### Loops

`for` iterates over an array, a map, or a string. Each iteration binds a fresh variable, so a closure created in the body keeps that iteration's value. `while` repeats while a condition holds. Both have type `void`. `break` and `continue` work as in JavaScript, without labels.

```ant
for (user in users) {
  if (user.banned) { continue }
  notify(user)
}

for (entry in ages) {           // entry: { key: string, value: int }
  print(`${entry.key}: ${entry.value}`)
}

for (i in Array.range(0, 10)) { ... }

while (!done) { done = step() }
```

### `match`

`match` compares a value against patterns in order and evaluates the first arm that fits. Arms are separated by commas or newlines. Every arm has the same type, and the patterns must cover every possible value, so a `match` can never fall through. For a tagged union that means every `kind`; for a primitive it usually means a final `_`.

```ant
func describe(n: int): string {
  match (n) {
    0 => "zero",
    x if x < 0 => "negative",
    _ => "positive",
  }
}
```

Patterns:

| Pattern | Matches |
|---|---|
| `42` `"a"` `true` `null` | the literal value |
| `name` | anything; binds `name` |
| `_` | anything; binds nothing |
| `name: Type` | a union member of `Type`; binds `name` |
| `{ x, y }` `{ x: px }` `{ kind: "circle", radius }` | a record; each field pattern binds the field, renames it, or tests it against a sub-pattern |
| `[]` `[first, ...rest]` | an array of matching length, or a prefix with the rest |
| `pattern if condition` | the pattern, when the guard is true |

Patterns nest. A record pattern ignores fields it does not mention. `var` accepts a record or array pattern on the left side when it cannot fail:

```ant
var { x, y } = origin
var [head, ...tail] = items          // compile error: could be empty
```

### `return`, `break`, `continue`, `panic`

These have type `never`, so they can appear anywhere an expression is expected:

```ant
var user = Map.get(users, id) ?? return Result.err({ message: "no such user" })
```

## 6. Functions

`func` declares a named function. Parameters are annotated; the return type may be inferred. The body is a block, so the last expression is the result and `return` is only needed to leave early.

```ant
func clamp(value: int, low: int, high: int): int {
  if (value < low) { return low }
  if (value > high) { return high }
  value
}
```

### Calling

Arguments are positional, named, or positional followed by named. A parameter with a default value may be omitted.

```ant
func connect(host: string, port: int = 443, tls: bool = true): Connection { ... }

connect("example.com")
connect("example.com", 8080)
connect("example.com", tls: false)
connect(port: 80, host: "example.com")
```

Named arguments require the callee to be a declared function or a value whose function type names its parameters. There are no variadic parameters; pass an array.

### Anonymous functions

An anonymous function is `func` without a name. A lambda is a bare block whose single parameter is implicitly named `x`. If the expected type is a zero-parameter function, the lambda takes no parameter.

```ant
var add = func(a: int, b: int) { a + b }
var double: func(int): int = { x * 2 }
var isAdult: func(User): bool = { x.age >= 18 }

Array.map([1, 2, 3], { x * x })
Mutex.withLock(lock, { counter += 1 })
```

A lambda's parameter type comes from the function type the context expects. With no expected type, as in an unannotated `var`, a lambda is a compile error. Nested lambdas each bind their own `x`; use `func` when you need both.

Because `{ x }` is a lambda, record literals have no shorthand properties: write `{ x: x }`.

### Closures and first-class values

Functions are values. They capture variables by reference, with JavaScript semantics: a closure sees later assignments to captured variables, and `return` inside a lambda returns from the lambda only.

```ant
func counter(): func(): int {
  var n = 0
  func() { n += 1; n }
}

var next = counter()
next()    // 1
next()    // 2
```

## 7. Nullability

`null` is a value of type `null` and nothing else. There is no `undefined`. A variable of type `string` can never hold `null`; a variable of type `string | null` can. There is no `Option` wrapper: a nullable type is just a union with `null`, so `T | null | null` is `T | null`. Where the difference between absent and null matters, ask the container instead of the value: `Map.has(m, k)` tells a missing key from a stored `null`.

```ant
func find(users: Array[User], id: int): User | null {
  Array.find(users, { x.id == id })
}
```

Four constructs handle nullable values, and together they replace the combinators other languages attach to an option type:

```ant
var user = find(users, 7)

var city = user?.address?.city          // string | null: null if any link is null
var label = user?.name ?? "anonymous"   // string: right side when left is null

match (user) {
  null => print("not found"),
  u => print(u.name),                   // u: User
}

if (user != null) {
  print(user.name)                      // user: User here
}
```

`?.` applies to field access, indexing, and calls: `f?.(x)` calls `f` when it is not null. `??` takes any expression on the right, including `return` and `panic`, so `value ?? panic("unreachable")` unwraps and `value ?? return null` propagates. The type checker narrows after a `null` test, as shown in the last two examples.

## 8. Errors

### `Result`

Expected failures are values of `Result[T, E]`, a tagged union:

```ant
type Result[T, E] = { kind: "ok", value: T } | { kind: "err", error: E }
```

`Result.ok(value)` and `Result.err(error)` build the two cases. The error type is whatever the author chooses. The standard library uses `Error`, a record `{ message: string }`; user code often declares a tagged union of its own.

```ant
type ParseError = { kind: "empty" } | { kind: "badDigit", at: int }

func parseInt(s: string): Result[int, ParseError] {
  if (String.isEmpty(s)) { return Result.err({ kind: "empty" }) }
  ...
  Result.ok(n)
}

match (parseInt(input)) {
  { kind: "ok", value } => print(`parsed ${value}`),
  { kind: "err", error: { kind: "empty" } } => print("nothing to parse"),
  { kind: "err", error: { kind: "badDigit", at } } => print(`bad digit at ${at}`),
}
```

Because unions are structural, error types compose without wrapping. A function that parses a file can return `Result[Config, ParseError | Error]` and `try` both kinds of call.

### `try`

`try` unwraps a `Result` or a nullable value. On `{ kind: "ok", value }` or a non-null value it evaluates to the value. On `{ kind: "err", ... }` it returns that record from the enclosing function; on `null` it returns `null`. The enclosing function must therefore return a `Result` whose error type accepts the error, or a type that includes `null`.

```ant
func loadConfig(path: string): Result[Config, Error] {
  var text = try File.read(path)
  var json = try Json.parse(text)
  Result.ok(Config.fromJson(json))
}
```

`try` binds like a prefix operator: `try f(x) | g()` means `(try f(x)) | g()`.

Besides the two constructors, the `Result` namespace provides `Result.map`, `Result.mapErr`, `Result.unwrap` (panics on an error), `Result.unwrapOr`, and `Result.isOk`.

### `panic`

`panic(message)` stops the current goroutine immediately. It is for bugs and impossible states, never for expected failures. Panics cannot be caught. A panic in the main goroutine ends the program with a non-zero exit status; a panic in any other goroutine ends only that goroutine (section 9).

Operations that panic are listed with the operation. The common ones: integer overflow, integer division by zero, array index out of range, lossy numeric conversion, and `unwrap` on the wrong case.

### `defer`

`defer` schedules a block to run when the enclosing block exits, whether by falling off the end, `return`, `break`, `continue`, or panic. Deferred blocks run in reverse order of registration.

```ant
func copy(src: string, dst: string): Result[void, Error] {
  var input = try File.open(src)
  defer { File.close(input) }
  var output = try File.create(dst)
  defer { File.close(output) }
  File.pipe(input, output)
}
```

## 9. Concurrency

### Goroutines

`go` runs a block on a new goroutine and returns immediately. Goroutines are cheap, and any function can start one or block inside one; there are no `async` functions or colored call chains. Blocking library calls such as file and network I/O block only the calling goroutine.

```ant
go { sendReport(report) }
```

The program exits when the main goroutine returns, regardless of other goroutines.

### Synchronization

There are no channels. Goroutines coordinate through shared memory guarded by the primitives in the standard library. Each is a reference value created by its `new` function:

| Type | Operations |
|---|---|
| `Mutex` | `Mutex.lock`, `Mutex.unlock`, `Mutex.withLock(m, { ... })` |
| `RwMutex` | `RwMutex.read`, `RwMutex.write`, `RwMutex.withRead`, `RwMutex.withWrite` |
| `WaitGroup` | `WaitGroup.add`, `WaitGroup.done`, `WaitGroup.wait` |
| `Once` | `Once.do(once, { ... })` |
| `Cond` | `Cond.wait`, `Cond.signal`, `Cond.broadcast` |
| `Atomic[T]` | `Atomic.load`, `Atomic.store`, `Atomic.add`, `Atomic.compareAndSwap` |

```ant
func fetchAll(urls: Array[string]): Array[Result[Response, Error]] {
  var results: Array[Result[Response, Error]] = Array.filled(Array.length(urls), Result.err({ message: "pending" }))
  var lock = Mutex.new()
  var wg = WaitGroup.new()

  for (entry in Array.entries(urls)) {
    WaitGroup.add(wg, 1)
    go {
      defer { WaitGroup.done(wg) }
      var response = Http.get(entry.value)
      Mutex.withLock(lock, { results[entry.index] = response })
    }
  }

  WaitGroup.wait(wg)
  results
}
```

Reading and writing the same memory from two goroutines without synchronization is a data race. A data race is a program error. The runtime guarantees memory safety in its presence, but not any particular result.

### Panics in goroutines

A panic ends the goroutine it occurs in, after running that goroutine's deferred blocks. The runtime reports the message and stack trace on standard error. Nothing else happens: no other goroutine is interrupted, and the program continues. Code that waits on a goroutine must therefore account for it never finishing its work; the `defer { WaitGroup.done(wg) }` above is the usual pattern.

## 10. Modules

Each file is a module. A declaration prefixed with `export` is visible to other modules; everything else is private.

```ant
// geometry.ant
export type Point = { x: float64, y: float64 }

export func distance(a: Point, b: Point): float64 {
  Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y))
}
```

`import` binds a whole module to a name. Members are accessed through that name, so user modules look like standard-library namespaces.

```ant
import Geometry from "./geometry"

var d = Geometry.distance(p, q)
```

There is no selective import and no re-export. Module paths are relative to the importing file or name a package; package resolution is outside this document. Import cycles are a compile error.

Execution starts at `func main()` in the module given to the compiler.

## 11. Standard library

The standard library is a set of global namespaces. Each is a plain record of functions; none has methods or state. Every function takes its subject as the first argument so it composes with `|`. This section lists the shape of the library, not its full contents.

### Arrays

`Array[T]` is dense and growable. `xs[i]` reads and `xs[i] = v` writes; both panic when `i` is out of range. `Array.get(xs, i)` returns `T | null` instead.

```ant
Array.length(xs)              Array.push(xs, v)            Array.pop(xs): T | null 
Array.get(xs, i)              Array.slice(xs, from, to)    Array.concat(xs, ys)
Array.map(xs, f)              Array.filter(xs, f)          Array.reduce(xs, init, f)
Array.find(xs, f)             Array.some(xs, f)            Array.every(xs, f)
Array.sort(xs)                Array.sortBy(xs, f)          Array.reverse(xs)
Array.contains(xs, v)         Array.indexOf(xs, v)         Array.entries(xs)
Array.range(from, to)         Array.filled(n, v)           Array.equals(xs, ys)
Array.sum(xs)                 Array.flatten(xs)            Array.isEmpty(xs)
```

Only `Array.push` and `Array.pop` modify their input. Every other function returns a new array and leaves the argument untouched, so `Array.sort(xs)` is a sorted copy. `Array.entries(xs)` yields `{ index: int, value: T }` records.

### Maps

`Map[K, V]` is an unordered hash map. `m[k]` reads `V | null`; `m[k] = v` inserts or replaces. When `V` itself includes `null`, `Map.has` is the only way to tell a missing key from a stored `null`.

```ant
Map.size(m)         Map.has(m, k)        Map.get(m, k)        Map.set(m, k, v)
Map.remove(m, k)    Map.keys(m)          Map.values(m)        Map.entries(m)
Map.map(m, f)       Map.filter(m, f)     Map.merge(m, n)      Map.equals(m, n)
```

Iterating a map with `for` yields `{ key: K, value: V }` records in unspecified order.

### Strings

A `string` is immutable. Index and length are in Unicode code points. Byte access goes through `String.toBytes`.

```ant
String.length(s)         String.slice(s, from, to)    String.concat(parts)
String.split(s, sep)     String.join(parts, sep)      String.trim(s)
String.contains(s, t)    String.startsWith(s, t)      String.replace(s, old, new)
String.toUpper(s)        String.toLower(s)            String.chars(s): Array[string]
String.toBytes(s)        String.fromBytes(bytes)      String.from(value)
```

`String.from` renders any value. Primitives render as their literal form; records, arrays, and maps render in literal syntax as well; functions render as `func`. It is the only implicit use of this function, and only inside template strings.

### Others

| Namespace | Purpose |
|---|---|
| `Math` | `abs`, `min`, `max`, `pow`, `sqrt`, `floor`, `ceil`, `round`, constants |
| `Bits` | `and`, `or`, `xor`, `not`, `shiftLeft`, `shiftRight`, `popCount` |
| `Result` | constructors and combinators (section 8) |
| `Mutex`, `RwMutex`, `WaitGroup`, `Once`, `Cond`, `Atomic` | synchronization (section 9) |
| `Record` | `equals` for structural comparison of records |
| `Json` | `parse`, `stringify` |
| `File`, `Http`, `Time`, `Os` | I/O; every operation that can fail returns `Result` |
| `print` | the only global function: writes `String.from(value)` and a newline to standard output |

## 12. Example

```ant
type Status = { kind: "active" } | { kind: "suspended", reason: string }

type Account = {
  id: int,
  owner: string,
  balance: float64,
  status: Status,
}

type TransferError =
  | { kind: "notFound", id: int }
  | { kind: "insufficient", needed: float64 }
  | { kind: "suspended", id: int, reason: string }

func transfer(accounts: Map[int, Account], from: int, to: int, amount: float64): Result[void, TransferError] {
  var source = accounts[from] ?? return Result.err({ kind: "notFound", id: from })
  var target = accounts[to] ?? return Result.err({ kind: "notFound", id: to })

  if (source.status.kind == "suspended") {
    return Result.err({ kind: "suspended", id: from, reason: source.status.reason })
  }
  if (source.balance < amount) {
    return Result.err({ kind: "insufficient", needed: amount - source.balance })
  }

  source.balance -= amount
  target.balance += amount
  Result.ok(void)
}

func report(accounts: Map[int, Account]): string {
  Map.values(accounts)
    | Array.filter({ x.status.kind == "active" })
    | Array.sortBy({ x.balance })
    | Array.map({ `${x.owner}: ${x.balance}` })
    | String.join("\n")
}

func main() {
  var accounts: Map[int, Account] = [:]
  accounts[1] = { id: 1, owner: "ada", balance: 100.0, status: { kind: "active" } }
  accounts[2] = { id: 2, owner: "linus", balance: 20.0, status: { kind: "suspended", reason: "audit" } }

  match (transfer(accounts, 1, 2, 50.0)) {
    { kind: "ok" } => print("ok"),
    { kind: "err", error: { kind: "notFound", id } } => print(`unknown account ${id}`),
    { kind: "err", error: { kind: "insufficient", needed } } => print(`short by ${needed}`),
    { kind: "err", error: { kind: "suspended", id, reason } } => print(`account ${id} is suspended: ${reason}`),
  }

  print(report(accounts))
}
```

## 13. Open decisions

Each item below is a choice this draft made for the sake of having examples, not a settled design. The current choice is stated first.

1. **Tagged unions follow TypeScript:** records with a literal `kind` field, no constructors, no nominal types. Building a value is verbose (`Result.err({ kind: "notFound", id: from })`), and an unannotated `var` widens the tag to `string`, so values built outside a typed context need an annotation. Generated constructor functions or a `const`-style declaration that keeps literal types may be wanted.
2. **Records, arrays, and maps are references, and `==` is identity on them.** This follows JavaScript but surprises anyone expecting `{ x: 1 } == { x: 1 }`. Value semantics for records would change `==`, map keys, and the mutation model.
3. **No explicit type arguments at call sites.** Keeps `f[T](x)` out of the grammar, so `a[b]` is always indexing. Needs confirmation that inference from arguments and expected type is always enough; `Result.err` relies on the expected type flowing into the call.
4. **`go` returns nothing.** Results come back through shared memory and a `WaitGroup`. A handle with `join` would be more convenient but is a channel in disguise, and panics would need a representation on it.
5. **Data races are undefined in outcome but memory safe.** The runtime cost of that guarantee is unexamined.
6. **Integer overflow panics.** Wrapping arithmetic would be library functions. The performance cost and the behavior of `uint` subtraction need review.
7. **Record literals are checked exactly, values structurally.** This mirrors TypeScript's excess-property check. Whether optional fields (`age?: int`) are worth adding on top of `int | null` fields is open.
8. **Newline rule.** The two-rule description in section 2 needs a precise token table, and the leading-`|` continuation should be tested against real code, in both expression and type context.
9. **Named arguments on function values** require parameter names in the function type. Whether names are part of type identity, and what happens when a lambda is assigned to a named type, is unspecified.
10. **Iteration is built in for arrays, maps, and strings only.** There is no iterator protocol, so user types cannot be used in `for`, and `Array.range` allocates. Lazy ranges or an `Iter` namespace would fix both.
11. **Modules** are sketched. Package resolution, versioning, and whether selective import is needed are open.
12. **No generic constraints.** Fine while `==` and hashing are universal. Sorting, numeric generics, and `String.from` for user types will eventually need some bound mechanism.
13. **`try` as the propagation keyword.** Postfix `?` collides with `?.`. `try` reads well but means something else in JavaScript.
14. **`{ x }` is a lambda, so record literals have no shorthand properties.** Patterns do allow `{ x, y }`. The asymmetry is deliberate but may confuse.
15. **Unions must be distinguishable at run time,** which limits them to one array, map, and function member and requires records to be tagged. Narrowing through a field path such as `source.status.kind` is unsound if another goroutine or an aliased reference reassigns the field, exactly as in TypeScript.
16. **Literal types are strings only.** Boolean and integer literal types (`ok: true`) are deferred until a need appears.
17. **Nothing is immutable** except strings. A `readonly` field modifier or frozen records may be needed for safe sharing between goroutines.
18. **Strings index by code point.** Grapheme-aware operations and a dedicated character type are deferred.
19. **Numeric aliases.** `int` for `int64` and `byte` for `uint8` give two names for one type, against the one-way principle. The alternative is to have only `int` and `uint` at 64 bits plus the sized names.
