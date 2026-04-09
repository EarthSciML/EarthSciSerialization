"""
Shared availability checking for MTK and Catalyst dependencies.

This module centralizes the lazy loading and availability checking for optional
dependencies (ModelingToolkit, Catalyst, Symbolics) to avoid duplicate Ref
constants across multiple modules.
"""

# Global availability flags - single source of truth
const MTK_AVAILABLE = Ref(false)
const CATALYST_AVAILABLE = Ref(false)
const SYMBOLICS_AVAILABLE = Ref(false)

# Checking flags to avoid repeated checks
const MTK_CHECKED = Ref(false)
const CATALYST_CHECKED = Ref(false)
const MTK_CATALYST_CHECKED = Ref(false)

"""
    check_mtk_availability() -> Bool

Check if ModelingToolkit and Symbolics are available.
Uses lazy loading to avoid precompilation issues.
"""
function check_mtk_availability()
    if !MTK_CHECKED[]
        try
            @eval using ModelingToolkit
            MTK_AVAILABLE[] = true
        catch e
            MTK_AVAILABLE[] = false
        end

        try
            @eval using Symbolics
            SYMBOLICS_AVAILABLE[] = true
        catch e
            SYMBOLICS_AVAILABLE[] = false
        end

        MTK_CHECKED[] = true
    end
    return MTK_AVAILABLE[]
end

"""
    check_catalyst_availability() -> Bool

Check if Catalyst and Symbolics are available.
Uses lazy loading to avoid precompilation issues.
"""
function check_catalyst_availability()
    if !CATALYST_CHECKED[]
        try
            @eval using Catalyst
            CATALYST_AVAILABLE[] = true
        catch e
            CATALYST_AVAILABLE[] = false
        end

        try
            @eval using Symbolics
            SYMBOLICS_AVAILABLE[] = true
        catch e
            SYMBOLICS_AVAILABLE[] = false
        end

        CATALYST_CHECKED[] = true
    end
    return CATALYST_AVAILABLE[]
end

"""
    check_mtk_catalyst_availability() -> Bool

Check if both ModelingToolkit and Catalyst are available.
Uses lazy loading to avoid precompilation issues.
"""
function check_mtk_catalyst_availability()
    if !MTK_CATALYST_CHECKED[]
        try
            @eval using ModelingToolkit
            MTK_AVAILABLE[] = true
        catch e
            MTK_AVAILABLE[] = false
        end

        try
            @eval using Catalyst
            CATALYST_AVAILABLE[] = true
        catch e
            CATALYST_AVAILABLE[] = false
        end

        try
            @eval using Symbolics
            SYMBOLICS_AVAILABLE[] = true
        catch e
            SYMBOLICS_AVAILABLE[] = false
        end

        MTK_CATALYST_CHECKED[] = true
    end
    return MTK_AVAILABLE[] && CATALYST_AVAILABLE[]
end