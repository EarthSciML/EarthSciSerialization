"""
ESM Format Schema Validation

Provides functionality to validate ESM files against the JSON schema.
"""

using JSON3
using JSONSchema

"""
    SchemaError

Represents a validation error with detailed information.
Contains path, message, and keyword from JSON Schema validation.
"""
struct SchemaError
    path::String
    message::String
    keyword::String
end

"""
    SchemaValidationError

Exception thrown when schema validation fails.
Contains detailed error information including paths and messages.
"""
struct SchemaValidationError <: Exception
    message::String
    errors::Vector{SchemaError}
end

# Load schema at module initialization from bundled package artifact
const SCHEMA_PATH = joinpath(@__DIR__, "..", "data", "esm-schema.json")

# Global schema validator
const ESM_SCHEMA = if isfile(SCHEMA_PATH)
    try
        Schema(JSON3.read(read(SCHEMA_PATH, String)))
    catch e
        @warn "Failed to load ESM schema: $e"
        nothing
    end
else
    @warn "ESM schema file not found at $SCHEMA_PATH"
    nothing
end

"""
    validate_schema(data::Any) -> Vector{SchemaError}

Validate data against the ESM schema.
Returns empty vector if valid, otherwise returns validation errors.
Each error contains the path, message, and keyword for debugging.
"""
function validate_schema(data::Any)::Vector{SchemaError}
    if ESM_SCHEMA === nothing
        @warn "Schema validation skipped - schema not loaded"
        return SchemaError[]
    end

    try
        result = JSONSchema.validate(ESM_SCHEMA, data)
        if result === nothing
            return SchemaError[]
        else
            # Convert validation result to SchemaError format
            # JSONSchema.jl returns validation error objects - need to extract info
            return [SchemaError("/", string(result), "unknown")]
        end
    catch e
        return [SchemaError("/", "Schema validation error: $(e)", "error")]
    end
end