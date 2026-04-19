package esm

// Round-trip coverage for the `call` op + `registered_functions` registry
// introduced in gt-p3ep. The shared cross-binding fixtures live in
// tests/registered_funcs/ and exercise:
//   - pure_math.esm              — scalar pure function invoked from RHS
//   - one_d_interpolator.esm     — 1D interpolator with arg_units + units
//   - two_d_table_lookup.esm     — two registered functions in the same RHS
//
// Handlers bodies are not serialized; the fixtures only declare the calling
// contract.

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func registeredFuncsFixturePath(t *testing.T, name string) string {
	t.Helper()
	wd, err := os.Getwd()
	require.NoError(t, err)
	repoRoot := filepath.Join(wd, "..", "..", "..", "..")
	return filepath.Join(repoRoot, "tests", "registered_funcs", name)
}

func TestRegisteredFuncsFixturesParse(t *testing.T) {
	for _, name := range []string{
		"pure_math.esm",
		"one_d_interpolator.esm",
		"two_d_table_lookup.esm",
	} {
		t.Run(name, func(t *testing.T) {
			parsed, err := Load(registeredFuncsFixturePath(t, name))
			require.NoError(t, err, "Load must accept `call` op + registered_functions")
			require.NotNil(t, parsed)
			require.NotEmpty(t, parsed.RegisteredFunctions,
				"registered_functions must be populated on parse")
		})
	}
}

// TestRegisteredFuncsRoundTrip drives load → save → load → save on each
// fixture and checks that the second and third serialized payloads are
// equal after parsing. Guards against field loss on round-trip.
func TestRegisteredFuncsRoundTrip(t *testing.T) {
	for _, name := range []string{
		"pure_math.esm",
		"one_d_interpolator.esm",
		"two_d_table_lookup.esm",
	} {
		t.Run(name, func(t *testing.T) {
			path := registeredFuncsFixturePath(t, name)

			original, err := Load(path)
			require.NoError(t, err)

			first, err := Save(original)
			require.NoError(t, err)

			reloaded, err := LoadString(first)
			require.NoError(t, err)

			second, err := Save(reloaded)
			require.NoError(t, err)

			var firstVal, secondVal interface{}
			require.NoError(t, json.Unmarshal([]byte(first), &firstVal))
			require.NoError(t, json.Unmarshal([]byte(second), &secondVal))
			assert.Equal(t, firstVal, secondVal,
				"serializer must be idempotent on call + registered_functions")
		})
	}
}

// TestCallOpHandlerIdPreserved anchors the semantic contract that a `call`
// node's handler_id survives a round-trip — the exact invariant the
// registered_functions feature relies on.
func TestCallOpHandlerIdPreserved(t *testing.T) {
	path := registeredFuncsFixturePath(t, "pure_math.esm")

	original, err := Load(path)
	require.NoError(t, err)

	serialized, err := Save(original)
	require.NoError(t, err)

	var payload map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(serialized), &payload))

	models := payload["models"].(map[string]interface{})
	m := models["PureMathCall"].(map[string]interface{})
	eqs := m["equations"].([]interface{})
	rhs := eqs[0].(map[string]interface{})["rhs"].(map[string]interface{})
	assert.Equal(t, "call", rhs["op"])
	assert.Equal(t, "sq", rhs["handler_id"],
		"handler_id must survive load → save")

	regs := payload["registered_functions"].(map[string]interface{})
	sq := regs["sq"].(map[string]interface{})
	sig := sq["signature"].(map[string]interface{})
	assert.Equal(t, float64(1), sig["arg_count"])
}
