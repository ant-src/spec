# Ant Language Specification

Draft 0.1 · October 2026

Ant is a general-purpose, garbage-collected language with JavaScript-like syntax, static types, expression-oriented control flow, and goroutine-style concurrency. This document describes the language as a programmer sees it. It does not describe the compiler or the runtime.

The name "Ant" is a placeholder.

## 1. Principles

- **One obvious way.** When two constructs would do the same job, the language keeps one.
- **No implicit coercion.** A value never changes type without a visible conversion.
- **Everything is an expression.** Blocks, `if`, `match`, and loops produce values.
- **Errors are values.** `Result` carries expected failures and `null` carries absence. `panic` is for bugs.
- **Types are advisory.** A separate checker reads annotations and the interpreter discards them. The only thing the interpreter keeps from a `type` declaration is its name, which becomes a tag (section 4). No runtime behavior depends on a type that was written down.
- **Minimal syntax.** The grammar needs one token of lookahead and no feedback from the type checker.

Section 13 lists the decisions this draft leaves open.

## 2. Lexical structure

Source files are UTF-8 text. The file extension is `.ant`.

### Comments

```ant
// line comment
/* block comment */
```

Block comments do not nest.

### Identifiers and keywords

An identifier starts with an ASCII letter or `_` and continues with ASCII letters, digits, or `_`. Case carries no meaning. `_` on its own is the wildcard pattern and cannot be read.

Keywords:

```
break continue defer else export false for func go if import
in match null return true try type var void while
```

These words are reserved so that they stay available and so that JavaScript habits produce an error rather than an identifier:

```
as async await class const enum interface is switch undefined yield
```

Names such as `Array`, `Map`, `Result`, `never`, `print`, and `panic` are ordinary identifiers bound by the standard library. They are not keywords.

### Literals

```ant
42          1_000_000     0xFF        0b1010    // integers
3.14        1e9           2.5e-3                // floats
"hello"     "line\nbreak" "\u{1F600}"           // strings
`total: ${count} items`                         // template strings
true        false         null
```

An integer literal is decimal, `0x` hexadecimal, or `0b` binary, with `_` allowed between digits. A float literal has digits on both sides of the point, an exponent, or both; `.5` and `1.` are errors. An integer literal is always an `int` and a float literal is always a `float64`. Other numeric types are reached through a conversion, as in `byte(255)` or `float32(1.5)`. `1` is never a float; write `1.0`.

The escapes are `\n`, `\t`, `\r`, `\\`, `\"`, `` \` ``, `\$`, and `\u{...}`. A plain string stays on one line; a template string may span lines. Template strings interpolate any expression. Each `${...}` is converted with `String.from`, which is defined for every type (section 11), and braces nest inside it, so a lambda or a record literal can appear there. There are no raw strings and no character literals.

### Line endings

A newline ends an expression, except when:

- the line ends with a token that cannot end an expression, such as a binary operator, `,`, `(`, `[`, `{`, `=`, or `=>`; or
- the next non-blank line starts with `.`, `?.`, or `|`.

A semicolon also ends an expression. Nothing else is inferred. In particular, a line that starts with `(` or `[` begins a new statement, so `a` followed by `(b)` on the next line is two statements and not a call, and a `return` at the end of a line returns `void`, which the checker rejects in a function with another return type. `else` must follow the closing `}` on the same line. A trailing comment does not change any of this.

Inside parentheses, square brackets, and braces that are not a block, newlines are ignored. The items of a call, a literal, a record type, a parameter list, a `match`, and an import list are separated by commas, with an optional trailing comma. Only blocks separate their items by newlines.

The continuation rule for a leading `.`, `?.`, or `|` exists so that pipelines, and union types, read top to bottom:

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
if count = 5 { ... }    // compile error: void is not bool
```

An assignment target is a variable, a field such as `p.x`, or an element such as `xs[i]`. Patterns are not assignment targets. There is no `++`, `--`, or `const`.

## 4. Types

Ant is statically typed. Types are checked before the program runs, and most annotations are inferred. A named record type is nominal: each `type` declaration of a record is a distinct type, identified by its tag. Every other type is structural: two types with the same shape are the same type.

Types are checked by a separate checker and erased before the program runs. The interpreter parses annotations and discards them. A `type` declaration is the one exception: its body is discarded, but its name is bound to a fresh tag value, and a record literal with that name stores the tag (see Records). Every `type` declaration binds a tag, even an alias, because the interpreter does not look at the body; only record literals and patterns use tags, and the checker allows a literal head only on a record type. Every rule in this document that mentions a type is enforced by the checker, and every runtime rule is defined on values, which carry their concrete type. A program can run without being checked; where the checker would have rejected it, the runtime panics at the point of the error, such as `==` or `+` on operands of different types, a call on a value that is not a function, or a field read on a value that is not a record.

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

A record type lists named fields. A record literal names the type and lists the fields, as in Go. Fields are mutable.

```ant
type Point = { x: float64, y: float64 }

var p = Point{ x: 1.0, y: 2.0 }
p.x = 3.0
```

Every record value therefore has a name; there are no anonymous record literals. The head of a literal is an identifier path, so a type reached through a namespace is written `Geometry.Point{ x: 1.0 }`. Type arguments are never written there. A literal has no shorthand entries: write `Point{ x: x }`, not `Point{ x }`.

The name is part of the value. A `type` declaration whose body is a record type binds its name to a fresh tag, and a literal stores the tag of its head in the record. The tag is all the interpreter keeps of a type declaration. It is compared only by identity, so the interpreter never interprets a type, and a tag reached through an import or an alias is the same tag. The checker identifies the type by the same tag: two declarations with the same fields are different types, and `type B = A` is a compile error when `A` is a record type, since it would mint a second tag for one type. Declare the fields again instead.

A record has no dynamic access: `p["x"]` is a compile error, and `for` does not iterate a record. When the keys are data rather than part of the type, use a `Map` (next section).

A named record type accepts only values that carry its tag. An anonymous record type, written in an annotation as `{ name: string }`, accepts any record that has at least those fields, whatever its tag. This is structural width subtyping, and it is how a function takes "anything with a name". A record literal must list exactly the fields of its named type, which catches typos.

```ant
type Named = { name: string }
type Person = { name: string, age: int }
func greet(n: { name: string }): string { `hi ${n.name}` }

var user = Person{ name: "ada", age: 36 }
greet(user)                                 // ok: user has a name field
var n: Named = user                         // compile error: a Person is not a Named
greet(Named{ name: "ada", age: 36 })        // compile error: Named has no field age
```

The spread `...` copies all fields of a record into a new literal. Later fields win. The tag comes from the head, so a spread also converts between record types with the same fields.

```ant
type Vec = { x: float64, y: float64 }

var moved = Point{ ...p, x: 0.0 }
var v = Vec{ ...p }                        // a Vec with the fields of p
```

Records, arrays, and maps are reference values: assigning or passing one shares it, and a change made through one name is visible through every other. `==` compares structure, never identity. Two records are equal when they carry the same tag and their fields are equal; arrays compare by length and elements, maps by key set and values, primitives by value, and functions and synchronization objects by identity. The comparison recurses with `==` over every run-time field, including fields the static type does not mention, so it agrees with `String.from` and `Json.stringify`. A pair of values already under comparison counts as equal, so cyclic structures compare in finite time. Identity is a library call: `Record.same`, `Array.same`, and `Map.same` report whether two names refer to one value.

```ant
var p = Point{ x: 1.0, y: 2.0 }
var q = p
q.x = 5.0
p.x                               // 5.0: one record under two names
p == Point{ x: 5.0, y: 2.0 }      // true
Record.same(p, q)                 // true
Record.same(p, Point{ ...p })     // false
```

### Arrays and maps

```ant
var xs: Array[int] = [1, 2, 3]
var more = [...xs, 4]                       // spread copies elements
var ages = Map{ "ada": 36, "linus": 54 }    // Map[string, int]
var empty: Map[string, int] = Map{}
```

Square brackets build arrays. A map literal is `Map{ key: value, ... }`, with the same type-name prefix as a record literal. Map keys are expressions, so `Map{ name: 1 }` keys on the variable `name`; write `Map{ "name": 1 }` for the string. `Array[T]` is dense and growable. `Map[K, V]` keys compare the way `==` does, so a record or an array can be a key. A key is hashed when it is inserted, and mutating it afterwards is a program error like a data race: memory stays safe, but the entry may become unreachable. Section 11 covers the operations.

### Unions

`A | B` is a type whose values belong to `A` or to `B`. In a type, `|` builds a union; in an expression, it is the pipe (section 5). A union may span several lines when each continuation line starts with `|`. A function type's return type extends as far right as possible, so `func(T): A | B` returns `A | B`; parenthesize the function type to put it inside a union.

```ant
type Id = int | string

func describe(id: Id): string {
  match id {
    n: int => `number ${n}`,
    s: string => `text ${s}`,
  }
}
```

A nullable type is written `T | null`. See section 7.

The members of a union must be distinguishable at run time. A union may contain at most one array type, one map type, and one function type. It may contain any number of named record types, since each carries its tag, but an anonymous record type cannot share a union with another record type.

### Tagged unions

A union of named record types is a tagged union: the tag each record carries tells the members apart. Matching on the record narrows the value to one member. There is no `kind` field and no `is` test; `match` is the only way to narrow a union of records, and a single-member test is a `match` with a `_` arm.

```ant
type Circle = { radius: float64 }
type Rect = { width: float64, height: float64 }
type Empty = {}
type Shape = Circle | Rect | Empty

var s: Shape = Circle{ radius: 2.0 }

func area(s: Shape): float64 {
  match s {
    Circle{ radius } => 3.14159 * radius * radius,
    Rect{ width, height } => width * height,
    Empty{} => 0.0,
  }
}

match s {
  Circle{ radius } => print(radius),
  _ => {},
}
```

A pattern with a head, such as `Circle{ radius }`, tests the tag and then the fields; a headless pattern `{ radius }` tests only the fields. Tags are compared by identity, so a pattern matches records built from the same declaration, under whatever name it was imported. A union of empty records is an enumeration, and each member is also a type of its own that a function can take as a parameter.

Through a value of union type, a field can be read when every member has it, and its type is the union of the members' field types. A field can never be assigned through a union type; narrow first, then assign.

`Result[T, E]` is a standard tagged union of `Ok[T]` and `Err[E]`. See section 8.

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
  Pair{ first: p.second, second: p.first }
}
```

Type arguments are never written at a call site. They are inferred from the arguments or from the expected type. When inference has nothing to work with, annotate the result.

```ant
var xs = Array.map([1, 2, 3], { x * 2 })   // Array[int]
var ys: Array[string] = []                  // annotation needed
```

Type parameters have no constraints in this draft. `==` and `Map` keys work on every type, so most generic code needs none.

### Type declarations

`type` declares a name and appears only at the top level of a module. When the body is a record type, the declaration creates a new type with that name as its tag (see Records). Otherwise the name is an alias: `type UserId = int` makes `UserId` interchangeable with `int`, and `type Shape = Circle | Rect` is interchangeable with the union written out. There are no classes, interfaces, or prototypes.

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
| equality | `==` `!=` | both operands must have the same type; structural (section 4) |
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

Braces mean one of three things, decided by the token before them. After a type name, including `Map`, they build a value of that type. After `func(...)`, `else`, `go`, `defer`, or `=>` in a `match` arm, and at the end of an `if`, `while`, `for`, or `match` header, they are a block. Anywhere else they are a lambda (section 6).

So `{}` after one of those keywords is an empty block of type `void`, and elsewhere it is a lambda that returns `void`. A record or map literal inside a block needs no extra braces: `if c { Point{ x: 1.0, y: 0.0 } } else { origin }`.

A header has no parentheses, as in Go. It ends at the first `{` that is not an operand: one that directly follows an identifier path, a literal, or a closing `)` or `]`. A `{` directly after an operator or an opening bracket starts a lambda. A record or map literal in a header would put `{` after an identifier path, so it must be parenthesized, as in Go: `if u == (User{ name: "ada" }) { ... }`. The `{` must sit on the same line as the header, because a newline would end the header expression (section 2).

### `if`

```ant
var label = if n < 0 { "negative" } else if n == 0 { "zero" } else { "positive" }
```

Both branches must have the same type. An `if` without `else` has type `void`.

### Loops

`for` iterates over an array, a map, or a string. Each iteration binds a fresh variable, so a closure created in the body keeps that iteration's value. `while` repeats while a condition holds. Both have type `void`. `break` and `continue` work as in JavaScript, without labels.

```ant
for user in users {
  if user.banned { continue }
  notify(user)
}

for { key, value } in ages {  // destructures each Entry[string, int]
  print(`${key}: ${value}`)
}

for i in Array.range(0, 10) { ... }

while !done { done = step() }
```

### `match`

`match` compares a value against patterns in order and evaluates the first arm that fits. Arms are separated by commas. Every arm has the same type, and the patterns must cover every possible value, so a `match` can never fall through. For a union of records that means every member; for a primitive it usually means a final `_`.

```ant
func describe(n: int): string {
  match n {
    0 => "zero",
    x if x < 0 => "negative",
    _ => "positive",
  }
}
```

Patterns:

| Pattern | Matches |
|---|---|
| `42` `-1` `"a"` `true` `null` | the literal value |
| `name` | anything; binds `name` |
| `_` | anything; binds nothing |
| `name: Type` | a union member; `Type` is a primitive, `null`, `Array`, `Map`, `func`, or a named record type; binds `name` |
| `{ x, y }` `{ x: px }` `{ status: Active{} }` | a record of any tag; each field pattern binds the field, renames it, or tests it against a sub-pattern |
| `Circle{ radius }` `Empty{}` `Geometry.Point{ x }` | a record carrying the tag of the named type, then its fields as above |
| `[]` `[first, ...rest]` | an array of matching length, or a prefix with the rest |
| `pattern if condition` | the pattern, when the guard is true |

Patterns nest. A record pattern ignores fields it does not mention. There are no or-patterns. `var` and `for` accept a record pattern on the left side; array patterns can always fail to match, so they appear only in `match`.

```ant
var { x, y } = origin
```

### `return`, `break`, `continue`

These have type `never`, so they can appear anywhere an expression is expected. `return` takes the whole expression to its right, so `x ?? return y + 1` returns `y + 1`; parenthesize it to end earlier. `panic` is an ordinary function of type `never` (section 8).

```ant
var user = Map.get(users, id) ?? return Result.err(Error{ message: "no such user" })
```

## 6. Functions

`func` declares a named function at the top level of a module; inside a block, bind a function with `var`. Parameters are annotated; the return type may be inferred. The body is a block, so the last expression is the result and `return` is only needed to leave early.

```ant
func clamp(value: int, low: int, high: int): int {
  if value < low { return low }
  if value > high { return high }
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

An anonymous function is `func` without a name. Its parameters are annotated and it may state a return type, exactly like a declaration. A lambda is a bare block with one implicit parameter named `x`. At run time a lambda accepts zero or one argument, so it also serves where a zero-parameter function is expected; the checker gives it the arity of the expected function type.

```ant
var add = func(a: int, b: int) { a + b }
var double: func(int): int = { x * 2 }
var isAdult: func(User): bool = { x.age >= 18 }

Array.map([1, 2, 3], { x * x })
Mutex.withLock(lock, { counter += 1 })
```

A lambda's parameter type comes from the function type the context expects. With no expected type, as in an unannotated `var`, a lambda is a compile error. Nested lambdas each bind their own `x`; use `func` when you need both.

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

match user {
  null => print("not found"),
  u => print(u.name),                   // u: User
}

if user != null {
  print(user.name)                      // user: User here
}
```

`?.` applies to field access, indexing, and calls, spelled `a?.b`, `a?.[i]`, and `f?.(x)`; each yields `null` when the left side is null. `??` takes any expression on the right, including `return` and `panic`, so `value ?? panic("unreachable")` unwraps and `value ?? return null` propagates. The type checker narrows after a `null` test, as shown in the last two examples.

## 8. Errors

### `Result`

Expected failures are values of `Result[T, E]`, a tagged union of two records:

```ant
type Ok[T] = { value: T }
type Err[E] = { error: E }
type Result[T, E] = Ok[T] | Err[E]
```

`Result.ok(value)` and `Result.err(error)` are plain functions that build the two records; `Ok{ value: 1 }` is the same value as `Result.ok(1)`. The error type is whatever the author chooses. The standard library uses `Error`, a record `{ message: string }`; user code often declares a tagged union of its own.

```ant
type EmptyInput = {}
type BadDigit = { at: int }
type ParseError = EmptyInput | BadDigit

func parseInt(s: string): Result[int, ParseError] {
  if String.isEmpty(s) { return Result.err(EmptyInput{}) }
  ...
  Result.ok(n)
}

match parseInt(input) {
  Ok{ value } => print(`parsed ${value}`),
  Err{ error: EmptyInput{} } => print("nothing to parse"),
  Err{ error: BadDigit{ at } } => print(`bad digit at ${at}`),
}
```

Because unions are flat, error types compose without wrapping. A function that parses a file can return `Result[Config, ParseError | Error]` and `try` both kinds of call.

### `try`

`try` unwraps a `Result` or a nullable value. On `Ok{ value }` or a non-null value it evaluates to the value. On an `Err` it returns that record from the enclosing function; on `null` it returns `null`. The enclosing function must therefore return a `Result` whose error type accepts the error, or a type that includes `null`.

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

`panic(message)` is a prelude function of type `never`. It stops the current goroutine immediately. It is for bugs and impossible states, never for expected failures. Panics cannot be caught. A panic in the main goroutine ends the program with a non-zero exit status; a panic in any other goroutine ends only that goroutine (section 9).

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
  var results: Array[Result[Response, Error]] = Array.filled(Array.length(urls), Result.err(Error{ message: "pending" }))
  var lock = Mutex.new()
  var wg = WaitGroup.new()

  for entry in Array.entries(urls) {
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

Each file is a module: a sequence of `import` declarations followed by `var`, `func`, and `type` declarations. Nothing else appears at the top level. A declaration prefixed with `export` is visible to other modules; everything else is private. Top-level `var` initializers run in source order the first time the module is imported, after the modules it imports.

```ant
// geometry.ant
export type Point = { x: float64, y: float64 }

export func distance(a: Point, b: Point): float64 {
  Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y))
}
```

A module is a record of its exports, and `import` destructures it with a pattern. A record pattern brings chosen exports into scope, with the usual `name: alias` renaming. A bare name binds the whole module as a namespace, so user modules look like standard-library namespaces.

```ant
import "./geometry.ant" { distance, Point }
import "./geometry.ant" { distance: dist, Point }
import "./geometry.ant" Geometry

var d = Geometry.distance(p, q)
```

The path is a file path relative to the importing file, extension included. It comes first so that an editor knows the module before the pattern is typed. Types and values import alike: a `type` export is its tag, so a record built in one module matches a pattern written against the imported name in another, under whatever local name it was given.

Two imports binding the same local name are a compile error, and a top-level declaration cannot shadow an imported name, so every name in a file has one visible origin. There is no re-export. Import cycles are a compile error.

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
Array.range(from, to)         Array.filled(n, v)           Array.same(xs, ys)
Array.sum(xs)                 Array.flatten(xs)            Array.isEmpty(xs)
```

Only `Array.push` and `Array.pop` modify their input. Every other function returns a new array and leaves the argument untouched, so `Array.sort(xs)` is a sorted copy. `Array.entries(xs)` yields `Indexed[T]` records, `{ index: int, value: T }`.

### Maps

`Map[K, V]` is an unordered hash map. `m[k]` reads `V | null`; `m[k] = v` inserts or replaces. When `V` itself includes `null`, `Map.has` is the only way to tell a missing key from a stored `null`.

```ant
Map.size(m)         Map.has(m, k)        Map.get(m, k)        Map.set(m, k, v)
Map.remove(m, k)    Map.keys(m)          Map.values(m)        Map.entries(m)
Map.map(m, f)       Map.filter(m, f)     Map.merge(m, n)      Map.same(m, n)
```

Iterating a map with `for` yields `Entry[K, V]` records, `{ key: K, value: V }`, in unspecified order.

### Strings

A `string` is immutable. Index and length are in Unicode code points. Byte access goes through `String.toBytes`.

```ant
String.length(s)         String.slice(s, from, to)    String.concat(parts)
String.split(s, sep)     String.join(parts, sep)      String.trim(s)
String.contains(s, t)    String.startsWith(s, t)      String.replace(s, old, new)
String.toUpper(s)        String.toLower(s)            String.chars(s): Array[string]
String.toBytes(s)        String.fromBytes(bytes)      String.from(value)
```

`String.from` renders any value. Primitives, arrays, and maps render in literal syntax; records render as `Point{ x: 1.0, y: 2.0 }` with the name of their tag; functions render as `func`. It is the only implicit use of this function, and only inside template strings.

### Others

| Namespace | Purpose |
|---|---|
| `Math` | `abs`, `min`, `max`, `pow`, `sqrt`, `floor`, `ceil`, `round`, constants |
| `Bits` | `and`, `or`, `xor`, `not`, `shiftLeft`, `shiftRight`, `popCount` |
| `Result` | constructors and combinators (section 8) |
| `Mutex`, `RwMutex`, `WaitGroup`, `Once`, `Cond`, `Atomic` | synchronization (section 9) |
| `Record` | `same` for identity comparison of records |
| `Json` | `parse`, `stringify` |
| `File`, `Http`, `Time`, `Os` | I/O; every operation that can fail returns `Result` |
| `print`, `panic` | the only global functions; `print` writes `String.from(value)` and a newline to standard output |

## 12. Example

```ant
type Active = {}
type Suspended = { reason: string }
type Status = Active | Suspended

type Account = {
  id: int,
  owner: string,
  balance: float64,
  status: Status,
}

type NotFound = { id: int }
type Insufficient = { needed: float64 }
type AccountSuspended = { id: int, reason: string }
type TransferError = NotFound | Insufficient | AccountSuspended

func transfer(accounts: Map[int, Account], from: int, to: int, amount: float64): Result[void, TransferError] {
  var source = accounts[from] ?? return Result.err(NotFound{ id: from })
  var target = accounts[to] ?? return Result.err(NotFound{ id: to })

  match source.status {
    Suspended{ reason } => return Result.err(AccountSuspended{ id: from, reason: reason }),
    _ => {},
  }
  if source.balance < amount {
    return Result.err(Insufficient{ needed: amount - source.balance })
  }

  source.balance -= amount
  target.balance += amount
  Result.ok(void)
}

func isActive(account: Account): bool {
  match account.status {
    Active{} => true,
    Suspended{} => false,
  }
}

func report(accounts: Map[int, Account]): string {
  Map.values(accounts)
    | Array.filter(isActive)
    | Array.sortBy({ x.balance })
    | Array.map({ `${x.owner}: ${x.balance}` })
    | String.join("\n")
}

func main() {
  var accounts: Map[int, Account] = Map{}
  accounts[1] = Account{ id: 1, owner: "ada", balance: 100.0, status: Active{} }
  accounts[2] = Account{ id: 2, owner: "linus", balance: 20.0, status: Suspended{ reason: "audit" } }

  match transfer(accounts, 1, 2, 50.0) {
    Ok{} => print("ok"),
    Err{ error: NotFound{ id } } => print(`unknown account ${id}`),
    Err{ error: Insufficient{ needed } } => print(`short by ${needed}`),
    Err{ error: AccountSuspended{ id, reason } } => print(`account ${id} is suspended: ${reason}`),
  }

  print(report(accounts))
}
```

## 13. Open decisions

Each item below is a choice this draft made for the sake of having examples, not a settled design. The current choice is stated first.

1. **Narrowing a union of records is `match` only.** Testing one member inside an expression needs a two-arm `match` or a helper such as `isActive` in section 12. A boolean pattern test, perhaps `x is Active{}`, would remove that cost; `is` is reserved for it.
2. **No explicit type arguments at call sites.** Keeps `f[T](x)` out of the grammar, so `a[b]` is always indexing. Needs confirmation that inference from arguments and expected type is always enough.
3. **`go` returns nothing.** Results come back through shared memory and a `WaitGroup`. A handle with `join` would be more convenient but is a channel in disguise, and panics would need a representation on it.
4. **Data races are undefined in outcome but memory safe.** The runtime cost of that guarantee is unexamined.
5. **Integer overflow panics.** Wrapping arithmetic would be library functions. The performance cost and the behavior of `uint` subtraction need review.
6. **A record literal must match its named type exactly, while anonymous record types are checked structurally.** Whether optional fields (`age?: int`) are worth adding on top of `int | null` fields is open.
7. **Newline rule.** The rules in section 2 and the grammar's layout notes should be tested against real code, especially the leading-`|` continuation in both expression and type context.
8. **Named arguments on function values** require parameter names in the function type. Whether names are part of type identity, and what happens when a lambda is assigned to a named type, is unspecified.
9. **Iteration is built in for arrays, maps, and strings only.** There is no iterator protocol, so user types cannot be used in `for`, and `Array.range` allocates. Lazy ranges or an `Iter` namespace would fix both.
10. **Packages.** Imports name files only. How packages are named, resolved, and versioned, and whether re-export is needed, are open.
11. **No generic constraints.** Fine while `==` and hashing are universal. Sorting, numeric generics, and `String.from` for user types will eventually need some bound mechanism.
12. **`try` as the propagation keyword.** Postfix `?` collides with `?.`. `try` reads well but means something else in JavaScript.
13. **Record literals have no shorthand entries, but patterns do.** `Point{ x, y }` is unambiguous now that bare braces are always a lambda, so allowing it in literals is a question of taste rather than parsing.
14. **Unions must be distinguishable at run time,** which limits them to one array, one map, one function, and one anonymous record member. Named records are free because they carry tags.
15. **Nothing is immutable** except strings. A `readonly` field modifier or frozen records may be needed for safe sharing between goroutines.
16. **Strings index by code point.** Grapheme-aware operations and a dedicated character type are deferred.
17. **Numeric aliases.** `int` for `int64` and `byte` for `uint8` give two names for one type, against the one-way principle. The alternative is to have only `int` and `uint` at 64 bits plus the sized names.
18. **Erasure makes sized integers explicit.** `var b: byte = 255` no longer type-checks; `byte(255)` is required, and a byte array literal needs a conversion per element or a helper such as `Bytes.of`. Literal suffixes such as `255u8` are the alternative.
19. **Map keys are expressions.** `Map{ name: 1 }` keys on the variable `name`, not the string. This is consistent but will trip JavaScript users. Bare-identifier string keys are the alternative, and they bring JavaScript's computed-key syntax with them.
20. **Unchecked programs panic on type errors.** The runtime checks the interpreter performs are the real dynamic semantics of the language and need to be listed in full, not by example.
21. **Deferred syntax.** Raw strings, character literals, string literal types, or-patterns, labeled loops, destructuring assignment, and a pattern test expression are left out until a need appears.
