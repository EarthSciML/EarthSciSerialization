package esm

// Closed function registry — Go reference implementation (esm-tzp / esm-aia).
//
// Implements the spec-defined closed function set from esm-spec §9.2:
//
//   * datetime.year, month, day, hour, minute, second, day_of_year,
//     julian_day, is_leap_year — proleptic-Gregorian calendar
//     decomposition of an IEEE-754 binary64 UTC scalar (seconds since
//     the Unix epoch, no leap-second consultation).
//   * interp.searchsorted — 1-based search-into-sorted-array
//     (smallest i with xs[i] >= x; out-of-range below → 1, above → N+1).
//
// The set is closed: callers MUST reject any `fn`-op `name` outside this
// list (diagnostic `unknown_closed_function`). New entries require a spec
// rev (esm-spec §9.1).

import (
	"fmt"
	"math"
	"time"
)

// ClosedFunctionError carries the spec-defined diagnostic codes pinned by
// esm-spec §9.1–§9.2 / §9.3:
//
//   - unknown_closed_function     — `fn` name is not in the v0.3.0 set.
//   - closed_function_arity       — wrong number of arguments.
//   - closed_function_overflow    — integer-typed result would overflow Int32.
//   - searchsorted_non_monotonic  — xs is not non-decreasing.
//   - searchsorted_nan_in_table   — xs contains a NaN entry.
type ClosedFunctionError struct {
	Code    string
	Message string
}

func (e *ClosedFunctionError) Error() string {
	return fmt.Sprintf("ClosedFunctionError(%s): %s", e.Code, e.Message)
}

func newClosedFunctionError(code, msg string) *ClosedFunctionError {
	return &ClosedFunctionError{Code: code, Message: msg}
}

// closedFunctionNames is the v0.3.0 closed function set. Bindings MUST
// reject any `fn` op `name` not in this set with diagnostic
// `unknown_closed_function`.
var closedFunctionNames = map[string]struct{}{
	"datetime.year":         {},
	"datetime.month":        {},
	"datetime.day":          {},
	"datetime.hour":         {},
	"datetime.minute":       {},
	"datetime.second":       {},
	"datetime.day_of_year":  {},
	"datetime.julian_day":   {},
	"datetime.is_leap_year": {},
	"interp.searchsorted":   {},
}

// ClosedFunctionNames returns the v0.3.0 closed function set as a sorted
// slice. Useful for error messages and round-trip validation tests.
func ClosedFunctionNames() []string {
	out := make([]string, 0, len(closedFunctionNames))
	for k := range closedFunctionNames {
		out = append(out, k)
	}
	// Stable order for diagnostic output.
	for i := 1; i < len(out); i++ {
		for j := i; j > 0 && out[j-1] > out[j]; j-- {
			out[j-1], out[j] = out[j], out[j-1]
		}
	}
	return out
}

// IsClosedFunction reports whether name is in the v0.3.0 closed registry.
func IsClosedFunction(name string) bool {
	_, ok := closedFunctionNames[name]
	return ok
}

// EvaluateClosedFunction dispatches a closed function call. `name` is the
// dotted-module spec name (e.g. "datetime.julian_day"); `args` is a slice
// of evaluated argument values. Integer-typed results are returned as
// int32 to make the integer contract explicit; float-typed results are
// float64. For interp.searchsorted, the second argument MUST be the
// inline table extracted from the `const`-op AST node — the caller is
// responsible for that extraction.
//
// Returns *ClosedFunctionError on contract violations.
func EvaluateClosedFunction(name string, args []interface{}) (interface{}, error) {
	if !IsClosedFunction(name) {
		return nil, newClosedFunctionError("unknown_closed_function",
			fmt.Sprintf("`fn` name %q is not in the v0.3.0 closed function registry "+
				"(esm-spec §9.2). Adding a primitive requires a spec rev.", name))
	}

	switch name {
	case "datetime.year":
		if err := expectArity(name, args, 1); err != nil {
			return nil, err
		}
		t, err := toUnixDateTime(args[0])
		if err != nil {
			return nil, err
		}
		return checkInt32(name, int64(t.Year()))
	case "datetime.month":
		if err := expectArity(name, args, 1); err != nil {
			return nil, err
		}
		t, err := toUnixDateTime(args[0])
		if err != nil {
			return nil, err
		}
		return int32(t.Month()), nil
	case "datetime.day":
		if err := expectArity(name, args, 1); err != nil {
			return nil, err
		}
		t, err := toUnixDateTime(args[0])
		if err != nil {
			return nil, err
		}
		return int32(t.Day()), nil
	case "datetime.hour":
		if err := expectArity(name, args, 1); err != nil {
			return nil, err
		}
		t, err := toUnixDateTime(args[0])
		if err != nil {
			return nil, err
		}
		return int32(t.Hour()), nil
	case "datetime.minute":
		if err := expectArity(name, args, 1); err != nil {
			return nil, err
		}
		t, err := toUnixDateTime(args[0])
		if err != nil {
			return nil, err
		}
		return int32(t.Minute()), nil
	case "datetime.second":
		if err := expectArity(name, args, 1); err != nil {
			return nil, err
		}
		t, err := toUnixDateTime(args[0])
		if err != nil {
			return nil, err
		}
		return int32(t.Second()), nil
	case "datetime.day_of_year":
		if err := expectArity(name, args, 1); err != nil {
			return nil, err
		}
		t, err := toUnixDateTime(args[0])
		if err != nil {
			return nil, err
		}
		return int32(t.YearDay()), nil
	case "datetime.julian_day":
		if err := expectArity(name, args, 1); err != nil {
			return nil, err
		}
		f, ok := toFloat64(args[0])
		if !ok {
			return nil, newClosedFunctionError("closed_function_arity",
				fmt.Sprintf("%s: argument must be numeric, got %T", name, args[0]))
		}
		return datetimeJulianDay(f), nil
	case "datetime.is_leap_year":
		if err := expectArity(name, args, 1); err != nil {
			return nil, err
		}
		t, err := toUnixDateTime(args[0])
		if err != nil {
			return nil, err
		}
		if isLeapYear(t.Year()) {
			return int32(1), nil
		}
		return int32(0), nil
	case "interp.searchsorted":
		if err := expectArity(name, args, 2); err != nil {
			return nil, err
		}
		x, ok := toFloat64(args[0])
		if !ok {
			return nil, newClosedFunctionError("closed_function_arity",
				fmt.Sprintf("%s: first argument (x) must be numeric, got %T", name, args[0]))
		}
		xs, err := toFloat64Slice(name, args[1])
		if err != nil {
			return nil, err
		}
		return interpSearchsorted(name, x, xs)
	}
	// Unreachable — IsClosedFunction guarded above.
	return nil, newClosedFunctionError("unknown_closed_function",
		fmt.Sprintf("internal: `fn` name %q is in the registry but has no dispatch arm", name))
}

// expectArity returns ClosedFunctionError(closed_function_arity) when the
// argument count differs from `n`.
func expectArity(name string, args []interface{}, n int) error {
	if len(args) != n {
		return newClosedFunctionError("closed_function_arity",
			fmt.Sprintf("%s expects %d argument(s), got %d", name, n, len(args)))
	}
	return nil
}

// checkInt32 range-checks an integer-typed closed-function result. The spec
// pins integer outputs to signed 32-bit; e.g. datetime.year of an absurd
// `t_utc` could overflow.
func checkInt32(name string, v int64) (int32, error) {
	if v < math.MinInt32 || v > math.MaxInt32 {
		return 0, newClosedFunctionError("closed_function_overflow",
			fmt.Sprintf("%s: result %d overflows Int32", name, v))
	}
	return int32(v), nil
}

// toUnixDateTime converts a UTC scalar time (seconds since Unix epoch) to
// time.Time at UTC. The spec pins floor-divmod by 86400 for the
// (date, time-of-day) split; time.Unix already does this with the
// proleptic-Gregorian calendar. Float fractional seconds are converted to
// nanoseconds before construction.
func toUnixDateTime(v interface{}) (time.Time, error) {
	f, ok := toFloat64(v)
	if !ok {
		return time.Time{}, newClosedFunctionError("closed_function_arity",
			fmt.Sprintf("argument must be numeric, got %T", v))
	}
	// Split into integer seconds and fractional nanoseconds. Use
	// math.Floor so that negative-fractional inputs ("0.5 seconds before
	// epoch") follow Python-style floored division per esm-spec §9.2.
	whole := math.Floor(f)
	frac := f - whole
	sec := int64(whole)
	nsec := int64(math.Round(frac * 1e9))
	if nsec >= 1e9 {
		sec++
		nsec -= 1e9
	}
	return time.Unix(sec, nsec).UTC(), nil
}

// datetimeJulianDay computes the continuous Julian Day Number (JDN) for a
// UTC scalar time, including the fractional time-of-day offset relative
// to noon UTC. Uses the Fliegel–van Flandern (1968) integer formula plus
// `(time_of_day_seconds − 43200) / 86400`, ≤ 1 ulp agreement to the spec
// reference per esm-spec §9.2.1.
func datetimeJulianDay(tUTC float64) float64 {
	t, _ := toUnixDateTime(tUTC)
	y := t.Year()
	m := int(t.Month())
	d := t.Day()
	mAdj := (m - 14) / 12
	jdn := (1461*(y+4800+mAdj))/4 +
		(367*(m-2-12*mAdj))/12 -
		(3*((y+4900+mAdj)/100))/4 +
		d - 32075
	// JDN counts noon-to-noon; convert time-of-day seconds (since 00:00 UTC)
	// to a fractional offset relative to noon.
	secondsInDay := math.Mod(tUTC, 86400.0)
	if secondsInDay < 0 {
		secondsInDay += 86400.0
	}
	return float64(jdn) + (secondsInDay-43200.0)/86400.0
}

// isLeapYear: proleptic-Gregorian. Pure integer arithmetic, exact zero
// error vs. the spec.
func isLeapYear(y int) bool {
	return (y%4 == 0 && y%100 != 0) || y%400 == 0
}

// interpSearchsorted implements `interp.searchsorted` per esm-spec §9.2.2:
// 1-based, left-side bias (smallest i with xs[i] ≥ x), out-of-range below
// → 1, above → N+1, NaN x → N+1, NaN entries in xs → error, non-monotonic
// xs → error.
func interpSearchsorted(name string, x float64, xs []float64) (int32, error) {
	n := len(xs)
	if n == 0 {
		// Empty table: extends "above-range → N+1" rule to N=0; the only
		// consistent extension that composes with `index`.
		return int32(1), nil
	}
	// Validate monotonicity + NaN-in-table once per call.
	for i := 0; i < n; i++ {
		if math.IsNaN(xs[i]) {
			return 0, newClosedFunctionError("searchsorted_nan_in_table",
				fmt.Sprintf("%s: xs[%d] is NaN; NaN entries in xs are forbidden", name, i+1))
		}
		if i > 0 && xs[i] < xs[i-1] {
			return 0, newClosedFunctionError("searchsorted_non_monotonic",
				fmt.Sprintf("%s: xs is not non-decreasing (xs[%d]=%g < xs[%d]=%g)",
					name, i+1, xs[i], i, xs[i-1]))
		}
	}
	// NaN x → N+1 ("greater than every finite element").
	if math.IsNaN(x) {
		return checkInt32(name, int64(n+1))
	}
	// Linear scan: spec mandates left-side bias on duplicates; binary search
	// would also work but the §9.2 inline-cap pins tables to ≤ 1024 entries.
	for i := 0; i < n; i++ {
		if xs[i] >= x {
			return checkInt32(name, int64(i+1))
		}
	}
	return checkInt32(name, int64(n+1))
}

// toFloat64Slice extracts a []float64 from an evaluated `const`-op array.
// Accepts []interface{} (post-parse) and []float64 (programmatically built).
// JSON literal "NaN" surfaces as the string "NaN" — the harness handles
// that via the canonical fixture path; this helper accepts numeric entries
// only, leaving NaN injection to higher layers.
func toFloat64Slice(name string, v interface{}) ([]float64, error) {
	switch xs := v.(type) {
	case []float64:
		out := make([]float64, len(xs))
		copy(out, xs)
		return out, nil
	case []interface{}:
		out := make([]float64, len(xs))
		for i, e := range xs {
			f, ok := toFloat64(e)
			if !ok {
				// Allow case-insensitive "NaN" string for the conformance
				// fixtures that JSON-encode NaN as a string literal.
				if s, isStr := e.(string); isStr && (s == "NaN" || s == "nan" || s == "NAN") {
					out[i] = math.NaN()
					continue
				}
				return nil, newClosedFunctionError("closed_function_arity",
					fmt.Sprintf("%s: xs[%d] is not numeric (%T)", name, i+1, e))
			}
			out[i] = f
		}
		return out, nil
	default:
		return nil, newClosedFunctionError("closed_function_arity",
			fmt.Sprintf("%s: xs argument must be an array, got %T", name, v))
	}
}
