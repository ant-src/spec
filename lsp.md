# `ant lsp`

Draft 0.1 · October 2026

`ant lsp` is the language server: it speaks the Language Server Protocol over standard input and
standard output, so that an editor shows the errors of `ant check` as a file is typed, completes
names, shows types and doc comments, finds declarations, and formats with `ant fmt`. This document
is the contract of the command and of what it offers an editor; section numbers in it refer to
`ant-lang.md`, and `fmt.md` and `doc.md` define the formatting and the doc comments it reuses.

## 1. Command

```
ant lsp                     serve the protocol on standard input and standard output
```

`ant lsp` takes no arguments and writes nothing to standard output but protocol messages; what it
logs goes to standard error. It implements version 3.17 of the protocol, with the base protocol's
`Content-Length` framing. It serves one client, the one that started it, and ends when that client
sends `exit`.

| Exit status | When                                                                     |
| ----------- | ------------------------------------------------------------------------ |
| `0`         | the client sent `shutdown` and then `exit`                               |
| `1`         | the client sent `exit` without `shutdown`, or the connection ended first |
| `2`         | the usage is wrong                                                       |

## 2. Documents and programs

The server analyzes a file as the root of a program (section 10): the file and every module it
imports, found as `ant run` finds them, by the path written in the `import` relative to the
importing file. A file opened on its own that is a library is a program whose root is a library, as
`ant run` accepts one. Each open file is the root of its own program, so two files that import the
same module each analyze it in their own program, and a module's errors are reported where it is
imported from as well as in the module itself (section 3). A declaration file (section 10,
Declaration files) is a program of its own: it imports nothing, and its signatures are checked
against the prelude, as `ant check` checks them.

The text of an open document stands in for the file on disk, saved or not. A module that is not open
is read from disk at each analysis, so a change saved by another tool is seen at the next edit, and
at once when the client reports it through `workspace/didChangeWatchedFiles`.

A position is a line and a character. Lines count the line breaks of section 2 (Line endings),
starting at 0. The character counts UTF-16 code units, the protocol's default; when the client
offers `utf-8` among its `positionEncodings`, the server chooses it and the character counts bytes,
which is what `ant check` prints as a column, from 1. Identifiers are ASCII (section 2), so only a
position inside or after a string, a comment, or markup text with other characters differs between
the two.

## 3. Diagnostics

The server reports every error `ant check` reports, with its message, and every error `ant run`
reports before any module runs: the syntax errors of sections 2 and 5, the scope and module errors
of section 10, and the compile errors of sections 4 through 8. Every diagnostic is an error. Its
range starts where `ant check` prints the position and covers the token, name, or expression the
message is about.

A syntax error does not stop the analysis. The server reads past it to the next statement, and
resolves and checks what parsed, so completion, hover, and the outline keep working while a line is
half typed. The diagnostics after a syntax error are those `ant check` would report once it is
fixed, as far as the server can tell; it reports nothing it is not sure of.

The errors of an imported module are reported in that module's own document when it is open. The
importing file gets one diagnostic on the `import`, naming the module and its first error, so that a
broken import is visible from every file that depends on it. An `import` of a module that cannot be
read, of a script, or in a cycle is reported on the `import` as `ant run` reports it.

Diagnostics are published when a document is opened and after each change, and cleared when it is
closed.

## 4. Features

| Request                            | What the server answers                                     |
| ---------------------------------- | ----------------------------------------------------------- |
| `textDocument/completion`          | names, members, fields, arguments, imports, types, markup   |
| `textDocument/hover`               | the kind, type, and doc comment of what is under the cursor |
| `textDocument/signatureHelp`       | the signature of the call the cursor is in                  |
| `textDocument/definition`          | the declaration of a name, a member, a field, or an import  |
| `textDocument/references`          | every use of a declaration in the program                   |
| `textDocument/documentHighlight`   | the uses of a declaration in the document                   |
| `textDocument/rename`              | a new name for a declaration and its uses                   |
| `textDocument/documentSymbol`      | the outline of the module                                   |
| `workspace/symbol`                 | the top-level declarations of the workspace                 |
| `textDocument/formatting`          | `ant fmt`                                                   |
| `textDocument/foldingRange`        | blocks, lists, markup, comment runs, imports                |
| `textDocument/selectionRange`      | the enclosing expressions, statements, and declarations     |
| `textDocument/semanticTokens/full` | what each identifier is                                     |
| `textDocument/inlayHint`           | inferred types                                              |
| `textDocument/codeAction`          | mechanical fixes for diagnostics                            |

**Completion** offers what can be written at the position:

- Where an expression can start: the names in scope, which are the variables declared above in the
  enclosing blocks, the parameters, `x` in a lambda that has one (section 6), the module's own
  declarations, the imported names, and the prelude names, and the keywords that start an expression
  or a statement there.
- After `.` or `?.`: the members of a namespace, an imported module, or a type, which are its
  functions and types; and the fields of a record, including the fields every member of a union
  declares (section 4, Unions) and, after `?.`, the fields of the members that are not `null`.
- After `|`: the functions whose first parameter accepts the type of the left side (section 5,
  Pipes), from the prelude, the imported modules, and the types in scope.
- Inside the arguments of a call: the parameters not yet given, as `name:`, beside the names in
  scope.
- Inside a record literal: the fields not yet given, marking those with a default (section 4, Field
  defaults).
- In an `import`: the paths of the `.ant` files under the importing file's directory, and then the
  module's exports between the braces.
- Where a type is written: the types in scope, the type parameters of the enclosing declarations,
  and the prelude types.
- After `is`: the types in scope and the kinds `is` tests (section 5, `is`).
- In markup (section 5, HTML expressions): element names after `<`, the attributes an element takes
  inside a start tag, and the end tag after `</`.

Each item carries what hover would show, as its detail and documentation: a function's signature, a
variable's type, and the first sentence of the doc comment (`doc.md` section 2). Items are offered
once, unsorted; the editor filters and orders them.

**Hover** shows, for a name: what it is (a variable, parameter, function, type, namespace, or
module), its name, and its type as the checker writes it, narrowed at that use (section 7); for a
function or a type, its signature as written (`doc.md` section 1); and then the doc comment,
rendered by the conventions of `doc.md`: paragraphs separated by empty comment lines, indented lines
as a code block, and a bracketed name as a link where it names a declaration. For a field, hover
shows `name: Type` and the record type it belongs to. For an element in markup, its name, and
whether it is a void element or takes text only. For a literal or an operator, hover shows nothing.

**Signature help** shows, inside the arguments of a call, the signature of the function called, with
each parameter's name, type, and default, and marks the active parameter: the one the cursor's
argument fills, by position or by name (section 6, Calling). Through a pipe the left side fills the
first parameter, so the active parameter counts from the second. A call of a function value shows
its function type, whose parameters have no names.

**Definition** goes from an identifier to the declaration that binds it: a `var`, a parameter, a
`func`, a `type`, an import name, or the lambda whose `x` it is; from a member to its declaration in
the namespace's module or in the prelude; from a field to the field in the type's declaration; from
the path of an `import` to the file. A declaration of the prelude opens the prelude's source,
`prelude.d.ant` (section 10, Declaration files), as a read-only document with the URI
`ant:/prelude.d.ant`, whose text the client fetches with the request `ant/source`, which takes the
URI and returns the text. The server serves that document as it serves a file: hover, definition,
and the other requests work inside it.

**References**, **document highlight**, and **rename** find every use of a declaration in its
program, in every module of it. Renaming an export also renames its uses in every module of the
workspace that imports the declaring module. A rename is refused when the new name is a keyword, a
reserved word, a prelude name, or a name already bound in a scope the renamed binding reaches
(section 10). Fields of a record type and elements of markup are not renamed.

**Document symbols** list the module's imports, its types with their fields and the functions
declared on them nested beneath, its functions, and its top-level variables, in source order, each
with its range and the range of its name. **Workspace symbols** list the top-level declarations of
every `.ant` file under the workspace folders whose name contains the query, matched without regard
to case, as `ant doc` matches a name.

**Formatting** is `ant fmt` (`fmt.md`): the whole document is replaced by its formatted text, and a
document that does not parse is left as it is. There is no range formatting and no formatting as you
type, since the layout of a line depends on the line breaks around it.

**Folding ranges** cover each block, each list spanning more than one line, each element of markup,
each run of comments, and the imports. **Selection ranges** are the expressions, statements, and
declarations enclosing the position, innermost first.

**Semantic tokens** say what each identifier is, so that an editor can color a namespace, a type, a
type parameter, a function, a parameter, a variable, a field, and a markup element and attribute
differently; a declaration is marked as such, and a prelude name as `defaultLibrary`.

**Inlay hints** show the type the checker inferred after the name of a `var` that states none, and
the name of each parameter before a positional argument.

**Code actions** fix what a diagnostic names when the fix is mechanical: they state the type of a
`var` or the return type of a function where a message asks for an annotation (section 4,
Inference), and add the fields a record literal leaves out, with placeholders for their values.

## 5. What `ant lsp` does not do

- It does not run programs. The editor runs `ant run`, and the extension for an editor may offer a
  command for it.
- It does not watch the file system; it relies on the client's notifications.
- It does not format a range or on type (section 4, Formatting).
- It offers no code lens, no call hierarchy, and no type hierarchy.
- It serves one workspace per process; an editor that opens two starts two servers.
