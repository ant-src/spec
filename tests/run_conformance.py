"""Conformance suite runner.

    python3 -I tests/run_conformance.py                 # check the programs parse and carry expectations
    python3 -I tests/run_conformance.py --ant ./ant     # also run each program with an interpreter

Each tests/run/*.ant file is a program whose expected behavior is written in trailing
comments after a "// ---- expected" line:

    // out: <one line of standard output>     (repeat per line; "// out:" alone is an empty line)
    // exit: <status>                          (default 0)
    // err: <text standard error must contain> (repeat as needed)
    // noparse                                 (the program is a syntax error; exit must be 2)
    // args: a b c                             (command-line arguments, split on spaces)

tests/run/lib/ holds modules the programs import; they are not tests. With --ant, the
interpreter is invoked as `<ant> run <file>` from the repository root with a timeout.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(HERE, "run")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from antparse import ParseError, parse  # noqa: E402


def expectations(src):
    out, exit_status, err, noparse, args = [], 0, [], False, []
    for line in src.splitlines():
        if line.startswith("// out:"):
            rest = line[len("// out:"):]
            out.append(rest[1:] if rest.startswith(" ") else rest)
        elif line.startswith("// exit:"):
            exit_status = int(line[len("// exit:"):].strip())
        elif line.startswith("// err:"):
            err.append(line[len("// err:"):].strip())
        elif line.strip() == "// noparse":
            noparse = True
        elif line.startswith("// args:"):
            args = line[len("// args:"):].split()
    return out, exit_status, err, noparse, args


def programs():
    return sorted(fn for fn in os.listdir(RUN) if fn.endswith(".ant"))


def main():
    args = sys.argv[1:]
    ant = args[args.index("--ant") + 1] if "--ant" in args else None
    failures, count = [], 0
    for fn in programs():
        path = os.path.join(RUN, fn)
        src = open(path, encoding="utf-8").read()
        out, status, err, noparse, prog_args = expectations(src)
        count += 1
        if "// ---- expected" not in src:
            failures.append(f"{fn}: no expectations")
            continue
        try:
            parse(src)
            if noparse:
                failures.append(f"{fn}: marked noparse but parses")
        except ParseError as e:
            if not noparse:
                failures.append(f"{fn}: does not parse: {e}")
        if noparse and status != 2:
            failures.append(f"{fn}: a syntax error must exit with 2")
        if ant is None:
            continue
        try:
            proc = subprocess.run([ant, "run", os.path.relpath(path, ROOT)] + prog_args, cwd=ROOT,
                                  capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            failures.append(f"{fn}: timed out")
            continue
        got = proc.stdout.splitlines()
        if got != out:
            failures.append(f"{fn}: stdout\n    expected: {out}\n    got:      {got}")
        if proc.returncode != status:
            failures.append(f"{fn}: exit status expected {status}, got {proc.returncode}")
        for text in err:
            if text not in proc.stderr:
                failures.append(f"{fn}: stderr lacks {text!r}")
    for f in failures:
        print("FAIL", f)
    mode = "parsed and run" if ant else "parsed"
    print(f"{count} programs {mode}, {len(failures)} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
