"""Reference parser for Ant, following grammar.ebnf production by production.

It exists to test the grammar: it builds a small tuple-based AST and raises
ParseError on anything the grammar rejects. It knows nothing about types.

    python3 -I tools/antparse.py file.ant        # parse a program
    python3 -I tools/antparse.py --spec file.ant # allow top-level statements and ... placeholders
"""
import sys

KEYWORDS = {
    "break", "continue", "defer", "else", "export", "false", "for", "func", "go",
    "if", "import", "in", "is", "null", "return", "true", "try", "type", "var",
    "void", "while",
}
RESERVED = {
    "as", "async", "await", "catch", "class", "const", "enum", "finally",
    "function", "interface", "let", "match", "switch", "this", "throw",
    "undefined",
}
# Keywords that can end an expression; every other keyword continues the line.
ENDING_KW = {"return", "break", "continue", "true", "false", "null", "void"}
OPS3 = {"..."}
OPS2 = {"?.", "??", "==", "!=", "<=", ">=", "&&", "||", "+=", "-=", "*=", "/=", "%="}
OPS1 = set("+-*/%<>=!|.,:;()[]{}")
ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%="}
ASCII_LETTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
ASCII_DIGITS = set("0123456789")
HEX_DIGITS = set("0123456789abcdefABCDEF")


def is_letter(c):
    return c in ASCII_LETTERS


def is_digit(c):
    return c in ASCII_DIGITS


class ParseError(Exception):
    def __init__(self, line, col, msg):
        super().__init__(f"line {line}:{col}: {msg}")
        self.line, self.col, self.msg = line, col, msg


class Token:
    __slots__ = ("kind", "value", "line", "col", "parts")

    def __init__(self, kind, value, line, col, parts=None):
        self.kind, self.value, self.line, self.col, self.parts = kind, value, line, col, parts

    def __repr__(self):
        if self.kind in ("OP", "KW"):
            return f"'{self.value}'"
        if self.kind == "NEWLINE":
            return "newline"
        if self.kind == "EOF":
            return "end of file"
        return f"{self.kind.lower()} {self.value!r}"


# ----------------------------------------------------------------------------- lexer

class Lexer:
    def __init__(self, src):
        self.src = src
        self.pos = 0
        self.line = 1
        self.col = 1
        self.toks = []

    def error(self, msg):
        raise ParseError(self.line, self.col, msg)

    def peekc(self, k=0):
        i = self.pos + k
        return self.src[i] if i < len(self.src) else ""

    def advance(self, n=1):
        for _ in range(n):
            if self.pos < len(self.src):
                if self.src[self.pos] == "\n":
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
                self.pos += 1

    def emit(self, kind, value, line, col, parts=None):
        self.toks.append(Token(kind, value, line, col, parts))

    def last_continues(self):
        if not self.toks:
            return True
        t = self.toks[-1]
        if t.kind == "NEWLINE":
            return True
        if t.kind == "OP":
            return t.value not in (")", "]", "}", ";", "...")
        if t.kind == "KW":
            return t.value not in ENDING_KW
        return False

    def next_line_continues(self):
        """True when the next non-blank, non-comment line starts with . ?. | or else."""
        i = self.pos
        src = self.src
        while i < len(src):
            c = src[i]
            if c in " \t\r\n":
                i += 1
            elif src.startswith("//", i):
                j = src.find("\n", i)
                i = len(src) if j < 0 else j
            elif src.startswith("/*", i):
                j = src.find("*/", i + 2)
                i = len(src) if j < 0 else j + 2
            else:
                break
        rest = src[i:i + 5]
        if rest.startswith("..."):
            return False
        if rest.startswith(".") or rest.startswith("?.") or rest.startswith("|"):
            return True
        if rest.startswith("else") and (len(rest) == 4 or not (rest[4].isalnum() or rest[4] == "_")):
            return True
        return False

    def tokenize(self):
        src = self.src
        while self.pos < len(src):
            c = src[self.pos]
            line, col = self.line, self.col
            if c == "\n":
                if not self.last_continues() and not self.next_line_continues():
                    self.emit("NEWLINE", "\n", line, col)
                self.advance()
            elif c in " \t\r":
                self.advance()
            elif src.startswith("//", self.pos):
                while self.pos < len(src) and src[self.pos] != "\n":
                    self.advance()
            elif src.startswith("/*", self.pos):
                end = src.find("*/", self.pos + 2)
                if end < 0:
                    self.error("unterminated block comment")
                self.advance(end + 2 - self.pos)
            elif is_digit(c):
                self.number()
            elif is_letter(c) or c == "_":
                self.identifier()
            elif c == '"':
                self.string()
            elif c == "`":
                self.template()
            else:
                three, two = src[self.pos:self.pos + 3], src[self.pos:self.pos + 2]
                if three in OPS3:
                    self.emit("OP", three, line, col); self.advance(3)
                elif two in OPS2:
                    self.emit("OP", two, line, col); self.advance(2)
                elif c in OPS1:
                    self.emit("OP", c, line, col); self.advance()
                else:
                    self.error(f"unexpected character {c!r}")
        if self.toks and self.toks[-1].kind != "NEWLINE":
            self.emit("NEWLINE", "\n", self.line, self.col)
        self.emit("EOF", "", self.line, self.col)
        return self.toks

    def number(self):
        src, start, line, col = self.src, self.pos, self.line, self.col
        kind = "INT"
        if src.startswith(("0x", "0b"), self.pos):
            digits = HEX_DIGITS if src[self.pos + 1] == "x" else set("01")
            self.advance(2)
            self.digits(digits)
        else:
            self.digits(ASCII_DIGITS)
            if self.peekc() == "." and is_digit(self.peekc(1)):
                kind = "FLOAT"
                self.advance()
                self.digits(ASCII_DIGITS)
            if self.peekc() in ("e", "E"):
                kind = "FLOAT"
                self.advance()
                if self.peekc() in ("+", "-"):
                    self.advance()
                self.digits(ASCII_DIGITS)
        nxt = self.peekc()
        if nxt and (is_letter(nxt) or is_digit(nxt) or nxt == "_"):
            self.error("malformed number")
        self.emit(kind, src[start:self.pos], line, col)

    def digits(self, allowed):
        """digit { [ "_" ] digit }: at least one digit, underscores only between digits."""
        if self.peekc() not in allowed or self.peekc() == "":
            self.error("malformed number")
        self.advance()
        while True:
            c = self.peekc()
            if c != "" and c in allowed:
                self.advance()
            elif c == "_" and self.peekc(1) != "" and self.peekc(1) in allowed:
                self.advance(2)
            else:
                return

    def identifier(self):
        src, start, line, col = self.src, self.pos, self.line, self.col
        while self.peekc() and (is_letter(self.peekc()) or is_digit(self.peekc()) or self.peekc() == "_"):
            self.advance()
        word = src[start:self.pos]
        prev = self.toks[-1] if self.toks else None
        if prev is not None and prev.kind == "OP" and prev.value in (".", "?."):
            kind = "IDENT"                      # a field name: any word is a name after a dot (section 2)
        elif word in RESERVED:
            kind = "RESERVED"
        elif word in KEYWORDS:
            kind = "KW"
        else:
            kind = "IDENT"
        self.emit(kind, word, line, col)

    def escape(self, closing):
        """At a backslash: validate the escape and step over it."""
        self.advance()
        c = self.peekc()
        if c in ("n", "t", "r", "\\", '"', "`", "$"):
            self.advance()
        elif c == "u" and self.peekc(1) == "{":
            self.advance(2)
            hexstart = self.pos
            while self.peekc() and self.peekc() in HEX_DIGITS:
                self.advance()
            if self.pos == hexstart or self.peekc() != "}":
                self.error("bad \\u escape")
            value = int(self.src[hexstart:self.pos], 16)
            if value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
                self.error("bad \\u escape: not a Unicode scalar value")
            self.advance()
        else:
            self.error(f"bad escape '\\{c}'")

    def string(self):
        line, col, start = self.line, self.col, self.pos
        self.advance()
        while True:
            c = self.peekc()
            if c == "" or c == "\n":
                raise ParseError(line, col, "unterminated string")
            if c == '"':
                self.advance()
                break
            if c == "\\":
                self.escape('"')
            else:
                self.advance()
        self.emit("STRING", self.src[start:self.pos], line, col)

    def template(self):
        line, col, start = self.line, self.col, self.pos
        parts = []
        self.advance()
        while True:
            c = self.peekc()
            if c == "":
                raise ParseError(line, col, "unterminated template string")
            if c == "`":
                self.advance()
                break
            if c == "\\":
                self.escape("`")
            elif c == "$" and self.peekc(1) == "{":
                self.advance(2)
                parts.append(self.embedded())
            else:
                self.advance()
        self.emit("TEMPLATE", self.src[start:self.pos], line, col, parts)

    def embedded(self):
        """Scan a ${ ... } body to its matching brace; return (line, col, source)."""
        line, col, start = self.line, self.col, self.pos
        depth = 0
        while True:
            c = self.peekc()
            if c == "":
                raise ParseError(line, col, "unterminated ${ in template string")
            if c == "{":
                depth += 1; self.advance()
            elif c == "}":
                if depth == 0:
                    text = self.src[start:self.pos]
                    self.advance()
                    return (line, col, text)
                depth -= 1; self.advance()
            elif c == '"':
                self.string(); self.toks.pop()
            elif c == "`":
                self.template(); self.toks.pop()
            else:
                self.advance()


# ---------------------------------------------------------------------------- parser

class Parser:
    def __init__(self, src, spec=False, line=1, col=1):
        self.spec = spec
        self.toks = Lexer(src).tokenize()
        if line != 1 or col != 1:
            for t in self.toks:
                t.col = t.col + col - 1 if t.line == 1 else t.col
                t.line += line - 1
        self.i = 0
        self.nl = 0        # > 0: newlines are ignored
        self.header = False
        self.funcs = 0     # boundaries entered: function bodies, lambdas, go and defer blocks
        self.loops = 0     # loops entered inside the current boundary
        self.boundary = None   # the innermost boundary: "func", "lambda", "go", or "defer"

    def enter_boundary(self, kind):
        """kind is "func", "lambda", "go", or "defer"; return takes no value inside the last two."""
        saved = (self.funcs, self.loops, self.boundary)
        self.funcs += 1
        self.loops = 0
        self.boundary = kind
        return saved

    def leave_boundary(self, saved):
        self.funcs, self.loops, self.boundary = saved

    def loop_body(self):
        self.loops += 1
        body = self.block()
        self.loops -= 1
        return body

    # --- token helpers
    def raw(self):
        return self.toks[self.i]

    def peek(self):
        while self.nl > 0 and self.toks[self.i].kind == "NEWLINE":
            self.i += 1
        return self.toks[self.i]

    def next(self):
        t = self.peek()
        self.i += 1
        return t

    def at(self, value, kind=None):
        t = self.peek()
        return t.value == value and t.kind in (kind, "OP", "KW") if kind is None else (t.kind == kind and t.value == value)

    def at_kind(self, kind):
        return self.peek().kind == kind

    def error(self, msg, tok=None):
        tok = tok or self.peek()
        if tok.kind == "RESERVED":              # a reserved word anywhere but after a dot or before ':' is the error
            msg = f"reserved word '{tok.value}'"
        raise ParseError(tok.line, tok.col, msg)

    def expect(self, value):
        t = self.peek()
        if t.value != value or t.kind not in ("OP", "KW"):
            self.error(f"expected '{value}', got {t}")
        self.i += 1
        return t

    def expect_ident(self, what="identifier"):
        t = self.peek()
        if t.kind != "IDENT":
            self.error(f"expected {what}, got {t}")
        self.i += 1
        return t.value

    def expect_name(self, what="field name"):
        """A field name before ':': an identifier, a keyword, or a reserved word (section 2)."""
        t = self.peek()
        if t.kind not in ("IDENT", "KW", "RESERVED"):
            self.error(f"expected {what}, got {t}")
        self.i += 1
        return t.value

    def skip_terms(self):
        n = 0
        while self.raw().kind == "NEWLINE" or (self.raw().kind == "OP" and self.raw().value == ";"):
            self.i += 1; n += 1
        return n

    def expect_term(self):
        t = self.raw()
        if t.kind == "EOF" or (t.kind == "OP" and t.value == "}"):
            return
        if self.skip_terms() == 0:
            self.error(f"expected newline or ';', got {t}", t)

    # --- scopes for newline sensitivity and headers
    def enter_list(self):
        saved = (self.nl, self.header)
        self.nl += 1
        self.header = False
        return saved

    def enter_block(self):
        saved = (self.nl, self.header)
        self.nl = 0
        self.header = False
        return saved

    def leave(self, saved):
        self.nl, self.header = saved

    # --- file
    def parse_file(self):
        imports, decls = [], []
        self.skip_terms()
        while self.at("import", "KW"):
            imports.append(self.import_decl())
            self.skip_terms()
        while not self.at_kind("EOF"):
            if self.at("import", "KW"):
                self.error("import must come before declarations")
            t = self.peek()
            if t.kind == "KW" and t.value in ("export", "var", "func", "type"):
                decls.append(self.declaration())
            elif self.spec:
                decls.append(self.expression())
            else:
                self.error(f"expected declaration, got {t}")
            self.expect_term()
            self.skip_terms()
        return ("File", imports, decls)

    def import_decl(self):
        self.expect("import")
        path = self.peek()
        if path.kind != "STRING":
            self.error(f"expected module path string, got {path}")
        self.i += 1
        if self.at_kind("IDENT"):
            pattern = ("Namespace", self.next().value)
        else:
            self.expect("{")
            saved = self.enter_list()
            items = []
            while not self.at("}"):
                name = self.expect_ident("export name")
                alias = None
                if self.at(":"):
                    self.next()
                    alias = self.expect_ident("local name")
                items.append((name, alias))
                if not self.at("}"):
                    self.expect(",")
            self.expect("}")
            self.leave(saved)
            pattern = ("Names", items)
        self.expect_term()
        return ("Import", path.value, pattern)

    def declaration(self):
        exported = False
        if self.at("export", "KW"):
            self.next(); exported = True
        t = self.peek()
        if t.value == "var":
            d = self.var_decl()
        elif t.value == "func":
            d = self.func_decl()
        elif t.value == "type":
            d = self.type_decl()
        else:
            self.error(f"expected var, func, or type after export, got {t}")
        return ("Export", d) if exported else d

    def var_decl(self):
        self.expect("var")
        if self.at("{") or self.at("["):
            target = self.destructure()
            typ = None
        elif self.at_kind("IDENT"):
            target = ("Name", self.next().value)
            typ = None
            if self.at(":"):
                self.next()
                typ = self.type()
        else:
            self.error(f"expected identifier, '{{', or '[' after var, got {self.peek()}")
        self.expect("=")
        return ("Var", target, typ, self.expression())

    def func_decl(self):
        self.expect("func")
        name = self.expect_ident("function name")
        owner = None
        if self.at("."):                       # func Type.name: a function declared on a type (section 6)
            self.next()
            owner, name = name, self.expect_name("function name")
            if self.at("."):
                self.error("a function belongs to one type: func Type.name")
        tparams = self.type_params() if self.at("[") else []
        sig = self.signature()
        saved = self.enter_boundary("func")
        body = self.block()
        self.leave_boundary(saved)
        return ("Func", name, tparams, sig, body) if owner is None else ("TypeFunc", owner, name, tparams, sig, body)

    def type_decl(self):
        self.expect("type")
        name = self.expect_ident("type name")
        tparams = self.type_params() if self.at("[") else []
        self.expect("=")
        return ("Type", name, tparams, self.type())

    def type_params(self):
        self.expect("[")
        saved = self.enter_list()
        params = []
        while not self.at("]"):
            name = self.expect_ident("type parameter")
            bound = None
            if self.at(":"):
                self.next()
                bound = self.type()
            params.append((name, bound))
            if not self.at("]"):
                self.expect(",")
        self.expect("]")
        self.leave(saved)
        return params

    def signature(self):
        self.expect("(")
        saved = self.enter_list()
        params = []
        while not self.at(")"):
            name = self.expect_ident("parameter name")
            self.expect(":")
            typ = self.type()
            default = None
            if self.at("="):
                self.next()
                default = self.expression()
            params.append((name, typ, default))
            if not self.at(")"):
                self.expect(",")
        self.expect(")")
        self.leave(saved)
        ret = None
        if self.at(":"):
            self.next()
            ret = self.type()
        return (params, ret)

    # --- types
    def type(self):
        terms = [self.type_term()]
        while self.at("|"):
            self.next()
            terms.append(self.type_term())
        return terms[0] if len(terms) == 1 else ("Union", terms)

    def type_term(self):
        t = self.peek()
        if t.kind == "KW" and t.value in ("null", "void"):
            self.next()
            return ("TPath", [t.value], [])
        if t.value == "{" and t.kind == "OP":
            return self.record_type()
        if t.kind == "KW" and t.value == "func":
            return self.func_type()
        if t.value == "(" and t.kind == "OP":
            self.next()
            saved = self.enter_list()
            inner = self.type()
            self.expect(")")
            self.leave(saved)
            return inner
        if t.kind != "IDENT":
            self.error(f"expected type, got {t}")
        path = [self.next().value]
        while self.at("."):
            self.next()
            path.append(self.expect_ident())
        args = []
        if self.at("["):
            self.next()
            saved = self.enter_list()
            while not self.at("]"):
                args.append(self.type())
                if not self.at("]"):
                    self.expect(",")
            self.expect("]")
            self.leave(saved)
        return ("TPath", path, args)

    def record_type(self):
        self.expect("{")
        saved = self.enter_list()
        fields = []
        while not self.at("}"):
            name = self.expect_name()
            self.expect(":")
            fields.append((name, self.type()))
            if not self.at("}"):
                self.expect(",")
        self.expect("}")
        self.leave(saved)
        return ("TRecord", fields)

    def func_type(self):
        self.expect("func")
        self.expect("(")
        saved = self.enter_list()
        params = []
        while not self.at(")"):
            typ = self.type()
            name = None
            if self.at(":"):
                if typ[0] == "TPath" and len(typ[1]) == 1 and not typ[2]:
                    name = typ[1][0]
                    self.next()
                    typ = self.type()
                else:
                    self.error("expected ',' or ')' in function type")
            params.append((name, typ))
            if not self.at(")"):
                self.expect(",")
        self.expect(")")
        self.leave(saved)
        self.expect(":")
        return ("TFunc", params, self.type())

    # --- blocks and statements
    def block(self):
        self.expect("{")
        saved = self.enter_block()
        stmts = self.statements()
        self.expect("}")
        self.leave(saved)
        return ("Block", stmts)

    def statements(self):
        stmts = []
        self.skip_terms()
        while not self.at("}"):
            if self.at_kind("EOF"):
                self.error("expected '}', got end of file")
            stmts.append(self.statement())
            if self.at("}"):
                break
            self.expect_term()
            self.skip_terms()
        return stmts

    def statement(self):
        t = self.peek()
        if t.kind == "KW":
            if t.value == "var":
                return self.var_decl()
            if t.value == "type":
                self.error("type declarations are only allowed at the top level")
            if t.value in ("export", "import"):
                self.error(f"'{t.value}' is only allowed at the top level")
        return self.expression()

    # --- expressions
    def expression(self):
        left = self.pipe()
        t = self.peek()
        if t.kind == "OP" and t.value in ASSIGN_OPS:
            self.next()
            if left[0] == "ArrayLit":
                if t.value != "=":
                    self.error("a destructuring target allows only '='", t)
                left = self.as_target(left, t)
            right = self.pipe()
            if self.peek().kind == "OP" and self.peek().value in ASSIGN_OPS:
                self.error("assignment cannot be chained")
            return ("Assign", t.value, left, right)
        return left

    def as_target(self, lit, tok):
        """Reinterpret an array literal on the left of '=' as a destructuring target."""
        items = []
        for i, el in enumerate(lit[1]):
            kind, e = el[0], el[1] if len(el) > 1 else None
            if kind == "Spread":
                if i != len(lit[1]) - 1:
                    self.error("rest must be the last position of a destructuring", tok)
                if e[0] != "Ident":
                    self.error("rest position must be a name", tok)
                items.append(("Rest", e[1]))
            elif kind == "Elem":
                if e[0] in ("Ident", "Field", "Index"):
                    items.append(("Place", e))
                elif e[0] == "ArrayLit":
                    items.append(("Nested", self.as_target(e, tok)))
                else:
                    self.error("destructuring target positions must be assignable places", tok)
            else:
                self.error("destructuring target positions must be assignable places", tok)
        return ("ArrayTarget", items)

    def pipe(self):
        left = self.pipe_operand()
        while self.at("|"):
            self.next()
            right = self.postfix()
            if right[0] != "Call":
                self.error("pipe right side must be a call")
            left = ("Pipe", left, right)
        return left

    def pipe_operand(self):
        left = self.equality()
        if self.at("??"):
            while self.at("??"):
                self.next()
                left = ("Nullish", left, self.equality())
            if self.at("&&") or self.at("||"):
                self.error("'??' cannot mix with '&&' or '||' without parentheses")
            return left
        if self.at("&&") or self.at("||"):
            while self.at("&&"):
                self.next()
                left = ("And", left, self.equality())
            while self.at("||"):
                self.next()
                right = self.equality()
                while self.at("&&"):
                    self.next()
                    right = ("And", right, self.equality())
                left = ("Or", left, right)
            if self.at("??"):
                self.error("'??' cannot mix with '&&' or '||' without parentheses")
        return left

    def equality(self):
        left = self.comparison()
        while self.peek().kind == "OP" and self.peek().value in ("==", "!="):
            op = self.next().value
            left = ("Bin", op, left, self.comparison())
        return left

    def comparison(self):
        left = self.additive()
        while True:
            t = self.peek()
            if t.kind == "OP" and t.value in ("<", "<=", ">", ">="):
                self.next()
                left = ("Bin", t.value, left, self.additive())
            elif t.kind == "KW" and t.value == "is":
                self.next()
                left = ("Is", left, self.is_target())
            else:
                return left

    def is_target(self):
        t = self.peek()
        if t.kind == "KW" and t.value in ("null", "void", "func"):
            self.next()
            return [t.value]
        if t.kind != "IDENT":
            self.error(f"expected type name after 'is', got {t}")
        path = [self.next().value]
        while self.at("."):
            self.next()
            path.append(self.expect_ident())
        return path

    def additive(self):
        left = self.multiplicative()
        while self.peek().kind == "OP" and self.peek().value in ("+", "-"):
            op = self.next().value
            left = ("Bin", op, left, self.multiplicative())
        return left

    def multiplicative(self):
        left = self.unary()
        while self.peek().kind == "OP" and self.peek().value in ("*", "/", "%"):
            op = self.next().value
            left = ("Bin", op, left, self.unary())
        return left

    def unary(self):
        t = self.peek()
        if (t.kind == "OP" and t.value in ("-", "!")) or (t.kind == "KW" and t.value == "try"):
            self.next()
            return ("Unary", t.value, self.unary())
        return self.postfix()

    def postfix(self):
        node = self.primary()
        is_path = node[0] == "Ident"
        path = [node[1]] if is_path else None
        while True:
            t = self.peek()
            if t.kind != "OP":
                return node
            if t.value == ".":
                self.next()
                name = self.expect_ident()
                node = ("Field", node, name)
                if is_path:
                    path.append(name)
                    if self.at("{") and not self.header:
                        return self.brace_lit(path)
            elif t.value == "?.":
                self.next()
                is_path = False
                if self.at("["):
                    self.next()
                    saved = self.enter_list()
                    idx = self.expression()
                    self.expect("]")
                    self.leave(saved)
                    node = ("OptIndex", node, idx)
                elif self.at("("):
                    node = ("OptCall", node, self.call_args())
                else:
                    node = ("OptField", node, self.expect_ident())
            elif t.value == "[":
                self.next()
                is_path = False
                saved = self.enter_list()
                idx = self.expression()
                self.expect("]")
                self.leave(saved)
                node = ("Index", node, idx)
            elif t.value == "(":
                is_path = False
                node = ("Call", node, self.call_args())
            else:
                return node

    def call_args(self):
        self.expect("(")
        saved = self.enter_list()
        args = []
        seen_named = False
        while not self.at(")"):
            e = self.expression()
            if e[0] == "Ident" and self.at(":"):
                self.next()
                args.append(("Named", e[1], self.expression()))
                seen_named = True
            else:
                if seen_named:
                    self.error("positional argument after a named argument")
                args.append(("Pos", e))
            if not self.at(")"):
                self.expect(",")
        self.expect(")")
        self.leave(saved)
        return args

    def primary(self):
        t = self.peek()
        if t.kind in ("INT", "FLOAT", "STRING"):
            self.next()
            return (t.kind.title(), t.value)
        if t.kind == "TEMPLATE":
            self.next()
            exprs = [self.sub_parser(src, line, col).template_expression() for (line, col, src) in t.parts]
            return ("Template", t.value, exprs)
        if t.kind == "IDENT":
            self.next()
            if self.at("{") and not self.header:
                return self.brace_lit([t.value])
            return ("Ident", t.value)
        if t.kind == "KW":
            if t.value in ("true", "false", "null", "void"):
                self.next()
                return ("Lit", t.value)
            if t.value == "func":
                self.next()
                if self.at_kind("IDENT"):
                    self.error("a named function is only allowed at the top level; bind it with var")
                sig = self.signature()
                saved = self.enter_boundary("func")
                body = self.block()
                self.leave_boundary(saved)
                return ("AnonFunc", sig, body)
            if t.value == "if":
                return self.if_expr()
            if t.value == "while":
                self.next()
                cond = self.header_expr()
                return ("While", cond, self.loop_body())
            if t.value == "for":
                return self.for_expr()
            if t.value in ("go", "defer"):
                self.next()
                saved = self.enter_boundary(t.value)
                body = self.block()
                self.leave_boundary(saved)
                return (t.value.title(), body)
            if t.value == "return":
                if self.funcs == 0 and not self.spec:
                    self.error("'return' outside a function")
                self.next()
                r = self.raw()
                if r.kind == "NEWLINE" or (r.kind == "OP" and r.value in (";", "}", ")", "]", ",")) or r.kind == "EOF":
                    return ("Return", None)
                if self.boundary in ("go", "defer"):
                    self.error(f"'return' takes no value in a {self.boundary} block")
                return ("Return", self.expression())
            if t.value in ("break", "continue"):
                if self.loops == 0:
                    self.error(f"'{t.value}' outside a loop in this function, lambda, go, or defer block")
                self.next()
                return (t.value.title(),)
            self.error(f"unexpected {t}")
        if t.kind == "OP":
            if t.value == "{":
                return self.lambda_()
            if t.value == "[":
                return self.array_lit()
            if t.value == "(":
                self.next()
                saved = self.enter_list()
                e = self.expression()
                self.expect(")")
                self.leave(saved)
                return ("Paren", e)
            if t.value == "..." and self.spec:
                self.next()
                return ("Placeholder",)
        self.error(f"unexpected {t}")

    def sub_parser(self, src, line, col):
        """A parser for an interpolated expression, inside the same function and loop as the template."""
        sub = Parser(src, self.spec, line, col)
        sub.funcs, sub.loops, sub.boundary = self.funcs, self.loops, self.boundary
        return sub

    def template_expression(self):
        self.nl += 1
        e = self.expression()
        if not self.at_kind("EOF"):
            self.error(f"unexpected {self.peek()} in template expression")
        return e

    def header_expr(self):
        saved_header = self.header
        self.header = True
        e = self.expression()
        self.header = saved_header
        if not self.at("{"):
            self.error(f"expected '{{' after header, got {self.peek()}")
        return e

    def if_expr(self):
        self.expect("if")
        cond = self.header_expr()
        then = self.block()
        otherwise = None
        if self.at("else", "KW"):
            self.next()
            if self.at("if", "KW"):
                otherwise = self.if_expr()
            else:
                otherwise = self.block()
        return ("If", cond, then, otherwise)

    def for_expr(self):
        self.expect("for")
        if self.at("{") or self.at("["):
            target = self.destructure()
        else:
            target = ("Name", self.expect_ident("loop variable"))
        self.expect("in")
        it = self.header_expr()
        return ("For", target, it, self.loop_body())

    def destructure(self):
        if self.at("["):
            return self.array_destructure()
        self.expect("{")
        saved = self.enter_list()
        fields = []
        while not self.at("}"):
            word = self.peek()
            name = self.expect_name()
            target = None
            if word.kind != "IDENT" and not self.at(":"):
                self.error(f"'{name}' is a keyword and cannot be bound: write {{ {name}: name }}")
            if self.at(":"):
                self.next()
                target = self.target()
            fields.append((name, target))
            if not self.at("}"):
                self.expect(",")
        self.expect("}")
        self.leave(saved)
        return ("Destructure", fields)

    def array_destructure(self):
        self.expect("[")
        saved = self.enter_list()
        items = []
        while not self.at("]"):
            if self.at("..."):
                self.next()
                items.append(("Rest", self.expect_ident("rest name")))
                if not self.at("]"):
                    self.error("rest must be the last position of a destructuring")
                break
            items.append(self.target())
            if not self.at("]"):
                self.expect(",")
        self.expect("]")
        self.leave(saved)
        return ("ArrayDestructure", items)

    def target(self):
        if self.at("{") or self.at("["):
            return self.destructure()
        return ("Name", self.expect_ident("name or destructuring"))

    def placeholder_next(self):
        """After a '...' token: is this a lone placeholder rather than a spread?"""
        r = self.toks[self.i + 1] if self.i + 1 < len(self.toks) else None
        return self.spec and r is not None and ((r.kind == "OP" and r.value in ("}", "]", ",")) or r.kind == "NEWLINE")

    def brace_lit(self, path):
        self.expect("{")
        saved = self.enter_list()
        is_map = path == ["Map"]
        entries = []
        while not self.at("}"):
            if self.at("..."):
                if self.placeholder_next():
                    self.next(); entries.append(("Placeholder",))
                else:
                    self.next()
                    if is_map:
                        self.error("spread is not allowed in a map literal")
                    entries.append(("Spread", self.expression()))
            else:
                word = self.peek()
                if word.kind in ("KW", "RESERVED"):          # a keyword key is a name and needs ':'
                    self.next()
                    if not self.at(":"):
                        self.error(f"'{word.value}' is a keyword: as a key it needs ':'")
                    key = ("Ident", word.value)
                else:
                    key = self.expression()
                if self.at(":"):
                    self.next()
                    value = self.expression()
                    if not is_map and key[0] != "Ident":
                        self.error("record field must be an identifier")
                    if is_map and key[0] == "Ident":
                        key = ("String", '"' + key[1] + '"')     # bare identifier key is its name
                    entries.append(("Entry", key, value))
                else:
                    if key[0] != "Ident":
                        self.error("shorthand entry must be an identifier")
                    name = ("String", '"' + key[1] + '"') if is_map else key
                    entries.append(("Entry", name, key))
            if not self.at("}"):
                self.expect(",")
        self.expect("}")
        self.leave(saved)
        return ("MapLit", entries) if is_map else ("RecordLit", path, entries)

    def array_lit(self):
        self.expect("[")
        saved = self.enter_list()
        elems = []
        while not self.at("]"):
            if self.at("..."):
                if self.placeholder_next():
                    self.next(); elems.append(("Placeholder",))
                else:
                    self.next()
                    elems.append(("Spread", self.expression()))
            else:
                elems.append(("Elem", self.expression()))
            if not self.at("]"):
                self.expect(",")
        self.expect("]")
        self.leave(saved)
        return ("ArrayLit", elems)

    def lambda_(self):
        self.expect("{")
        saved = self.enter_block()
        bound = self.enter_boundary("lambda")
        stmts = self.statements()
        self.leave_boundary(bound)
        self.expect("}")
        self.leave(saved)
        return ("Lambda", stmts)


def parse(src, spec=False):
    return Parser(src, spec).parse_file()


def parse_expression(src):
    p = Parser(src, spec=True)
    e = p.expression()
    p.skip_terms()
    if not p.at_kind("EOF"):
        p.error(f"unexpected {p.peek()}")
    return e


if __name__ == "__main__":
    args = sys.argv[1:]
    spec = "--spec" in args
    paths = [a for a in args if a != "--spec"]
    status = 0
    for path in paths:
        with open(path, encoding="utf-8") as f:
            try:
                parse(f.read(), spec)
                print(f"ok   {path}")
            except ParseError as e:
                print(f"FAIL {path}: {e}")
                status = 1
    sys.exit(status)
