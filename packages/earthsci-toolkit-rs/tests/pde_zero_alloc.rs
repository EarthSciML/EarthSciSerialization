//! Zero-allocation verification for the Rust PDE tier (ess-mro).
//!
//! The vectorized whole-array stencil evaluator (ess-bdm) is algorithmically
//! N-independent, but it used to allocate `O(#AST-nodes)` arrays per RHS call.
//! diffsol's RHS is in-place (`call_inplace` writes the solver-owned `dy`), so
//! there is no allocation floor: a correct closure can be 100% allocation-free.
//! `RhsScratch` carries the reusable per-variable state arrays, the observed
//! container, and a buffer pool across diffsol steps so the steady-state
//! vectorized RHS performs **zero** heap allocations.
//!
//! This test wraps the global allocator with a counter and asserts that, after
//! a warm-up, a tight loop of vectorized RHS evaluations allocates nothing — at
//! **two** grid sizes, so the property is both N-independent and ≈0 (ess-mro
//! acceptance criterion 1). It lives in its own test binary with a single test
//! so no other test thread perturbs the process-wide allocation counter.

#![cfg(not(target_arch = "wasm32"))]

use std::alloc::{GlobalAlloc, Layout, System};
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

use earthsci_toolkit::load;
use earthsci_toolkit::simulate_array::{ArrayCompiled, RhsStats};

/// A pass-through allocator that counts heap allocations (and reallocations,
/// which may move/grow a block) while `MEASURING` is set. Deallocations are not
/// counted — the metric is "did the hot path request new memory".
struct CountingAlloc;

static ALLOC_COUNT: AtomicUsize = AtomicUsize::new(0);
static MEASURING: AtomicBool = AtomicBool::new(false);

unsafe impl GlobalAlloc for CountingAlloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if MEASURING.load(Ordering::Relaxed) {
            ALLOC_COUNT.fetch_add(1, Ordering::Relaxed);
        }
        unsafe { System.alloc(layout) }
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        unsafe { System.dealloc(ptr, layout) }
    }

    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        if MEASURING.load(Ordering::Relaxed) {
            ALLOC_COUNT.fetch_add(1, Ordering::Relaxed);
        }
        unsafe { System.realloc(ptr, layout, new_size) }
    }
}

#[global_allocator]
static GLOBAL: CountingAlloc = CountingAlloc;

/// A discretized 1-D heat equation on `n` cells (interior + two ghost regions),
/// parameterized by grid size — identical stencil AST at every N. Mirrors
/// `fixtures/arrayop/15_discretized_1d_heat.esm`.
fn heat1d_json(n: usize) -> String {
    const TEMPLATE: &str = r#"{
 "esm": "0.1.0",
 "metadata": {"name": "heat1d_zero_alloc"},
 "models": {
  "Heat1D": {
   "variables": {"u": {"type": "state", "shape": ["i"]}},
   "equations": [
    {
     "lhs": {"op": "arrayop", "args": [], "output_idx": ["i"],
             "expr": {"op": "D", "args": [{"op": "index", "args": ["u", "i"]}], "wrt": "t"},
             "ranges": {"i": [1, __N__]}},
     "rhs": {"op": "arrayop", "args": [], "output_idx": ["i"],
             "ranges": {"i": [1, __N__]},
             "expr": {"op": "index", "args": [
               {"op": "makearray", "args": [],
                "regions": [[[1, __N__]], [[1, 1]], [[__N__, __N__]]],
                "values": [
                  {"op": "*", "args": [25, {"op": "+", "args": [
                    {"op": "index", "args": ["u", {"op": "-", "args": ["i", 1]}]},
                    {"op": "*", "args": [-2, {"op": "index", "args": ["u", "i"]}]},
                    {"op": "index", "args": ["u", {"op": "+", "args": ["i", 1]}]}
                  ]}]},
                  {"op": "*", "args": [25, {"op": "+", "args": [
                    {"op": "*", "args": [-2, {"op": "index", "args": ["u", "i"]}]},
                    {"op": "index", "args": ["u", {"op": "+", "args": ["i", 1]}]}
                  ]}]},
                  {"op": "*", "args": [25, {"op": "+", "args": [
                    {"op": "index", "args": ["u", {"op": "-", "args": ["i", 1]}]},
                    {"op": "*", "args": [-2, {"op": "index", "args": ["u", "i"]}]}
                  ]}]}
                ]},
               "i"]}}
    }
   ]
  }
 }
}"#;
    TEMPLATE.replace("__N__", &n.to_string())
}

fn compile_json(json: &str) -> ArrayCompiled {
    let file = load(json).expect("load json model");
    ArrayCompiled::from_file(&file).expect("compile json model")
}

fn sample_state(n: usize) -> Vec<f64> {
    (0..n).map(|k| (0.7 * k as f64 + 0.3).sin()).collect()
}

#[test]
fn vectorized_rhs_is_allocation_free_in_steady_state() {
    // Counts must match at two grid sizes: both N-independent (equal) and ≈0.
    let mut counts = Vec::new();
    for &n in &[4usize, 8usize] {
        let compiled = compile_json(&heat1d_json(n));
        assert_eq!(compiled.state_variable_names().len(), n);

        let state = sample_state(n);
        let params = compiled.debug_resolve_params(&HashMap::new());
        let mut scratch = compiled.debug_new_scratch();
        let mut dy = vec![0.0f64; n];
        let mut stats = RhsStats::default();

        // Warm-up: the first calls populate the buffer pool and grow each buffer
        // to the output-box capacity. Generous count so capacity is stable.
        for _ in 0..32 {
            compiled.debug_eval_rhs_into(&state, 0.0, &params, &mut dy, &mut scratch, &mut stats);
        }

        // Confirm the spatial derivative actually takes the vectorized path —
        // a zero-allocation oracle fallback would be a meaningless pass.
        let mut probe = RhsStats::default();
        compiled.debug_eval_rhs_into(&state, 0.0, &params, &mut dy, &mut scratch, &mut probe);
        assert_eq!(probe.vectorized_rules, 1, "N={n}: RHS did not vectorize");
        assert_eq!(probe.scalar_rules, 0, "N={n}: RHS fell back to the oracle");

        // Measure: a tight loop of RHS evaluations must request no new memory.
        // Nothing else allocates between the fences (the counter reads are
        // atomic loads and `debug_eval_rhs_into` borrows all its buffers).
        let iters = 200usize;
        let before = ALLOC_COUNT.load(Ordering::Relaxed);
        MEASURING.store(true, Ordering::Relaxed);
        for _ in 0..iters {
            compiled.debug_eval_rhs_into(&state, 0.0, &params, &mut dy, &mut scratch, &mut stats);
        }
        MEASURING.store(false, Ordering::Relaxed);
        let allocs = ALLOC_COUNT.load(Ordering::Relaxed) - before;

        assert_eq!(
            allocs, 0,
            "N={n}: steady-state vectorized RHS allocated {allocs} times over {iters} calls \
             (expected 0 — the scratch/pool must recycle every buffer)"
        );
        counts.push(allocs);
    }

    // N-independence: the (zero) allocation count is identical across grid sizes.
    assert_eq!(
        counts[0], counts[1],
        "allocation count must be independent of grid size N (got {counts:?})"
    );
}
