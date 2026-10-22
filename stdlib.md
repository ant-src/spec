# Ant Standard Library: I/O Namespaces

Companion to `ant-lang.md`. The core library, which every program needs, is section 11 of the
specification. The namespaces here talk to the world outside the program, and they follow one rule:
every operation that can fail returns a `Result` with `Error` as the error type, and nothing here
panics on bad input, with two exceptions. `Json.stringify` panics on a value that contains itself,
and `Time`, which is computation rather than I/O, panics where the core library would, on a field
that cannot be, as `int8(300)` does; each such case is marked ◆ in its comment. Blocking calls
block only the calling goroutine (section 9).

A type a namespace declares is written through the namespace, `Json.Value` or `Http.Response`,
since a namespace is a record like an imported module and the bare name would collide with it. A
parameter with a default may be omitted or named at the call, as for a declared function
(section 6, Calling). The namespaces are smaller than the Go packages behind them; a function is
added when a program needs it, and what is here is complete as written.

## File

```
type Handle                                                // opaque: an open file, or a standard stream
type Info = { name: string, size: int, isDir: bool, modified: Time.Instant }

File.read(path: string): Result[string, Error]
File.readBytes(path: string): Result[Array[byte], Error]
File.write(path: string, text: string): Result[void, Error]
File.writeBytes(path: string, bytes: Array[byte]): Result[void, Error]
File.exists(path: string): bool
File.stat(path: string): Result[File.Info, Error]
File.remove(path: string): Result[void, Error]             // one file, or an empty directory
File.removeAll(path: string): Result[void, Error]          // a whole tree; Ok when there is nothing to remove
File.rename(from: string, to: string): Result[void, Error]
File.mkdir(path: string): Result[void, Error]              // with its parents; Ok when it exists
File.tempDir(prefix: string): Result[string, Error]        // a fresh directory under the host's temporary directory
File.list(dir: string): Result[Array[string], Error]       // the names in dir
File.walk(dir: string): Result[Array[string], Error]       // every file below dir, as paths relative to it

File.open(path: string): Result[File.Handle, Error]        // for reading
File.create(path: string): Result[File.Handle, Error]      // for writing; truncates
File.append(path: string): Result[File.Handle, Error]      // for writing at the end; creates
File.readLine(f: File.Handle): Result[string | null, Error]   // null at end of file
File.readAll(f: File.Handle): Result[string, Error]        // the rest of the file
File.writeLine(f: File.Handle, line: string): Result[void, Error]
File.writeText(f: File.Handle, text: string): Result[void, Error]   // writeLine without the newline
File.flush(f: File.Handle): Result[void, Error]            // writes out what is buffered
File.pipe(src: File.Handle, dst: File.Handle): Result[void, Error]  // copies the rest of src to dst
File.close(f: File.Handle): void                           // flushes; nothing on a standard stream
```

`File.list` returns names and `File.walk` paths: `walk` descends into every directory below `dir`,
does not follow symbolic links, lists files and not directories, and returns them in lexical
order. `modified` is the time of the last write. `remove` refuses a directory with entries;
`removeAll` is the recursive form, named so the dangerous one is the longer name.

## Http

```
type Response = { status: int, headers: Map[string, string], body: string }

Http.get(url: string): Result[Http.Response, Error]
Http.post(url: string, body: string, headers: Map[string, string]): Result[Http.Response, Error]
```

## Path

Pure functions over paths in the host's convention: `/` on Unix, `\` and drive letters on Windows.

```
Path.join(parts: Array[string]): string          // joins with the separator and cleans the result
Path.base(p: string): string                     // the last element; "." for ""
Path.dir(p: string): string                      // all but the last element; "." when there is none
Path.ext(p: string): string                      // ".ant", or "" when there is none
Path.clean(p: string): string                    // the shortest equivalent path
Path.isAbs(p: string): bool
Path.abs(p: string): Result[string, Error]       // against the working directory
Path.rel(base: string, target: string): Result[string, Error]   // target as a path from base
```

## Time

Dates and times follow JavaScript's Temporal: exact time and wall-clock time are different types,
a zone is named and carried, calendar arithmetic and exact arithmetic are different operations,
and nothing assumes UTC or the machine's zone. The seven types are opaque, immutable, always valid,
and compared by value. Unlike the other namespaces, `Time` is computation and panics where the core
library would: a field that cannot be is a ◆ like `int8(300)`, while text from the world goes
through the `parse` functions, which return `Result`.

- `Instant` is a moment on the time line: nanoseconds since the Unix epoch, with no zone and no
  calendar.
- `ZonedDateTime` is an instant seen in a zone, the only type that answers "what time is it here".
- `PlainDate`, `PlainTime` and `PlainDateTime` are what a calendar or a clock shows, with no zone:
  a birthday, an alarm, a meeting before its zone is known.
- `Zone` is a zone of the IANA database, such as `Europe/Stockholm`, or a fixed offset, such as
  `+05:30`.
- `Duration` is years, months, weeks, days, hours, minutes, seconds, milliseconds, microseconds
  and nanoseconds, all of one sign, kept as given: 90 minutes stays 90 minutes until
  `roundDuration` balances it.

Four unions name the types a function serves, and three enumerations name its options;
`Time.Hour{}` and `Time.Later{}` are values of them. Every time type has its own tag, so a union of
them is legal and `t is Time.PlainDate` narrows it (`ant-lang.md`, sections 4 and 5). A type
parameter bounded by one of the unions stands for a single member, so a value typed `Time.Dated`
passes to `Time.year` but not to `Time.add` until an `is` test narrows it:

```ant
func bump(t: Time.Dated): Time.Dated {
  var day = Time.duration(days: 1)
  if t is Time.ZonedDateTime { Time.add(t, day) }
  else if t is Time.PlainDate { Time.add(t, day) }
  else { Time.add(t, day) }
}
```

```
type Zone
type Instant
type ZonedDateTime
type PlainDate
type PlainTime
type PlainDateTime
type Duration
type Point = Instant | ZonedDateTime | PlainDate | PlainTime | PlainDateTime
type Wall = ZonedDateTime | PlainDate | PlainTime | PlainDateTime      // the types with fields
type Dated = ZonedDateTime | PlainDate | PlainDateTime                 // the types with a date
type Timed = ZonedDateTime | PlainTime | PlainDateTime                 // the types with a time
type Unit = Year | Month | Week | Day | Hour | Minute | Second | Millisecond | Microsecond | Nanosecond
type Disambiguation = Compatible | Earlier | Later
type RoundingMode = Ceil | Floor | Expand | Trunc | HalfCeil | HalfFloor | HalfExpand | HalfTrunc | HalfEven
```

**Zones.**

```
Time.utc: Time.Zone
Time.zone(id: string): Result[Time.Zone, Error]     // a name of the IANA database in any case, or "+05:30"
Time.localZone(): Time.Zone                         // the host's zone
Time.zoneId(z: Time.Zone): string                   // "Europe/Stockholm", "+05:30"
```

`Time.zone` accepts a name of the IANA database in any letter case, including an alias such as
`Asia/Calcutta`, and an offset `±HH:MM` or `±HH`; anything else, the empty string included, is
`Err`. `zoneId` returns the name as the database spells it, or the offset as `±HH:MM`. Two named
zones are equal when they name the same zone, so `Time.zone("Asia/Calcutta")` equals
`Time.zone("Asia/Kolkata")`; two offset zones are equal when their offsets are; a named zone never
equals an offset zone. `Time.localZone()` is the zone the host's configuration names, from the `TZ`
environment variable first and the system's setting second; when neither names a zone of the
database, it is the fixed offset the host reports at the moment of the call.

**Now, and the epoch.**

```
Time.now(): Time.Instant
Time.nowIn(z: Time.Zone): Time.ZonedDateTime
Time.sleep(ms: int): void                           // blocks the calling goroutine
Time.monotonic(): int                               // milliseconds from an arbitrary origin, for measuring
Time.fromEpochMillis(ms: int): Time.Instant         // ◆ outside the range
Time.fromEpochNanos(ns: int): Time.Instant
Time.epochMillis(t: Time.Instant | Time.ZonedDateTime): int      // rounded down
Time.epochNanos(t: Time.Instant | Time.ZonedDateTime): int       // ◆ outside 1677-09-21 to 2262-04-11
```

Every type holds nanoseconds, and an `Instant` spans 100 million days each way from the epoch,
about 270,000 years, as Temporal's does; the plain types span a day more each way. `epochNanos` as
an `int` reaches only 1677 to 2262 and panics outside, while `epochMillis` always fits.

**Construction.**

```
Time.plainDate(year: int, month: int, day: int): Time.PlainDate                 // ◆ no such date
Time.plainTime(hour: int = 0, minute: int = 0, second: int = 0, millisecond: int = 0,
               microsecond: int = 0, nanosecond: int = 0): Time.PlainTime      // ◆ out of range
Time.plainDateTime(date: Time.PlainDate, time: Time.PlainTime): Time.PlainDateTime
Time.duration(years: int = 0, months: int = 0, weeks: int = 0, days: int = 0, hours: int = 0,
              minutes: int = 0, seconds: int = 0, milliseconds: int = 0, microseconds: int = 0,
              nanoseconds: int = 0): Time.Duration           // ◆ mixed signs, or out of range
```

A constructor rejects what it cannot build: `Time.plainDate(2026, 13, 1)` and
`Time.plainDate(2026, 2, 30)` panic, where `with` and `add` below constrain. A program holding a
year, a month and a day from the world checks the month against 1 to 12 and the day against
`Time.daysInMonth(Time.plainDate(year, month, 1))` before it constructs, or hands the text it was
given to `parsePlainDate`. A `Duration` is bounded as Temporal's: years, months, weeks and days
each below 2^32 in magnitude, and the time part, days included at 24 hours, below 2^53 seconds in
all.

**Text.** Every value renders as its RFC 9557 string, which is ISO 8601 with the zone in brackets,
and parses back from it; `String.from`, template strings and `Json.stringify`, which writes a time
value as a JSON string, all use that form.

```
Time.parseInstant(s: string): Result[Time.Instant, Error]            // 2026-10-22T14:03:05Z
Time.parseZoned(s: string, disambiguation: Time.Disambiguation = Time.Compatible{}):
    Result[Time.ZonedDateTime, Error]                                // 2026-10-22T16:03:05+02:00[Europe/Stockholm]
Time.parsePlainDate(s: string): Result[Time.PlainDate, Error]        // 2026-10-22
Time.parsePlainTime(s: string): Result[Time.PlainTime, Error]        // 14:03:05.123
Time.parsePlainDateTime(s: string): Result[Time.PlainDateTime, Error]   // 2026-10-22T14:03:05
Time.parseDuration(s: string): Result[Time.Duration, Error]          // P1Y2M3DT4H5M6.5S, -PT1H, PT0S
```

The forms: an `Instant` is `2026-10-22T14:03:05.5Z`; a `ZonedDateTime` is
`2024-11-03T01:00:00-04:00[America/New_York]`, offset and zone both, so the exact moment survives
a round trip even where the wall-clock time is ambiguous; a `PlainDate` is `2026-10-22`, a
`PlainTime` `14:03:05`, a `PlainDateTime` `2026-10-22T14:03:05`; a `Duration` is
`P1Y2M3DT4H5M6.5S` with the fields as given, the subsecond fields folded into the seconds, a sign
in front when negative, and `PT0S` when zero; a `Zone` is its identifier. The fractional second is
written to its last nonzero digit and omitted when zero, and a year outside 0 to 9999 as a sign
and six digits.

Parsing takes the date `YYYY-MM-DD`, the time `HH:MM`, `HH:MM:SS` or `HH:MM:SS.F` with up to nine
digits of fraction, `T` or a space between them, `Z` or an offset `±HH:MM`, a zone in brackets and
`[u-ca=iso8601]`, each where its type needs it. `parseInstant` needs a date, a time and `Z` or an
offset, and ignores a bracketed zone. `parseZoned` needs a bracketed zone; with no offset it
resolves the wall-clock time by `disambiguation`, with `Z` it takes the exact moment and shows it
in the zone, and with an offset the zone does not have at that time it is `Err`. The plain parsers
take their own part of a longer string and ignore the rest, so `parsePlainDate` accepts a bare
date or a full zoned string, `parsePlainTime` a bare time or a date and time, and
`parsePlainDateTime` a date and time; none accepts `Z` without a bracketed zone, since `Z` names a
moment, not a wall-clock time. `parseDuration` takes ISO 8601's `PnYnMnWnDTnHnMnS` with an
optional leading sign, where only the last time component may carry a fraction. A string in
another calendar is `Err`.

**Conversion.**

```
Time.inZone(t: Time.Instant, z: Time.Zone): Time.ZonedDateTime
Time.withZone(t: Time.ZonedDateTime, z: Time.Zone): Time.ZonedDateTime      // the same instant in another zone
Time.toZoned(t: Time.PlainDateTime, z: Time.Zone,
             disambiguation: Time.Disambiguation = Time.Compatible{}): Time.ZonedDateTime
Time.possibleInstants(t: Time.PlainDateTime, z: Time.Zone): Array[Time.Instant]   // 0 in a gap, 2 in an overlap, else 1
Time.toInstant(t: Time.ZonedDateTime): Time.Instant
Time.toPlainDate(t: Time.ZonedDateTime | Time.PlainDateTime): Time.PlainDate
Time.toPlainTime(t: Time.ZonedDateTime | Time.PlainDateTime): Time.PlainTime
Time.toPlainDateTime(t: Time.ZonedDateTime): Time.PlainDateTime
Time.startOfDay(t: Time.ZonedDateTime): Time.ZonedDateTime                  // the first instant of its date
Time.zoneOf(t: Time.ZonedDateTime): Time.Zone
Time.offset(t: Time.ZonedDateTime): string                                  // "+02:00"; with seconds when there are some
Time.offsetSeconds(t: Time.ZonedDateTime): int
Time.hoursInDay(t: Time.ZonedDateTime): float64                             // 23.0, 24.0 or 25.0; 23.5 on Lord Howe Island
Time.nextTransition(t: Time.ZonedDateTime): Time.ZonedDateTime | null       // the next change of offset after t
Time.previousTransition(t: Time.ZonedDateTime): Time.ZonedDateTime | null   // the last one before t
```

A wall-clock time in a zone has one instant, none when a daylight-saving change skipped it, or two
when a change repeated it. `disambiguation` says which to take: `Compatible` takes the later
instant in a gap and the earlier in an overlap, which is what the common libraries do; `Earlier`
and `Later` take those. A program that wants to refuse an ambiguous time tests the length of
`possibleInstants`. `startOfDay` is the first instant of the date in the zone, which is not
midnight on a day whose midnight falls in a gap. `nextTransition` is the earliest moment after `t`
at which the zone's offset changes, in the same zone, or `null` when there is none, as for an
offset zone or a zone that has stopped changing; `previousTransition` is the latest before `t`.

**Fields.**

```
Time.year(t: Time.Dated): int
Time.month(t: Time.Dated): int                      // 1 to 12
Time.day(t: Time.Dated): int
Time.dayOfWeek(t: Time.Dated): int                  // 1 Monday to 7 Sunday, as ISO 8601
Time.dayOfYear(t: Time.Dated): int
Time.weekOfYear(t: Time.Dated): int                 // the ISO week, 1 to 53
Time.yearOfWeek(t: Time.Dated): int                 // the year of that week, which differs around New Year
Time.daysInMonth(t: Time.Dated): int
Time.daysInYear(t: Time.Dated): int
Time.inLeapYear(t: Time.Dated): bool
Time.hour(t: Time.Timed): int
Time.minute(t: Time.Timed): int
Time.second(t: Time.Timed): int
Time.millisecond(t: Time.Timed): int
Time.microsecond(t: Time.Timed): int
Time.nanosecond(t: Time.Timed): int

Time.with[T: Time.Wall](t: T, year: int | null = null, month: int | null = null,
                        day: int | null = null, hour: int | null = null, minute: int | null = null,
                        second: int | null = null, millisecond: int | null = null,
                        microsecond: int | null = null, nanosecond: int | null = null,
                        disambiguation: Time.Disambiguation = Time.Compatible{}): T
                                                    // ◆ a field the type lacks
```

`with` returns `t` with the named fields replaced and the rest kept, and constrains the result:
`month: 13` is December and `day: 31` in April is April 30, as Temporal's `overflow: "constrain"`
has it. A `PlainDate` takes the three date fields and a `PlainTime` the six time fields; another
field is ◆. On a `ZonedDateTime` the new wall-clock time is placed in the zone with the value's
own offset when the zone has that offset at the new time, and by `disambiguation` otherwise, so
`Time.with(t, day: 3)` from November 2 in New York keeps `-04:00` and from November 4 keeps
`-05:00`, each a valid offset for the repeated hour of November 3; the plain types ignore
`disambiguation`.

**Arithmetic.**

```
Time.add[T: Time.Point](t: T, d: Time.Duration): T       // ◆ years, months, weeks or days on an Instant
Time.subtract[T: Time.Point](t: T, d: Time.Duration): T  // add(t, negate(d))
Time.until[T: Time.Point](from: T, to: T, largestUnit: Time.Unit | null = null): Time.Duration
                                                         // ◆ a unit the type lacks; Day or larger across zones
Time.since[T: Time.Point](t: T, other: T, largestUnit: Time.Unit | null = null): Time.Duration
                                                         // negate(until(t, other)); ◆ as until
Time.round[T: Time.Instant | Time.Timed](t: T, smallestUnit: Time.Unit, increment: int = 1,
                                         mode: Time.RoundingMode = Time.HalfExpand{}): T
                                                         // ◆ Year, Month or Week; Day on an Instant or a
                                                         // PlainTime; an increment that does not fit
Time.compare[T: Time.Point](a: T, b: T): int             // -1, 0 or 1
```

Years, months, weeks and days are calendar units and move the wall clock; hours and smaller are
exact units and move the instant. `add` applies the calendar part first, years then months with
the day constrained, so August 31 plus a month is September 30, then weeks and days, and the exact
part after. On a `ZonedDateTime` the wall-clock result of the calendar part is placed in the zone
by `Compatible` before the exact part is added, so a day added to 01:00 on the Saturday before a
change in New York is 01:00 on the Sunday with the new offset, and an hour added is the next hour
of the time line, whatever the clock shows. An `Instant` has no calendar, so a duration with
years, months, weeks or days is ◆. A `PlainDate` takes the exact part as whole days of 24 hours
and drops the remainder; a `PlainTime` ignores the calendar part and wraps around the clock; a
`PlainDateTime` takes everything with days of 24 hours.

`until` is the duration from `from` to `to`, negative when `to` is earlier, with its fields
balanced up to `largestUnit`: `Day` gives days and smaller, `Month` gives months, days and
smaller. The default is `Second` for an `Instant`, `Hour` for a `ZonedDateTime` or a `PlainTime`,
and `Day` otherwise. Years and months are counted from `from`, with the day constrained.
`since(t, other)` is `negate(until(t, other))`, the duration from `other` to `t` counted from
`t`, and the two differ for calendar units because the anchor does: with `Month` as the largest
unit, `Time.since(mar31, feb29)` is `P1M` and `Time.until(feb29, mar31)` is `P1M2D`. An `Instant`
or a `PlainTime` has units up to `Hour` and a `PlainDate` units down to `Day`; another
`largestUnit` is ◆, as is `Day` or larger between two `ZonedDateTime`s in different zones, whose
days do not line up. Between two `ZonedDateTime`s in one zone, days are the zone's real days.

`round` rounds to a multiple of `increment` of `smallestUnit` by `mode`, the number rounded
being the nanoseconds since the start of the day for the wall-clock types and since the epoch for
an `Instant`. `increment` must divide the count of `smallestUnit` in the next larger unit, 24
hours, 60 minutes, 60 seconds or 1000 of a subsecond unit, and be smaller than it; for `Day` it is
1. On a `ZonedDateTime` rounding to `Day` chooses between the start of its day and the start of
the next by the fraction of the real day that has passed; rounding to a smaller unit works on the
wall clock and places the result in the zone as `with` does, keeping the offset when the zone has
it.

`compare` orders by instant for `Instant` and `ZonedDateTime`, so two zoned values at one moment
in different zones compare as `0` though they are not `==`, and by fields for the plain types.
`<` and the other comparison operators do not apply to time values (section 5); `Time.compare` is
the ordering.

**Durations.**

```
Time.part(d: Time.Duration, unit: Time.Unit): int   // the field as given
Time.sign(d: Time.Duration): int                    // -1, 0 or 1
Time.negate(d: Time.Duration): Time.Duration
Time.abs(d: Time.Duration): Time.Duration
Time.addDuration(a: Time.Duration, b: Time.Duration): Time.Duration     // ◆ years, months or weeks in either
Time.compareDuration(a: Time.Duration, b: Time.Duration, relativeTo: Time.Dated | null = null): int
                                                    // ◆ years, months or weeks without relativeTo
Time.total(d: Time.Duration, unit: Time.Unit, relativeTo: Time.Dated | null = null): float64
                                                    // ◆ years, months or weeks, in d or as unit, without relativeTo
Time.roundDuration(d: Time.Duration, smallestUnit: Time.Unit | null = null,
                   largestUnit: Time.Unit | null = null, increment: int = 1,
                   mode: Time.RoundingMode = Time.HalfExpand{},
                   relativeTo: Time.Dated | null = null): Time.Duration
                                                    // ◆ no unit given; years, months or weeks without relativeTo
```

Years, months and weeks have no fixed length, so a function that must know theirs takes a
`relativeTo` point and counts from it, and is ◆ without one; a day is 24 hours unless `relativeTo`
is a `ZonedDateTime`, whose days have their daylight-saving hours. `addDuration` sums two
durations without years, months or weeks, days at 24 hours, and balances the result up to the
larger of the two largest units given, so `PT90M` plus `PT30M` is `PT120M` and `P1D` plus `PT25H`
is `P2DT1H`. `compareDuration` orders by length. `total` is the whole duration in `unit` as a
number with a fraction, `PT1H30M` in hours being `1.5`. `roundDuration` balances `d` so that no
field below `largestUnit` exceeds its next unit, and rounds the result to a multiple of
`increment` of `smallestUnit` by `mode`, dropping the smaller fields: `largestUnit` alone
balances, `PT90M` to `Hour` being `PT1H30M`; `smallestUnit` alone rounds; `largestUnit` defaults
to the larger of `d`'s largest nonzero unit and `smallestUnit`, and `increment` follows the rule
of `round`. The rounding modes are Temporal's nine: `Ceil` toward positive infinity, `Floor`
toward negative, `Expand` away from zero, `Trunc` toward zero, the four `Half` forms to the
nearest multiple with a tie resolved as the plain form says, and `HalfEven` to the nearest with a
tie to the even multiple; `HalfExpand`, the default, is what `Math.round` does.

Two durations are `==` when their ten fields are, as given, so `PT90M` and `PT1H30M` are not. For
the other types `==` is the same moment for an `Instant`, the same moment and zone for a
`ZonedDateTime`, the same fields for a plain value, and the same zone for a `Zone`, as above.
Time values are immutable and serve as map keys.

## Os

```
type Output = { status: int, stdout: string, stderr: string }

Os.args(): Array[string]              // the arguments after the program path: `ant run main.ant a b` gives ["a", "b"]
Os.env(name: string): string | null
Os.environ(): Map[string, string]     // every variable
Os.cwd(): Result[string, Error]       // the working directory
Os.exit(status: int): never           // ends the process at once; no deferred block runs, in any goroutine
Os.exec(program: string, args: Array[string] = [], dir: string | null = null,
        env: Map[string, string] | null = null, stdin: string = ""): Result[Os.Output, Error]
Os.stdin(): File.Handle               // the program's standard input
Os.stdout(): File.Handle              // its standard output, which print writes to as well
Os.stderr(): File.Handle              // its standard error
```

`Os.exec` starts `program` with `args` as its arguments and no shell between: `args` arrive as
they are, and `program` is looked up in `PATH` when it has no path separator. The child inherits
the parent's working directory and environment unless `dir` or `env` is given; `env` is the
child's whole environment, so a program that adds one variable starts from `Os.environ()`.
`stdin` is what the child reads. Both outputs are captured whole and taken as text, as `File.read`
takes a file. The call blocks the calling goroutine until the child has exited, and returns `Err`
only when the child could not be started or run to its end: the program is not found, `dir` does
not exist, the host cancelled the run. A nonzero exit is `Ok` with its `status`; a child ended by
a signal has status `-1`. When the host cancels the run, the child is killed.

The three streams are handles, so `File.readLine(Os.stdin())`, `File.readAll(Os.stdin())`,
`File.writeLine(Os.stderr(), msg)` and `File.pipe(Os.stdin(), Os.stdout())` need nothing new.
`Os.stdout()` and `print` write to one buffer, so their output interleaves in program order, and
a read of standard input flushes it first, so a prompt is seen before the program waits.
`File.close` on a stream does nothing. In the REPL standard input belongs to the REPL, and
`Os.stdin()` is at end of file.

## Json

```
type Value = null | bool | float64 | string | Array[Value] | Map[string, Value]

Json.parse(text: string): Result[Json.Value, Error]
Json.stringify[T](value: T): string                     // records as objects without their tag, as String.from would; a time value as its string; ◆ cyclic value
```

`Json.Value` is a recursive alias through an array and a map, which section 4 allows. Numbers parse
as `float64`; a program that needs integers converts with `Math.toInt`, which returns `null`
wherever `int(x)` would panic: a fraction, a value outside the `int` range such as `1e30`, `NaN`, or
an infinity. A decoder into records is a function per type: narrow the tree with `is`, build the
record, and propagate errors with `try`, passing the path along so an error can say
`$.servers[2].port`. Typed decoding through reflection is deferred; the design is in the repository
history at commit 81525d2.

`Json.stringify` renders numbers as `String.from` does, so `1e21` is `1e+21`, and `NaN` and the
infinities, which JSON cannot carry, as `null`. A value that contains itself has no JSON form, so
`Json.stringify` panics with `cyclic value` where `String.from` would print `...`.
