# Ant Language Specification

Draft 0.1 · October 2026

Ant is a general-purpose, garbage-collected language with JavaScript-like syntax, static types,
expression-oriented control flow, and goroutine-style concurrency. This document describes the
language as a programmer sees it, not the compiler or the runtime.

## 1. Principles

- **One obvious way.** When two constructs would do the same job, the language keeps one.
- **No implicit coercion.** A value never changes type without a visible conversion.
- **Everything is an expression.** Blocks, `if`, and loops produce values.
- **Errors are values.** `Result` carries expected failures and `null` carries absence. `panic` is
  for bugs.
- **Types are advisory.** `ant check` reads annotations and `ant run` discards them. The interpreter
  keeps only a type's name, as a tag, and a record's field names in order (section 4). No evaluation
  rule consults a written type.
- **Minimal syntax.** The grammar needs one token of lookahead and no feedback from the type
  checker.

## 2. Lexical structure

Source files are UTF-8 text with the extension `.ant`. A byte that begins no UTF-8 character is a
syntax error at that byte, so a string literal holds only scalar values (section 11, String).

### Comments

```ant
// line comment
/* block comment */
```

Block comments do not nest.

A doc comment is a run of line comments, each alone on its line, on consecutive lines, followed by
a line break and then directly by a top-level `var`, `func`, or `type` declaration, or by the
`export` that starts one, with nothing between but white space. It documents that declaration. A
blank line, a block comment, a module doc line, or a comment that follows code on its line ends the
run, so a comment separated from a declaration by a blank line documents nothing, and neither does
a trailing comment on the line before it; in `var a = 1; var b = 2`, a doc comment above the line
documents only `a`. The doc is the run's text with each line's `//`, the one space after it when
present, and its trailing white space removed.

A line comment that starts with `//!` is a module doc line, and the module doc lines of a file
document the module (section 10). They come before its first `import` or declaration, each alone on
its line, on consecutive lines: other comments may come before and after them, such as a license,
but not between. A `//!` comment anywhere else is a syntax error, after code or apart from the
other module doc lines, so a module has one doc and it is where a reader looks first. The doc is the lines' text with each line's `//!`, the one space after it when present,
and its trailing white space removed.

Doc comments and module docs mean nothing to `ant check` or `ant run`; editors and `ant doc` read
them, and `doc.md` gives their conventions.

```ant
// Copyright 2026 The Ant Authors. MIT license.

//! Geometry computes distances and areas on the plane.

// Point is a position on the plane.
export type Point = { x: float64, y: float64 }

// Distances

// distance returns the straight-line distance from a to b.
export func distance(a: Point, b: Point): float64 { ... }
```

The license comment is followed by a blank line and is not a `//!` line, so it documents nothing;
`// Distances` is followed by a blank line, so it labels a section and documents nothing either.

### Identifiers and keywords

An identifier starts with an ASCII letter or `_` and continues with ASCII letters, digits, or `_`.
Identifiers are case-sensitive, so `value` and `Value` are two names, but case means nothing else:
unlike in Go, it does not decide what a module exports. `_` on its own is a write-only identifier: it can be bound or assigned
wherever a name can, which discards the value. Reading it is a compile error in `ant check` and a
panic in `ant run`.

Keywords:

```
break continue defer else export false for func go if import
in is null return select true try type var void while
```

Reserved words, so that they stay available and JavaScript habits produce an error rather than an
identifier:

```
as async await catch class const enum finally function interface
let match switch this throw undefined
```

Neither list can name a variable, function, type, or parameter. A field can have any name: after `.`
or `?.`, and before `:` in a record type, a record or map literal, or a record destructuring, a
keyword or reserved word is a plain name. So `event.type`, `{ type: string }`, and
`Map{ class: "a" }` are fine, and the key of `Map{ null: 1 }` is the string `"null"`, as in
JavaScript. The shorthands `Map{ type }` and `var { type } = event` would read or bind a variable
named `type`, which cannot exist, so they are errors; write `var { type: kind } = event`.

`Array`, `Map`, `Set`, `Result`, `never`, `println`, `panic`, and the other standard library names
are ordinary identifiers bound by the prelude, not keywords.

### Literals

```
42          1_000_000     0xFF        0b1010    // integers
3.14        1e9           2.5e-3                // floats
"hello"     "line\nbreak" "\u{1F600}"           // strings
`total: ${count} items`                         // template strings
/^\d{4}-\d{2}$/   /\bant\b/i                    // regular expressions
true        false         null
```

An integer literal is decimal, `0x` hexadecimal, or `0b` binary, with `_` allowed between digits. A
float literal has digits on both sides of the point, an exponent, or both; `.5`, `1.`, and `1.x` are
errors, since a digit followed by a point always begins a float. The prefixes and the `e` of an
exponent are lowercase, so `0XFF`, `0B1`, and `1E9` are errors; hexadecimal digits may be either
case. A decimal integer, or the digits before a float's point, start with `0` only when they are
`0`: `0`, `0.5`, and `0e3` are fine, while `007` and `00.5` are errors, since other languages read
`007` as octal. There are no literal suffixes: an
integer literal is always an `int` and a float literal is always a `float64`. `1` is never a float;
write `1.0`. Other numeric types are reached through a conversion, as in `byte(255)` or
`float32(1.5)`. An integer literal that does not fit an `int` is a syntax error, so the most
negative `int` is written `Math.minInt`. So is a float literal out of the range of `float64`: one so
large that it would round to infinity, such as `1e400`, or one whose digits are not all zero but
that would round to `0.0`, such as `1e-400`.

The escapes are `\n`, `\t`, `\r`, `\\`, `\"`, `` \` ``, `\$`, and `\u{...}`, whose hexadecimal value
must be a Unicode scalar value: at most `10FFFF` and not a surrogate. A plain string stays on one
line; a template string may span lines. A template string interpolates any expression: each `${...}`
is rendered with `String.from`, which is defined for every type (section 11). Braces nest inside
`${...}`, so a lambda or a record literal can appear there. There are no raw strings and no
character literals.

A regular expression literal is a pattern between slashes with optional flags after the closing
slash, as in JavaScript. The pattern is RE2 syntax, which section 11 (Regex) describes, and it is
checked when the source is parsed, so `/(/` is a syntax error in `ant check` and `ant run` alike. A
backslash inside the literal belongs to the pattern, so `\d` is a digit class and needs no doubling;
`\/` is a `/` and does not end the literal, nor does a `/` inside a character class `[...]`. The
literal stays on one line. `//` and `/*` begin comments, so an empty pattern and a pattern that
starts with `*` cannot be written as literals; an empty pattern is `Regex.compile("")`. The flags
are `i`, `m`, and `s`, each at most once, in any order: `i` ignores case, `m` makes `^` and `$`
match at line ends, and `s` lets `.` match a line break. JavaScript's other flags are syntax errors
whose message names the Ant way: `g` is `Regex.findAll` or `Regex.replace`, `y` is a `^` anchor on
a `String.slice`, and `u`, `v`, and `d` are how Ant already behaves. The literal evaluates to a
`Regex.Pattern`.

`/` begins a regular expression unless the last token before it, skipping line breaks, is an
operand: an identifier, a literal of any kind, `true`, `false`, `null`, `void`, `)`, `]`, or `}`.
After an operand, `/` is division and `/=` is the compound assignment. `return`, `break`, and
`continue` can end a line (see Line endings) but are not operands, so `return /x/` returns a
pattern. When there is no previous token, at the start of a file or of a `${...}` interpolation,
`/` begins a pattern. The rule reads one token back, so the grammar keeps its one token of
lookahead, and no program written before the literal existed changes meaning: every `/` that begins
a pattern follows a token after which division was a syntax error.

```ant
var r = (total
  / count)                        // division: the last token before / is an identifier
var ok = Regex.test(/^ant$/i, s)  // a pattern: the last token is (
x /= 2                            // an assignment
```

RE2 has no lookahead, lookbehind, or backreferences, so a JavaScript pattern that uses `(?=`,
`(?!`, `(?<=`, `(?<!`, or `\1` is a syntax error whose message names the construct; `\1` through
`\9` are the backreferences, while `\10` and up are octal escapes, as RE2 reads them. JavaScript's
`\u0041` is a syntax error whose message names `\x{0041}`. `(?<name>...)` names a group as in
JavaScript. Inside `\Q...\E`, where RE2 takes every character as itself, `\/` is two characters,
while the normalization of section 11 takes it for `/`; write `/` there. A few patterns are valid in both and match differently: `\s` is `[\t\n\f\r ]`, without
`\v` or the Unicode spaces, and `.` excludes only `\n`, where JavaScript also excludes `\r`, U+2028,
and U+2029. `\d`, `\w`, and `\b` are ASCII in both.

### Line endings

A line break is a line feed `\n`, a carriage return and line feed `\r\n`, or a carriage return `\r`
alone, as in JavaScript. Each is one line break wherever this document speaks of a line or a
newline: it ends a line comment, a plain string or a regular expression literal cannot hold one, and
the text of a template string keeps it as written.

A newline or a semicolon ends an expression. A newline does not end one when:

- the line ends with a token that cannot end an expression, such as a binary operator, `,`, `(`,
  `[`, `{`, or `=`; or
- the next non-blank line starts with `.`, `?.`, `|`, or `else`.

Nothing else is inferred. A line that starts with `(` or `[` begins a new statement, so `a` followed
by `(b)` on the next line is two statements, not a call. A `return` at the end of a line returns
`void`, which the checker rejects in a function with another return type. A trailing comment changes
none of this.

Inside parentheses, square brackets, and braces that are not a block, newlines are ignored. Calls,
literals, record types, parameter lists, and import lists separate their items with commas and allow
a trailing comma. Only blocks separate their items with newlines.

The continuation rule for a leading `.`, `?.`, `|`, or `else` lets pipelines, union types, and
`else` chains read top to bottom. None of those tokens can start a statement, so the rule is
unambiguous:

```ant
var total = orders
  | Array.filter({ x.paid })
  | Array.map({ x.amount })
  | Array.sum()
```

## 3. Variables

`var` declares a mutable binding. Every declaration has an initializer, and the type is inferred
from it or written explicitly.

```ant
var count = 0
var name: string = "ant"
var scores: Array[int] = []
```

A name cannot be redeclared in the same scope, which is a syntax error; an inner scope may shadow an
outer one, except that no declaration in any scope may shadow a prelude name (section 10). A `var`
is visible from its declaration to the end of the enclosing block; its own initializer may refer to
it only inside a nested function body, which is how a local function calls itself (section 6).
Top-level `func`, `type`, and `var` declarations are visible throughout the module regardless of
order, but a top-level initializer may refer directly, outside a nested function body, only to the
`var`s above it (section 10).

Assignment is an expression of type `void`, so it cannot be chained or used as a condition:

```ant
count = count + 1
count += 1                // also -= *= /= %=
if count = 5 { ... }    // compile error: void is not bool
```

An assignment target is a variable, a field such as `p.x`, an element such as `xs[i]`, or an array
destructuring of targets such as `[a, b]` (section 5). There is no `++`, `--`, or `const`.

## 4. Types

Ant is statically typed, and most annotations are inferred. A named record type or a named primitive
type is nominal: each `type` declaration whose body is a record type or a primitive type is a
distinct type, identified by its tag. Every other type is structural: two types with the same shape
are the same type.

### Checking and running

Types are checked by one command and erased by the other.

`ant check file.ant` runs the checker over the file and every module it imports, including code
nothing calls, and exits non-zero with the errors. Inference, bounds, and narrowing live here, and
so does their cost. Every rule in this document that mentions a type is a checker rule, and a
compile error is an error the checker reports.

`ant run file.ant` does no static work beyond parsing. It loads the import graph, so a syntax error
anywhere stops the program before `main`, and then it runs with annotations parsed and discarded. An
unknown name panics when it is reached, not before, though an implementation may resolve names to
slots as it loads. Every runtime rule is defined on values, which carry their concrete type: every
value has a kind, such as `int`, `string`, array, or record, and a record or a tagged primitive also
carries a tag (section 12). A program can run without being checked. Where the checker would have
rejected it, the runtime panics at the point of the error: `+` on operands of different types, a
call on a value that is not a function, a field read on a value that is not a record. Section 12
lists every such check.

Editors and continuous integration run `check`; the terminal runs `run`. No flag makes `run` check
first.

A `type` declaration is the one thing the interpreter keeps of the type language. It binds the name
to a fresh tag, or, for a named primitive type, to a constructor function that carries one. A record
tag also keeps the names of its fields in declaration order; the rest of the body is discarded (see
Type declarations). Every `type` declaration binds a tag or a constructor, even an alias, but only
record literals, constructor calls, and `is` tests use tags, and the checker allows a literal head
only on a record type.

### Primitives

| Type                               | Values                                                                       |
| ---------------------------------- | ---------------------------------------------------------------------------- |
| `bool`                             | `true`, `false`                                                              |
| `int8` `int16` `int32` `int64`     | signed integers                                                              |
| `uint8` `uint16` `uint32` `uint64` | unsigned integers                                                            |
| `float32` `float64`                | IEEE 754 floats                                                              |
| `string`                           | immutable sequence of Unicode code points, stored as UTF-8                   |
| `null`                             | the single value `null`                                                      |
| `void`                             | the single value `void`, which carries no information                        |
| `never`                            | the type of expressions that do not return, such as `panic(...)` or `return` |

`int` is an alias for `int64` and `byte` for `uint8`. `int` is the default; the sized names are for
when the size matters. The prelude also declares `Integer`, the union of the eight integer types,
`Number`, which adds the two float types, and `Ordered`, which is `Number | string`. They exist to
bound type parameters (see Generics).

`void` is both a type and its only value, like `null`. A block that ends in a declaration or
assignment, a loop, and a function with nothing to return all produce `void`. Write it explicitly
when a value is required, as in `Result.ok(void)`.

`Bytes` is an immutable sequence of bytes, for binary data rather than text: an image, a digest, a
frame of a network protocol. It is built in, so `len`, `for`, indexing, and `is` take it, but it is
not a primitive, so no named primitive type is declared over it. Section 11 has its functions.

Numeric types never mix. Convert explicitly by calling the target type as a function. Each of the
ten numeric names is a prelude function that takes any numeric value, and it is a value in its own
right, so `Array.map([72, 105], byte)` builds an `Array[byte]`. A conversion to an integer kind must
be exact: a fraction, a value out of range, `NaN`, or an infinity panics, and truncation is spelled
`int(Math.trunc(x))`. A conversion to a float kind rounds to the nearest representable value and
never panics. Section 12 has the table. `string` and `bool` are callable too, but only to unwrap a
named primitive type (see Named primitive types) or as the identity on their own kind. Parsing is
`String.toInt` and `String.toFloat`; rendering is `String.from`.

```ant
var n = 7
var ratio = float64(n) / 2.0      // 3.5
var small = int8(n)               // ok
var bad = int8(300)               // panic: out of range
```

### Records

A record type lists named fields. A record literal names the type and lists the fields, as in Go.
Fields are mutable, and there is no `readonly` or frozen form: strings are the only immutable
values, and goroutines share records under the sync objects of section 9.

```ant
type Point = { x: float64, y: float64 }

var p = Point{ x: 1.0, y: 2.0 }
p.x = 3.0
```

Every record value has a name; there are no anonymous record literals. The head of a literal is an
identifier path, so a type reached through a namespace is written `Geometry.Point{ x: 1.0 }`. Type
arguments are never written there. A bare identifier is a shorthand entry: `Point{ x, y }` means
`Point{ x: x, y: y }`, the same shorthand destructuring uses. Map literals follow the same two rules
(see Arrays and maps).

The name is part of the value: a literal stores the tag of its head in the record. The interpreter
keeps the field names so that `ant run` can reject a literal with a missing or unknown field and
render fields in declaration order; it keeps no field type. A tag is compared only by identity, and
a tag reached through an import or an alias is the same tag. The checker identifies the type by the
same tag, so two declarations with the same fields are different types. `type B = A` is a compile
error when `A` is a record or named primitive type, since it would mint a second tag for one type.
Declare the fields, or the base type, again instead.

A record has no dynamic access: `p["x"]` is a compile error, and `for` does not iterate a record.
When the keys are data rather than part of the type, use a `Map`.

A named record type accepts only values that carry its tag. An anonymous record type, written in an
annotation as `{ name: string }`, accepts any record with at least those fields, whatever its tag.
This is structural width subtyping, and it is how a function takes "anything with a name". A record
literal must list exactly the fields of its named type, which catches typos.

```ant
type Named = { name: string }
type Person = { name: string, age: int }
func greet(n: { name: string }): string { `hi ${n.name}` }

var user = Person{ name: "ada", age: 36 }
greet(user)                                 // ok: user has a name field
var n: Named = user                         // compile error: a Person is not a Named
greet(Named{ name: "ada", age: 36 })        // compile error: Named has no field age
```

The spread `...` copies all fields of a record into a new literal; later fields win. The tag comes
from the head, so a spread also converts between record types with the same fields. The operand must
have a named record type: a value of anonymous record type may carry fields its type does not list,
and the spread would copy them too.

```ant
type Vec = { x: float64, y: float64 }

var moved = Point{ ...p, x: 0.0 }
var v = Vec{ ...p }                        // a Vec with the fields of p
```

Records, arrays, maps, and sets are reference values: assigning or passing one shares it, and a
change made through one name is visible through every other. `==` compares structure, never
identity. Two records are equal when they carry the same tag and their fields are equal. Arrays
compare by length and elements, maps by key set and values, sets by members, primitives, time values
(`stdlib.md`), and regular expression patterns (section 11) by value, and functions, sync objects,
and generators by identity. The comparison recurses with `==` over every run-time field, including
fields the static type does not mention, so it agrees with `String.from` and `Json.stringify`. A
pair of values already under comparison counts as equal, so cyclic structures compare in finite
time. Identity is a library call: `Record.same`, `Array.same`, `Map.same`, and `Set.same` report
whether two names refer to one value.

```ant
var p = Point{ x: 1.0, y: 2.0 }
var q = p
q.x = 5.0
p.x                               // 5.0: one record under two names
p == Point{ x: 5.0, y: 2.0 }      // true
Record.same(p, q)                 // true
Record.same(p, Point{ ...p })     // false
```

### Named primitive types

A `type` declaration whose body is one of the twelve primitive types, the ten numeric kinds, `bool`,
and `string`, also creates a new nominal type, with its name as the tag. A value of it is a
primitive carrying the tag, built by calling the type name with one argument of the base type,
exactly as `byte(255)` builds a `byte`. A literal cannot carry the tag, because the interpreter
never sees an annotation. Calling the base type name on it, `string(id)` or `int(count)`, gives the
payload back. The type is assignable only to itself, never to its base or to another type over the
same base, which is what keeps two kinds of identifier apart.

```ant
type UserId = string
type AccountId = string
type Meters = float64

var id = UserId("u-1")                       // a string carrying the UserId tag
var raw = string(id)                         // "u-1"
var other: AccountId = id                    // compile error: a UserId is not an AccountId
var same = id == UserId("u-1")               // true: same tag, equal payload
var d = Meters(3.0) * Meters(2.0)            // Meters: operators need both operands of one tagged type
var e = Meters(3.0) * 2.0                    // compile error; unwrap or tag the other operand
var byUser: Map[UserId, Account] = Map{}     // keys work, since == works
```

An arithmetic operator applies to two values of one named primitive type when it applies to the
base, and the result has that type. A comparison on them is a plain `bool`, as is `==`, which
follows the equality rule of section 5 and never panics. Mixing a tagged value with a plain one, or
two different tags, in arithmetic or a comparison is a compile error and a kind panic. Library
functions take the base kinds, so `String.length(id)` needs `string(id)`, while `len(id)`, like the
conversions, unwraps it (section 11, Prelude).

In expression position `UserId` is its constructor, a function from the base type to `UserId`, in
the checker as in the interpreter. The name binds a function value that carries the tag, so
`UserId is func` holds and `Array.map(raw, UserId)` tags every element. `is UserId` tests the tag,
so `UserId | string` and `UserId | AccountId` are distinguishable unions. A type parameter the body
does not mention is allowed: `type Id[T] = string` gives `Id[User]` and `Id[Account]` as distinct
static types over one tag, and a union of the two is rejected, since they share it. `Ok[T]` and
`Err[E]` stay records rather than taking this form, because a tag over an arbitrary payload needs a
field to get the payload out, and a record with one field is exactly that.

### Arrays, maps, and sets

```ant
var xs: Array[int] = [1, 2, 3]
var more = [...xs, 4]                       // spread copies elements
var ages = Map{ ada: 36, linus: 54 }        // Map[string, int]
var keyed = Map{ (name): 1, 7: "seven" }    // computed and non-string keys
var empty: Map[string, int] = Map{}
var tags = Set.of(["red", "blue"])          // Set[string]
var seen: Set[int] = Set.of([])
```

Square brackets build arrays. A map literal is `Map{ key: value, ... }`, with the same type-name
prefix as a record literal. A key that is a single word, an identifier or a keyword, is the string
of that word, as in JavaScript, so `Map{ name: 1 }` has the key `"name"`. Any other expression is
evaluated as the key, and a parenthesized identifier `(name)` is the variable. A bare identifier
alone is shorthand: `Map{ name }` means `Map{ "name": name }`. In both brace literals, then, a bare
word before `:` is a name: the field of a record, the string key of a map.

`Array[T]` is dense and growable. `Map[K, V]` keys compare the way `==` does, so a record or an
array can be a key. A map keeps insertion order: `for`, `Map.keys`, `Map.values`, `Map.entries`, and
rendering visit entries in the order their keys were first inserted. Replacing a value keeps the
entry's position; a key removed and inserted again goes to the end. A key is hashed when it is
inserted, and mutating it afterwards is a program error like a data race: memory stays safe, but the
entry may become unreachable. Section 11 covers the operations.

`Set[T]` holds each `==` value at most once, and is otherwise a map without values: members compare
the way keys do, so a record or an array can be one, it keeps insertion order, and a member is
hashed when it is added, so mutating it afterwards is the same program error. A set has no literal
and no indexing. `Set.of` builds one from an array, `Set.has` asks for a member, and `for` visits the
members in order. Two sets are `==` when they have the same members, in any order, as two maps are
when they have the same entries.

### Unions

`A | B` is a type whose values belong to `A` or to `B`. In a type, `|` builds a union; in an
expression, it is the pipe (section 5). A union may span several lines when each continuation line
starts with `|`. A function type's return type extends as far right as possible, so `func(T): A | B`
returns `A | B`; parenthesize the function type to put it inside a union.

```ant
type Id = int | string

func describe(id: Id): string {
  if id is int { `number ${id}` } else { `text ${id}` }
}
```

A nullable type is written `T | null` (section 7).

The members of a union must be distinguishable at run time, because `is` has only kinds and tags to
look at. Each member has a discriminator:

- the kind, for `bool`, `string`, `null`, `void`, and each of the ten numeric kinds;
- the word array, map, set, or func, type arguments not counting; or
- the tag, for a named record or primitive type, for a time type of `stdlib.md`, or for
  `Regex.Pattern`, whose values carry the tag of their type as records do.

A union may contain each discriminator at most once, so `Array[int] | Array[string]` is a compile
error and `Array[int | string]` is the type to write, while `int | float64` is fine. The rule
applies to every union the checker forms, not only to those written in an annotation: an `if` whose
branches join to `Array[int] | Array[string]`, a field read through a union whose members declare it
as `Array[User]` and `Array[Order]` (see Tagged unions), or a variable assigned `Box[int]` on one
path and `Box[string]` on another is a compile error at the join, which says to narrow first or to
give the whole an expected type.

An anonymous record type has no discriminator and cannot be tested by `is`, so a union may contain
at most one, as in `{ name: string } | null`, and never alongside a named record type. The reason is
that width subtyping lets a value in by shape while `is` tests only the tag, which carries no type
arguments:

```ant
type Box[T] = { value: T }
type Mixed = Box[int] | { value: string }        // compile error, and here is why

func increment(b: Mixed): int {
  if b is Box { b.value + 1 } else { 0 }        // a Box[string] enters through the anonymous member and passes the test
}
```

A type parameter has no discriminator either. It may share a union only with `null`, `void`, other
type parameters, and named record or primitive types that take no type arguments. `T | null`,
`T | NotFound`, and `Ok[T] | Err[E]` are fine; `T | Array[int]` would become ambiguous once `T` is
an array, and `T | Box[int]` once `T` is a `Box[string]`. With these two restrictions every value in
a union carries the discriminator of one declared member at that member's type arguments, and the
checker's work for `is` and for exhaustive chains is one lookup per member.

Substituting type arguments forms unions too, and the same rules apply where the arguments are
written. `type Either[A, B] = A | B` is allowed, since two type parameters may share a union, but
`Either[Box[int], Box[string]]` repeats a tag and `Either[Box[int], { value: string }]` is the
`Mixed` type above, so both are compile errors at the use.

A sync type has no discriminator either, because `is` does not accept one (section 5). A union may
contain at most one sync type, and it is narrowed by testing the other members: after `m != null`,
an `m` of type `Mutex | null` is a `Mutex`.

### Tagged unions

A union of named record or primitive types is a tagged union: the tag each value carries tells the
members apart. `s is Circle` tests the tag (section 5). In the branch it guards, `s` has type
`Circle`; in the `else` branch, `s` has the union minus `Circle` (section 7). There is no `kind`
field and no pattern matching: `is` with `if` is the only way to narrow a union of records.

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

if s is Circle { println(s.radius) }
```

The chain in `area` has no final `else` and still has type `float64`: after the third test `s` has
no member left, so the checker knows the chain is complete (section 5, `if`). Adding a member to
`Shape` later breaks the chain, and `area` fails to check until it handles the new member. That is
the exhaustiveness check. A union of empty records is an enumeration, and each member is also a type
of its own that a function can take as a parameter.

Through a value of union type, a field can be read when every member declares it and the union of
the members' field types is itself a valid union (see Unions); that union is the field's type.
Otherwise narrow the value first. A field can never be assigned through a union type: narrow first,
then assign.

`Result[T, E]` is a standard tagged union of `Ok[T]` and `Err[E]` (section 8).

### Function types

A function type lists parameter types and the return type. Parameter names are optional and only
document intent: a call through a function value is always positional (section 6). The return type
extends as far as it can, so `func(): int | Meters` is a function returning `int | Meters`; for a
union with a function type, parenthesize the function type: `(func(): int) | Meters`.

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

Type arguments are never written at a call site. They are solved from the expected type and the
arguments (see Inference). When nothing fixes a type parameter, annotate the result.

```ant
var xs = Array.map([1, 2, 3], { x * 2 })   // Array[int]
var ys: Array[string] = []                  // annotation needed
```

A type parameter may carry a bound, written `[T: Bound]`, where the bound is any type. A solution
for `T` must be assignable to the bound, and when the bound is a union, the solution must be a
single member of it, never a union: `[T: Ordered]` admits `int` or `string`, not `int | string` and
not `Ordered` itself. Inside the body, `T` is known only to be assignable to its bound: the fields
of a record bound can be read and assigned, and an operator applies to `T` when it applies to every
member of the bound. That is sound only because `T` stands for one member, which is what the
restriction guarantees:

```ant
func bigger[T: Ordered](a: T, b: T): T { if a > b { a } else { b } }

func choose(a: Number, b: Number): Number {
  bigger(a, b)                      // compile error: T would be Number, a union; narrow a and b first
}
```

Without a bound, `T` is opaque; `==`, `Map` keys, and `Set` members still work, because they work on
every type. A bounded parameter may be tested against a member of its bound, so with `[T: Ordered]`,
`x is string` narrows `x` to `string`. Bounds are the way to accept any array whose elements have a
given field, since type arguments are invariant and `Array[Person]` is not an `Array[{ name: string
}]`. Nothing changes at run time; the interpreter never sees a bound.

```ant
func max[T: Ordered](a: T, b: T): T { if a > b { a } else { b } }
func names[T: { name: string }](xs: Array[T]): Array[string] { Array.map(xs, { x.name }) }

names(people)                     // ok with Array[Person]: T = Person, which has a name
max(1, 2)                         // int
max(1, 2.0)                       // compile error: int and float64 are different T
```

There are no interfaces, no `where` clauses, and no bounds on type constructors. A user type cannot
customize `String.from` or ordering, so records sort through `Array.sortBy` or `Array.sortWith`. A
generic type with different type arguments is a different type: `Array[Circle]` is not an
`Array[Shape]` (see Assignability).

### Type declarations

`type` declares a name and appears only at the top level of a module. The body decides what the name
means:

- A record type creates a new type with that name as its tag, marked as a record tag (see Records).
- A primitive type creates a new type as well, and the name binds the type's constructor, a function
  value that carries the tag and its base kind (see Named primitive types).
- Any other body makes the name an alias. Its tag is marked as an alias tag, which neither a record
  literal, a constructor call, nor `is` accepts, since an alias has no runtime identity. An alias is
  interchangeable with its body: `type Id = int | string` is the union written out, and
  `type Shape = Circle | Rect` likewise.

A type may refer to itself through a record, array, map, set, or function type, so
`type Tree = { value: int, children: Array[Tree] }` is fine; `type A = A | null`, or a cycle of
plain aliases, is a compile error.

A type name is also the namespace of the functions declared on it (section 6, Functions on types).
It is an expression only as the head of a record literal, as the target of `is`, as the left side of
`.` naming one of its functions, or, for a named primitive type, as its constructor. Anywhere else
it is a compile error, since a type has no value. There are no classes, interfaces, or prototypes.

### Assignability

A value of type `S` can be used where `T` is expected when one of these holds:

- `S` and `T` are the same type. Primitives never widen: `int8` is not an `int`, and a named
  primitive type is neither its base nor another type over that base.
- `T` is a union and `S` is assignable to one of its members, or `S` is a union and every member of
  `S` is assignable to `T`. Members flatten and deduplicate, so `T | null | null` is `T | null`.
- `S` is `never`. `void` is assignable only to `void`, and `null` only to a type that includes it.
- `T` is an anonymous record type and `S` is a record type with at least the fields of `T`, each
  with exactly the type `T` gives it. A named record type accepts only its own tag.
- `S` and `T` are the same generic type with identical type arguments. Type arguments are invariant
  because contents are mutable: if `Array[Circle]` were an `Array[Shape]`, a widened alias could
  store a `Rect` among the circles for a later read to panic on, and the checker's guarantee would
  be gone.
- `S` and `T` are function types with the same number of parameters, each parameter of `T`
  assignable to the corresponding parameter of `S`, and the result of `S` assignable to the result
  of `T`. A function with default parameters is also assignable to a type that lists its required
  parameters plus any prefix of the optional ones. There is no exception for a `void` result: a
  value of static type `void` is always the value `void`, because the interpreter would return a
  lambda's value whatever the type said. A callback that must return `void` discards its last value
  with `_ = ...`, which is an assignment and therefore `void`.

There is no top type: no `any` or `unknown` that every value is assignable to, and no union that
could serve as one, since arrays, maps, sets, and records have one discriminator each. A function
that accepts every type is generic, `func show[T](v: T)`, and data whose type is not known
statically is a union written out, such as `Json.Value` in the library, narrowed with `is`. `never`
is the bottom type and is assignable to everything.

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

Inference is local and bidirectional. Every expression either synthesizes a type or is checked
against an expected type. Expected types come from annotations, parameter types, declared return
types, the field types of a record literal, the element types of an expected array or map, and the
branches of an `if` whose whole has an expected type. Nothing is inferred across statements: an
unannotated `var` takes exactly the type of its initializer. `var s = Active{}` has type `Active`,
and a later `s = Suspended{ reason: "x" }` is a compile error unless the declaration says
`var s: Status`.

A generic call solves its type parameters in a fixed order: from the expected type first, then from
the non-lambda arguments left to right, then from the lambdas. The expected type goes first because
type arguments are invariant: `Result.err(NotFound{ id: from })` under an expected
`Result[void, TransferError]` sets `E` to `TransferError` and then checks the argument against it.
Lambdas go last so that the other arguments have fixed the type their `x` depends on, which is also
what lets an editor complete `x.` inside a lambda. A type parameter that nothing fixes is a compile
error: annotate the result, or use `func` with annotated parameters. Inside a generic function its
own type parameters are types the caller chooses, so a call in its body binds nothing to them: a
lambda whose body has another type is an error there, as `var t: T = 1` is.

```ant
Array.map([1, 2, 3], { x * 2 })           // T = int from the array, U = int from the body
var ys: Array[string] = []                // the expected type fixes the element type
var zs = []                               // compile error: annotate
```

Every function parameter is annotated, except lambda parameters. A lambda needs an expected function
type with zero or one parameter; its result type is synthesized from the body, and when the expected
result mentions an unsolved type parameter, as `U` in `Array.map` or `Array[U]` in `Array.flatMap`,
the body solves it. A function's return type is inferred from
its body unless the function is exported or recursive. Exported functions state it so that a
module's interface reads without its bodies. Recursion is found on demand: the checker infers a
callee's type when it meets a call, and meeting a function whose inference is already in progress is
a compile error asking for an annotation.

The branches of an `if` are each checked against the expected type when there is one. Otherwise the
expression has the union of the branch types, with `never` dropped, so
`if n > 0 { "positive" } else { null }` has type `string | null`.

Literals get no help from context: an integer literal is always `int`, a float literal always
`float64`, and a string literal never carries a tag. `var id: UserId = "u-1"` is a compile error and
`UserId("u-1")` is the spelling, because the interpreter never sees the expected type (see Named
primitive types).

## 5. Expressions

Every construct is an expression with a type. Statements are expressions whose value is `void`.

Evaluation is strictly left to right: the callee before its arguments, arguments in written order,
and record fields, array elements, and map entries in written order. An assignment evaluates the
target's sub-expressions, such as the index in `xs[i()] = f()`, before the right-hand side. `&&`,
`||`, and `??` short-circuit. `a | f(b)` evaluates `a`, then `f`, then `b`.

### Operators

From tightest to loosest binding:

| Level          | Operators                    | Notes                                                                                                                    |
| -------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| postfix        | `a.b` `a?.b` `a[i]` `f(x)`   |                                                                                                                          |
| prefix         | `-a` `!a` `try a`            |                                                                                                                          |
| multiplicative | `*` `/` `%`                  | integer `/` truncates toward zero; `%` is the truncated remainder with the dividend's sign, for floats too; a `/` that does not follow an operand begins a regular expression literal (section 2) |
| additive       | `+` `-`                      | `+` also concatenates strings                                                                                            |
| comparison     | `<` `<=` `>` `>=` `is`       | numbers and strings; `is` tests a union member                                                                           |
| equality       | `==` `!=`                    | one operand's type must be assignable to the other's, so `x == null` checks when `x` is nullable; structural (section 4) |
| logical        | `&&` then `\|\|`             | short-circuit, `bool` only                                                                                               |
| null           | `??`                         | cannot mix with `&&` or `\|\|` without parentheses                                                                       |
| pipe           | `\|`                         | left associative; in a type, `\|` is a union (section 4)                                                                 |
| assignment     | `=` `+=` `-=` `*=` `/=` `%=` | type `void`                                                                                                              |

There is no `===`, no `+` between different types, and no truthiness: a condition must be a `bool`.
An arithmetic or comparison operator needs both operands of the same type, and that type must be a
single numeric kind, `string` where strings are allowed, or one named primitive type over such a
base. An arithmetic result has the operands' type, tag included; a comparison or an equality test is
a plain `bool`. A union such as `Number` is not a kind, so `a > b` on two `Number` values is a
compile error until they are narrowed. Integer overflow panics, including unsigned subtraction below
zero. Division by zero panics for integers and follows IEEE 754 for floats. Wrapping arithmetic is
`Bits.wrapAdd`, `Bits.wrapSub`, and `Bits.wrapMul`, and a shift count outside the operand's width
panics.

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

A block is a sequence of expressions separated by newlines or semicolons. Its value is the value of
the last expression. A block that ends in a declaration or assignment has type `void`.

Braces mean one of three things, decided by the token before them:

- After a type name, including `Map`, they build a value of that type.
- After `func(...)`, `else`, `go`, or `defer`, at the end of an `if`, `while`, or `for` header,
  and at the end of a `select` clause's head, they are a block.
- Anywhere else they are a lambda (section 6).

So `{}` after one of those keywords is an empty block of type `void`, and elsewhere it is a lambda
that returns `void`. A record or map literal inside a block needs no extra braces:
`if c { Point{ x: 1.0, y: 0.0 } } else { origin }`.

A header has no parentheses, as in Go. It ends at the first `{` that is not an operand: one that
directly follows an identifier path, a literal, or a closing `)` or `]`. A `{` directly after an
operator or an opening bracket starts a lambda. A record or map literal in a header would put `{`
after an identifier path, so it must be parenthesized, as in Go:
`if u == (User{ name: "ada" }) { ... }`. The `{` must sit on the same line as the header, because a
newline would end the header expression (section 2).

### `if`

```ant
var label = if n < 0 { "negative" } else if n == 0 { "zero" } else { "positive" }
```

The branches are checked against the expected type, or the `if` has the union of their types
(section 4, Inference). An `if` without `else` has an implicit `else` branch of type `void`. That
branch disappears when the condition narrows its subject to `never`, as at the end of a complete
chain of `is` tests (section 4, Tagged unions); an explicit `else` there cannot run and is a compile
error.

In the header of an `if`, `while`, or `for`, a record or map literal must be parenthesized, since
its `{` would otherwise begin the body: `if p == (Point{ x: 1 }) { ... }` and
`for e in (Map{ a: 1 }) { ... }`.

### `is`

`x is T` is `true` when the value of `x` belongs to `T`. `T` is a named record or primitive type, a
time type of `stdlib.md`, `Regex.Pattern`, a primitive kind, `null`, `Array`, `Map`, `Set`, or
`func`, written without type arguments, because the runtime has only tags and kinds to look at. An
alias is not accepted. With `type Id = int | string`, the checker sees `Id` as the union, while the
runtime would see a tag no value carries. So `x is Id` is a compile error that says to test the
members, and a panic in an unchecked program.

The static type of `x` must be a union with `T` as a member, or an anonymous record type to which
the named record type `T` is assignable. In the second case the test narrows `x` to the one
instantiation of `T` assignable to that type, and it is a compile error when the anonymous type does
not determine every type argument of `T`. Otherwise the test is always true or always false, which
is a compile error.

`is` binds like a comparison, so `!(x is Circle)` and `x is Circle || x is Rect` read as expected.
As the condition of an `if` on a local variable or a parameter, it narrows (section 7).

```ant
Array.filter(shapes, { x is Circle })
if s is Circle && s.radius > 1.0 { ... }          // s: Circle after the &&
```

### Loops

`for` iterates over an array, a map, a set, a string, `Bytes`, or a sequence function; over a map it
yields each `Entry`, over a set each member, over a string each code point as a one-character
string, and over `Bytes` each byte as a `byte`.
Each iteration binds a fresh variable, so a closure created in the body keeps that iteration's
value. `while` repeats while a condition holds. Both have type `void`, except that a `while` whose
condition is the literal `true` and whose body contains no `break` has type `never`, since only
`return` or a panic can leave it. `break` and `continue` work as in JavaScript, without labels.

```ant
for user in users {
  if user.banned { continue }
  notify(user)
}

for { key, value } in ages {  // destructures each Entry[string, int]
  println(`${key}: ${value}`)
}

for i in Iter.range(0, 10) { ... }

while !done { done = step() }
```

A sequence is a function that pushes elements to a callback, as in Go: `Seq[T]` is the prelude alias
`func(func(T): bool): void`. `for x in seq` calls `seq` with a `yield` function. Each call of
`yield` runs the body once and returns `true`, or `false` after a `break`, after which the sequence
must return. `return` and panics in the body propagate through the sequence as through any call.
Writing a sequence is an ordinary loop that calls `yield`, so user types and lazy ranges need no
other protocol.

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

for n in evens(10) { println(n) }
Iter.range(0, 1000) | Iter.filter({ x % 7 == 0 }) | Iter.take(5) | Iter.toArray()
```

### `select`

A `select` waits for the first of several things, with a block for each:

```ant
select {
  var line = Channel.receive(lines) { println(line ?? "closed") }
  Channel.send(out, batch) { batch = [] }
  Time.sleep(Time.duration(seconds: 1)) { flush() }
  Context.wait(ctx) { return }
  else { idle += 1 }
}
```

A clause is a head and a block, one clause per line. A head is one of five blocking calls of
section 11 and `stdlib.md`, written as the call would be and not performed: `Channel.receive(c)`,
`Channel.send(c, v)`, `Context.wait(ctx)`, `WaitGroup.wait(wg)`, or `Time.sleep(d)`. `var x =`
before a head binds the call's result in the block: a receive binds `T | null`, `null` when the
channel is closed, a send binds `bool`, and a binding on a head that returns `void` is a compile
error. A head takes no context, since the context is its own clause, and a head given one is a
compile error. An `else` block, written last, runs when no head can proceed at once, so a `select`
with `else` never waits. The block begins at the head's `{`, which the header rule above finds: a
`{` after a `)` ends a header.

The heads' operands evaluate first, in order, once. Then the `select` waits until one head can
proceed, performs it, binds its result, and runs its block, whose value is the value of the
`select`. A head can proceed when its channel holds a value or is closed, when its channel can
take the value, when its context is done, when its group's counter is zero, or when its time has
passed. When several can proceed at once, one is chosen at random, so no source starves. A
`select` without `else` whose heads can never proceed waits until the run is cancelled, as any
wait does. A closed channel's receive is always ready, so a loop that keeps one in its `select`
spins until the block leaves the loop on `null`. A send chosen on a closed channel panics, as
`Channel.send` does (section 12).

A `select` is an expression: its blocks are checked against the expected type, or it has the
union of their types with `never` dropped, as an `if`. A block's `return`, `break`, and
`continue` act on the function or loop around the `select`, since the block belongs to that body;
a bound variable is a local of its block and narrows there.

```ant
var event: Event = select {
  var line = Channel.receive(lines) { if line == null { Closed{} } else { Line{ text: line } } }
  Time.sleep(Time.duration(seconds: 1)) { Timeout{} }
}
```

A `select` needs at least one head. A body with no clause or with `else` alone, two `else`
clauses, an `else` that is not last, a binding on `else`, a head that is not a call of one of the
five, and a `{` on a line after its head are each a syntax error.

### Destructuring

`var` and `for` accept a destructuring on the left side instead of a name. A record destructuring
`{ x, y }` binds the fields `x` and `y`, and `{ x: px }` binds the field `x` as `px`; fields not
mentioned are ignored. An array destructuring `[a, b]` binds elements by position and ignores extra
elements, and `[head, ...tail]` binds the rest as a new array. Each position holds a name, `_` to
discard, or another destructuring, so they nest.

Destructuring is binding plus indexing, and it fails the way indexing does. An array with fewer
elements than the fixed positions panics, as `xs[1]` would on a one-element array. A nested record
destructuring that meets a non-record such as `null` panics as a field read would. The checker types
each binding from the source, `T` for an element of `Array[T]` and `Array[T]` for the rest, and
cannot know lengths. An array literal on the right is no exception: `var [n, s] = [1, "t"]` gives
both `n` and `s` the type `int | string`, the element type of the literal; two values of two types
want two declarations.

```ant
var { x, y } = origin
var { address: { city } } = user
var [first, second] = xs             // panics when xs has fewer than two elements
var [head, ...tail] = xs             // tail is a new array; panics only when xs is empty
var [_, y] = pair
for { key, value } in ages { println(`${key}: ${value}`) }
for [a, b] in pairs { println(a + b) }
```

An array destructuring is also an assignment target. Its positions are assignable places or nested
array destructurings, and `=` is the only operator allowed, so `[a, b] = [b, a]` swaps and
`[xs[0], p.x] = f()` stores into any places. Evaluation follows the assignment rule: the targets'
sub-expressions left to right, then the right side, then the stores left to right. There is no
record destructuring assignment, because a `{` at the start of a statement is a lambda; use `var`.

### `return`, `break`, `continue`

These have type `never`, so they can appear anywhere an expression is expected. `return` takes the
whole expression to its right, so `x ?? return y + 1` returns `y + 1`; parenthesize it to end
earlier. `panic` is an ordinary function of type `never` (section 8).

A function body, a lambda, a `go` block, and a `defer` block are the four boundaries. `return`
leaves the innermost one; inside a `go` or `defer` block it takes no value, since neither has a
result. `break` and `continue` target the innermost loop inside the same boundary, so a `break` in a
lambda or a `go` block cannot leave a loop outside it. A `break` or `continue` with no loop to
target is a syntax error, as is a `return` outside any boundary. The parser enforces all of this.

```ant
var user = Map.get(users, id) ?? return Result.err(Error{ message: "no such user" })
```

## 6. Functions

`func` declares a named function at the top level of a module; inside a block, bind a function with
`var`. Such a function may call itself, since the closure finds the name when it runs, but its type
must be stated before its body is checked, by a return type on the `func` or a type on the `var`:
inferring it from a body that calls it would meet its own inference in progress. Parameters are
annotated; the return type is inferred unless the function is exported or recursive (section 4,
Inference). The body is a block, so the last expression is the result and `return` is only needed to
leave early.

```ant
func clamp(value: int, low: int, high: int): int {
  if value < low { return low }
  if value > high { return high }
  value
}
```

### Calling

Arguments are positional, named, or positional followed by named. A parameter with a default value
may be omitted.

```ant
func connect(host: string, port: int = 443, tls: bool = true): Connection { ... }

connect("example.com")
connect("example.com", 8080)
connect("example.com", tls: false)
connect(port: 80, host: "example.com")
```

Named arguments apply only to a direct call of a declared function, by its name or through a
namespace. A call through a function value is positional, because the value may be a lambda whose
only parameter is `x`, and the interpreter resolves names against the callee's own parameter list.
There are no variadic parameters; pass an array.

### Anonymous functions

An anonymous function is `func` without a name. Its parameters are annotated and it may state a
return type, exactly like a declaration. A lambda is a bare block with one implicit parameter named
`x`. At run time a lambda accepts zero or one argument, so it also serves where a zero-parameter
function is expected; the checker gives it the arity of the expected function type. In a lambda of
arity zero, `x` is not in scope, and reading it is a compile error; at run time a lambda called
without an argument binds `x` to `void`.

```ant
var add = func(a: int, b: int) { a + b }
var double: func(int): int = { x * 2 }
var isAdult: func(User): bool = { x.age >= 18 }

Array.map([1, 2, 3], { x * x })
Mutex.withLock(lock, { counter += 1 })
```

A lambda's parameter type comes from the function type the context expects. With no expected type,
as in an unannotated `var`, a lambda is a compile error. Nested lambdas each bind their own `x`; use
`func` when you need both.

### Closures and first-class values

Functions are values. They capture variables by reference, with JavaScript semantics: a closure sees
later assignments to captured variables, and `return` inside a lambda returns from the lambda only.

```ant
func counter(): func(): int {
  var n = 0
  func() { n += 1; n }
}

var next = counter()
next()    // 1
next()    // 2
```

### Functions on types

`func Point.distance(a: Point, b: Point)` declares `distance` in the namespace of `Point`. The call
is `Point.distance(p, q)`, or `p | Point.distance(q)` through the pipe. The type must be declared by
the same module and may be a record, a named primitive type, or an alias, including an alias of a
union. A type's namespace is therefore closed, and the prelude's types cannot be extended.

The function is an ordinary function. It need not take the type as a parameter, which is how
`Point.origin()` and `UserId.parse(s)` are written; it is a value like any other; and named
arguments apply to it as to any declared function. It is reached only through the type name, never
bare. Two functions on one type may not share a name, a function may not share its name with a field
of the type, and an exported function needs an exported type. There is no method call:
`p.distance(q)` reads a field of `p`, which does not exist.

```ant
type Point = { x: float64, y: float64 }

func Point.origin(): Point { Point{ x: 0.0, y: 0.0 } }

func Point.distance(a: Point, b: Point): float64 {
  Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y))
}

func Point.norm(p: Point): float64 { p | Point.distance(Point.origin()) }

type Circle = { radius: float64 }
type Rect = { width: float64, height: float64 }
type Shape = Circle | Rect

func Shape.area(s: Shape): float64 {
  if s is Circle { 3.14159 * s.radius * s.radius } else { s.width * s.height }
}

type Box[T] = { value: T }

func Box.map[T, U](b: Box[T], f: func(T): U): Box[U] { Box{ value: f(b.value) } }

var lengths = Array.map(points, Point.norm)
var box = Box{ value: 2 } | Box.map({ x * 10 })        // Box{ value: 20 }
```

At run time the functions are fields of the type's tag or constructor (section 12), so
`Geometry.Point.norm` is a field read like `Array.map`, and `Point.norm` is a function value. The
standard library is written this way: `Result.ok`, `Mutex.new`, and `Atomic.load` are functions on
the types `Result`, `Mutex`, and `Atomic` (section 11).

## 7. Nullability

`null` is a value of type `null` and nothing else. There is no `undefined`. A variable of type
`string` can never hold `null`; a variable of type `string | null` can. There is no `Option`
wrapper: a nullable type is a union with `null`, so `T | null | null` is `T | null`. Where the
difference between absent and null matters, ask the container instead of the value: `Map.has(m, k)`
tells a missing key from a stored `null`.

```ant
func find(users: Array[User], id: int): User | null {
  Array.find(users, { x.id == id })
}
```

Three constructs handle nullable values, and together they replace the combinators other languages
attach to an option type:

```ant
var user = find(users, 7)

var city = user?.address?.city          // string | null: null if any link is null
var label = user?.name ?? "anonymous"   // string: right side when left is null

if user != null {
  println(user.name)                    // user: User here
}
```

`?.` applies to field access, indexing, and calls, spelled `a?.b`, `a?.[i]`, and `f?.(x)`; each
yields `null` when the left side is null. `??` takes any expression on the right, including `return`
and `panic`, so `value ?? panic("unreachable")` unwraps and `value ?? return null` propagates. Both
operators require a left side whose type includes `null`; on any other type they are dead code and a
compile error.

### Narrowing

The checker narrows after a test, as in the last example, but only for a local variable or a
parameter:

- A condition narrows after `x is T`, `x == null`, or `x != null`, through `&&`, `||`, and `!`. The
  `else` branch gets the complement: the union minus the tested member.
- When an `if` has no `else` and its branch has type `never`, because it ends in `return`, `break`,
  `continue`, or `panic`, the complement applies to the rest of the block, so
  `if user == null { return }` leaves `user` a `User` below it. `x ?? return ...` and
  `x ?? panic(...)` narrow the same way.
- After a `while` whose body contains no `break`, the complement of its condition holds, whatever
  the body assigned, because the condition was evaluated last.
- An assignment narrows the variable to the type of the assigned expression, and where branches
  meet, the variable has the union of the branch types, so `if c == null { c = load() }` leaves `c`
  a `Config`. The narrowing holds even when it makes a later test dead: with `v: UserId | string`,
  after `v = "plain"` the test `v is UserId` is a compile error, since `v` is then a `string`.
- Otherwise a narrowing lasts until the next assignment to the variable. Inside a loop, an
  assignment anywhere in the body cancels it from the loop head on.

A field path such as `user.address` never narrows, because any call between the test and the use may
reassign it. Bind it to a local first, or use `?.` or `??`. A top-level `var`, including an imported
one, never narrows either, because any call may reassign it; read it into a local first in the same
way.

Narrowing is limited to locals because a local can go stale in only one way, by reassignment: a
record's tag never changes and a reference never becomes `null` on its own. Another goroutine can
reassign a local only through a closure that captures it, so one rule about closures makes narrowing
sound under concurrency. A nested body is a lambda, an anonymous `func`, a `go` block, or a `defer`
block, and the rule has two directions:

- A local assigned inside a nested body never narrows in the enclosing function, since the
  assignment may run at any moment.
- Inside a nested body, outer locals start at their declared type, since the body may run after a
  later reassignment. The exception is a local never assigned after its declaration: it keeps its
  narrowing there, because nothing can change it, so the narrowing holds whenever and wherever the
  body runs.

```ant
var user = find(id)                          // User | null, never reassigned
if user != null {
  Mutex.withLock(lock, { println(user.name) })  // ok: user keeps its narrowing
}

var hit: User | null = null
go { hit = find(id) }                        // assigned in a go block
if hit != null { println(hit.name) }         // compile error: hit never narrows
```

```ant
if user.address != null { println(user.address.city) }   // compile error: a path does not narrow
var address = user.address
if address != null { println(address.city) }             // ok
```

## 8. Errors

### `Result`

Expected failures are values of `Result[T, E]`, a tagged union of two records:

```ant
type Ok[T] = { value: T }
type Err[E] = { error: E }
type Result[T, E] = Ok[T] | Err[E]
```

`Result.ok(value)` and `Result.err(error)` are plain functions that build the two records;
`Ok{ value: 1 }` is the same value as `Result.ok(1)`. The error type is whatever the author chooses.
The standard library uses `Error`, a record `{ message: string }`; user code often declares a tagged
union of its own.

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
if parsed is Ok { println(`parsed ${parsed.value}`) }
else {
  var error = parsed.error                 // parsed: Err[ParseError] here
  if error is EmptyInput { println("nothing to parse") }
  else { println(`bad digit at ${error.at}`) }   // error: BadDigit here
}
```

Because unions are flat, error types compose without wrapping. A function that parses a file can
return `Result[Config, ParseError | Error]` and `try` both kinds of call. The narrower
`Result[Config, ParseError]` is not itself assignable to the wider type, since type arguments are
invariant (section 4): `try` widens on the way out, and `Result.mapErr(r, { x })` widens explicitly
where `try` does not apply.

### `try`

`try` unwraps a `Result`. Its operand must have a `Result[T, E]` type. On `Ok{ value }` it evaluates
to the value, of type `T`; on an `Err` it returns a fresh `Err` carrying the same error from the
enclosing function, typed by that function's return type. The enclosing function must therefore
return a `Result` whose error type accepts `E`. A `go` or `defer` block has no result, so `try`
directly inside one is a compile error. `try` reads only the outer tag, so on an `Ok[Ok[int]]` it
yields the inner `Ok[int]`. It has no nullable form: `x ?? return null` propagates `null` (section
7), and a `Result[T, E] | null` operand needs that first. An operand of type parameter type is a
compile error, since it is not a `Result`; under erasure a second meaning chosen by static type
would be unsound.

```ant
func loadConfig(path: string): Result[Config, Error] {
  var text = try File.read(path)
  var json = try Json.parse(text)
  Result.ok(Config.fromJson(json))
}
```

`try` binds like a prefix operator: `try f(x) | g()` means `(try f(x)) | g()`, which unwraps the
first stage and pipes the value onward. To propagate the error of a whole pipeline, parenthesize it:
`try (xs | Array.map(parse) | Result.all())`.

Besides the two constructors, `Result` provides `Result.map`, `Result.mapErr`, `Result.unwrap`
(panics on an error), `Result.unwrapOr`, and `Result.isOk` (section 11).

### `panic`

`panic(message)` is a prelude function of type `never`. It stops the current goroutine immediately.
It is for bugs and impossible states, never for expected failures. Panics cannot be caught. A panic
in the main goroutine ends the program with a non-zero exit status; a panic in any other goroutine
ends only that goroutine (section 9).

Section 12 lists every operation that panics. The common ones: integer overflow, integer division by
zero, array index out of range, lossy numeric conversion, and `unwrap` on the wrong case.

### `defer`

`defer` schedules a block to run when the enclosing block exits, whether by falling off the end,
`return`, `break`, `continue`, or panic. Deferred blocks run in reverse order of registration.
`Os.exit` ends the process without unwinding, so no deferred block runs.

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

`go` runs a block on a new goroutine and returns immediately, with type `void`. There is no handle
to join or to read a result from: results come back through shared memory (see Sharing results),
completion through a `WaitGroup`, and a goroutine's panic is reported, not returned. Goroutines are
cheap, and any function can start one or block inside one; there are no `async` functions or colored
call chains. Blocking library calls such as file and network I/O block only the calling goroutine.

```ant
go { sendReport(report) }
```

The program exits when the main goroutine returns, regardless of other goroutines.

The host can end a run before that: the `ant` command on an interrupt the program did not ask for
(`stdlib.md`, `Os.interrupt`), a Go program by cancelling the context it gave `Run`. Every
goroutine then ends at its next call or loop iteration, a blocking call returns with the reason
`cancelled`, and the process exits after a short grace. That is an end, not an event a program
handles; the interrupt a program asks for is the event.

### Synchronization

Goroutines coordinate through shared memory guarded by the sync objects of the standard library,
`Mutex`, `RwMutex`, `WaitGroup`, `Once`, `Cond`, and `Atomic[T]`; through channels, `Channel[T]`,
which carry values from goroutine to goroutine and block the side that is ahead; and through
contexts, `Context`, which bound a wait with a deadline or end it with a cancellation. Each is a
reference value created by its `new` function, and section 11 lists their operations. A `select`
(section 5) waits on several of them at once, and Waiting, below, shows how a program waits for
several things.

```ant
func fetchAll(urls: Array[string]): Array[Result[Http.Response, Error]] {
  var results: Array[Result[Http.Response, Error]] = Array.filled(Array.length(urls), Result.err(Error{ message: "pending" }))
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

### Waiting

A context becomes done once: when a call cancels it, when its deadline passes, or when its parent
is done. Every context descends from the run's, so a cancelled run ends every wait. Every blocking
library call takes a context as its last parameter, `ctx: Context | null = null`, and gives up when
the context is done. What giving up means follows the call's return type: a `Result` is `Err` with
the context's reason as its message, a value-or-null is `null`, and a `void` call returns early, so
the program asks `Context.isDone` when it needs to know. With `null` the call waits until its
condition holds or the run is cancelled. Locks and conditions take no context.

```ant
var ctx = Context.new(Time.duration(seconds: 2))
var reply = Channel.receive(replies, ctx) ?? return Result.err(Error{ message: "no reply" })
```

A goroutine that waits on several channels writes a `select` (section 5) in a loop, one clause
per source, and a transition is the block's own `return` or `break`:

```ant
func generating(s: Session, ctx: Context): void {
  while true {
    select {
      Context.wait(ctx) { return }
      Channel.receive(s.speechStarted) {
        flushRenderer(s)
        Context.cancel(s.generation)
      }
      var message = Channel.receive(s.userMessages) {
        if message != null { Array.push(s.pendingMessages, message) }   // deferred to the next state
      }
      var interrupt = Channel.receive(s.interrupts) {
        if interrupt != null { s.turn.interrupt = interrupt }
        return
      }
    }
  }
}
```

When the producers are the program's own, one channel can carry them all: a mailbox whose element
type is a union of the events, and a loop over it with an `is` chain. Every event then reaches
whatever state is current, in arrival order across all sources, and a state defers what it cannot
handle. The first of several things is the mailbox's shape too: a goroutine per source, one
receive, and a context that stops the rest.

```ant
type Line = { text: string }
type Timeout = {}

func lineOrTimeout(input: File.Handle, wait: Time.Duration): Line | Timeout {
  var events: Channel[Line | Timeout] = Channel.new()
  var ctx = Context.new()
  go {
    var got = Result.unwrapOr(File.readLine(input, ctx), null)
    if got != null { Channel.send(events, Line{ text: got }, ctx) }
  }
  go {
    Time.sleep(wait, ctx)
    Channel.send(events, Timeout{}, ctx)
  }
  var event = Channel.receive(events) ?? Timeout{}
  Context.cancel(ctx)
  event
}
```

A worker pool is a channel of jobs that each worker drains with `Channel.values`, a channel of
results, and a `WaitGroup` that says when to close it. A future is a channel of capacity one. A
ticker is `Time.ticker` (`stdlib.md`), a channel that a `select` reads beside the others. A goroutine that should stop checks
`Context.isDone` between steps and passes the context into its waits; one that ignores its context
runs until the run ends.

### Data races

Reading and writing the same memory from two goroutines without synchronization is a data race. A
data race is a program error. The runtime guarantees memory safety in its presence, but not any
particular result:

- A racy read of a variable, field, or element observes some value that was stored there, never a
  mix of two or a value from nowhere. Since every store into a slot has the slot's declared type,
  the checker's types stay true in a racing program.
- A racy array, map, or set operation observes the state before or after each concurrent mutation,
  or panics with the ordinary index error, or finds the key absent, never a corrupted structure. An
  operation over many elements, such as `Array.map`, may see some of several racing stores and not
  others. Each operation on a `Random` generator (section 11), a whole `shuffle` included, comes
  before or after every racing one, so its values are those of some order of the draws.
- The interpreter itself never crashes.

An implementation may also detect a race and end the program with a report and exit status 1, since
the state of a racy program is not worth continuing.

*Implementation note.* The guarantee costs one word per value, so that a variable, field, or element
store is a single machine word and cannot tear, plus an atomic header load per array operation with
`push` and `pop` under a lock, and one lock per map or set operation, shared between reads, since a
read during a resize is not safe with mutations alone locked. An implementation in a language whose
strings or dynamic values span two words boxes them.

### Visibility

Within one goroutine, effects happen in program order. Across goroutines, a read observes the write
that happens before it when no other write to that location is ordered between them; a read that
nothing orders against a write may or may not see it, and observes some write that is not ordered
after it and is not hidden by another write ordered before the read. These are the orderings, in the
sense of Go's memory model:

- The `go` expression happens before the first action of the goroutine it starts.
- `Mutex.unlock`, and the release at the end of `withLock`, happen before every later `lock` of the
  same mutex. For an `RwMutex`, a write unlock happens before every later read or write lock, and a
  read unlock before every later write lock.
- A `WaitGroup.done` happens before the return of the `wait` it unblocks.
- The completion of the function given to `Once.do` or `Once.value` happens before any call of them
  returns.
- All operations on all `Atomic` objects form one total order, and a `store` happens before every
  `load` that observes it.
- A send on a channel happens before the receive that takes its value, and a close happens before
  a receive that returns `null` because of it; a clause of `select` is a send or a receive.
- `Context.cancel`, and the passing of a deadline, happen before the return of every wait the
  context ends.

`Cond` adds nothing; its mutex supplies the order. A goroutine's exit is ordered with nothing, so a
program that needs a goroutine's result waits on a `WaitGroup`, not on the goroutine being gone. A
data race is then exactly two accesses to one variable, field, or element, or to the length of an
array, the key set of a map, or the members of a set, from different goroutines, at least one of
them a write, with no ordering between them.

### Sharing results

A local assigned inside a `go` block never narrows (section 7), so a goroutine does not hand back a
result by reassigning a local of its parent, even when a `WaitGroup` makes that safe. The checker
cannot see happens-before and does not try. Share through containers instead. Write into an array
slot, a map entry, a record field, or an `Atomic`, and after the wait read the value into a fresh
local and narrow that. A fresh local is a snapshot, so the same idiom reads shared state under a
mutex.

```ant
var results: Array[Result[Http.Response, Error] | null] = Array.filled(n, null)
go { results[i] = Http.get(url) }            // an index write, not a reassignment
WaitGroup.wait(wg)
var r = results[i]                           // a snapshot
if r != null && r is Ok { println(r.value.status) }

var latest: Atomic[Result[Http.Response, Error] | null] = Atomic.new(null)
go { Atomic.store(latest, Http.get(url)) }
WaitGroup.wait(wg)
var v = Atomic.load(latest)
if v != null && v is Ok { println(v.value.status) }

var config = Once.value({ load() })          // lazy initialization without a nullable variable
println(config().name)
```

### Panics in goroutines

A panic ends the goroutine it occurs in, after running that goroutine's deferred blocks. The runtime
reports the message and stack trace on standard error. Nothing else happens: no other goroutine is
interrupted, and the program continues. Code that waits on a goroutine must therefore account for it
never finishing its work; the `defer { WaitGroup.done(wg) }` above is the usual pattern.

## 10. Modules

Each file is a module: a sequence of `import` declarations followed by `var`, `func`, and `type`
declarations. Nothing else appears at the top level. A declaration prefixed with `export` is visible
to other modules; everything else is private. The module's `//!` lines, before its first `import`,
document it (section 2).

```ant
// geometry.ant
export type Point = { x: float64, y: float64 }

export func distance(a: Point, b: Point): float64 {
  Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y))
}
```

A module is a record. Its top-level scope is a record whose fields are its declarations, and
`export` marks the fields other modules may see. `import` destructures that record: a record
destructuring brings chosen exports into scope, with the usual `name: alias` renaming, and a bare
name binds the whole record as a namespace. The standard-library namespaces are prelude variables
bound to records of the same kind, so `Geometry.distance` and `Array.map` are both a field read
followed by a call, and `Geometry.Point{ x: 1.0 }` is a field read that yields a tag. The
interpreter has no notion of a namespace beyond this; the checker keeps each module's export table
so that `Geometry.Point` also resolves in a type.

```ant
import "./geometry.ant" { distance, Point }
import "./geometry.ant" { distance: dist, Point }
import "./geometry.ant" Geometry

var d = Geometry.distance(p, q)
```

The path is a file path relative to the importing file, extension included. There are no packages: a
program is the files it imports. A module is identified by its canonical path, so two spellings of
one file are one module. The path comes first so that an editor knows the module before the names
are typed.

Types and values import alike. A `type` export is its tag, so a record built in one module passes an
`is` test written against the imported name in another, under whatever local name it was given. The
exported functions declared on a type come with it: `import "./geometry.ant" { Point }` makes
`Point.distance` available and `Point: P` makes it `P.distance`. A function without `export` is a
compile error outside its module, like any other private field.

Imports are live and read-only. `export var` is allowed; an imported name reads the exporting
module's current value each time, and assigning to an imported name or to a field of a namespace
from outside the module is a compile error. Two imports binding the same local name, or a top-level
declaration that shadows an imported name, are syntax errors, so every name in a file has one
visible origin. The prelude names count as imports in every module: `print`, `println`, `panic`,
`len`, the type and conversion names such as `int` and `Result`, and the namespaces. Unlike other
imports, a prelude name cannot be shadowed in an inner scope either, so `int` and `x is int` mean
one thing everywhere; the parser enforces it, since the prelude is a fixed list. There is no
re-export. An import cycle is an error in both commands, since no module in it could be initialized
after its imports: `ant run` stops before `main`.

Imports are resolved depth first in source order, and each module is initialized once, after
everything it imports. Within a module, `func` and `type` declarations are hoisted, so functions may
refer to each other in any order. Top-level `var` initializers run in source order. An initializer
that refers to a later `var` outside a nested function body is a compile error; reaching one through
a function call before it is initialized is a runtime panic, since the checker does not trace calls.

Execution starts at `func main()` in the module given to `ant run`, which must declare it. `main`
takes no parameters and returns `void`; command-line arguments come from `Os.args()`. The exit
status is `0` when `main` returns, `1` when the main goroutine panics, and `2` when the program
could not be loaded because of a syntax error, an import cycle, or a missing module or `main`.

## 11. Standard library

The standard library is a set of namespaces in the prelude. Each is a plain record of functions and
types, exactly like an imported module (section 10), so a type a namespace declares is written
through it, as in `Http.Response`; none has methods or state. `Array`, `Map`, and `Set` are the
functions of the three built-in container types, `Bytes` those of binary data, and `Result`,
`Random`, and the sync types are types with functions declared on them (section 6); all read as
`Name.function`, like a namespace. Every function takes its subject as the first argument so it
composes with `|`. This section is the complete core library. The I/O namespaces `File`, `Http`,
`Net`, `Path`, `Time`, `Os`, `Json`, `Csv`, `Encoding`, `Url`, and `Crypto` are policy rather than
language and live in `stdlib.md`.

Signatures are written in Ant's own notation with bounds (section 4, Generics), and a parameter may
carry a default, which a call omits or names as for a declared function (section 6). A callback
whose result the library ignores is typed with a type parameter, never with `void`, so any lambda
fits; the library discards the value itself. A function marked `mutates` changes its first argument
and returns `void`, the removed element, or whether it changed anything; every other function leaves
its arguments untouched and returns a new value. A function that can panic on a particular value
says so in its comment, as in "panics if n < 0" or "panics on overflow". Every function also panics
when an argument has a kind it does not take (section 12).

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

print[T](value: T): void                         // String.from(value) to standard output
println[T](value: T): void                       // String.from(value) and a newline; println() writes only the newline
panic(message: string): never
int8[T: Number](x: T): int8                      // panics if out of range, NaN, or infinite; likewise the other nine; a named primitive over a number is accepted and unwrapped
string(x): string                                // x is a string or a named primitive over string: the payload
bool(x): bool                                    // likewise
len(x): int                                      // x is an array, a map, a set, a string, Bytes, or a channel: its size
```

The twelve conversion names are built into the checker. The signatures give their shape; each also
accepts a value of a named primitive type whose base is a kind it takes, and unwraps it, so
`int(count)` works on a `Count` declared over `int` although `Count` is not assignable to `Number`
(section 4, Named primitive types).

`len` is built into the checker as well. It counts an array's elements, a map's entries, a set's
members, a string's code points (as `String.length` does), the bytes of `Bytes` (as `Bytes.length`
does), and the values a channel buffers now (as `Channel.length` does). It also accepts a named
primitive over `string` and unwraps it, as the conversions do, and a union or a bounded type
parameter whose every member it accepts. Any other argument is a compile error. As a value, `len`
takes its parameter type from the function type expected, which must be one of these, so
`Array.map(words, len)` is an `Array[int]`. The namespace functions stay; `len(xs)` and
`Array.length(xs)` are the same count.

`println` is built into the checker too, so that it may be called with no argument, which writes an
empty line. `print` writes no newline, so a prompt or a progress dot needs nothing else; output is
buffered and flushed when the program reads standard input, blocks, or exits (stdlib.md, Os).

### Array

`Array[T]` is dense and growable. `xs[i]` reads and `xs[i] = v` writes, and both panic when `i` is
out of range; `Array.get` returns `null` instead. Indices are `int`s from `0` up to but excluding
the length, and ranges are half-open: `from` inclusive, `to` exclusive.

```
Array.length[T](xs: Array[T]): int
Array.isEmpty[T](xs: Array[T]): bool
Array.get[T](xs: Array[T], i: int): T | null
Array.first[T](xs: Array[T]): T | null                         // null when empty
Array.last[T](xs: Array[T]): T | null
Array.push[T](xs: Array[T], v: T): void                        // mutates
Array.pop[T](xs: Array[T]): T | null                           // mutates; null when empty
Array.insert[T](xs: Array[T], i: int, v: T): void              // mutates; v becomes element i; panics if i is outside 0 ..= length
Array.removeAt[T](xs: Array[T], i: int): T                     // mutates; the removed element; panics if i is out of range
Array.slice[T](xs: Array[T], from: int, to: int): Array[T]     // panics if from > to, or if either is outside 0 ..= length
Array.concat[T](xs: Array[T], ys: Array[T]): Array[T]
Array.map[T, U](xs: Array[T], f: func(T): U): Array[U]
Array.flatMap[T, U](xs: Array[T], f: func(T): Array[U]): Array[U]   // the arrays f returns, concatenated
Array.filter[T](xs: Array[T], f: func(T): bool): Array[T]
Array.reduce[T, A](xs: Array[T], init: A, f: func(A, T): A): A
Array.find[T](xs: Array[T], f: func(T): bool): T | null        // the first element f accepts
Array.findIndex[T](xs: Array[T], f: func(T): bool): int | null
Array.findLast[T](xs: Array[T], f: func(T): bool): T | null    // the last element f accepts
Array.findLastIndex[T](xs: Array[T], f: func(T): bool): int | null
Array.some[T](xs: Array[T], f: func(T): bool): bool
Array.every[T](xs: Array[T], f: func(T): bool): bool
Array.countWhere[T](xs: Array[T], f: func(T): bool): int       // how many elements f accepts
Array.contains[T](xs: Array[T], v: T): bool                    // by ==
Array.indexOf[T](xs: Array[T], v: T): int | null               // first index, by ==
Array.lastIndexOf[T](xs: Array[T], v: T): int | null           // last index, by ==
Array.min[T: Ordered](xs: Array[T]): T | null                  // null when empty; NaN when any element is NaN
Array.max[T: Ordered](xs: Array[T]): T | null
Array.minBy[T, K: Ordered](xs: Array[T], key: func(T): K): T | null   // the first element with the least key
Array.maxBy[T, K: Ordered](xs: Array[T], key: func(T): K): T | null   // the first with the greatest
Array.sort[T: Ordered](xs: Array[T]): Array[T]                 // ascending, stable; NaN after every number
Array.sortBy[T, K: Ordered](xs: Array[T], key: func(T): K): Array[T]   // ascending by key, stable; a NaN key after every number
Array.sortWith[T](xs: Array[T], cmp: func(T, T): int): Array[T]   // cmp < 0 puts a before b; stable
Array.reverse[T](xs: Array[T]): Array[T]
Array.unique[T](xs: Array[T]): Array[T]                        // the first of each == value, in order
Array.uniqueBy[T, K](xs: Array[T], key: func(T): K): Array[T]  // the first of each == key, in order
Array.chunk[T](xs: Array[T], n: int): Array[Array[T]]          // n elements each, the last fewer; panics if n < 1
Array.groupBy[T, K](xs: Array[T], key: func(T): K): Map[K, Array[T]]   // keys in first-seen order, elements in order
Array.entries[T](xs: Array[T]): Array[Indexed[T]]
Array.range(from: int, to: int): Array[int]                    // empty when to <= from; panics if to − from is above 2^31 − 1
Array.filled[T](n: int, v: T): Array[T]                        // the same v in every slot; panics if n < 0 or n is above 2^31 − 1
Array.flatten[T](xs: Array[Array[T]]): Array[T]
Array.sum[T: Number](xs: Array[T]): T | null                   // null when empty; panics on overflow
Array.same[T](xs: Array[T], ys: Array[T]): bool                // identity
```

`Array.sum` returns `null` on an empty array rather than zero because the interpreter never knows
`T` and so cannot produce the zero of the right kind (section 4, Checking and running). Write
`Array.sum(xs) ?? 0.0`. `Array.min` and `Array.max` return `null` on an empty array for the same
reason. `minBy` and `maxBy` scan from the left and replace the element they hold only when a key
is strictly less, or greater, than its key by `<`, so of equal keys the first wins and a `NaN` key
never replaces one. `Array.chunk([1, 2, 3, 4, 5], 2)` is `[[1, 2], [3, 4], [5]]`, and
`Array.chunk([], 2)` is `[]`.

### Map

`Map[K, V]` is a hash map keyed by `==` that keeps insertion order (section 4). A function that
builds a map from another keeps the order of its source, and `Map.merge` appends the keys of `n`
that `m` lacks. `m[k]` reads `V | null`; `m[k] = v` inserts or replaces. When `V` itself includes
`null`, `Map.has` is the only way to tell a missing key from a stored `null`. Functions that take a
predicate or a mapper receive each `Entry[K, V]`.

```
Map.size[K, V](m: Map[K, V]): int
Map.isEmpty[K, V](m: Map[K, V]): bool
Map.has[K, V](m: Map[K, V], k: K): bool
Map.get[K, V](m: Map[K, V], k: K): V | null
Map.set[K, V](m: Map[K, V], k: K, v: V): void                  // mutates; same as m[k] = v
Map.remove[K, V](m: Map[K, V], k: K): V | null                 // mutates; the removed value
Map.keys[K, V](m: Map[K, V]): Array[K]                         // insertion order, as are values and entries
Map.values[K, V](m: Map[K, V]): Array[V]
Map.entries[K, V](m: Map[K, V]): Array[Entry[K, V]]
Map.fromEntries[K, V](entries: Array[Entry[K, V]]): Map[K, V]  // later entries win
Map.map[K, V, W](m: Map[K, V], f: func(Entry[K, V]): W): Map[K, W]
Map.filter[K, V](m: Map[K, V], f: func(Entry[K, V]): bool): Map[K, V]
Map.merge[K, V](m: Map[K, V], n: Map[K, V]): Map[K, V]         // entries of n win
Map.same[K, V](m: Map[K, V], n: Map[K, V]): bool               // identity
```

### Set

`Set[T]` is a hash set keyed by `==` that keeps insertion order (section 4). Adding a member that
is already there changes nothing, so it keeps its position; a member removed and added again goes
to the end. A function that builds a set from others keeps the order of its first argument. There
is no literal and no `Set.new`: the empty set is `Set.of([])`, whose element type comes from the
expected type, as for `[]`.

```
Set.of[T](xs: Array[T]): Set[T]                                // the first of each == value, in order
Set.size[T](s: Set[T]): int
Set.isEmpty[T](s: Set[T]): bool
Set.has[T](s: Set[T], x: T): bool
Set.add[T](s: Set[T], x: T): bool                              // mutates; true when x was not a member
Set.remove[T](s: Set[T], x: T): bool                           // mutates; true when x was a member
Set.values[T](s: Set[T]): Array[T]                             // insertion order
Set.union[T](a: Set[T], b: Set[T]): Set[T]                     // the members of a, then those of b that a lacks
Set.intersect[T](a: Set[T], b: Set[T]): Set[T]                 // the members of a that b has
Set.difference[T](a: Set[T], b: Set[T]): Set[T]                // the members of a that b lacks
Set.isSubset[T](a: Set[T], b: Set[T]): bool                    // every member of a is a member of b
Set.same[T](a: Set[T], b: Set[T]): bool                        // identity
```

`Set.add` and `Set.remove` say whether they changed the set, so a loop that keeps the first of
each value needs no separate test:

```ant
var seen: Set[string] = Set.of([])
for line in lines {
  if Set.add(seen, line) { println(line) }
}
```

### String

A `string` is immutable and stored as UTF-8. There is no `s[i]`: indexing by code point is linear,
so a loop over indices would be quadratic, and indexing by byte would be a trap. Lengths, indices,
and slices count code points, `for` iterates them (section 5), `String.chars` gives them as an array
to index, `String.toCodePoints` gives them as integers, and `String.toBytes` gives the bytes. There
is no character type: a character is a string of one code point. What a reader sees as one
character can be several code points, such as an `e` followed by a combining accent, or a family
emoji joined from three people; `String.graphemes` splits text into those units, and
`String.normalize` brings the two spellings of `é` to one.

Every string holds only scalar values. Text that reaches a program as a `string` from outside it, a
file, standard input, a network peer, an argument, the environment, or a child process, is decoded
as UTF-8 with each maximal subpart of an ill-formed sequence replaced by U+FFFD, as Unicode
recommends and the WHATWG Encoding standard does: the bytes `FF FE` become two U+FFFD, and `E2 82`,
a euro sign cut short, one. A program that must keep the bytes as they were reads them as
`Bytes`, which a file, a handle, an HTTP body, and a child's output also give, and
`String.fromBytes` tells it whether they are text.
What the host gives only as text has no such form: `Os.args`, `Os.env`, `Os.environ`, and the names
`File.list` and `File.walk` return. A file name that is not UTF-8, which some file systems allow,
comes back with U+FFFD in it, and a path built from that name does not reach the file. Two names
that differ only in such bytes become one, so `Os.environ` then holds one of the two variables.

```
type Cut = { before: string, after: string }                   // the two sides of String.cut

String.length(s: string): int
String.isEmpty(s: string): bool
String.slice(s: string, from: int, to: int): string            // panics as Array.slice does
String.concat(parts: Array[string]): string
String.split(s: string, sep: string): Array[string]            // panics if sep is empty
String.join(parts: Array[string], sep: string): string
String.repeat(s: string, n: int): string                       // panics if n < 0 or n is above 2^31 − 1
String.trim(s: string): string                                 // Unicode white space at both ends
String.trimStart(s: string): string                            // at the start only
String.trimEnd(s: string): string                              // at the end only
String.trimPrefix(s: string, prefix: string): string           // prefix removed once, when present
String.trimSuffix(s: string, suffix: string): string
String.padStart(s: string, width: int, pad: string = " "): string   // pad repeated on the left up to width code points; panics if pad is empty or width is above 2^31 − 1
String.padEnd(s: string, width: int, pad: string = " "): string     // on the right; panics as padStart does
String.contains(s: string, t: string): bool
String.startsWith(s: string, t: string): bool
String.endsWith(s: string, t: string): bool
String.indexOf(s: string, t: string): int | null               // first code point index
String.lastIndexOf(s: string, t: string): int | null           // last code point index
String.count(s: string, t: string): int                        // non-overlapping occurrences; panics if t is empty
String.replace(s: string, old: string, new: string): string    // every occurrence; panics if old is empty
String.replaceFirst(s: string, old: string, new: string): string   // the first occurrence only; panics if old is empty
String.cut(s: string, sep: string): String.Cut | null          // around the first sep; null when absent; panics if sep is empty
String.fields(s: string): Array[string]                        // the runs between Unicode white space; [] when none
String.lines(s: string): Array[string]                         // split at \n, a \r before it dropped; no empty final line
String.toUpper(s: string): string                              // the full mappings, so "straße" gives "STRASSE"
String.toLower(s: string): string                              // likewise
String.foldCase(s: string): string                             // the full case folding: a key in which case does not matter
String.equalFold(a: string, b: string): bool                   // String.foldCase(a) == String.foldCase(b)
String.normalize(s: string, form: string): string              // form is "NFC", "NFD", "NFKC", or "NFKD"; panics on another
String.isDigit(s: string): bool                                // every code point is a decimal digit, Nd; false on ""
String.isLetter(s: string): bool                               // every code point is a letter, L; false on ""
String.isNumber(s: string): bool                               // every code point is a number, N: Nd, Nl such as Ⅻ, or No such as ½; false on ""
String.isSpace(s: string): bool                                // every code point is white space, the White_Space property; false on ""
String.isUpper(s: string): bool                                // every code point is an upper-case letter, Lu; false on ""
String.isLower(s: string): bool                                // every code point is a lower-case letter, Ll; false on ""
String.isPunct(s: string): bool                                // every code point is punctuation, P; false on ""
String.isSymbol(s: string): bool                               // every code point is a symbol, S; false on ""
String.isMark(s: string): bool                                 // every code point is a mark, M, such as a combining accent; false on ""
String.isControl(s: string): bool                              // every code point is a control character, Cc; false on ""
String.isGraphic(s: string): bool                              // every code point is in L, M, N, P, S, or Zs; false on ""
String.isPrint(s: string): bool                                // every code point is in L, M, N, P, or S, or is the space U+0020; false on ""
String.category(c: string): string                             // the two-letter general category of c, such as "Lu"; "Cn" when unassigned; panics unless c is one code point
String.inScript(c: string, script: string): bool               // whether c has the Script property script; panics unless c is one code point, or if script names no script
String.chars(s: string): Array[string]                         // one code point each
String.graphemes(s: string): Array[string]                     // one extended grapheme cluster of Unicode's UAX #29 each
String.toBytes(s: string): Bytes                               // UTF-8
String.fromBytes(bytes: Bytes): string | null                  // null on invalid UTF-8
String.fromBytesLossy(bytes: Bytes): string                    // each maximal subpart of an ill-formed sequence as U+FFFD, as outside text is
String.codePoint(c: string): int                               // the scalar value of c; panics unless c is one code point
String.fromCodePoint(n: int): string | null                    // the string of the one code point n; null when n is not a scalar value
String.toCodePoints(s: string): Array[int]                     // one scalar value per code point
String.fromCodePoints(points: Array[int]): string | null       // null when a value is not a scalar value
String.toInt(s: string, base: int = 10): int | null            // digits of base, optional sign, no prefix; null otherwise; panics if base is outside 2 ..= 36
String.toFloat(s: string): float64 | null                     // a decimal number, below; null otherwise
String.fromInt[T: Integer](x: T, base: int = 10): string       // lower-case digits, - in front when negative; panics if base is outside 2 ..= 36
String.fromFloat(x: float64, digits: int): string              // fixed point with digits decimals, rounded half to even; panics if digits < 0 or is above 2^31 − 1
String.from[T](value: T): string
String.unicodeVersion: string                                  // the version of the Unicode tables, such as "17.0.0"
```

The padding of `padStart` and `padEnd` is `pad` repeated and cut to the code points `s` lacks, so
`String.padStart("7", 4, "ab")` is `"aba7"`, and a string already at or beyond `width` comes back
unchanged. `String.lines` splits the text `File.read` gives at every `\n`, drops a `\r` just before
one, and omits the piece after the last `\n` when it is empty: `"a\r\nb\n"` gives `["a", "b"]`,
`"\n"` gives `[""]`, and `""` gives `[]`. `String.cut("k=v=w", "=")` is `String.Cut{ before: "k",
after: "v=w" }`. The class tests take a string because Ant has no character type: `for c in s`
yields one-code-point strings, so `String.isDigit(c)` tests a character, and `String.isDigit(s)`
tests that a whole field is digits. Each names the Unicode general categories or property it
follows. A decimal digit is one in any script, `٣` among them, while `toInt` reads only `0` to `9`
and the letters of a base above ten, `a` to `z`, which it accepts in either case; so
`String.isDigit("٣")` is `true` and `String.toInt("٣")` is `null`. A number that does not fit an
`int` is `null` too. `toFloat` reads ASCII decimal digits with an optional sign, an optional
fraction after `.`, and an optional exponent after `e` or `E` with its own optional sign, so `-1.5`,
`.5`, `5.`, and `1e+3` are numbers; it rounds to the nearest `float64`, so a tiny value is `0.0`,
and returns `null` on a value beyond the range of `float64` and on anything else: white space,
`_`, a prefix such as `0x`, and `Infinity` and `NaN`, which `String.from` writes but which are not
numbers to parse. `fromInt` writes an unsigned
value as the number it is, so the largest `uint64` is `18446744073709551615`. `fromFloat` of `NaN`
or an infinity renders as `String.from` does. `${String.fromFloat(total, 2)}` and
`String.padStart(String.fromInt(n, 16), 8, "0")` are the fixed-point and zero-padded forms a format
string would give; there is no format string.

`category`, `inScript`, and `codePoint` ask about one character, so they panic on any other string.
A script is named as in Unicode's `Scripts.txt`, in full: `"Latin"`, `"Han"`, `"Cyrillic"`,
`"Common"`, `"Old_Italic"`, and `"Unknown"`, the script of every code point no other script holds,
the unassigned among them. A name the tables do not know panics, so a typo such as `"latin"` or a
short code such as `"Latn"` is caught where it is written; so does a script that a later Unicode
version adds, until the implementation moves to that version. The test reads the Script property,
not Script_Extensions, so a character that several scripts share, such as the Japanese long-vowel
mark `ー`, is in `Common`, as digits and punctuation are. A test for letters of a foreign script
therefore runs per character:

```ant
func mixesScripts(host: string): bool {
  var latin = false
  var cyrillic = false
  for c in host {
    if String.inScript(c, "Latin") { latin = true }
    if String.inScript(c, "Cyrillic") { cyrillic = true }
  }
  latin && cyrillic                     // true for "pаypal.com", whose second letter is Cyrillic
}
```

`toUpper` and `toLower` apply Unicode's full case mappings that hold in every language, so a string
can change length: `String.toUpper("ß")` is `"SS"`. The mappings depend on context, as the Greek
sigma does at the end of a word, so a string is mapped whole, not one character at a time:
`String.toLower("ΣΟΦΟΣ")` is `"σοφος"`, while mapping each character gives `"σοφοσ"`. The rules for
Turkish and Lithuanian, which depend on the language, are not applied, so `String.toLower("İ")` is
`"i\u{307}"`, an `i` and a combining dot. `foldCase` maps every case variant of a string to one
form, so it is the key for grouping or deduplicating text without regard to case:
`String.foldCase("Straße")` and `String.foldCase("STRASSE")` are both `"strasse"`. Neither it nor
`==` normalizes: `"\u{E9}" == "e\u{301}"` is `false`, and text that can arrive in either spelling
is compared or keyed after `String.normalize(s, "NFC")`. `normalize` takes the four forms of
Unicode's UAX #15. `NFD` splits an accent from its letter, so dropping the code points that
`isMark` accepts strips accents; `NFKD` also replaces compatibility characters, such as `ﬁ` with
`fi`.

Code point indices can cut through what a reader sees as one character. `String.slice` can end
inside an emoji, and reversing `String.chars` moves an accent onto another letter and turns the flag
🇨🇭 into two loose letter symbols. `String.graphemes("👨‍👩‍👧e\u{301}")` is the two strings `"👨‍👩‍👧"`
and `"e\u{301}"`, so text cut, reversed, or counted for display goes through `graphemes`. Grapheme
splitting, normalization, case mapping, the class tests, and the rendering of `String.from` follow
the Unicode version `String.unicodeVersion` names. A code point that a later version assigns is
unassigned, `"Cn"`, until the implementation moves to that version, and `String.from` writes it as
an escape inside quotes until then.

`String.from` renders any value. `print`, `println` and template strings use it, so this is the format a
program's output has. It is the only function the language calls implicitly, and only inside
template strings.

- Integers render in decimal. Floats render as the shortest decimal that reads back to the same
  value, with `.0` added when integral: `1.5`, `100.0`, `0.001`. A magnitude at or above `1e21` or
  below `1e-6` takes the exponent form of JavaScript, `1e+21` and `1.5e-7`, with no `.0`. The
  non-finite values render as `NaN`, `Infinity`, and `-Infinity`.
- A string renders as itself at the top level and quoted with escapes inside a container. Inside
  the quotes, `"` and `\` are escaped, `\n`, `\t`, and `\r` are written so, and every other code
  point that `String.isPrint` rejects, such as a control character, a non-breaking space, a
  zero-width joiner, or a bidirectional override, is written `\u{...}` in lower-case hexadecimal
  without leading zeros, as `\u{7f}`. The rendering shows every code point that is there and reads
  back as a literal, which an emoji joined from several shows too: `String.from(["👨‍👩‍👧"])` is
  `["👨\u{200d}👩\u{200d}👧"]`. `bool`, `null`, and `void` render as their literals.
- Arrays render as `[1, 2]`, maps as `Map{ "a": 1 }` with string keys always quoted, sets as the
  call that builds them, `Set.of([1, 2])`, and records as `Point{ x: 1.0, y: 2.0 }` with the name of
  their tag and the fields in declaration order. Entries are separated by `, `. An empty array, map,
  set, or record renders as `[]`, `Map{}`, `Set.of([])`, or `Empty{}`, with nothing inside the
  brackets.
- A named primitive renders as its constructor call, `UserId("u-1")`.
- `Bytes` renders as `Bytes(89 50 4e 47)`, two lower-case hexadecimal digits per byte separated by
  spaces, and `Bytes()` when empty.
- Functions render as `func`, a constructor and a tag as their type's name, sync objects and
  generators as their namespace name, and time values as `stdlib.md` says: an RFC 9557 string, or a
  zone's identifier.
- A regular expression pattern renders as a literal that reads back to it, `/a\/b/i`, as the Regex
  section says.
- A value already being rendered renders as `...`, so cyclic structures terminate.

### Bytes

`Bytes` is an immutable sequence of bytes, for binary data: what a file, a connection, or a child
process gives that is not text, and what a digest or an encoding works on. It holds one byte per
byte, where an `Array[byte]` holds a value per element, and `==` compares the contents, so `Bytes`
serves as a map key. `len(b)` is the number of bytes; `b[i]` reads one as a `byte` and panics
outside `0 ..= len(b) - 1`, as an array index does; `for x in b` yields each byte. There is no
`b[i] = x`. A program that computes bytes one at a time builds an `Array[byte]` and converts it, and
one that joins pieces collects them for `Bytes.concat`, as text is joined with `String.concat`.

```
Bytes.length(b: Bytes): int
Bytes.slice(b: Bytes, from: int, to: int): Bytes               // panics as Array.slice does
Bytes.concat(parts: Array[Bytes]): Bytes
Bytes.indexOf(b: Bytes, sub: Bytes): int | null                // the first index of sub; 0 for an empty sub
Bytes.startsWith(b: Bytes, prefix: Bytes): bool
Bytes.endsWith(b: Bytes, suffix: Bytes): bool
Bytes.fromArray[T: Integer](xs: Array[T]): Bytes               // panics if an element is outside 0 ..= 255
Bytes.toArray(b: Bytes): Array[byte]
```

There is no literal. Bytes come from I/O, from `String.toBytes`, from `Encoding.fromHex` and
`Encoding.fromBase64`, and from `Bytes.fromArray`, which takes integers of any kind so that a
constant is written with plain literals: `Bytes.fromArray([0x89, 0x50, 0x4e, 0x47])` begins every
PNG file. A string escape does not write a byte: `String.toBytes("\u{89}")` is U+0089 in UTF-8, the
two bytes `c2 89`.

`Bytes` renders as `Bytes(89 50 4e 47)`. `Json.stringify` panics on it, since JSON has no form for
bytes and its reader would have to know which encoding to undo; a program writes
`Encoding.toBase64(b)` or `Encoding.toHex(b)` into the JSON instead. Since neither side can change,
`Bytes.slice`, `String.toBytes`, and `String.fromBytes` need not copy the bytes.

### Regex

Regular expressions. A pattern in the source is a literal, `/.../flags` (section 2); a pattern from
data goes through `Regex.compile`, which returns a `Result`. Both build a `Regex.Pattern`, which is
opaque, immutable, and compared by value, so it serves as a map key. The syntax is RE2: Perl's
classes, repetition, alternation, and groups, including the named `(?<name>...)` and the flag groups
`(?i)`, `(?m)`, and `(?s)`, without lookahead, lookbehind, or backreferences, so that a match takes
time linear in the input. `\d`, `\w`, `\s`, and `\b` are ASCII; the Unicode classes are `\pL` and
`\p{Greek}`.

```
type Pattern                                                   // a compiled expression, from a literal or Regex.compile
type Match = { text: string, start: int, end: int, groups: Array[string | null], named: Map[string, string | null] }

Regex.compile(source: string, flags: string = ""): Result[Regex.Pattern, Error]   // Err on bad syntax or flags
Regex.test(p: Regex.Pattern, s: string): bool
Regex.find(p: Regex.Pattern, s: string): Regex.Match | null    // the leftmost match
Regex.findAll(p: Regex.Pattern, s: string): Array[Regex.Match] // every match, left to right, without overlap
Regex.replace(p: Regex.Pattern, s: string, replacement: string): string   // every match; $1 and ${name} expand
Regex.replaceFirst(p: Regex.Pattern, s: string, replacement: string): string   // the first match only, likewise
Regex.replaceWith(p: Regex.Pattern, s: string, f: func(Regex.Match): string): string   // every match, by f
Regex.split(p: Regex.Pattern, s: string): Array[string]        // the pieces between the matches
Regex.escape(s: string): string                                // s with every metacharacter escaped, to match it literally
Regex.source(p: Regex.Pattern): string                         // the normalized source
Regex.flags(p: Regex.Pattern): string                          // "", or some of i, m, s in that order
```

A pattern is its source and its flags. `Regex.compile` takes the flags as a string of the same
letters a literal takes, in any order, and is `Err` on any other letter or a repeated one. The
source is normalized: a `\/` loses its backslash, since RE2 reads `\/` and `/` alike, a line break
becomes `\n` or `\r` and an empty source becomes `(?:)`, which RE2 reads the same, and the flags
are sorted. Two patterns are `==` when their normalized sources and flags are, so `/a/i == /a/i`,
`/a/si == /a/is`, `Regex.compile("a+", "i") == /a+/i`, `Regex.compile("a/b") == /a\/b/`,
`Regex.compile("a\nb") == /a\nb/` and `Regex.compile("") == /(?:)/` all hold, and
`Regex.source(/a\/b/)` is `"a/b"`. A pattern renders as a literal that reads back to it: every `/`
of the normalized source written `\/`, so `/(?:)/` for the empty pattern, as JavaScript renders
it. `Json.stringify` writes that rendering as a JSON string, and `Json.parse` gives it back as a
string.

A `Match` is one match of the whole pattern: `text` is the matched text, `start` and `end` are its
code point indices into `s`, so `String.slice(s, m.start, m.end)` is `m.text`, `groups[0]` is the
whole match and `groups[n]` the `n`th group, `null` when the group took no part, and `named` has
an entry for each named group, in the pattern's order, `null` likewise. `findAll` takes successive
matches from the left without overlap, and skips an empty match that abuts the match before it.
`split` returns the pieces of `s` between the matches, so a pattern that never matches gives
`[s]`; with an empty `s` it gives `[""]`, whatever the pattern. An empty match at the start or at
the end of `s` adds no empty piece, as JavaScript's `split` has it, so `Regex.split(/a*/, "baaab")`
is `["b", "b"]`.

The `i` flag folds case one code point at a time, as RE2 does, so `/k/i` matches the Kelvin sign
`K`, but `/straße/i` does not match `"STRASSE"`, which `String.equalFold` accepts. Text compared
without regard to case is compared through `String.foldCase`.

In `replacement`, `$n` and `${n}` expand to group `n`, `${name}` to a named group, `$$` to one `$`,
and a group that took no part to `""`. A name after `$` is taken as long as it can be: `$1x` is
`${1x}`, which is no group and so expands to `""`; write `${1}x`. A plain string does not
interpolate `$`, so `"$1"` needs no escape. `replaceWith` calls `f` with each `Match` in order and
puts its result in the match's place, as written, with no expansion.

`Regex` is a namespace that declares two types, like `Time`, and not a type with functions, like
`Mutex`, so the annotation is `Regex.Pattern`. `p is Regex.Pattern` tests a value for the kind, as
`t is Time.Instant` does (section 5).

### Iter

Lazy sequences (section 5, Loops). Every function here returns a new `Seq` without running the
source; `Iter.toArray` and `for` run it. A sequence may be run more than once if its source allows.

```
Iter.range(from: int, to: int): Seq[int]                       // from inclusive, to exclusive; empty when to <= from
Iter.fromArray[T](xs: Array[T]): Seq[T]
Iter.map[T, U](s: Seq[T], f: func(T): U): Seq[U]
Iter.filter[T](s: Seq[T], f: func(T): bool): Seq[T]
Iter.take[T](s: Seq[T], n: int): Seq[T]                        // panics if n < 0
Iter.toArray[T](s: Seq[T]): Array[T]
```

### Math and Bits

```
Math.abs[T: Number](x: T): T                                   // panics on the most negative integer, whose absolute value does not fit
Math.min[T: Ordered](a: T, b: T): T                            // NaN when either is NaN
Math.max[T: Ordered](a: T, b: T): T                            // NaN when either is NaN
Math.pow(x: float64, y: float64): float64
Math.sqrt(x: float64): float64
Math.floor(x: float64): float64
Math.ceil(x: float64): float64
Math.round(x: float64): float64                                // half away from zero
Math.trunc(x: float64): float64                                // toward zero; int(Math.trunc(x)) is the explicit truncating conversion
Math.toInt(x: float64): int | null                             // int(x) without the panic: null on a fraction, out of range, NaN, or an infinity
Math.log(x: float64): float64                                  // natural logarithm
Math.log2(x: float64): float64
Math.log10(x: float64): float64
Math.exp(x: float64): float64                                  // e to the power x
Math.sin(x: float64): float64                                  // radians, as are the five below
Math.cos(x: float64): float64
Math.tan(x: float64): float64
Math.asin(x: float64): float64
Math.acos(x: float64): float64
Math.atan(x: float64): float64
Math.atan2(y: float64, x: float64): float64                    // the angle of the point (x, y), in -PI ..= PI
Math.hypot(x: float64, y: float64): float64                    // the square root of x² + y², without overflow in between
Math.cbrt(x: float64): float64                                 // cube root
Math.isNaN(x: float64): bool
Math.isFinite(x: float64): bool                                // neither NaN nor an infinity
Math.clamp[T: Ordered](x: T, lo: T, hi: T): T                  // x held within lo ..= hi; panics if lo > hi or a bound is NaN
Math.random(): float64                                         // uniform in [0, 1); the sequence cannot be seeded, which Random is
Math.randomInt(from: int, to: int): int                        // uniform, from inclusive, to exclusive; the same sequence; panics if to <= from
Math.PI: float64
Math.E: float64
Math.NaN: float64
Math.Infinity: float64                                         // positive; -Math.Infinity is the other
Math.maxFloat64: float64                                       // the largest finite float64
Math.minInt: int                                               // -2^63; not writable as a literal
Math.maxInt: int

Bits.and[T: Integer](a: T, b: T): T
Bits.or[T: Integer](a: T, b: T): T
Bits.xor[T: Integer](a: T, b: T): T
Bits.not[T: Integer](a: T): T
Bits.shiftLeft[T: Integer](a: T, n: int): T                    // panics if n < 0 or n >= width
Bits.shiftRight[T: Integer](a: T, n: int): T                   // arithmetic for signed, logical for unsigned; panics as shiftLeft does
Bits.rotateLeft[T: Integer](a: T, n: int): T                   // by n mod the width, so n may exceed it; panics if n < 0
Bits.rotateRight[T: Integer](a: T, n: int): T                  // panics if n < 0
Bits.popCount[T: Integer](a: T): int
Bits.leadingZeros[T: Integer](a: T): int                       // at the type's width, of the two's complement bits; the width for 0
Bits.trailingZeros[T: Integer](a: T): int                      // likewise
Bits.wrapAdd[T: Integer](a: T, b: T): T                        // two's complement, never panics
Bits.wrapSub[T: Integer](a: T, b: T): T
Bits.wrapMul[T: Integer](a: T, b: T): T
```

The functions over `float64` follow IEEE 754 and never panic: `Math.log(0.0)` is `-Infinity`,
`Math.log(-1.0)` and `Math.sqrt(-1.0)` are `NaN`, and `Math.clamp(x, lo, hi)` with a `NaN` `x` is
`NaN`. The rotations pair with the shifts and panic on a negative count as they do, but a count at
or beyond the width is taken modulo the width, since a rotation by the width is the identity.

### Random

A seeded generator of pseudo-random numbers. The same seed gives the same values in the same order
on every implementation of Ant, so a simulation, a test, or a game can be run again exactly.
`Random` is a prelude type with its functions declared on it (section 6), as the sync types are: a
generator is a reference, compared by identity, and renders as `Random`. Every function but `new`
draws from the generator and so changes it, which makes two goroutines that draw from one generator
without a lock a data race, as two that push to one array are (section 9); `Random.fork` gives each
goroutine its own. `Math.random` stays the unseeded source, and neither is fit for keys or tokens,
which take `Crypto.randomBytes` (`stdlib.md`).

```
Random.new(seed: int | null = null): Random                    // without a seed, from the host's secure source
Random.int(r: Random, from: int, to: int): int                 // uniform, from inclusive, to exclusive; panics if to <= from
Random.float(r: Random): float64                               // uniform in [0, 1)
Random.bool(r: Random): bool                                   // true or false, each half the time
Random.pick[T](r: Random, xs: Array[T]): T | null              // a uniform element; null when empty, without a draw
Random.shuffle[T](r: Random, xs: Array[T]): void               // reorders xs in place into a uniform permutation
Random.fork(r: Random): Random                                 // a generator with r's state, after which r jumps 2^128 draws ahead
```

The values are fixed by what follows, and a later version of Ant may add functions here but never
change what these return. Arithmetic is on `uint64` and wraps modulo 2^64; `rotl(x, k)` rotates left
by `k` bits.

- **State and draw.** A generator holds four words `s0`, `s1`, `s2`, `s3`, and a draw is one step of
  `xoshiro256**` (Blackman and Vigna, 2018). Its value is `rotl(s1 * 5, 7) * 9`, and then, with `t =
  s1 << 17`, the words become `s2 ^= s0`, `s3 ^= s1`, `s1 ^= s2`, `s0 ^= s3`, `s2 ^= t`, and `s3 =
  rotl(s3, 45)`, in that order.
- **Seeding.** `Random.new` fills `s0` to `s3`, in order, with four outputs of SplitMix64 started
  from the seed's two's complement bits as `x`. Each output adds `0x9E3779B97F4A7C15` to `x`, takes
  `z = x`, then `z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9`, `z = (z ^ (z >> 27)) *
  0x94D049BB133111EB`, and is `z ^ (z >> 31)`. SplitMix64 maps distinct values of `x` to distinct
  outputs, so at most one word is zero, and `xoshiro256**` needs only that not all four are. Without
  a seed, or with `null`, `Random.new` fills the words from the source `Crypto.randomBytes` reads
  (`stdlib.md`) instead, reading again in the case, one in 2^256, that all four are zero, so its
  values differ from run to run as `Math.random`'s do.
- **`float`** is one draw `d` as `(d >> 11) * 2^-53`, the top 53 bits as a fraction, exact in a
  `float64`. **`bool`** is whether the top bit of one draw is 1.
- **`int`** takes `n = to - from` as a `uint64`, which every pair of `int` bounds fits, and the mask
  `m = 2^k - 1` for the smallest `k` with `2^k >= n`. It draws `d` until `d & m < n`, which happens
  within two draws on average, and returns `from + (d & m)`. Each try is one draw, `n = 1` included,
  where `m` is 0 and the first try succeeds.
- **`pick`** is `xs[Random.int(r, 0, len(xs))]`, and on an empty array returns `null` and draws
  nothing.
- **`shuffle`** is Fisher-Yates from the end: for `i` from `len(xs) - 1` down to 1, it swaps `xs[i]`
  with `xs[Random.int(r, 0, i + 1)]`.
- **`fork`** returns a new generator holding `r`'s four words, and then moves `r` by the jump of
  `xoshiro256**`: with `t0` to `t3` at 0, for each bit of `0x180ec6d33cfd0aba`,
  `0xd5a61266f0c9392c`, `0xa9582618e03fc9aa`, and `0x39abdc4529b1661c`, in that order and lowest bit
  first, a set bit xors `s0` to `s3` into `t0` to `t3`, and then `r` draws; after the 256 bits, `t0`
  to `t3` become `r`'s words. The new generator goes on with the values `r` would have given, and
  `r` gives values 2^128 draws further along, so neither reaches the other's within any run.

These values check an implementation:

```ant
var r = Random.new(42)
Array.map(Array.range(0, 5), { Random.int(r, 0, 100) })   // [22, 33, 33, 56, 50]
var f = Random.new(42)
Random.float(f)                                           // 0.08386297105988216
var xs = Array.range(1, 11)
Random.shuffle(Random.new(42), xs)
xs                                                        // [6, 8, 10, 4, 3, 1, 5, 9, 2, 7]
```

### Result and Record

```
Result.ok[T, E](value: T): Result[T, E]
Result.err[T, E](error: E): Result[T, E]
Result.isOk[T, E](r: Result[T, E]): bool
Result.map[T, U, E](r: Result[T, E], f: func(T): U): Result[U, E]
Result.mapErr[T, E, F](r: Result[T, E], f: func(E): F): Result[T, F]
Result.unwrap[T, E](r: Result[T, E]): T                        // panics if r is an Err
Result.unwrapOr[T, E](r: Result[T, E], fallback: T): T
Result.all[T, E](rs: Array[Result[T, E]]): Result[Array[T], E]   // the first Err, or Ok of every value

Record.same[T: {}](a: T, b: T): bool                           // identity; {} bounds T to any record
```

`Result.ok` and the others are functions declared on the `Result` type (section 6), so `Result`
names the alias in a type and its functions in an expression. `Record` is a namespace.

### Synchronization

The sync objects of section 9. Each is a prelude type with its functions declared on it (section 6),
so `Mutex` is the type in an annotation and `Mutex.new()` creates one; objects compare by identity.
The `with` forms acquire, run the function, and release even if it panics. A `ctx` parameter is the
context of section 9, Waiting: the call gives up when the context is done.

```
Mutex.new(): Mutex
Mutex.lock(m: Mutex): void                                     // blocks
Mutex.unlock(m: Mutex): void                                   // panics if m is not locked
Mutex.withLock[T](m: Mutex, f: func(): T): T

RwMutex.new(): RwMutex
RwMutex.readLock(m: RwMutex): void                             // blocks while a writer holds m
RwMutex.readUnlock(m: RwMutex): void                           // panics if m is not read-locked
RwMutex.writeLock(m: RwMutex): void                            // blocks while any reader or writer holds m
RwMutex.writeUnlock(m: RwMutex): void                          // panics if m is not write-locked
RwMutex.withRead[T](m: RwMutex, f: func(): T): T
RwMutex.withWrite[T](m: RwMutex, f: func(): T): T

WaitGroup.new(): WaitGroup
WaitGroup.add(wg: WaitGroup, n: int): void                     // panics if the counter would go negative or past the largest int
WaitGroup.done(wg: WaitGroup): void                            // panics if the counter is already zero
WaitGroup.wait(wg: WaitGroup, ctx: Context | null = null): void   // blocks until the counter is zero, or ctx is done

Once.new(): Once
Once.do[T](once: Once, f: func(): T): void                     // runs f the first time only and discards its value; later calls wait for it
Once.value[T](f: func(): T): func(): T                         // the returned function runs f once and caches the value; it panics if that run was left by a return before f gave one
                                                               // for both: if f panics, the once is complete and every call, waiting or later, panics with the same message

Cond.new(m: Mutex): Cond
Cond.wait(c: Cond): void                                       // releases m, waits, reacquires; panics if m is not locked
Cond.signal(c: Cond): void                                     // wakes one goroutine waiting on c, if any
Cond.broadcast(c: Cond): void                                  // wakes every goroutine waiting on c

Atomic.new[T](v: T): Atomic[T]
Atomic.load[T](a: Atomic[T]): T
Atomic.store[T](a: Atomic[T], v: T): void
Atomic.add[T: Number](a: Atomic[T], d: T): T                   // returns the new value; panics on overflow
Atomic.compareAndSwap[T](a: Atomic[T], expected: T, v: T): bool   // compares with ==

Context.new(timeout: Time.Duration | null = null, parent: Context | null = null): Context
                                                               // a child of parent, or of the run; panics if the timeout has years, months or weeks, or is not positive
Context.cancel(ctx: Context): void                             // done now, with the reason "cancelled"; nothing when done already
Context.isDone(ctx: Context): bool
Context.reason(ctx: Context): string | null                    // null while running; "cancelled", "timeout", "interrupt", or the parent's reason
Context.deadline(ctx: Context): Time.Instant | null            // the earliest deadline of ctx and its parents
Context.wait(ctx: Context): void                               // blocks until done

Channel.new[T](capacity: int = 0): Channel[T]                            // 0 is a rendezvous; panics if capacity < 0 or is above 2^31 − 1
Channel.send[T](c: Channel[T], v: T, ctx: Context | null = null): bool   // blocks until taken or buffered; false when ctx ends first; panics if c is closed
Channel.receive[T](c: Channel[T], ctx: Context | null = null): T | null  // blocks; null when closed and drained, or when ctx ends first
Channel.close[T](c: Channel[T]): void                                    // panics if c is closed already
Channel.isClosed[T](c: Channel[T]): bool
Channel.length[T](c: Channel[T]): int                                    // values buffered now
Channel.values[T](c: Channel[T], ctx: Context | null = null): Seq[T]     // every value until closed, or until ctx ends
```

A context's timeout converts as `Http.request`'s does, days at 24 hours and the smaller units
exact, but a calendar unit or a duration that is not positive makes it panic, since `Context.new` is
computation. A child of a done parent is done at once with the parent's reason. `Context.wait` is
how a main goroutine waits for the interrupt while a server runs.

An unbuffered channel hands a value over directly: `send` returns when a receiver has taken it. A
buffered one holds `capacity` values and blocks a sender beyond that. Closing lets receivers drain
what is buffered and then get `null`; a later `send` panics, since a value with no receiver is the
sender's bug. `Channel.new` fixes `T` from nothing, so a declaration annotates: `var jobs:
Channel[Job] = Channel.new()`. `Channel.receive` conflates a `null` value with the end of the
channel when `T` includes `null`, as `Map.get` and `Array.pop` do; a program with such a `T` wraps
the value, and `Context.isDone(ctx)` tells a cancellation from a close. A wait on several channels
at once, or on a channel and a context, a group or a timer, is a `select` (section 5), which takes
nothing from any channel until its choice is made.

## 12. Dynamic semantics

This section is the contract of `ant run`. It defines what every construct does to values, and it is
the only part of the language the interpreter implements; every rule that mentions a type belongs to
the checker. Where the checker would have rejected a program, the rules below say "panic", and the
table at the end collects every such case. A program that passes the checker reaches only the
value-dependent rows of that table, and a data race (section 9).

### Values

Every value has a kind, fixed when the value is created:

| Kind                             | Values                                                                                                                                                                                                                                         |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| the ten numeric kinds            | `int8` … `uint64`, `float32`, `float64`; a number carries its width, because overflow and conversion depend on it                                                                                                                              |
| `bool`, `string`, `null`, `void` | as in section 4                                                                                                                                                                                                                                |
| array                            | a growable sequence of values                                                                                                                                                                                                                  |
| map                              | a hash table from values to values, keyed by `==`, that keeps its entries in insertion order; a key's hash depends on a bounded prefix of its structure, so hashing terminates on cyclic values and agrees with `==`                           |
| set                              | a hash set of values, keyed by `==` and hashed as map keys are, that keeps its members in insertion order                                                                                                                                      |
| record                           | a tag plus a fixed set of named fields, in the order the type declares them                                                                                                                                                                    |
| tagged primitive                 | a value of one of the twelve primitive kinds plus a tag, made by calling the type's constructor (section 4)                                                                                                                                    |
| func                             | a declared function, an anonymous function, or a lambda, with the scopes it captured; or the constructor of a named primitive type, which carries that type's tag and base kind, and the functions declared on the type as fields (section 6)  |
| tag                              | the value a `type` declaration of a record or an alias binds (section 4), marked as one or the other, or the tag of a time type of `stdlib.md` or of `Regex.Pattern`; a record tag also lists the field names in declaration order; every tag carries the functions declared on its type as fields (section 6) |
| sync                             | a `Mutex`, `RwMutex`, `WaitGroup`, `Once`, `Cond`, `Atomic`, `Channel`, or `Context`                                                                                                                                                              |
| time                             | a `Zone`, `Instant`, `ZonedDateTime`, `PlainDate`, `PlainTime`, `PlainDateTime`, or `Duration` of `stdlib.md`: the tag of its type plus the fields that type fixes, which `==` compares by value                                               |
| bytes                            | an immutable sequence of bytes (section 11, Bytes), which `==` compares by content                                                                                                                                                              |
| regex                            | a `Regex.Pattern` of section 11: the tag of that type plus the normalized source and the sorted flags, which `==` compares by value; one is built for each literal when its module is loaded                                                    |
| random                           | a `Random` generator of section 11: four `uint64` words that each draw changes                                                                                                                                                                  |

Arrays, maps, sets, records, functions, sync objects, and generators are references: a variable
holds a reference, and copying the variable copies the reference. Numbers, booleans, strings,
`Bytes`, `null`, `void`, tags, time values, and patterns are immutable, so for them the distinction
never shows.

### Names and scopes

A block opens a scope. `var` binds a name in the current scope from its declaration to the end of
the block, each name at most once per scope, which the parser enforces (section 3); a function
body's scope starts with the parameters. Lookup walks outward through the enclosing scopes to the
module scope and then to the prelude. A closure keeps a reference to the scopes it was created in,
so it sees later assignments to the variables it captured, and a closure made in a `var`'s
initializer sees that `var` once it is bound. The initializer runs first, so a call that reaches the
variable before it is bound panics, as for a top-level `var`. Each iteration of a `for` opens a
fresh scope for the loop variable.

The module scope holds every top-level name from the start, so a function body can name a `var`
declared below it, and a function declared on a type is a field of its tag or constructor from the
start. Reading a top-level `var` whose initializer has not run yet panics (section 10). A module's
scope is a record, and `export` is a checker rule: at run time every field of a module record is
readable.

### Expressions

Operands evaluate left to right (section 5). Below, "must be" means the operation panics otherwise.

- **Literals.** An integer literal is an `int`, a float literal a `float64`. A template string
  evaluates each `${...}` in order and renders it with `String.from`. A regular expression literal
  yields the pattern built from it when its module was loaded, the same value at every evaluation.
- **Record literal `Head{ ... }`.** The head must evaluate to a record tag, not an alias tag.
  Entries evaluate in order; a spread copies every field of a value that must be a record; a later
  entry replaces an earlier one with the same name. Every name must be one the tag lists, and every
  name the tag lists must have received a value. The result is a new record with that tag and those
  fields, in the tag's order whatever order the literal wrote them.
- **Map literal `Map{ ... }`.** A key that is a single word, an identifier or a keyword, is the
  string of that word, decided by the parser (section 4); other keys and all values evaluate in
  order; a later entry whose key is `==` to an earlier one replaces its value and keeps its
  position. The result is a new map.
- **Array literal `[ ... ]`.** Elements evaluate in order; a spread appends every element of a value
  that must be an array. The result is a new array.
- **Variable.** The value bound to the name; a name no scope binds panics.
- **Field read `a.b`.** `a` must be a record with a field `b`; the value is that field. A namespace
  is a record, so this rule also covers `Array.map` and `Geometry.Point`; a tag and a constructor
  have the functions declared on their type as fields, so it also covers `Point.distance`.
- **Index read `a[i]`.** `a` must be an array, a map, or `Bytes`. For an array, `i` must be an `int`
  from `0` up to but excluding the length, and the value is that element; for `Bytes` likewise, and
  the value is that byte as a `byte`. For a map, the value is the entry whose key is `==` to `i`, or
  `null` when there is none.
- **`a?.b`, `a?.[i]`, `f?.(x)`.** If the left operand is `null`, the result is `null` and the rest
  of the postfix chain is skipped. Otherwise the plain rule applies.
- **Call `f(args)`.** `f` evaluates first and must be a function. A constructor takes exactly one
  positional argument, which must have its base kind, and yields that value carrying the tag. For
  any other function, arguments evaluate in order. Positional arguments fill parameters left to
  right; a named argument fills the parameter of that name, which must exist and must not be filled
  already; every parameter still unfilled must have a default, and the defaults evaluate in the
  callee's scope, in parameter order, after the arguments. A lambda has the single parameter `x` and
  accepts zero or one positional argument, binding `x` to `void` when none is given. The body then
  runs in a new scope, and the call's value is the body's value, or the operand of the `return` that
  ended it.
- **Conversion `int8(x)` … `float64(x)`, `string(x)`, `bool(x)`.** The twelve primitive names are
  prelude functions. A tagged argument is unwrapped first. `string` and `bool` then require their
  own kind and yield the value. For the numeric names the argument must be a number, and the result
  follows this table:

  | From    | To      | Rule                                                                                         |
  | ------- | ------- | -------------------------------------------------------------------------------------------- |
  | integer | integer | exact; panics when out of the target's range, including a negative value to an unsigned kind |
  | integer | float   | rounds to the nearest representable value, ties to even; never panics                        |
  | float   | integer | must be integral and in range; panics on a fraction, out of range, `NaN`, or an infinity     |
  | float   | float   | rounds to the nearest representable value; `NaN` and infinities are preserved                |

- **Arithmetic `+ - * / %`.** Both operands must be numbers of the same kind, except that `+` also
  takes two strings and concatenates them. Two tagged values with the same tag are unwrapped,
  operated on as their base kind, and the result carries the tag; a tagged value with a plain one,
  or two different tags, panics. An integer result that does not fit the kind panics, which includes
  unsigned subtraction below zero. Integer `/` truncates toward zero, `%` takes the sign of the
  dividend, and both panic on a zero divisor. Float arithmetic follows IEEE 754 and never panics.
  Unary `-` needs a number; `!` needs a `bool`.
- **Comparison `< <= > >=`.** Both operands must be numbers of the same kind, or two strings, which
  compare by code point, or two tagged values with the same tag, which compare as their base kind.
- **Equality `== !=`.** Never panics. Two values are equal when they have the same kind and: numbers
  are equal by value, with IEEE 754 rules for floats; strings have the same code points; `Bytes`
  have the same bytes; `bool`, `null`, and `void` values are equal by value; records have the same
  tag and `==` fields; tagged primitives have the same tag and equal payloads; time values have the
  same tag and equal fields, as `stdlib.md` lists them per type; patterns have the same normalized
  source and flags; arrays have the same length and `==` elements in order; maps have the same key
  set and `==` values per key; sets have the same members; functions, tags, and sync objects are the
  same object. A pair of values already under comparison counts as equal (section 4). Values of
  different kinds are unequal, so `x == null` is simply `false` for a non-null `x`.
- **`a is T`.** `T` is resolved by name. `null`, `void`, `bool`, `string`, `Bytes`, `func`, `Array`,
  `Map`, `Set`, the ten numeric names, and their aliases `int` and `byte` test the kind of `a`. Any
  other path evaluates and must be a record tag, a time type's tag, `Regex.Pattern`, or a
  constructor, not an alias tag, and the test is whether `a` is a record, tagged primitive, time
  value, or pattern carrying that tag. The result is a `bool`.
- **Logical `&& ||`.** The left operand must be a `bool`. `&&` yields the right operand when the
  left is `true` and `false` otherwise, without evaluating the right; `||` mirrors that. The right
  operand must be a `bool` when it is evaluated.
- **`a ?? b`.** Yields `a`, unless it is `null`, in which case `b` is evaluated and yielded.
- **Pipe `a | f(b)`.** Is `f(a, b)`: `a` evaluates, then `f`, then `b`.
- **Assignment.** The target's sub-expressions evaluate first, then the right side. A variable
  target rebinds the name in the scope that declared it. A field target must be a record that
  already has that field. An index target on an array must be an `int` in range; on a map it inserts
  or replaces. An array destructuring target requires an array with at least as many elements as its
  positions, and stores element by element left to right, with a rest position receiving a new array
  of the remainder. Compound assignment reads the target, applies the operator, and stores. The
  value is `void`.
- **Destructuring in `var` and `for`.** A record destructuring requires a record with every named
  field. An array destructuring requires an array with at least as many elements as its fixed
  positions; extra elements are ignored, and a rest binder receives a new array of the remainder.
  Nested destructurings apply the same rules to the element they receive. `_` binds nothing, and
  reading `_` panics.
- **Block.** Opens a scope and evaluates its statements in order. Its value is that of the last
  expression, or `void` when the block is empty or ends in a declaration or an assignment. Deferred
  blocks registered in it run when it exits (below).
- **`if`.** The condition must be a `bool`. The value is the chosen branch's value; with no `else`
  and a `false` condition it is `void`.
- **`while`.** Evaluates the condition, which must be a `bool`, before each iteration. The value is
  `void`.
- **`select`.** The operands of every head evaluate in order; each must have the kind its call
  takes. Then the goroutine waits until a head can proceed: a receive when its channel holds a
  value or is closed, a send when its channel can take the value, `Context.wait` when the context
  is done, `WaitGroup.wait` when the counter is zero, `Time.sleep` when the time has passed; with
  an `else` clause it does not wait, and `else` is taken when no head can proceed at once. One of
  the heads that can proceed is performed, chosen at random among them, its result is bound when
  the clause binds, and its block is evaluated; the value is the block's. A send performed on a
  closed channel panics.
- **`for x in e`.** `e` must be an array, a map, a set, a string, `Bytes`, or a function. Over an
  array it iterates by index from zero while the index is below the current length, so elements
  appended during the loop are visited and removed ones are not. Over a map it visits the entries as
  `Entry` records in insertion order, reading the map as it goes, like an array. An entry inserted
  during the loop is visited, an entry removed before the loop reaches it is not, and no entry is
  visited twice. A key removed and inserted again is a new entry at the end. Over a set it visits
  the members the same way. Over a string it yields each code point as a one-character string, and
  over `Bytes` each byte as a `byte`. Over a function it calls the function with a fresh `yield`
  function; each call of `yield` with one argument binds `x`, runs the body, and returns `true`, or
  `false` when the body ended with `break`. Calling `yield` again after it returned `false`, or
  after the sequence function has returned, panics; a `return` or a panic in the body propagates
  through the sequence function like any other call. A destructuring on the left reads the named
  fields of each element, which must be a record with those fields. The value is `void`.
- **`break`, `continue`.** Leave or restart the innermost enclosing loop within the same function
  body, lambda, `go` block, or `defer` block, running the deferred blocks of every block they exit.
- **`return e`.** Evaluates `e`, or `void`, and leaves the innermost enclosing function body,
  lambda, `go` block, or `defer` block, running the deferred blocks of every block it exits.
  Directly inside a `go` or `defer` block it has no operand (section 5), so it ends the block with
  `void`.
- **`try e`.** The value must be a record tagged `Ok` or `Err`. `Ok` yields its `value` field; `Err`
  returns a new `Err` record with the same `error` field from the enclosing function.
- **Lambda and anonymous `func`.** Create a function value that captures the current scopes.
- **`defer { ... }`.** Registers the block with the innermost enclosing block. The value is `void`.
- **`go { ... }`.** Starts a new goroutine that evaluates the block, and yields `void` at once.
- **`panic(message)`.** Begins a panic in the current goroutine (below).

### Deferred blocks and panics

When a block exits, by reaching its end, by `return`, `break`, or `continue`, or by a panic, its
deferred blocks run in reverse order of registration, each in the scope it was registered in. A
`return` inside a deferred block returns from the deferred block only.

A panic unwinds the current goroutine: every block being evaluated exits in turn, running its
deferred blocks, until the goroutine's root block has exited. A panic inside a deferred block
replaces the one in progress. When unwinding finishes, the runtime writes the message and a stack
trace to standard error. In the main goroutine the program then exits with a non-zero status; in any
other goroutine, that goroutine ends and nothing else happens. Panics cannot be caught.

### Goroutines

Goroutines are preemptive: a goroutine that never blocks cannot keep others from running. They share
memory, and the sync objects of section 9 are the only synchronization. The runtime guarantees that
a data race cannot corrupt memory or crash the interpreter, as section 9 spells out; the values a
racing program observes are otherwise unspecified, and an implementation may end a racing program
with a report. The program ends when `main` returns, whatever other goroutines are doing.

### Runtime panics

The complete list. The checker rules out every panic in the middle column, so a checked program
can only panic in the ways the last column lists, which depend on values known at run time.

| Operation                                         | Panics when (ruled out by the checker)                                                                                                                                                                                                                | Panics when (possible in a checked program)                                                                                                      |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `+ - * / %`, `< <= > >=`, unary `-`               | an operand is not a number, or the operands differ in kind or tag; `+` and the comparisons also take two strings                                                                                                                                      |                                                                                                                                                  |
| `!`, `&&`, `\|\|`, `if`, `while`                  | an operand or condition is not a `bool`                                                                                                                                                                                                               |                                                                                                                                                  |
| integer `+ - *`, compound assignment, `Array.sum` |                                                                                                                                                                                                                                                       | the result does not fit the kind                                                                                                                 |
| integer `/`, `%`                                  |                                                                                                                                                                                                                                                       | the divisor is zero                                                                                                                              |
| `Bits.shiftLeft`, `Bits.shiftRight`               |                                                                                                                                                                                                                                                       | the count is negative or not below the operand's width                                                                                           |
| numeric conversion                                |                                                                                                                                                                                                                                                       | an integer target is given a fraction, a value out of range, `NaN`, or an infinity                                                               |
| `string`, `bool`                                  | the argument, after unwrapping, is not of that kind                                                                                                                                                                                                   |                                                                                                                                                  |
| `len`                                             | the argument, after unwrapping, is not an array, a map, a set, a string, `Bytes`, or a channel                                                                                                                                                        |                                                                                                                                                  |
| `a.b`, `a.b = v`                                  | `a` is not a record, or has no field `b`                                                                                                                                                                                                              |                                                                                                                                                  |
| `a[i]`, `a[i] = v`                                | `a` is not an array or a map, nor `Bytes` for a read                                                                                                                                                                                                  | `a` is an array or `Bytes` and `i` is not an `int` from `0` up to but excluding the length                                                       |
| call                                              | the callee is not a function; a constructor given other than one positional argument of its base kind; too many positional arguments; a named argument for an unknown or already filled parameter, or to a lambda; a required parameter left unfilled |                                                                                                                                                  |
| record literal                                    | the head is not a record tag; a spread operand is not a record; an entry or a spread gives a field the tag does not list; a field the tag lists is left without a value                                                                               |                                                                                                                                                  |
| array literal                                     | a spread operand is not an array                                                                                                                                                                                                                      |                                                                                                                                                  |
| `is`                                              | the right side is a path that does not evaluate to a record tag, a time type's tag, `Regex.Pattern`, or a constructor                                                                                                                                 |                                                                                                                                                  |
| `for`                                             | the operand is not an array, a map, a set, a string, `Bytes`, or a function                                                                                                                                                                           | a sequence calls `yield` after it returned `false` or after the sequence returned                                                                |
| destructuring                                     | a record destructuring meets a value that is not a record with every named field; an array destructuring meets a value that is not an array                                                                                                           | the array has fewer elements than the fixed positions                                                                                            |
| variable                                          | no scope binds the name                                                                                                                                                                                                                               |                                                                                                                                                  |
| `_`                                               | read                                                                                                                                                                                                                                                  |                                                                                                                                                  |
| library function                                  | an argument has a kind the function does not take                                                                                                                                                                                                     | the documented case, such as `Result.unwrap` on an `Err` or `Mutex.unlock` when not locked                                                       |
| `var`                                             |                                                                                                                                                                                                                                                       | read before its initializer has run: a top-level `var`, or a local through a call made from its own initializer                                  |
| `panic`                                           |                                                                                                                                                                                                                                                       | always                                                                                                                                           |
| any call                                          |                                                                                                                                                                                                                                                       | the goroutine's call depth exceeds the runtime's limit                                                                                           |
| a count                                           |                                                                                                                                                                                                                                                       | above 2^31 − 1 in `Array.filled`, `Array.range`, `String.repeat`, `String.padStart`, `String.padEnd`, `String.fromFloat`, `Crypto.randomBytes` or `Channel.new`, which size what the runtime must hold |
| `try`                                             | the operand is not a record tagged `Ok` or `Err`                                                                                                                                                                                                      |                                                                                                                                                  |
| `select`                                          |                                                                                                                                                                                                                                                       | a send clause is chosen on a closed channel                                                                                                      |
| `??`, `?.`, `==`, `!=`                            | never                                                                                                                                                                                                                                                 | never                                                                                                                                            |

## 13. Example

```ant
type Active = {}
type Suspended = { reason: string }
type Status = Active | Suspended
type AccountId = int

type Account = {
  id: AccountId,
  owner: string,
  balance: float64,
  status: Status,
}

type NotFound = { id: AccountId }
type Insufficient = { needed: float64 }
type AccountSuspended = { id: AccountId, reason: string }
type TransferError = NotFound | Insufficient | AccountSuspended

func transfer(accounts: Map[AccountId, Account], from: AccountId, to: AccountId, amount: float64): Result[void, TransferError] {
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

func report(accounts: Map[AccountId, Account]): string {
  Map.values(accounts)
    | Array.filter({ x.status is Active })
    | Array.sortBy({ x.balance })
    | Array.map({ `${x.owner}: ${x.balance}` })
    | String.join("\n")
}

func main() {
  var accounts: Map[AccountId, Account] = Map{}
  var ada = AccountId(1)
  var linus = AccountId(2)
  accounts[ada] = Account{ id: ada, owner: "ada", balance: 100.0, status: Active{} }
  accounts[linus] = Account{ id: linus, owner: "linus", balance: 20.0, status: Suspended{ reason: "audit" } }

  var result = transfer(accounts, ada, linus, 50.0)
  if result is Ok { println("ok") }
  else {
    var error = result.error
    if error is NotFound { println(`unknown account ${int(error.id)}`) }
    else if error is Insufficient { println(`short by ${error.needed}`) }
    else { println(`account ${int(error.id)} is suspended: ${error.reason}`) }
  }

  println(report(accounts))
}
```
