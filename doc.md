# `ant doc`

Draft 0.1 · October 2026

`ant doc` prints the signature and doc comment of a declaration, from the standard library or from
a module. It is what an editor shows on hover, in a terminal. This document is the contract of the
command and the conventions of the comments it prints; section numbers in it refer to
`ant-lang.md`, where section 2 defines a doc comment.

## 1. Command

```
ant doc <name>              a prelude declaration or namespace: Array.map, Array, Result, print
ant doc <file.ant>          the exported declarations of a module
ant doc <file.ant> <name>   one exported declaration of a module: Point, Point.distance
```

A name is `Name` or `Owner.name`, matched as identifiers are, without regard to case. A `var` that
destructures has no name of its own: a module lists it, but a name does not find it. An argument
that ends in `.ant` is a module path; every other first argument is a prelude name. `ant doc` reads
only the file it is given: it does not follow imports and does not run the checker, so a module with
type errors is documented like any other. The file must parse as a module (section 10).

For a single declaration, `ant doc` prints its signature as written in the source, followed by its
doc comment with every non-empty line indented by four spaces. The signature of a `func` runs
through its result type, or its parameters when it has none, of a `type` through its whole
definition, and of a `var` through its annotation, leaving out the body or initializer. A
declaration without a doc comment prints only its signature.

A name without a dot that is a namespace, or a type with functions declared on it, prints its own
declaration, if it has one, as above, and then the signature of every declaration owned by it, one
after another in source order. A namespace of the standard library without a type of its name, such
as `Array` or `Time`, has a doc of its own, which stands in for the declaration: its name, then its
doc indented. A module prints the signature of each exported declaration in source
order.

| Exit status | When                                                                  |
| ----------- | --------------------------------------------------------------------- |
| `0`         | the declaration was found                                             |
| `1`         | there is no such declaration, or no exported one in the module       |
| `2`         | the usage is wrong, or the file could not be read or parsed           |

## 2. Writing doc comments

A doc comment is plain text, read in a terminal as often as rendered by an editor. These are the
conventions the standard library follows, and editors may rely on:

- **The first sentence is a summary** that starts with the declared name, as written in a call:
  `Array.map returns a new array holding f applied to each element of xs.` An editor shows it alone
  in a completion list, so it stands on its own. It ends at the first period followed by a space or
  a line break.
- **Paragraphs** are separated by an empty comment line, `//` with nothing after it.
- **Code** is a run of lines indented by at least one space beyond the comment's own one, which an
  editor shows in a monospaced block, as Ant:

  ```ant
  // Array.map returns a new array holding f applied to each element of xs, in order.
  //
  //     Array.map([1, 2, 3], { x * 2 })   // [2, 4, 6]
  func Array.map[T, U](xs: Array[T], f: func(T): U): Array[U]
  ```

- **Links** are names in brackets, `[Array.filter]`, which an editor may turn into a link to that
  declaration. A bracketed text that names no declaration is left as written.
- **Parameters** are named as declared, as in "panics if n < 0", without markup.

There is no other markup: no headings, emphasis, or tables.
