# `ant fmt`

Draft 0.1 · October 2026

`ant fmt` rewrites Ant source files into one layout. It has no options and no configuration file,
so every formatted file in every project looks the same, and a diff shows only what changed. It
works on tokens and line breaks: it never changes what a program means, never reorders anything,
and never rewrites one construct into another. This document is the contract of the command;
section numbers in it refer to `ant-lang.md`.

## 1. Command

```
ant fmt <path>...           rewrite each file in place
ant fmt --check <path>...   list the files that are not formatted, and change nothing
ant fmt -                   read standard input, write the formatted source to standard output
```

A path is a `.ant` file or a directory. A directory is walked recursively for files ending in
`.ant`, in lexical order, skipping any entry whose name starts with `.`; symbolic links are not
followed. A file named on the command line is formatted whatever its extension. `ant fmt` with no
path is a usage error, so that nothing is rewritten by accident; the current directory is
`ant fmt .`.

`ant fmt` reads only the files it is given. It does not follow imports, and it does not run the
checker: a file with type errors is formatted like any other. A file must parse as a module
(section 10), the same as `ant run` and `ant check` require. A file that does not parse is left
untouched, and its error is reported as those commands report it, `path:line:col: message`, with
`<stdin>` as the path for standard input. The remaining files are still formatted.

In place, a file is written only when its formatted contents differ from what is on disk, and the
new contents replace the old in one step, so an interrupted run leaves either the old file or the
new one. With `--check`, each file whose contents would change is printed to standard output, one
path per line, as it was named or found.

| Exit status | When                                                                              |
| ----------- | --------------------------------------------------------------------------------- |
| `0`         | every file is formatted, or was rewritten                                         |
| `1`         | with `--check`, at least one file is not formatted                                |
| `2`         | the usage is wrong, or a file could not be read, parsed, or written              |

A `2` outranks a `1`: a run that finds both a syntax error and an unformatted file exits `2`.

## 2. Guarantees

- **Meaning.** The formatted file has the same tokens as the original, in the same order, with the
  same spelling, except for the layout tokens this document names: newlines, semicolons that end a
  statement, and trailing commas. It therefore parses to the same tree, and `ant run` and
  `ant check` behave exactly as they did, error positions aside.
- **Comments.** Every comment is kept, in order, with its text. Only the whitespace before it and
  the indentation of its first line change.
- **Idempotence.** Formatting a formatted file changes nothing.
- **Locality.** The layout of a line depends only on its own tokens, the brackets it is inside, and
  the author's line breaks around it. Editing one function never reformats another.

## 3. What is kept

`ant fmt` keeps everything a reader might have chosen on purpose:

- **Line breaks.** Where the grammar allows a line break (section 2, Line endings), the author
  decides whether there is one. `ant fmt` never joins two lines of an expression and never splits
  one, except inside brackets (section 4.4) and between statements (section 4.3). There is no
  maximum line width.
- **Order.** Declarations, statements, record fields, arguments, and imports stay in written order.
  Imports in particular are never sorted, since their order is the order modules are initialized
  (section 10).
- **Spelling.** Identifiers, number literals (`0xFF`, `1_000`, `1e9`), string literals and their
  escapes, regular expression literals and their flags, and template strings are printed exactly
  as written. A template string is printed verbatim from its opening backtick to its closing one,
  interpolations included.
- **Parentheses.** Every pair of parentheses the author wrote is kept, even where precedence makes
  it redundant, and none is added.
- **`else` placement.** `} else {` on one line and `else` at the start of the next line are both
  kept as written (see 4.6).

## 4. Layout

### 4.1 Files

- The output is UTF-8 with `\n` line endings. A `\r\n` or a lone `\r` line ending becomes `\n`,
  except inside a template string, whose text is kept byte for byte. A byte order mark at the
  start of the file is removed.
- No line ends in spaces or tabs, except inside a template string.
- The file starts with its first token or comment, and ends with exactly one `\n`.
- Indentation is two spaces per level and never a tab. A tab anywhere outside a string, template,
  or comment becomes the spacing this section prescribes.

### 4.2 Blank lines

A run of blank lines becomes one blank line. A block, a list, or a file never starts or ends with a
blank line: blank lines directly after an opening bracket, before a closing one, at the start of
the file, and at its end are removed. Otherwise a blank line is kept where the author put it, and
none is added, not even between top-level declarations.

### 4.3 Statements and blocks

A block is the body of a `func`, an `if`, `else`, `while`, `for`, `go`, `defer`, `select`, or
`select` clause, or a lambda (section 5, Blocks). The top level of a file is laid out like a broken
block at indentation zero.

A block is **flat** when the author wrote it on one line: no newline between its `{` and its `}`,
outside the nested brackets of its statements. A flat block stays on one line, with one space
inside each brace and `; ` between its statements: `{ n += 1; n }`. An empty block is `{}`.

Any other block is **broken**. Its `{` ends its line, each statement starts its own line one level
deeper than the line that holds the `{`, and the `}` starts a line at that line's level. A
semicolon that separates two statements of a broken block becomes a line break, so `a; b` on one
line of a broken block becomes two lines. A semicolon at the end of a line, and an empty statement
such as `;;`, are removed.

```ant
// before
func counter(): func(): int {
var n = 0;
  func() { n += 1; n }
}

// after
func counter(): func(): int {
  var n = 0
  func() { n += 1; n }
}
```

A block that holds a line comment cannot be flat, since the comment ends the line; it is broken.

### 4.4 Lists

A list is anything between brackets that is not a block: the arguments of a call, the parameters of
a function or function type, type parameters and type arguments, an index, an array or map literal,
a record literal, a record type, a destructuring, an import list, and a parenthesized expression.
Items are separated by commas, and a parenthesized expression has one item.

A list is **broken** when the author wrote a newline between its opening bracket and its first
item, between two of its items, or between its last item and its closing bracket. A newline inside
an item, such as inside a lambda passed as an argument, does not break the list. Any other list is
**flat**.

A flat list stays on one line. Its items are separated by `, `, and a trailing comma is removed.

A broken list puts each item on its own line, one level deeper than the line that holds the opening
bracket. Every item, the last included, is followed by a comma, and the closing bracket starts a
line at the level of the line that holds the opening one. A parenthesized expression is the
exception: it takes no comma, since `(a,)` is not an expression, and its closing `)` follows its
item when the author wrote it there.

```ant
// before
var accounts = Map{ ada: Account{ id: "ada", balance: 100 },
  bob: Account{ id: "bob", balance: 20 } }
connect("example.com",
        tls: false)

// after
var accounts = Map{
  ada: Account{ id: "ada", balance: 100 },
  bob: Account{ id: "bob", balance: 20 },
}
connect(
  "example.com",
  tls: false,
)
```

Because a newline inside an item does not break the list, a call whose last argument is a broken
lambda or anonymous function keeps its other arguments on the call's line:

```ant
RwMutex.withWrite(b.lock, {
  var source = b.accounts[from]
  source.balance -= amount
})
```

An empty list is `()`, `[]`, or `{}`, with nothing inside, unless it holds a comment, in which case
it is broken and the comment takes the place of an item.

### 4.5 Continuation lines

Outside brackets, an expression continues onto the next line where section 2 says it does: after a
token that cannot end an expression, such as a binary operator, `=`, or `,`, or before a line that
starts with `.`, `?.`, or `|`. Every continuation line of an expression is indented one level
deeper than the line the expression starts on. The indentation does not grow with each
continuation, so a pipeline's stages line up:

```ant
var names = users
  | Array.filter({ x.age >= 18 })
  | Array.map({ x.name })
  | Array.sort()

var total = subtotal +
  shipping +
  tax
```

A bracket opened on a continuation line indents its contents relative to that line, by the rules
of 4.3 and 4.4.

### 4.6 `else`

An `else` that the author wrote after the `}` on the same line stays there, with one space on each
side: `} else {`, `} else if c {`. An `else` that the author wrote at the start of a line starts a
line at the level of the `if` it belongs to, which keeps chains of one-line branches readable:

```ant
if e is NoAccount { `no account named ${e.id}` }
else if e is Insufficient { `${e.id} is short by ${e.short}` }
else { "unknown" }
```

The same holds for the `else` clause of a `select`, which is always on its own line, as every
clause is (section 5, `select`).

### 4.7 Spacing

Within a line, tokens are separated by nothing or by one space, as follows. The first rule that
applies wins.

| Between                                                                   | Spacing | Example                          |
| ------------------------------------------------------------------------- | ------- | -------------------------------- |
| an opening bracket and what follows it, except a flat block's `{`         | none    | `f(a)`, `[1, 2]`, `(a + b)`      |
| what precedes a closing bracket and it, except a flat block's `}`         | none    | `f(a)`, `xs[i]`                  |
| a flat block's or a flat brace list's `{` or `}` and its contents         | one     | `{ x * 2 }`, `Point{ x: 1.0 }`   |
| a token and `,` `;` `:` `.` `?.`                                          | none    | `a, b`, `x: int`, `p.x`, `a?.b`  |
| `,` `;` `:` and the next token                                            | one     | `f(a, b)`, `{ a; b }`            |
| `.` `?.` `...` and the next token                                         | none    | `p.x`, `[head, ...tail]`         |
| an operand and `(` or `[` (a call, an index, type arguments or parameters) | none    | `f(x)`, `Array[int]`, `max[T]`   |
| `?.` and `(` or `[`                                                       | none    | `f?.(x)`, `xs?.[0]`              |
| a type name, including `Map`, and the `{` of its literal                   | none    | `Point{ x: 1.0 }`, `Map{}`       |
| prefix `-` or `!` and its operand                                         | none    | `-x`, `!done`                    |
| `func` and the `(` of an anonymous function or function type              | none    | `func(a: int) { a }`, `func(int): int` |
| a binary operator, `is`, `=`, a compound assignment, or `\|` and either side | one   | `a + b`, `x is T`, `A \| B`      |
| a keyword and the next token, and the next token and a keyword            | one     | `try f()`, `return x`, `for x in xs` |
| any other pair, such as a header and its `{`                              | one     | `if ready {`, `func f() {`       |

A `-` is prefix when the token before it is not an operand, by the same rule that tells a regular
expression from a division (section 2, Literals). `type` before a record type's `{` is a keyword
and takes a space: `type P = { x: int }`.

### 4.8 Comments

A comment on a line of its own is indented to the level of the code that follows it in the same
block or list, or, when it is the last thing before a closing bracket, one level deeper than that
bracket. A run of such comments moves together. Only the first line of a block comment is
reindented; its other lines are kept as written, trailing spaces removed.

A comment after code on the same line is a trailing comment. It keeps the column the author wrote
it at, so that a column of aligned comments stays aligned, as long as at least one space then
separates it from the code. When the code has grown past that column, one space separates them.
A tab before a trailing comment counts as one column.

```ant
// before
var xs = [3, 1, 2]
Array.length( xs )                  // => 3
Array.reverse(xs)                   // => [2, 1, 3]

// after
var xs = [3, 1, 2]
Array.length(xs)                    // => 3
Array.reverse(xs)                   // => [2, 1, 3]
```

A block comment between two tokens of a line, as in `f(a, /* b */ c)`, takes the spacing of the
token after it on its left and one space on its right. The text of a comment, including any space
after `//`, is never changed, so the corpus's `// expect`, `// =>`, and `// ERR:` markers keep
their meaning.

## 5. What `ant fmt` does not do

- It does not wrap long lines or join short ones; line breaks are the author's (section 3).
- It does not sort imports, declarations, or record fields.
- It does not remove redundant parentheses, simplify expressions, or rename anything.
- It does not align anything except by keeping the columns of trailing comments.
- It does not format the code inside template interpolations, nor Ant code in Markdown files.
- It has no options, no configuration file, and no way to turn it off for part of a file.

## 6. Open questions

- Whether `ant fmt` should also accept the top-level statements of the library tables
  (`tests/stdlib`), which are not modules, or the corpus formats them through the test harness.
- Whether a `--diff` flag that prints a unified diff instead of writing earns its place next to
  `--check`.
- Whether `ant check` should warn on an unformatted file, or that stays the job of
  `ant fmt --check` in continuous integration.
