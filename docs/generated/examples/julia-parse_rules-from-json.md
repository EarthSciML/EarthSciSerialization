# parse_rules from JSON (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
json = """
        {
          "drop_zero": {
            "pattern":     {"op": "+", "args": ["\$a", 0]},
            "replacement": "\$a"
          },
          "self_mul_zero": {
            "pattern":     {"op": "*", "args": ["\$a", 0]},
            "replacement": 0
          }
        }
        """
        obj = JSON3.read(json)
        rules = parse_rules(obj)
        @test length(rules) == 2
        @test rules[1].name == "drop_zero"
        @test rules[2].name == "self_mul_zero"

        # Array form preserves order explicitly.
        json_arr = """
        [
          {"name": "a_first",  "pattern": {"op": "*", "args": ["\$a", 0]}, "replacement": 0},
          {"name": "b_second", "pattern": {"op": "+", "args": ["\$a", 0]}, "replacement": "\$a"}
        ]
        """
        obj2 = JSON3.read(json_arr)
        rules2 = parse_rules(obj2)
        @test [r.name for r in rules2] == ["a_first", "b_second"]
```

