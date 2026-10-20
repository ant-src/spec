# Ant Language Specification

Draft 0.1 · October 2026

Ant is a general-purpose, garbage-collected language with JavaScript-like syntax, static types, expression-oriented control flow, and goroutine-style concurrency. This document describes the language as a programmer sees it. It does not describe the compiler or the runtime.

The name "Ant" is a placeholder.

## 1. Principles

- **One obvious way.** When two constructs would do the same job, the language keeps one.
- **No implicit coercion.** A value never changes type without a visible conversion.
- **Everything is an expression.** Blocks, `if`, and loops produce values.
- **Errors are values.** `Result` carries expected failures and `null` carries absence. `panic` is for bugs.
- **Types are advisory.** `ant check` reads annotations and `ant run` discards them. The only thing the interpreter keeps from a `type` declaration is its name, which becomes a tag (section 4). No runtime behavior depends on a type that was written down.
- **Minimal syntax.** The grammar needs one token of lookahead and no feedback from the type checker.

Section 14 lists the decisions this draft leaves open.

## 2. Lexical structure

Source files are UTF-8 text. The file extension is `.ant`.

### Comments

```ant
// line comment
/* block comment */
```

Block comments do not nest.

### Identifiers and keywords

An identifier starts with an ASCII letter or `_` and continues with ASCII letters, digits, or `_`. Case carries no meaning. `_` on its own is a write-only identifier: it can be bound or assigned wherever a name can, which discards the value, and reading it is a compile error in `ant check` and a panic in `ant run`.

Keywords:

```
break continue defer else export false for func go if import
in is null return true try type var void while
```

These words are reserved so that they stay available and so that JavaScript habits produce an error rather than an identifier:

```
as async await class const enum interface match switch undefined
```

Names such as `Array`, `Map`, `Result`, `never`, `print`, and `panic` are ordinary identifiers bound by the standard library. They are not keywords.

### Literals

```
42          1_000_000     0xFF        0b1010    // integers
3.14        1e9           2.5e-3                // floats
"hello"     "line\nbreak" "\u{1F600}"           // strings
`total: ${count} items`                         // template strings
true        false         null
```

An integer literal is decimal, `0x` hexadecimal, or `0b` binary, with `_` allowed between digits. A float literal has digits on both sides of the point, an exponent, or both; `.5` and `1.` are errors. An integer literal is always an `int` and a float literal is always a `float64`. An integer literal that does not fit an `int` is a compile error, so the most negative `int` is written `Math.minInt`. Other numeric types are reached through a conversion, as in `byte(255)` or `float32(1.5)`. `1` is never a float; write `1.0`.

The escapes are `\n`, `\t`, `\r`, `\\`, `\"`, `` \` ``, `\$`, and `\u{...}`, whose hexadecimal value must be a Unicode scalar value: at most `10FFFF` and not a surrogate. A plain string stays on one line; a template string may span lines. Template strings interpolate any expression. Each `${...}` is converted with `String.from`, which is defined for every type (section 11), and braces nest inside it, so a lambda or a record literal can appear there. There are no raw strings and no character literals.

### Line endings

A newline ends an expression, except when:

- the line ends with a token that cannot end an expression, such as a binary operator, `,`, `(`, `[`, `{`, or `=`; or
- the next non-blank line starts with `.`, `?.`, `|`, or `else`.

A semicolon also ends an expression. Nothing else is inferred. In particular, a line that starts with `(` or `[` begins a new statement, so `a` followed by `(b)` on the next line is two statements and not a call, and a `return` at the end of a line returns `void`, which the checker rejects in a function with another return type. A trailing comment does not change any of this.

Inside parentheses, square brackets, and braces that are not a block, newlines are ignored. The items of a call, a literal, a record type, a parameter list, and an import list are separated by commas, with an optional trailing comma. Only blocks separate their items by newlines.

The continuation rule for a leading `.`, `?.`, `|`, or `else` exists so that pipelines, union types, and `else` chains read top to bottom; none of those tokens can start a statement, so the rule is unambiguous:

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

An assignment target is a variable, a field such as `p.x`, an element such as `xs[i]`, or an array destructuring of targets such as `[a, b]` (section 5). There is no `++`, `--`, or `const`.

## 4. Types

Ant is statically typed. Types are checked before the program runs, and most annotations are inferred. A named record type is nominal: each `type` declaration of a record is a distinct type, identified by its tag. Every other type is structural: two types with the same shape are the same type.

Types are checked by a separate command and erased before the program runs. `ant check file.ant` runs the checker over the file and every module it imports, including code nothing calls, and exits non-zero with the errors; this is where inference, bounds, and narrowing live, and where their cost goes. `ant run file.ant` performs no static work beyond parsing: it loads the import graph, so a syntax error anywhere stops the program before `main`, and then it runs, with annotations parsed and discarded and no name resolution ahead of time. Editors and continuous integration run `check`; the terminal runs `run`. There is no flag that makes `run` check first. A `type` declaration is the one exception: its body is discarded, but its name is bound to a fresh tag value, and a record literal with that name stores the tag (see Records). Every `type` declaration binds a tag, even an alias, because the interpreter does not look at the body; only record literals and `is` tests use tags, and the checker allows a literal head only on a record type. Every rule in this document that mentions a type is enforced by the checker, and every runtime rule is defined on values, which carry their concrete type. A program can run without being checked; where the checker would have rejected it, the runtime panics at the point of the error, such as `+` on operands of different types, a call on a value that is not a function, or a field read on a value that is not a record. Section 12 lists every such check.

### Primitives

| Type | Values |
|---|---|
| `bool` | `true`, `false` |
| `int8` `int16` `int32` `int64` | signed integers |
| `uint8` `uint16` `uint32` `uint64` | unsigned integers |
| `float32` `float64` | IEEE 754 floats |
| `string` | immutable sequence of Unicode code points, stored as UTF-8 |
| `null` | the single value `null` |
| `void` | the single value `void`, which carries no information |
| `never` | the type of expressions that do not return, such as `panic(...)` or `return` |

`int` is an alias for `int64` and `byte` is an alias for `uint8`: `int` is the default, and the sized names are for when the size matters. The prelude also declares `Integer`, the union of the eight integer types, `Number`, which adds the two float types, and `Ordered`, which is `Number | string`; they exist to bound type parameters (see Generics).

`void` is both a type and its only value, like `null`. A block that ends in a declaration or assignment, a loop, and a function with nothing to return all produce `void`. Write it explicitly when a value is required, as in `Result.ok(void)`.

Numeric types never mix. Convert explicitly by calling the target type as a function: each of the ten numeric names is a prelude function that takes any numeric value, and it is a value in its own right, so `Array.map([72, 105], byte)` builds an `Array[byte]`. Conversions that lose information panic rather than wrap or truncate silently; float-to-int conversion truncates toward zero and panics when out of range. `bool` and `string` are not callable: parsing is `String.toInt` and `String.toFloat`, rendering is `String.from`. There are no literal suffixes; an integer literal is always an `int` and a float literal a `float64`, so a `byte` is written `byte(255)`.

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

Every record value therefore has a name; there are no anonymous record literals. The head of a literal is an identifier path, so a type reached through a namespace is written `Geometry.Point{ x: 1.0 }`. Type arguments are never written there. A bare identifier is a shorthand entry: `Point{ x, y }` means `Point{ x: x, y: y }`, the same shorthand destructuring uses. Map literals follow the same two rules (next section).

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

The spread `...` copies all fields of a record into a new literal. Later fields win. The tag comes from the head, so a spread also converts between record types with the same fields. The operand must have a named record type: a value of anonymous record type may carry fields its type does not list, and the spread would copy them too.

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
var ages = Map{ ada: 36, linus: 54 }        // Map[string, int]
var keyed = Map{ (name): 1, 7: "seven" }    // computed and non-string keys
var empty: Map[string, int] = Map{}
```

Square brackets build arrays. A map literal is `Map{ key: value, ... }`, with the same type-name prefix as a record literal. A key that is a single identifier is the string of that identifier, as in JavaScript, so `Map{ name: 1 }` has the key `"name"`; any other expression is evaluated as the key, and a parenthesized identifier `(name)` is the variable. A bare identifier alone is shorthand, so `Map{ name }` means `Map{ "name": name }`. In both brace literals, then, a bare identifier before `:` is a name: the field of a record, the string key of a map. `Array[T]` is dense and growable. `Map[K, V]` keys compare the way `==` does, so a record or an array can be a key. A key is hashed when it is inserted, and mutating it afterwards is a program error like a data race: memory stays safe, but the entry may become unreachable. Section 11 covers the operations.

### Unions

`A | B` is a type whose values belong to `A` or to `B`. In a type, `|` builds a union; in an expression, it is the pipe (section 5). A union may span several lines when each continuation line starts with `|`. A function type's return type extends as far right as possible, so `func(T): A | B` returns `A | B`; parenthesize the function type to put it inside a union.

```ant
type Id = int | string

func describe(id: Id): string {
  if id is int { `number ${id}` } else { `text ${id}` }
}
```

A nullable type is written `T | null`. See section 7.

The members of a union must be distinguishable at run time. A union may contain at most one array type, one map type, and one function type. It may contain any number of named record types, since each carries its tag, but an anonymous record type cannot share a union with another record type.

### Tagged unions

A union of named record types is a tagged union: the tag each record carries tells the members apart. `s is Circle` tests the tag (section 5). In the branch it guards, `s` has type `Circle`; in the `else` branch, `s` has the union minus `Circle` (section 7). There is no `kind` field and no pattern matching: `is` with `if` is the only way to narrow a union of records.

```ant
type Circle = { radius: float64 }
type Rect = { width: float64, height: float64 }
type Empty = {}
type Shape = Circle | Rect | Empty

var s: Shape = Circle{ radius: 2.0 }

func area(s: Shape): float64 {
  if s is Circle { 3.14159 * s.radius * s.radius }
  else if s is Rect { s.width * s.height }
  else if s is Empty { 0.0 }
}

if s is Circle { print(s.radius) }
```

The chain in `area` has no final `else` and still has type `float64`: after the third test `s` has no member left, so the checker knows the chain is complete (section 5, `if`). Adding a member to `Shape` later breaks the chain, and `area` fails to check until it handles the new member. That is the exhaustiveness check. A union of empty records is an enumeration, and each member is also a type of its own that a function can take as a parameter.

Through a value of union type, a field can be read when every member has it, and its type is the union of the members' field types. A field can never be assigned through a union type; narrow first, then assign.

`Result[T, E]` is a standard tagged union of `Ok[T]` and `Err[E]`. See section 8.

### Function types

A function type lists parameter types and the return type. Parameter names are optional and only document intent: a call through a function value is always positional (section 6).

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

Type arguments are never written at a call site. They are solved from the expected type and the arguments (see Inference). When nothing fixes a type parameter, annotate the result.

```ant
var xs = Array.map([1, 2, 3], { x * 2 })   // Array[int]
var ys: Array[string] = []                  // annotation needed
```

A type parameter may carry a bound, written `[T: Bound]`, where the bound is any type. A solution for `T` must be assignable to the bound. Inside the body, `T` is known only to be assignable to its bound: the fields of a record bound can be read and assigned, and an operator applies to `T` when it applies to every member of the bound. Without a bound, `T` is opaque; `==` and `Map` keys still work, because they work on every type. Bounds are the way to accept any array whose elements have a given field, since type arguments are invariant and `Array[Person]` is not an `Array[{ name: string }]`. Nothing changes at run time; the interpreter never sees a bound.

```ant
func max[T: Ordered](a: T, b: T): T { if a > b { a } else { b } }
func names[T: { name: string }](xs: Array[T]): Array[string] { Array.map(xs, { x.name }) }

names(people)                     // ok with Array[Person]: T = Person, which has a name
max(1, 2)                         // int
max(1, 2.0)                       // compile error: int and float64 are different T
```

There are no interfaces, no `where` clauses, and no bounds on type constructors. A user type cannot customize `String.from` or ordering, so records sort through `Array.sortBy` or `Array.sortWith`. A generic type with different type arguments is a different type: `Array[Circle]` is not an `Array[Shape]` (see Assignability).

### Type declarations

`type` declares a name and appears only at the top level of a module. When the body is a record type, the declaration creates a new type with that name as its tag (see Records). Otherwise the name is an alias: `type UserId = int` makes `UserId` interchangeable with `int`, and `type Shape = Circle | Rect` is interchangeable with the union written out. A type may refer to itself through a record, array, map, or function type, so `type Tree = { value: int, children: Array[Tree] }` is fine; `type A = A | null`, or a cycle of plain aliases, is a compile error. There are no classes, interfaces, or prototypes.

### Assignability

A value of type `S` can be used where `T` is expected when one of these holds:

- `S` and `T` are the same type. Primitives never widen; `int8` is not an `int`.
- `T` is a union and `S` is assignable to one of its members, or `S` is a union and every member of `S` is assignable to `T`. Members flatten and deduplicate, so `T | null | null` is `T | null`.
- `S` is `never`. `void` is assignable only to `void`, and `null` only to a type that includes it.
- `T` is an anonymous record type and `S` is a record type with at least the fields of `T`, each with exactly the type `T` gives it. A named record type accepts only its own tag.
- `S` and `T` are the same generic type with identical type arguments. Type arguments are invariant, because contents are mutable: if `Array[Circle]` were an `Array[Shape]`, a widened alias could store a `Rect` among the circles for a later read to panic on, and the checker's guarantee would be gone.
- `S` and `T` are function types with the same number of parameters, each parameter of `T` assignable to the corresponding parameter of `S`, and the result of `S` assignable to the result of `T`. A function with default parameters is also assignable to a type that lists its required parameters plus any prefix of the optional ones.

Widening a container is therefore always by construction, which also makes the copy visible:

```ant
var circles = [Circle{ radius: 1.0 }]
var shapes: Array[Shape] = circles          // compile error: Array[Circle] is not Array[Shape]
var widened: Array[Shape] = [...circles]    // ok: a new array; the expected type widens the elements

var f: func(Circle): float64 = area         // ok: area takes any Shape
var g: func(Shape): float64 = circleArea    // compile error: circleArea takes only a Circle
```

For a `Result`, `try` is the widening step (section 8).

### Inference

Inference is local and bidirectional. Every expression either synthesizes a type or is checked against an expected type. Expected types come from annotations, parameter types, declared return types, the field types of a record literal, the element types of an expected array or map, and the branches of an `if` whose whole has an expected type. Nothing is inferred across statements: an unannotated `var` takes exactly the type of its initializer, so `var s = Active{}` has type `Active`, and a later `s = Suspended{ reason: "x" }` is a compile error unless the declaration says `var s: Status`.

A generic call solves its type parameters in a fixed order: from the expected type first, then from the non-lambda arguments left to right, then from the lambdas. The expected type goes first because type arguments are invariant: `Result.err(NotFound{ id: from })` under an expected `Result[void, TransferError]` sets `E` to `TransferError` and then checks the argument against it. Lambdas go last so that the other arguments have fixed the type their `x` depends on, which is also what lets an editor complete `x.` inside a lambda. A type parameter that nothing fixes is a compile error: annotate the result, or use `func` with annotated parameters.

```ant
Array.map([1, 2, 3], { x * 2 })           // T = int from the array, U = int from the body
var ys: Array[string] = []                // the expected type fixes the element type
var zs = []                               // compile error: annotate
```

Every function parameter is annotated, except lambda parameters. A lambda needs an expected function type with zero or one parameter; its result type is synthesized from the body, and when the expected result is an unsolved type parameter, the body solves it. A function's return type is inferred from its body unless the function is exported or recursive. Exported functions state it so that a module's interface reads without its bodies. Recursion is found on demand: the checker infers a callee's type when it meets a call, and meeting a function whose inference is already in progress is a compile error asking for an annotation.

The branches of an `if` are each checked against the expected type when there is one. Otherwise the expression has the union of the branch types, with `never` dropped, so `if n > 0 { "positive" } else { null }` has type `string | null`.

Literals get no help from context: an integer literal is always `int` and a float literal always `float64`, because the interpreter never sees the expected type (see Primitives).

## 5. Expressions

Every construct is an expression with a type. Statements are just expressions whose value is `void`.

Evaluation is strictly left to right: the callee before its arguments, arguments in written order, and record fields, array elements, and map entries in written order. An assignment evaluates the target's sub-expressions, such as the index in `xs[i()] = f()`, before the right-hand side. `&&`, `||`, and `??` short-circuit. `a | f(b)` evaluates `a`, then `f`, then `b`.

### Operators

From tightest to loosest binding:

| Level | Operators | Notes |
|---|---|---|
| postfix | `a.b` `a?.b` `a[i]` `f(x)` | |
| prefix | `-a` `!a` `try a` | |
| multiplicative | `*` `/` `%` | integer `/` truncates toward zero; `%` is the truncated remainder with the dividend's sign, for floats too |
| additive | `+` `-` | `+` also concatenates strings |
| comparison | `<` `<=` `>` `>=` `is` | numbers and strings; `is` tests a union member |
| equality | `==` `!=` | one operand's type must be assignable to the other's, so `x == null` checks when `x` is nullable; structural (section 4) |
| logical | `&&` then `\|\|` | short-circuit, `bool` only |
| null | `??` | cannot mix with `&&` or `\|\|` without parentheses |
| pipe | `\|` | left associative; in a type, `\|` is a union (section 4) |
| assignment | `=` `+=` `-=` `*=` `/=` `%=` | type `void` |

There is no `===`, no `+` between different types, and no truthiness: a condition must be a `bool`. Integer overflow panics, including unsigned subtraction below zero. Division by zero panics for integers and follows IEEE 754 for floats. Wrapping arithmetic is `Bits.wrapAdd`, `Bits.wrapSub`, and `Bits.wrapMul`, and a shift count outside the operand's width panics.

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

Braces mean one of three things, decided by the token before them. After a type name, including `Map`, they build a value of that type. After `func(...)`, `else`, `go`, or `defer`, and at the end of an `if`, `while`, or `for` header, they are a block. Anywhere else they are a lambda (section 6).

So `{}` after one of those keywords is an empty block of type `void`, and elsewhere it is a lambda that returns `void`. A record or map literal inside a block needs no extra braces: `if c { Point{ x: 1.0, y: 0.0 } } else { origin }`.

A header has no parentheses, as in Go. It ends at the first `{` that is not an operand: one that directly follows an identifier path, a literal, or a closing `)` or `]`. A `{` directly after an operator or an opening bracket starts a lambda. A record or map literal in a header would put `{` after an identifier path, so it must be parenthesized, as in Go: `if u == (User{ name: "ada" }) { ... }`. The `{` must sit on the same line as the header, because a newline would end the header expression (section 2).

### `if`

```ant
var label = if n < 0 { "negative" } else if n == 0 { "zero" } else { "positive" }
```

The branches are checked against the expected type, or the `if` has the union of their types (section 4, Inference). An `if` without `else` has an implicit `else` branch of type `void`. That branch disappears when the condition narrows its subject to `never`, as at the end of a complete chain of `is` tests (section 4, Tagged unions); an explicit `else` there cannot run and is a compile error.

### `is`

`x is T` is `true` when the value of `x` belongs to `T`. `T` is a named record type, a primitive, `null`, `Array`, `Map`, or `func`, written without type arguments, because the runtime has only tags and kinds to look at. The static type of `x` must be a union with `T` as a member, or an anonymous record type to which the named record type `T` is assignable; otherwise the test is always true or always false, which is a compile error. `is` binds like a comparison, so `!(x is Circle)` and `x is Circle || x is Rect` read as expected. As the condition of an `if` on a local variable or a parameter, it narrows (section 7).

```ant
Array.filter(shapes, { x is Circle })
if s is Circle && s.radius > 1.0 { ... }          // s: Circle after the &&
```

### Loops

`for` iterates over an array, a map, a string, or a sequence function; over a string it yields each code point as a one-character string. Each iteration binds a fresh variable, so a closure created in the body keeps that iteration's value. `while` repeats while a condition holds. Both have type `void`. `break` and `continue` work as in JavaScript, without labels.

```ant
for user in users {
  if user.banned { continue }
  notify(user)
}

for { key, value } in ages {  // destructures each Entry[string, int]
  print(`${key}: ${value}`)
}

for i in Iter.range(0, 10) { ... }

while !done { done = step() }
```

A sequence is a function that pushes elements to a callback, as in Go: `Seq[T]` is the prelude alias `func(func(T): bool): void`. `for x in seq` calls `seq` with a `yield` function; each call of `yield` runs the body once and returns `true`, or `false` after a `break`, after which the sequence must return. `return` and panics in the body propagate through the sequence as through any call. Writing a sequence is an ordinary loop that calls `yield`, so user types and lazy ranges need no other protocol.

```ant
func evens(limit: int): Seq[int] {
  func(yield: func(int): bool) {
    var i = 0
    while i < limit {
      if !yield(i) { return }
      i += 2
    }
  }
}

for n in evens(10) { print(n) }
Iter.range(0, 1000) | Iter.filter({ x % 7 == 0 }) | Iter.take(5) | Iter.toArray()
```

### Destructuring

`var` and `for` accept a destructuring on the left side instead of a name. A record destructuring `{ x, y }` binds the fields `x` and `y`, and `{ x: px }` binds the field `x` as `px`; fields not mentioned are ignored. An array destructuring `[a, b]` binds elements by position, extra elements are ignored, and `[head, ...tail]` binds the rest as a new array. Each position holds a name, `_` to discard, or another destructuring, so they nest.

Destructuring is binding plus indexing, and it fails the way indexing does: an array with fewer elements than the fixed positions panics, as `xs[1]` would on a one-element array, and a nested record destructuring that meets a non-record such as `null` panics as a field read would. The checker types each binding from the source, `T` for an element of `Array[T]` and `Array[T]` for the rest, and cannot know lengths.

```ant
var { x, y } = origin
var { address: { city } } = user
var [first, second] = xs             // panics when xs has fewer than two elements
var [head, ...tail] = xs             // tail is a new array; panics only when xs is empty
var [_, y] = pair
for { key, value } in ages { print(`${key}: ${value}`) }
for [a, b] in pairs { print(a + b) }
```

An array destructuring is also an assignment target. Its positions are assignable places or nested array destructurings, and `=` is the only operator allowed, so `[a, b] = [b, a]` swaps and `[xs[0], p.x] = f()` stores into any places. Evaluation follows the assignment rule: the targets' sub-expressions left to right, then the right side, then the stores left to right. There is no record destructuring assignment, because a `{` at the start of a statement is a lambda; use `var`.

### `return`, `break`, `continue`

These have type `never`, so they can appear anywhere an expression is expected. `return` takes the whole expression to its right, so `x ?? return y + 1` returns `y + 1`; parenthesize it to end earlier. `panic` is an ordinary function of type `never` (section 8).

```ant
var user = Map.get(users, id) ?? return Result.err(Error{ message: "no such user" })
```

## 6. Functions

`func` declares a named function at the top level of a module; inside a block, bind a function with `var`. Parameters are annotated; the return type is inferred unless the function is exported or recursive (section 4, Inference). The body is a block, so the last expression is the result and `return` is only needed to leave early.

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

Named arguments apply only to a direct call of a declared function, by its name or through a namespace. A call through a function value is positional, because the value may be a lambda whose only parameter is `x`, and the interpreter resolves names against the callee's own parameter list. There are no variadic parameters; pass an array.

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

Three constructs handle nullable values, and together they replace the combinators other languages attach to an option type:

```ant
var user = find(users, 7)

var city = user?.address?.city          // string | null: null if any link is null
var label = user?.name ?? "anonymous"   // string: right side when left is null

if user != null {
  print(user.name)                      // user: User here
}
```

`?.` applies to field access, indexing, and calls, spelled `a?.b`, `a?.[i]`, and `f?.(x)`; each yields `null` when the left side is null. `??` takes any expression on the right, including `return` and `panic`, so `value ?? panic("unreachable")` unwraps and `value ?? return null` propagates. Both operators require a left side whose type includes `null`; on any other type they are dead code, and a compile error.

The checker narrows after a `null` test, as in the last example, but only for a local variable or a parameter. A condition narrows after `x is T`, `x == null`, or `x != null`, through `&&`, `||`, and `!`, and the `else` branch gets the complement: the union minus the tested member. When an `if` has no `else` and its branch has type `never`, because it ends in `return`, `break`, `continue`, or `panic`, the complement applies to the rest of the block, so `if user == null { return }` leaves `user` a `User` below it. `x ?? return ...` and `x ?? panic(...)` narrow the same way. After a `while` whose body contains no `break`, the complement of its condition holds, whatever the body assigned, because the condition was evaluated last. An assignment narrows the variable to the type of the assigned expression, and where branches meet, the variable has the union of the branch types, so `if c == null { c = load() }` leaves `c` a `Config`. Otherwise a narrowing lasts until the next assignment to the variable; inside a loop, an assignment anywhere in the body cancels it from the loop head on.

A field path such as `user.address` never narrows, because any call between the test and the use may reassign it: bind it to a local first, or use `?.` or `??`. Narrowing is limited to locals because a local can go stale in only one way, by reassignment: a record's tag never changes and a reference never becomes `null` on its own. Another goroutine can reassign a local only through a closure that captures it, so one rule about closures makes narrowing sound under concurrency. A nested body is a lambda, an anonymous `func`, a `go` block, or a `defer` block, and the rule has two directions. A local assigned inside a nested body never narrows in the enclosing function, since the assignment may run at any moment. Inside a nested body, outer locals start at their declared type, since the body may run after a later reassignment, except that a local never assigned after its declaration keeps its narrowing there: nothing can change it, so the narrowing holds whenever and wherever the body runs.

```ant
var user = find(id)                          // User | null, never reassigned
if user != null {
  Mutex.withLock(lock, { print(user.name) })  // ok: user keeps its narrowing
}

var hit: User | null = null
go { hit = find(id) }                        // assigned in a go block
if hit != null { print(hit.name) }           // compile error: hit never narrows
```

```ant
if user.address != null { print(user.address.city) }   // compile error: a path does not narrow
var address = user.address
if address != null { print(address.city) }             // ok
```

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

var parsed = parseInt(input)
if parsed is Ok { print(`parsed ${parsed.value}`) }
else {
  var error = parsed.error                 // parsed: Err[ParseError] here
  if error is EmptyInput { print("nothing to parse") }
  else { print(`bad digit at ${error.at}`) }   // error: BadDigit here
}
```

Because unions are flat, error types compose without wrapping. A function that parses a file can return `Result[Config, ParseError | Error]` and `try` both kinds of call. The narrower `Result[Config, ParseError]` is not itself assignable to the wider type, since type arguments are invariant (section 4): `try` widens on the way out, and `Result.mapErr(r, { x })` widens explicitly where `try` does not apply.

### `try`

`try` unwraps a `Result` or a nullable value. On `Ok{ value }` or a non-null value it evaluates to the value. On an `Err` it returns a fresh `Err` carrying the same error from the enclosing function, typed by that function's return type; on `null` it returns `null`. The enclosing function must therefore return a `Result` whose error type accepts the error, or a type that includes `null`.

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

Section 12 lists every operation that panics. The common ones: integer overflow, integer division by zero, array index out of range, lossy numeric conversion, and `unwrap` on the wrong case.

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

There are no channels. Goroutines coordinate through shared memory guarded by the sync objects in the standard library: `Mutex`, `RwMutex`, `WaitGroup`, `Once`, `Cond`, and `Atomic[T]`. Each is a reference value created by its `new` function; section 11 lists their operations.

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

### Sharing results

A local assigned inside a `go` block never narrows (section 7), so a goroutine does not hand back a result by reassigning a local of its parent, even when a `WaitGroup` makes that safe; the checker cannot see happens-before and does not try. Share through containers instead: write into an array slot, a map entry, a record field, or an `Atomic`, and after the wait read the value into a fresh local and narrow that. A fresh local is a snapshot, so the same idiom reads shared state under a mutex.

```ant
var results: Array[Response | null] = Array.filled(n, null)
go { results[i] = Http.get(url) }            // an index write, not a reassignment
WaitGroup.wait(wg)
var r = results[i]                           // a snapshot
if r != null { print(r.status) }

var latest: Atomic[Response | null] = Atomic.new(null)
go { Atomic.store(latest, Http.get(url)) }
WaitGroup.wait(wg)
var v = Atomic.load(latest)
if v != null { print(v.status) }

var config = Once.value({ load() })          // lazy initialization without a nullable variable
print(config().name)
```

### Panics in goroutines

A panic ends the goroutine it occurs in, after running that goroutine's deferred blocks. The runtime reports the message and stack trace on standard error. Nothing else happens: no other goroutine is interrupted, and the program continues. Code that waits on a goroutine must therefore account for it never finishing its work; the `defer { WaitGroup.done(wg) }` above is the usual pattern.

## 10. Modules

Each file is a module: a sequence of `import` declarations followed by `var`, `func`, and `type` declarations. Nothing else appears at the top level. A declaration prefixed with `export` is visible to other modules; everything else is private.

```ant
// geometry.ant
export type Point = { x: float64, y: float64 }

export func distance(a: Point, b: Point): float64 {
  Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y))
}
```

A module is a record. Its top-level scope is a record whose fields are its declarations, and `export` marks the fields other modules may see. `import` destructures that record: a record destructuring brings chosen exports into scope, with the usual `name: alias` renaming, and a bare name binds the whole record as a namespace. The standard-library namespaces are prelude variables bound to records of the same kind, so `Geometry.distance` and `Array.map` are both a field read followed by a call, and `Geometry.Point{ x: 1.0 }` is a field read that yields a tag. The interpreter has no notion of a namespace beyond this; the checker keeps each module's export table so that `Geometry.Point` also resolves in a type.

```ant
import "./geometry.ant" { distance, Point }
import "./geometry.ant" { distance: dist, Point }
import "./geometry.ant" Geometry

var d = Geometry.distance(p, q)
```

The path is a file path relative to the importing file, extension included. A module is identified by its canonical path, so two spellings of one file are one module. The path comes first so that an editor knows the module before the names are typed. Types and values import alike: a `type` export is its tag, so a record built in one module passes an `is` test written against the imported name in another, under whatever local name it was given.

Imports are live and read-only. `export var` is allowed; an imported name reads the exporting module's current value each time, and assigning to an imported name or to a field of a namespace from outside the module is a compile error. Two imports binding the same local name are a compile error, and a top-level declaration cannot shadow an imported name, so every name in a file has one visible origin. The prelude names, `print`, `panic`, the type and conversion names such as `int` and `Result`, and the namespaces, count as imports in every module. There is no re-export. Import cycles are a compile error.

Imports are resolved depth first in source order, and each module is initialized once, after everything it imports. Within a module, `func` and `type` declarations are hoisted, so functions may refer to each other in any order. Top-level `var` initializers run in source order. An initializer that refers directly to a later `var` is a compile error; reaching one through a function call before it is initialized is a runtime panic, since the checker does not trace calls.

Execution starts at `func main()` in the module given to `ant run`, which must declare it. `main` takes no parameters and returns `void`; command-line arguments come from `Os.args()`. The exit status is `0` when `main` returns, `1` when the main goroutine panics, and `2` when the program could not be loaded because of a syntax error or a missing module or `main`.

## 11. Standard library

The standard library is a set of namespaces in the prelude. Each is a plain record of functions, exactly like an imported module (section 10); none has methods or state. Every function takes its subject as the first argument so it composes with `|`. This section is the complete core library. The I/O namespaces `File`, `Http`, `Time`, `Os`, and `Json` are policy rather than language and live in `stdlib.md`.

Signatures are written in Ant's own notation with bounds (section 4, Generics). A function marked `mutates` changes its first argument and returns `void` or the removed element; every other function leaves its arguments untouched and returns a new value. A function marked ◆ has a value-dependent panic, named in its comment; every function also panics when an argument has a kind it does not take (section 12).

### Prelude

Besides the namespaces below, the prelude declares these names in every module:

```
type Ok[T] = { value: T }
type Err[E] = { error: E }
type Result[T, E] = Ok[T] | Err[E]
type Error = { message: string }                 // the library's error type
type Entry[K, V] = { key: K, value: V }          // yielded by maps
type Indexed[T] = { index: int, value: T }       // yielded by Array.entries
type Seq[T] = func(func(T): bool): void          // a sequence: pushes elements to yield until it returns false
type Integer = int8 | int16 | int32 | int64 | uint8 | uint16 | uint32 | uint64
type Number = Integer | float32 | float64
type Ordered = Number | string

print[T](value: T): void                         // String.from(value) and a newline to standard output
panic(message: string): never
int8[T: Number](x: T): int8                      // ◆ out of range, NaN, or infinite; likewise the other nine
```

### Array

`Array[T]` is dense and growable. `xs[i]` reads and `xs[i] = v` writes, and both panic when `i` is out of range; `Array.get` returns `null` instead. Indices are `int`s from `0` up to but excluding the length, and ranges are half-open: `from` inclusive, `to` exclusive.

```
Array.length[T](xs: Array[T]): int
Array.isEmpty[T](xs: Array[T]): bool
Array.get[T](xs: Array[T], i: int): T | null
Array.push[T](xs: Array[T], v: T): void                        // mutates
Array.pop[T](xs: Array[T]): T | null                           // mutates; null when empty
Array.slice[T](xs: Array[T], from: int, to: int): Array[T]     // ◆ from > to, or either out of 0 ..= length
Array.concat[T](xs: Array[T], ys: Array[T]): Array[T]
Array.map[T, U](xs: Array[T], f: func(T): U): Array[U]
Array.filter[T](xs: Array[T], f: func(T): bool): Array[T]
Array.reduce[T, A](xs: Array[T], init: A, f: func(A, T): A): A
Array.find[T](xs: Array[T], f: func(T): bool): T | null
Array.some[T](xs: Array[T], f: func(T): bool): bool
Array.every[T](xs: Array[T], f: func(T): bool): bool
Array.contains[T](xs: Array[T], v: T): bool                    // by ==
Array.indexOf[T](xs: Array[T], v: T): int | null               // first index, by ==
Array.sort[T: Ordered](xs: Array[T]): Array[T]                 // ascending, stable
Array.sortBy[T, K: Ordered](xs: Array[T], key: func(T): K): Array[T]
Array.sortWith[T](xs: Array[T], cmp: func(T, T): int): Array[T]   // cmp < 0 puts a before b
Array.reverse[T](xs: Array[T]): Array[T]
Array.entries[T](xs: Array[T]): Array[Indexed[T]]
Array.range(from: int, to: int): Array[int]                    // empty when to <= from
Array.filled[T](n: int, v: T): Array[T]                        // ◆ n < 0; the same v in every slot
Array.flatten[T](xs: Array[Array[T]]): Array[T]
Array.sum[T: Number](xs: Array[T]): T | null                   // ◆ overflow; null when empty
Array.same[T](xs: Array[T], ys: Array[T]): bool                // identity
```

`Array.sum` returns `null` on an empty array rather than zero because the interpreter never knows `T` and so cannot produce the zero of the right kind (section 4, erasure). Write `Array.sum(xs) ?? 0.0`.

### Map

`Map[K, V]` is an unordered hash map keyed by `==`. `m[k]` reads `V | null`; `m[k] = v` inserts or replaces. When `V` itself includes `null`, `Map.has` is the only way to tell a missing key from a stored `null`. Functions that take a predicate or a mapper receive each `Entry[K, V]`.

```
Map.size[K, V](m: Map[K, V]): int
Map.isEmpty[K, V](m: Map[K, V]): bool
Map.has[K, V](m: Map[K, V], k: K): bool
Map.get[K, V](m: Map[K, V], k: K): V | null
Map.set[K, V](m: Map[K, V], k: K, v: V): void                  // mutates; same as m[k] = v
Map.remove[K, V](m: Map[K, V], k: K): V | null                 // mutates; the removed value
Map.keys[K, V](m: Map[K, V]): Array[K]                         // unspecified order
Map.values[K, V](m: Map[K, V]): Array[V]
Map.entries[K, V](m: Map[K, V]): Array[Entry[K, V]]
Map.fromEntries[K, V](entries: Array[Entry[K, V]]): Map[K, V]  // later entries win
Map.map[K, V, W](m: Map[K, V], f: func(Entry[K, V]): W): Map[K, W]
Map.filter[K, V](m: Map[K, V], f: func(Entry[K, V]): bool): Map[K, V]
Map.merge[K, V](m: Map[K, V], n: Map[K, V]): Map[K, V]         // entries of n win
Map.same[K, V](m: Map[K, V], n: Map[K, V]): bool               // identity
```

### String

A `string` is immutable and stored as UTF-8. There is no `s[i]`: indexing by code point is linear, so a loop over indices would be quadratic, and indexing by byte would be a trap. Lengths, indices, and slices count code points, `for` iterates them (section 5), and `String.toBytes` gives the bytes.

```
String.length(s: string): int
String.isEmpty(s: string): bool
String.slice(s: string, from: int, to: int): string            // ◆ as Array.slice
String.concat(parts: Array[string]): string
String.split(s: string, sep: string): Array[string]            // ◆ sep is empty
String.join(parts: Array[string], sep: string): string
String.repeat(s: string, n: int): string                       // ◆ n < 0
String.trim(s: string): string                                 // Unicode white space at both ends
String.contains(s: string, t: string): bool
String.startsWith(s: string, t: string): bool
String.endsWith(s: string, t: string): bool
String.indexOf(s: string, t: string): int | null               // first code point index
String.replace(s: string, old: string, new: string): string    // every occurrence; ◆ old is empty
String.toUpper(s: string): string
String.toLower(s: string): string
String.chars(s: string): Array[string]                         // one code point each
String.toBytes(s: string): Array[byte]                         // UTF-8
String.fromBytes(bytes: Array[byte]): string | null            // null on invalid UTF-8
String.toInt(s: string): int | null                            // decimal, optional sign; null otherwise
String.toFloat(s: string): float64 | null
String.from[T](value: T): string
```

`String.from` renders any value, and `print` and template strings use it, so this is the format a program's output has. Integers render in decimal. Floats render as the shortest decimal that reads back to the same value, with `.0` added when integral, and as `NaN`, `Infinity`, or `-Infinity`. A string renders as itself at the top level and quoted with escapes inside a container. `bool`, `null`, and `void` render as their literals. Arrays render as `[1, 2]`, maps as `Map{ "a": 1 }` with keys always quoted when they are strings, and records as `Point{ x: 1.0, y: 2.0 }` with the name of their tag, each with entries in iteration order and separated by `, `. Functions render as `func`, tags as their name, and sync objects as their namespace name. A value already being rendered renders as `...`, so cyclic structures terminate. It is the only function the language calls implicitly, and only inside template strings.

### Iter

Lazy sequences (section 5, Loops). Every function here returns a new `Seq` without running the source; `Iter.toArray` and `for` run it. A sequence may be run more than once if its source allows.

```
Iter.range(from: int, to: int): Seq[int]                       // from inclusive, to exclusive
Iter.fromArray[T](xs: Array[T]): Seq[T]
Iter.map[T, U](s: Seq[T], f: func(T): U): Seq[U]
Iter.filter[T](s: Seq[T], f: func(T): bool): Seq[T]
Iter.take[T](s: Seq[T], n: int): Seq[T]                        // ◆ n < 0
Iter.toArray[T](s: Seq[T]): Array[T]
```

### Math and Bits

```
Math.abs[T: Number](x: T): T                                   // ◆ the most negative integer
Math.min[T: Ordered](a: T, b: T): T
Math.max[T: Ordered](a: T, b: T): T
Math.pow(x: float64, y: float64): float64
Math.sqrt(x: float64): float64
Math.floor(x: float64): float64
Math.ceil(x: float64): float64
Math.round(x: float64): float64                                // half away from zero
Math.PI: float64
Math.E: float64
Math.minInt: int                                               // -2^63; not writable as a literal
Math.maxInt: int

Bits.and[T: Integer](a: T, b: T): T
Bits.or[T: Integer](a: T, b: T): T
Bits.xor[T: Integer](a: T, b: T): T
Bits.not[T: Integer](a: T): T
Bits.shiftLeft[T: Integer](a: T, n: int): T                    // ◆ n < 0 or n >= width
Bits.shiftRight[T: Integer](a: T, n: int): T                   // arithmetic for signed, logical for unsigned; ◆ as above
Bits.popCount[T: Integer](a: T): int
Bits.wrapAdd[T: Integer](a: T, b: T): T                        // two's complement, never panics
Bits.wrapSub[T: Integer](a: T, b: T): T
Bits.wrapMul[T: Integer](a: T, b: T): T
```

### Result and Record

```
Result.ok[T, E](value: T): Result[T, E]
Result.err[T, E](error: E): Result[T, E]
Result.isOk[T, E](r: Result[T, E]): bool
Result.map[T, U, E](r: Result[T, E], f: func(T): U): Result[U, E]
Result.mapErr[T, E, F](r: Result[T, E], f: func(E): F): Result[T, F]
Result.unwrap[T, E](r: Result[T, E]): T                        // ◆ r is an Err
Result.unwrapOr[T, E](r: Result[T, E], fallback: T): T

Record.same[T: {}](a: T, b: T): bool                           // identity; {} bounds T to any record
```

### Synchronization

The sync objects of section 9. Each is created by its `new` function and compared by identity. The `with` forms acquire, run the function, and release even if it panics.

```
Mutex.new(): Mutex
Mutex.lock(m: Mutex): void                                     // blocks
Mutex.unlock(m: Mutex): void                                   // ◆ not locked
Mutex.withLock[T](m: Mutex, f: func(): T): T

RwMutex.new(): RwMutex
RwMutex.readLock(m: RwMutex): void
RwMutex.readUnlock(m: RwMutex): void                           // ◆ not read-locked
RwMutex.writeLock(m: RwMutex): void
RwMutex.writeUnlock(m: RwMutex): void                          // ◆ not write-locked
RwMutex.withRead[T](m: RwMutex, f: func(): T): T
RwMutex.withWrite[T](m: RwMutex, f: func(): T): T

WaitGroup.new(): WaitGroup
WaitGroup.add(wg: WaitGroup, n: int): void                     // ◆ counter would go negative
WaitGroup.done(wg: WaitGroup): void                            // ◆ counter already zero
WaitGroup.wait(wg: WaitGroup): void                            // blocks until the counter is zero

Once.new(): Once
Once.do(once: Once, f: func(): void): void                     // runs f the first time only; later calls wait for it
Once.value[T](f: func(): T): func(): T                         // the returned function runs f once and caches the value

Cond.new(m: Mutex): Cond
Cond.wait(c: Cond): void                                       // ◆ m not locked; releases m, waits, reacquires
Cond.signal(c: Cond): void
Cond.broadcast(c: Cond): void

Atomic.new[T](v: T): Atomic[T]
Atomic.load[T](a: Atomic[T]): T
Atomic.store[T](a: Atomic[T], v: T): void
Atomic.add[T: Number](a: Atomic[T], d: T): T                   // ◆ overflow; returns the new value
Atomic.compareAndSwap[T](a: Atomic[T], expected: T, v: T): bool   // compares with ==
```

## 12. Dynamic semantics

This section is the contract of `ant run`. It defines what every construct does to values, and it is the only part of the language the interpreter implements; every rule that mentions a type belongs to the checker. Where the checker would have rejected a program, the rules below say "panic", and the table at the end collects every such case. A program that passes the checker reaches only the value-dependent rows of that table, and a data race (section 9).

### Values

Every value has a kind, fixed when the value is created:

| Kind | Values |
|---|---|
| the ten numeric kinds | `int8` … `uint64`, `float32`, `float64`; a number carries its width, because overflow and conversion depend on it |
| `bool`, `string`, `null`, `void` | as in section 4 |
| array | a growable sequence of values |
| map | a hash table from values to values, keyed by `==`; a key's hash depends on a bounded prefix of its structure, so hashing terminates on cyclic values and agrees with `==` |
| record | a tag plus a fixed set of named fields |
| func | a declared function, an anonymous function, or a lambda, with the scopes it captured |
| tag | the value a `type` declaration binds (section 4) |
| sync | a `Mutex`, `RwMutex`, `WaitGroup`, `Once`, `Cond`, or `Atomic` |

Arrays, maps, records, functions, and sync objects are references: a variable holds a reference, and copying the variable copies the reference. Numbers, booleans, strings, `null`, `void`, and tags are immutable, so for them the distinction never shows.

### Names and scopes

A block opens a scope. `var` binds a name in the current scope from its declaration to the end of the block; a function body's scope starts with the parameters. Lookup walks outward through the enclosing scopes to the module scope and then to the prelude. A closure keeps a reference to the scopes it was created in, so it sees later assignments to the variables it captured. Each iteration of a `for` opens a fresh scope for the loop variable. Reading a top-level `var` whose initializer has not run yet panics (section 10). A module's scope is a record, and `export` is a checker rule: at run time every field of a module record is readable.

### Expressions

Operands evaluate left to right (section 5). Below, "must be" means the operation panics otherwise.

- **Literals.** An integer literal is an `int`, a float literal a `float64`. A template string evaluates each `${...}` in order and renders it with `String.from`.
- **Record literal `Head{ ... }`.** The head must evaluate to a tag. Entries evaluate in order; a spread copies every field of a value that must be a record; a later entry replaces an earlier one with the same name. The result is a new record with that tag and those fields.
- **Map literal `Map{ ... }`.** A key that is a single identifier is the string of its name, decided by the parser (section 4); other keys and all values evaluate in order; a later entry whose key is `==` to an earlier one replaces it. The result is a new map.
- **Array literal `[ ... ]`.** Elements evaluate in order; a spread appends every element of a value that must be an array. The result is a new array.
- **Variable.** The value bound to the name.
- **Field read `a.b`.** `a` must be a record with a field `b`; the value is that field. A namespace is a record, so this rule also covers `Array.map` and `Geometry.Point`.
- **Index read `a[i]`.** `a` must be an array or a map. For an array, `i` must be an `int` from `0` up to but excluding the length, and the value is that element. For a map, the value is the entry whose key is `==` to `i`, or `null` when there is none.
- **`a?.b`, `a?.[i]`, `f?.(x)`.** If the left operand is `null`, the result is `null` and the rest of the postfix chain is skipped. Otherwise the plain rule applies.
- **Call `f(args)`.** `f` evaluates first and must be a function. Arguments evaluate in order. Positional arguments fill parameters left to right; a named argument fills the parameter of that name, which must exist and must not be filled already; every parameter still unfilled must have a default, and the defaults evaluate in the callee's scope, in parameter order, after the arguments. A lambda has the single parameter `x` and accepts zero or one positional argument. The body then runs in a new scope, and the call's value is the body's value, or the operand of the `return` that ended it.
- **Conversion `int8(x)` … `float64(x)`.** The ten numeric names are prelude functions. The argument must be a number. An integer target panics when the value, truncated toward zero if it is a float, lies outside the target's range, and on `NaN` or an infinity. A float target rounds to the nearest representable value.
- **Arithmetic `+ - * / %`.** Both operands must be numbers of the same kind, except that `+` also takes two strings and concatenates them. An integer result that does not fit the kind panics, which includes unsigned subtraction below zero. Integer `/` truncates toward zero, `%` takes the sign of the dividend, and both panic on a zero divisor. Float arithmetic follows IEEE 754 and never panics. Unary `-` needs a number; `!` needs a `bool`.
- **Comparison `< <= > >=`.** Both operands must be numbers of the same kind, or two strings, which compare by code point.
- **Equality `== !=`.** Never panics. Two values are equal when they have the same kind and: numbers are equal by value, with IEEE 754 rules for floats; strings have the same code points; `bool`, `null`, and `void` values are equal by value; records have the same tag and `==` fields; arrays have the same length and `==` elements in order; maps have the same key set and `==` values per key; functions, tags, and sync objects are the same object. A pair of values already under comparison counts as equal (section 4). Values of different kinds are unequal, so `x == null` is simply `false` for a non-null `x`.
- **`a is T`.** `T` is resolved by name. `null`, `void`, `bool`, `string`, `func`, `Array`, `Map`, and the ten numeric names test the kind of `a`. Any other path evaluates and must be a tag, and the test is whether `a` is a record with that tag. The result is a `bool`.
- **Logical `&& ||`.** The left operand must be a `bool`. `&&` yields the right operand when the left is `true` and `false` otherwise, without evaluating the right; `||` mirrors that. The right operand must be a `bool` when it is evaluated.
- **`a ?? b`.** Yields `a`, unless it is `null`, in which case `b` is evaluated and yielded.
- **Pipe `a | f(b)`.** Is `f(a, b)`: `a` evaluates, then `f`, then `b`.
- **Assignment.** The target's sub-expressions evaluate first, then the right side. A variable target rebinds the name in the scope that declared it. A field target must be a record that already has that field. An index target on an array must be an `int` in range; on a map it inserts or replaces. An array destructuring target requires an array with at least as many elements as its positions, and stores element by element left to right, with a rest position receiving a new array of the remainder. Compound assignment reads the target, applies the operator, and stores. The value is `void`.
- **Destructuring in `var` and `for`.** A record destructuring requires a record with every named field. An array destructuring requires an array with at least as many elements as its fixed positions; extra elements are ignored, and a rest binder receives a new array of the remainder. Nested destructurings apply the same rules to the element they receive. `_` binds nothing, and reading `_` panics.
- **Block.** Opens a scope and evaluates its statements in order. Its value is that of the last expression, or `void` when the block is empty or ends in a declaration or an assignment. Deferred blocks registered in it run when it exits (below).
- **`if`.** The condition must be a `bool`. The value is the chosen branch's value; with no `else` and a `false` condition it is `void`.
- **`while`.** Evaluates the condition, which must be a `bool`, before each iteration. The value is `void`.
- **`for x in e`.** `e` must be an array, a map, a string, or a function. Over an array it iterates by index from zero while the index is below the current length, so elements appended during the loop are visited and removed ones are not. Over a map it visits each entry once as an `Entry` record in unspecified order; inserting or removing during the loop is a program error of the data-race kind, and entries may be skipped or seen twice. Over a string it yields each code point as a one-character string. Over a function it calls the function with a fresh `yield` function; each call of `yield` with one argument binds `x`, runs the body, and returns `true`, or `false` when the body ended with `break`. Calling `yield` again after it returned `false`, or after the sequence function has returned, panics; a `return` or a panic in the body propagates through the sequence function like any other call. A destructuring on the left reads the named fields of each element, which must be a record with those fields. The value is `void`.
- **`break`, `continue`.** Leave or restart the innermost enclosing loop, running the deferred blocks of every block they exit.
- **`return e`.** Evaluates `e`, or `void`, and leaves the innermost enclosing function body or lambda, running the deferred blocks of every block it exits.
- **`try e`.** If the value is `null`, returns `null` from the enclosing function. If it is a record tagged `Err`, returns a new `Err` record with the same `error` field. If it is a record tagged `Ok`, yields its `value` field. Any other value is yielded unchanged.
- **Lambda and anonymous `func`.** Create a function value that captures the current scopes.
- **`defer { ... }`.** Registers the block with the innermost enclosing block. The value is `void`.
- **`go { ... }`.** Starts a new goroutine that evaluates the block, and yields `void` at once.
- **`panic(message)`.** Begins a panic in the current goroutine (below).

### Deferred blocks and panics

When a block exits, by reaching its end, by `return`, `break`, or `continue`, or by a panic, its deferred blocks run in reverse order of registration, each in the scope it was registered in. A `return` inside a deferred block returns from the deferred block only.

A panic unwinds the current goroutine: every block being evaluated exits in turn, running its deferred blocks, until the goroutine's root block has exited. A panic inside a deferred block replaces the one in progress. When unwinding finishes, the runtime writes the message and a stack trace to standard error. In the main goroutine the program then exits with a non-zero status; in any other goroutine, that goroutine ends and nothing else happens. Panics cannot be caught.

### Goroutines

Goroutines are preemptive: a goroutine that never blocks cannot keep others from running. They share memory, and the sync objects of section 9 are the only synchronization. The runtime guarantees that a data race cannot corrupt memory or crash the interpreter; the values a racing program observes are otherwise unspecified. The program ends when `main` returns, whatever other goroutines are doing.

### Runtime panics

The complete list. The checker rules out every kind and arity row. The value-dependent rows, marked ◆, can occur in a checked program.

| Operation | Panics when |
|---|---|
| `+ - * / %`, `< <= > >=`, unary `-` | an operand is not a number, or the operands differ in kind; `+` and the comparisons also take two strings |
| `!`, `&&`, `\|\|`, `if`, `while` | an operand or condition is not a `bool` |
| ◆ integer `+ - *`, compound assignment, `Array.sum` | the result does not fit the kind |
| ◆ integer `/`, `%` | the divisor is zero |
| ◆ `Bits.shiftLeft`, `Bits.shiftRight` | the count is negative or not below the operand's width |
| ◆ numeric conversion | the value is outside the target's range, or is `NaN` or infinite with an integer target |
| `a.b`, `a.b = v` | `a` is not a record, or has no field `b` |
| `a[i]`, `a[i] = v` | `a` is neither an array nor a map; ◆ `a` is an array and `i` is not an `int` from `0` up to but excluding the length |
| call | the callee is not a function; too many positional arguments; a named argument for an unknown or already filled parameter, or to a lambda; a required parameter left unfilled |
| record literal | the head is not a tag; a spread operand is not a record |
| array literal | a spread operand is not an array |
| `is` | the right side is a path that does not evaluate to a tag |
| `for` | the operand is not an array, a map, a string, or a function; ◆ a sequence calls `yield` after it returned `false` or after the sequence returned |
| destructuring | a record destructuring meets a value that is not a record with every named field; an array destructuring meets a value that is not an array; ◆ the array has fewer elements than the fixed positions |
| `_` | ◆ read |
| library function | an argument has a kind the function does not take; ◆ the documented case, such as `Result.unwrap` on an `Err` or `Array.pop` on an empty array |
| ◆ top-level `var` | read before its initializer has run |
| ◆ `panic` | always |
| ◆ any call | the goroutine's call depth exceeds the runtime's limit |
| `??`, `?.`, `try`, `==`, `!=` | never |

## 13. Example

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

  var status = source.status
  if status is Suspended {
    return Result.err(AccountSuspended{ id: from, reason: status.reason })
  }
  if source.balance < amount {
    return Result.err(Insufficient{ needed: amount - source.balance })
  }

  source.balance -= amount
  target.balance += amount
  Result.ok(void)
}

func report(accounts: Map[int, Account]): string {
  Map.values(accounts)
    | Array.filter({ x.status is Active })
    | Array.sortBy({ x.balance })
    | Array.map({ `${x.owner}: ${x.balance}` })
    | String.join("\n")
}

func main() {
  var accounts: Map[int, Account] = Map{}
  accounts[1] = Account{ id: 1, owner: "ada", balance: 100.0, status: Active{} }
  accounts[2] = Account{ id: 2, owner: "linus", balance: 20.0, status: Suspended{ reason: "audit" } }

  var result = transfer(accounts, 1, 2, 50.0)
  if result is Ok { print("ok") }
  else {
    var error = result.error
    if error is NotFound { print(`unknown account ${error.id}`) }
    else if error is Insufficient { print(`short by ${error.needed}`) }
    else { print(`account ${error.id} is suspended: ${error.reason}`) }
  }

  print(report(accounts))
}
```

## 14. Open decisions

Each item below is a choice this draft made for the sake of having examples, not a settled design. The current choice is stated first.

1. **`go` returns nothing.** Results come back through shared memory and a `WaitGroup`. A handle with `join` would be more convenient but is a channel in disguise, and panics would need a representation on it.
2. **Data races are undefined in outcome but memory safe.** The runtime cost of that guarantee is unexamined.
3. **Packages.** Imports name files only. How packages are named, resolved, and versioned, and whether re-export is needed, are open.
4. **`try` as the propagation keyword.** Postfix `?` collides with `?.`. `try` reads well but means something else in JavaScript.
5. **Unions must be distinguishable at run time,** which limits them to one array, one map, one function, and one anonymous record member. Named records are free because they carry tags.
6. **Nothing is immutable** except strings. A `readonly` field modifier or frozen records may be needed for safe sharing between goroutines.
7. **Deferred syntax.** Raw strings, character literals, string literal types, pattern matching, labeled loops, record destructuring assignment, and destructuring in parameters are left out until a need appears.
