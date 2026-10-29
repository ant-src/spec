# `ant doc`

Draft 0.1 · October 2026

`ant doc` prints the signature and doc comment of a declaration, from the standard library or from a
module. It is what an editor shows on hover, in a terminal. This document is the contract of the
command and the conventions of the comments it prints; section numbers in it refer to `ant-lang.md`,
where section 2 defines a doc comment.

## 1. Command

```
ant doc <name>              a prelude declaration or namespace: Array.map, Array, Result, print
ant doc <file.ant>          a module's doc and its exported declarations
ant doc <file.ant> <name>   one exported declaration of a module: Point, Point.distance
```

A name is `Name` or `Owner.name`. `ant doc` looks it up without regard to case, so `array.MAP` finds
`Array.map`, although identifiers in a program are case-sensitive (section 2). A `var` that
destructures has no name of its own: a module lists it, but a name does not find it. An argument
that ends in `.ant` is a module path; every other first argument is a prelude name. `ant doc` reads
only the file it is given: it does not follow imports and does not run the checker, so a module with
type errors is documented like any other. The file must parse as a module (section 10), or as a
declaration file when its name ends in `.d.ant` (section 10, Declaration files): every declaration
of one is visible, so `ant doc` lists them all and a name finds any of them.

For a single declaration, `ant doc` prints its signature as written in the source, followed by its
doc comment with every non-empty line indented by four spaces. The signature of a `func` runs
through its result type, or its parameters when it has none, of a `type` through its whole
definition, and of a `var` through its annotation, leaving out the body or initializer. A
declaration without a doc comment prints only its signature.

A name without a dot that is a namespace (section 10, Namespaces), a type with functions declared
on it included, prints its own declaration, if it has one, as above, and then the signature of every
declaration owned by it, one after another in source order. A namespace that no type declares, such
as `Array` or `Time`, has the doc of its section label (section 10, Declaration files), which stands
in for the declaration: its name, then its doc indented. A module prints its doc, if it has one,
with every non-empty line indented by four spaces, and then the signature of each exported
declaration in source order.

| Exit status | When                                                                     |
| ----------- | ------------------------------------------------------------------------ |
| `0`         | the declaration or the module was found                                  |
| `1`         | there is no such declaration, or a module has no doc and exports nothing |
| `2`         | the usage is wrong, or the file could not be read or parsed              |

## 2. Writing doc comments

A doc comment is plain text, read in a terminal as often as rendered by an editor. These are the
conventions the standard library follows, and editors may rely on:

- **The first sentence is a summary** that starts with the declared name, as written in a call:
  `Array.map returns a new array holding f applied to each element of xs.` An editor shows it alone
  in a completion list, so it stands on its own. It ends at the first period followed by a space or
  a line break.
- **A module doc** starts with a summary of the module in its own terms, since the name a module
  goes by is the one each importer gives it:
  `//! Geometry computes distances and areas on the plane.` It goes on to what a reader of the whole
  module needs: its main types, how its functions fit together, an example of use. A script's doc
  says what the program does and how to run it.
- **A namespace doc** is a section label in a declaration file (section 10, Declaration files): a
  comment line holding the namespace's name alone, an empty comment line, and a paragraph that
  starts with the name, set off from the declarations by blank lines:

  ```ant
  // Os
  //
  // Os holds the process: its arguments, environment, standard streams, exit, and pipes.
  ```

- **Paragraphs** are separated by an empty comment line, `//` or `//!` with nothing after it.
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
