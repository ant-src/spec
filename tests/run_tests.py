"""Grammar test runner.

    python3 -I tests/run_tests.py

1. tests/ok/*.ant and the conformance programs under tests/run/ must parse as programs.
2. tests/err/*.ant must fail; the first line is `// expect error: <substring>`.
3. Every ```ant block in ../ant-lang.md must parse in spec mode, which allows
   top-level statements and `...` placeholders.
4. A few inline AST assertions.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import antparse  # noqa: E402
from antparse import ParseError, parse, parse_expression  # noqa: E402

failures = []
count = 0


def check(name, ok, detail=""):
    global count
    count += 1
    if not ok:
        failures.append(f"{name}: {detail}")


def run_ok():
    # tests/ok are grammar programs; tests/run and tests/run/lib are the conformance programs,
    # which must keep parsing too (those marked "// noparse" must not).
    for sub in ("ok", "run", os.path.join("run", "lib")):
        d = os.path.join(HERE, sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".ant"):
                continue
            src = open(os.path.join(d, fn), encoding="utf-8").read()
            noparse = "\n// noparse\n" in src
            try:
                parse(src)
                check(f"{sub}/{fn}", not noparse, "marked noparse but parses")
            except ParseError as e:
                check(f"{sub}/{fn}", noparse, str(e))


def run_err():
    d = os.path.join(HERE, "err")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".ant"):
            continue
        src = open(os.path.join(d, fn), encoding="utf-8").read()
        m = re.match(r"// expect error: (.*)", src)
        if not m:
            check(f"err/{fn}", False, "missing '// expect error:' header")
            continue
        want = m.group(1).strip()
        try:
            parse(src)
            check(f"err/{fn}", False, f"parsed, but expected error containing {want!r}")
        except ParseError as e:
            check(f"err/{fn}", want in str(e), f"got {e}, expected {want!r}")


def run_spec_blocks():
    path = os.path.join(ROOT, "ant-lang.md")
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    i = 0
    n = 0
    while i < len(lines):
        if lines[i].strip() == "```ant":
            start = i + 1
            j = start
            while j < len(lines) and lines[j].strip() != "```":
                j += 1
            block = "\n".join(lines[start:j])
            n += 1
            try:
                parse(block, spec=True)
                check(f"spec block at line {start + 1}", True)
            except ParseError as e:
                check(f"spec block at line {start + 1}", False, f"{e} (block line {e.line} = file line {start + e.line})")
            i = j + 1
        else:
            i += 1
    return n


def run_inline():
    def expr(src):
        return parse_expression(src)

    def file(src):
        return parse(src)

    # a newline before "(" starts a new statement
    f = file("func main() {\n  a\n  (b)\n}")
    check("newline before (", f[2][0][4][1] == [("Ident", "a"), ("Paren", ("Ident", "b"))], repr(f))
    # pipe desugars to a call with the left operand first
    check("pipe", expr("a | f(b)") == ("Pipe", ("Ident", "a"), ("Call", ("Ident", "f"), [("Pos", ("Ident", "b"))])))
    # try binds tighter than the pipe
    check("try precedence", expr("try f(x) | g()")[0] == "Pipe" and expr("try f(x) | g()")[1][0] == "Unary")
    # && binds tighter than ||
    e = expr("a && b || c && d")
    check("logical precedence", e[0] == "Or" and e[1][0] == "And" and e[2][0] == "And", repr(e))
    # is binds like a comparison
    e = expr("x is int == true")
    check("is precedence", e == ("Bin", "==", ("Is", ("Ident", "x"), ["int"]), ("Lit", "true")), repr(e))
    # shorthand record entry
    e = expr("Point{ x, y: 2 }")
    check("shorthand", e == ("RecordLit", ["Point"], [("Entry", ("Ident", "x"), ("Ident", "x")), ("Entry", ("Ident", "y"), ("Int", "2"))]), repr(e))
    # a keyword before ":" is a name, and as a map key the string of that word
    e = expr("Map{ type: 1, null: 2 }")
    check("keyword keys", e == ("MapLit", [("Entry", ("String", '"type"'), ("Int", "1")), ("Entry", ("String", '"null"'), ("Int", "2"))]), repr(e))
    # greedy function return type
    f = file("type H = func(int): A | B\n")
    check("greedy return type", f[2][0][3][0] == "TFunc" and f[2][0][3][2][0] == "Union", repr(f))
    # multi-line union with leading |
    f = file("type S = Circle\n  | Rect\n  | Empty\n")
    check("leading | union", f[2][0][3] == ("Union", [("TPath", ["Circle"], []), ("TPath", ["Rect"], []), ("TPath", ["Empty"], [])]), repr(f))
    # else on the next line continues the if
    f = file("func f(a: bool): int {\n  if a { 1 }\n  else { 2 }\n}")
    check("else on next line", f[2][0][4][1][0][0] == "If" and f[2][0][4][1][0][3] is not None, repr(f))
    # return at end of line returns void
    f = file("func f() {\n  return\n  5\n}")
    check("return at eol", f[2][0][4][1] == [("Return", None), ("Int", "5")], repr(f))
    # header: path followed by { ends the header
    f = file("func f() {\n  if u { v }\n}")
    check("header path", f[2][0][4][1][0] == ("If", ("Ident", "u"), ("Block", [("Ident", "v")]), None), repr(f))
    # brace after a type name in a block is a literal, not a lambda
    f = file("func f() {\n  if c { Point{ x: 1.0 } } else { origin }\n}")
    check("literal in block", f[2][0][4][1][0][2][1][0][0] == "RecordLit", repr(f))
    # Map literal
    check("map literal", expr('Map{ "a": 1 }') == ("MapLit", [("Entry", ("String", '"a"'), ("Int", "1"))]))
    # a bare identifier key is its name; a parenthesized one is the variable; shorthand
    e = expr("Map{ name: 1, (name): 2, age }")
    check("map keys", e == ("MapLit", [("Entry", ("String", '"name"'), ("Int", "1")),
                                        ("Entry", ("Paren", ("Ident", "name")), ("Int", "2")),
                                        ("Entry", ("String", '"age"'), ("Ident", "age"))]), repr(e))
    # template with nested braces
    e = expr("`${ Point{ x: 1.0 }.x } and ${ y }`")
    check("template", e[0] == "Template" and len(e[2]) == 2 and e[2][0][0] == "Field", repr(e))
    # array destructuring assignment reinterprets the literal
    f = file("func f() {\n  [a, xs[0], ...rest] = ys\n}")
    check("destructuring assignment", f[2][0][4][1][0] == ("Assign", "=", ("ArrayTarget", [("Place", ("Ident", "a")), ("Place", ("Index", ("Ident", "xs"), ("Int", "0"))), ("Rest", "rest")]), ("Ident", "ys")), repr(f))
    f = file("var [a, { b: [c, _] }] = v\n")
    check("nested destructuring", f[2][0][1] == ("ArrayDestructure", [("Name", "a"), ("Destructure", [("b", ("ArrayDestructure", [("Name", "c"), ("Name", "_")]))])]), repr(f))
    # named arguments
    e = expr('connect(port: 80, host: "x")')
    check("named args", e[2] == [("Named", "port", ("Int", "80")), ("Named", "host", ("String", '"x"'))], repr(e))


def main():
    run_ok()
    run_err()
    n = run_spec_blocks()
    run_inline()
    print(f"{count} checks, {len(failures)} failures ({n} spec blocks)")
    for f in failures:
        print("FAIL", f)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
