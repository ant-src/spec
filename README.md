# Ant

Specification for Ant, a garbage-collected language with JavaScript-like syntax, static types, and
goroutine-style concurrency.

- [ant-lang.md](ant-lang.md) — the language specification
- [stdlib.md](stdlib.md) — the I/O standard library

## A taste

Expected failures are values: a `Result` whose error type is a flat union of records. `?? return`
exits on a missing key, `try` propagates a nested failure, and `is` narrows the union. The chain in
`explain` has no final `else`, because the checker knows both members are covered.

```ant
type Account = { id: string, balance: int }
type Transfer = { from: string, to: string, amount: int }

type NoAccount = { id: string }
type Insufficient = { id: string, short: int }
type TransferError = NoAccount | Insufficient

func withdraw(accounts: Map[string, Account], id: string, amount: int): Result[void, TransferError] {
  var account = accounts[id] ?? return Result.err(NoAccount{ id })
  if account.balance < amount {
    return Result.err(Insufficient{ id, short: amount - account.balance })
  }
  account.balance -= amount
  Result.ok(void)
}

func transfer(accounts: Map[string, Account], t: Transfer): Result[void, TransferError] {
  var target = accounts[t.to] ?? return Result.err(NoAccount{ id: t.to })
  try withdraw(accounts, t.from, t.amount)
  target.balance += t.amount
  Result.ok(void)
}

func explain(e: TransferError): string {
  if e is NoAccount { `no account named ${e.id}` }
  else if e is Insufficient { `${e.id} is short by ${e.short}` }
}

func main(): void {
  var accounts = Map{
    ada: Account{ id: "ada", balance: 100 },
    bob: Account{ id: "bob", balance: 20 },
  }
  var transfers = [
    Transfer{ from: "ada", to: "bob", amount: 30 },
    Transfer{ from: "bob", to: "ada", amount: 500 },
    Transfer{ from: "ada", to: "eve", amount: 1 },
  ]
  for t in transfers {
    var result = transfer(accounts, t)
    if result is Err { print(explain(result.error)) }
  }
  print(Map.values(accounts) | Array.map({ `${x.id}: ${x.balance}` }))
}
```

```
$ ant run bank.ant
bob is short by 450
no account named eve
["ada: 70", "bob: 50"]
```

Add a third member to the union, `type TransferError = NoAccount | Insufficient | Frozen`, and
change nothing else: `ant check` rejects `explain`, since its chain no longer covers every member,
while `ant run` still runs the program. Types are checked by the editor and CI and erased at run
time.

## License

[MIT](LICENSE)
