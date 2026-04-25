/**
 * Closed function registry — TypeScript binding for esm-spec §9.2.
 *
 * v0.3.0 set:
 *  - datetime.year / .month / .day / .hour / .minute / .second
 *  - datetime.day_of_year / .julian_day / .is_leap_year
 *  - interp.searchsorted
 *
 * The dispatch table is closed by construction. `fn`-op nodes whose name
 * is not in this set MUST be rejected with diagnostic
 * `unknown_closed_function`.
 *
 * Boundary semantics, tolerances, and error codes match the Julia
 * reference implementation (packages/EarthSciSerialization.jl/src/registered_functions.jl).
 */

/** Stable diagnostic codes raised by the registry. */
export type ClosedFunctionErrorCode =
  | 'unknown_closed_function'
  | 'closed_function_arity'
  | 'closed_function_overflow'
  | 'searchsorted_non_monotonic'
  | 'searchsorted_nan_in_table'

/**
 * Error thrown by closed function dispatch and load-time table validation.
 * `code` identifies the spec-pinned diagnostic; cross-binding harnesses
 * compare against this exact string.
 */
export class ClosedFunctionError extends Error {
  constructor(public code: ClosedFunctionErrorCode, message: string) {
    super(`[${code}] ${message}`)
    this.name = 'ClosedFunctionError'
  }
}

/** Names that bindings MUST recognize. */
export const CLOSED_FUNCTION_NAMES: readonly string[] = Object.freeze([
  'datetime.year',
  'datetime.month',
  'datetime.day',
  'datetime.hour',
  'datetime.minute',
  'datetime.second',
  'datetime.day_of_year',
  'datetime.julian_day',
  'datetime.is_leap_year',
  'interp.searchsorted',
])

const SECONDS_PER_DAY = 86400
// Days from proleptic-Gregorian year 0000-01-01 to Unix epoch 1970-01-01.
// Matches the Julia ref (Date(1970,1,1) - Date(0,1,1)).value = 719528.
const UNIX_EPOCH_DAYS_FROM_YEAR_ZERO = 719528

const INT32_MIN = -2147483648
const INT32_MAX = 2147483647

function checkInt32(name: string, v: number): number {
  if (!Number.isFinite(v) || v < INT32_MIN || v > INT32_MAX) {
    throw new ClosedFunctionError(
      'closed_function_overflow',
      `${name} result ${v} overflows signed 32-bit integer range`,
    )
  }
  return v
}

/**
 * Floor-division of two integers (matches Math.floor semantics for
 * negative dividends, which Julia's `fld` and Python's `//` also use).
 */
function fdiv(a: number, b: number): number {
  return Math.floor(a / b)
}
function fmod(a: number, b: number): number {
  // Euclidean mod with positive result for positive b.
  const r = a - fdiv(a, b) * b
  return r
}

/**
 * Decompose UTC seconds-since-epoch (IEEE-754 binary64, no leap seconds)
 * into proleptic-Gregorian Y/M/D/h/m/s plus day_of_year and julian_day.
 *
 * Pure integer arithmetic for Y/M/D/h/m/s — bit-exact across bindings
 * given the same input. The fractional-day component for `julian_day` is
 * the only floating-point step.
 */
interface DateParts {
  year: number
  month: number
  day: number
  hour: number
  minute: number
  second: number
  dayOfYear: number
  julianDay: number
  isLeapYear: number
}

function isLeapProleptic(y: number): boolean {
  return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0
}

const DAYS_BEFORE_MONTH_NORMAL = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
const DAYS_BEFORE_MONTH_LEAP = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

/** Convert "days since 0000-01-01" (proleptic Gregorian) to Y/M/D. */
function daysToYMD(dayOfEra: number): { year: number; month: number; day: number } {
  // Algorithm follows Howard Hinnant's date / civil_from_days, adjusted
  // so day 0 = 0000-01-01. Equivalent to the Julia Date arithmetic used
  // in the reference implementation.
  // Shift so day 0 is the start of year 0 in Hinnant's epoch (0000-03-01).
  // Hinnant's days[z] is days since 0000-03-01.
  // We have dayOfEra = days since 0000-01-01.
  // 0000-01-01 → 0000-03-01 is +60 days (year 0 is leap by Gregorian rule? 0%400==0 → yes).
  // But Hinnant's algorithm operates on integer-floor arithmetic; do this carefully.
  // To keep cross-binding parity with Julia (which uses Dates.Date arithmetic),
  // we replicate via month-table lookup walking centuries.

  // Compute year by Hinnant's formula directly:
  const z = dayOfEra - 60 // days since 0000-03-01
  const era = fdiv(z >= 0 ? z : z - 146096, 146097)
  const doe = z - era * 146097 // [0, 146096]
  const yoe = fdiv(doe - fdiv(doe, 1460) + fdiv(doe, 36524) - fdiv(doe, 146096), 365)
  const y = yoe + era * 400
  const doy = doe - (365 * yoe + fdiv(yoe, 4) - fdiv(yoe, 100))
  const mp = fdiv(5 * doy + 2, 153)
  const d = doy - fdiv(153 * mp + 2, 5) + 1
  const m = mp < 10 ? mp + 3 : mp - 9
  const year = m <= 2 ? y + 1 : y
  return { year, month: m, day: d }
}

function dayOfYear(year: number, month: number, day: number): number {
  const tbl = isLeapProleptic(year) ? DAYS_BEFORE_MONTH_LEAP : DAYS_BEFORE_MONTH_NORMAL
  return tbl[month - 1] + day
}

/**
 * Julian Day Number (continuous including fractional day-of-day).
 * 1970-01-01T00:00:00 UTC → 2440587.5.
 */
function julianDayValue(tUtc: number): number {
  // Constant offset by Unix-epoch JDN. The only float op is the divide.
  return 2440587.5 + tUtc / SECONDS_PER_DAY
}

function decomposeUtcSeconds(tUtc: number): DateParts {
  if (!Number.isFinite(tUtc)) {
    throw new ClosedFunctionError(
      'closed_function_overflow',
      `datetime input ${tUtc} is not a finite value`,
    )
  }
  const totalDays = fdiv(tUtc, SECONDS_PER_DAY) // floor seconds → days
  const remSeconds = tUtc - totalDays * SECONDS_PER_DAY // [0, 86400)
  const dayOfEra = totalDays + UNIX_EPOCH_DAYS_FROM_YEAR_ZERO

  const { year, month, day } = daysToYMD(dayOfEra)
  // remSeconds may be fractional; Y/M/D/h/m/s integer outputs are taken
  // from the floored second count.
  const wholeRem = Math.floor(remSeconds)
  const hour = fdiv(wholeRem, 3600)
  const minute = fdiv(wholeRem - hour * 3600, 60)
  const second = wholeRem - hour * 3600 - minute * 60

  const doy = dayOfYear(year, month, day)
  const jdn = julianDayValue(tUtc)
  const isLeap = isLeapProleptic(year) ? 1 : 0

  return {
    year,
    month,
    day,
    hour,
    minute,
    second,
    dayOfYear: doy,
    julianDay: jdn,
    isLeapYear: isLeap,
  }
}

function requireArity(name: string, args: unknown[], expected: number): void {
  if (args.length !== expected) {
    throw new ClosedFunctionError(
      'closed_function_arity',
      `${name} expects ${expected} argument(s); got ${args.length}`,
    )
  }
}

function asNumber(name: string, v: unknown, idx = 0): number {
  if (typeof v === 'number') return v
  throw new ClosedFunctionError(
    'closed_function_arity',
    `${name} argument #${idx + 1} must be a scalar number; got ${typeof v}`,
  )
}

/**
 * Validate a `searchsorted` xs table. Throws on NaN entries or
 * non-monotonic order. Empty arrays are rejected with the spec arity
 * code (the registry requires N ≥ 1).
 */
export function validateSearchsortedTable(xs: readonly number[], where = 'interp.searchsorted'): void {
  if (xs.length === 0) {
    throw new ClosedFunctionError(
      'closed_function_arity',
      `${where}: xs table is empty (must have at least one entry)`,
    )
  }
  for (let i = 0; i < xs.length; i++) {
    if (Number.isNaN(xs[i])) {
      throw new ClosedFunctionError(
        'searchsorted_nan_in_table',
        `${where}: xs[${i + 1}] is NaN`,
      )
    }
  }
  for (let i = 1; i < xs.length; i++) {
    if (xs[i] < xs[i - 1]) {
      throw new ClosedFunctionError(
        'searchsorted_non_monotonic',
        `${where}: xs is not non-decreasing at index ${i + 1} (xs[${i + 1}]=${xs[i]} < xs[${i}]=${xs[i - 1]})`,
      )
    }
  }
}

/**
 * Smallest 1-based `i` with `xs[i] ≥ x` (Julia `searchsortedfirst`
 * semantics). NaN x → N+1. xs MUST be pre-validated; the table is
 * inspected at every call so the caller can pass a fresh array each
 * scenario without bookkeeping (validation is cheap relative to the
 * dispatch overhead).
 */
export function searchsortedFirst(x: number, xs: readonly number[]): number {
  validateSearchsortedTable(xs)
  if (Number.isNaN(x)) return xs.length + 1
  // Binary search for the first index with xs[i] >= x (1-based output).
  let lo = 0
  let hi = xs.length // exclusive
  while (lo < hi) {
    const mid = (lo + hi) >>> 1
    if (xs[mid] >= x) {
      hi = mid
    } else {
      lo = mid + 1
    }
  }
  return lo + 1
}

/**
 * Resolve a closed-function name + already-evaluated positional args
 * into a scalar result. `args` semantics:
 *
 *  - datetime.* take a single scalar `t_utc` (number).
 *  - interp.searchsorted takes [scalar x, number[] xs]. The xs array
 *    MUST be a plain array of numbers (the AST evaluator extracts it
 *    from a `const`-op child without numeric-collapsing it).
 *
 * Unknown names raise `unknown_closed_function`.
 */
export function dispatchClosedFunction(name: string, args: unknown[]): number {
  switch (name) {
    case 'datetime.year': {
      requireArity(name, args, 1)
      return checkInt32(name, decomposeUtcSeconds(asNumber(name, args[0])).year)
    }
    case 'datetime.month': {
      requireArity(name, args, 1)
      return decomposeUtcSeconds(asNumber(name, args[0])).month
    }
    case 'datetime.day': {
      requireArity(name, args, 1)
      return decomposeUtcSeconds(asNumber(name, args[0])).day
    }
    case 'datetime.hour': {
      requireArity(name, args, 1)
      return decomposeUtcSeconds(asNumber(name, args[0])).hour
    }
    case 'datetime.minute': {
      requireArity(name, args, 1)
      return decomposeUtcSeconds(asNumber(name, args[0])).minute
    }
    case 'datetime.second': {
      requireArity(name, args, 1)
      return decomposeUtcSeconds(asNumber(name, args[0])).second
    }
    case 'datetime.day_of_year': {
      requireArity(name, args, 1)
      return decomposeUtcSeconds(asNumber(name, args[0])).dayOfYear
    }
    case 'datetime.julian_day': {
      requireArity(name, args, 1)
      return decomposeUtcSeconds(asNumber(name, args[0])).julianDay
    }
    case 'datetime.is_leap_year': {
      requireArity(name, args, 1)
      return decomposeUtcSeconds(asNumber(name, args[0])).isLeapYear
    }
    case 'interp.searchsorted': {
      requireArity(name, args, 2)
      const x = asNumber(name, args[0], 0)
      const xs = args[1]
      if (!Array.isArray(xs) || !xs.every((v) => typeof v === 'number')) {
        throw new ClosedFunctionError(
          'closed_function_arity',
          `${name}: xs (arg 2) must be a const-array of numbers`,
        )
      }
      return searchsortedFirst(x, xs as number[])
    }
    default:
      throw new ClosedFunctionError(
        'unknown_closed_function',
        `'${name}' is not in the v0.3.0 closed function registry`,
      )
  }
}

/** Suppress unused-symbol lint for fmod (kept for parity). */
void fmod
