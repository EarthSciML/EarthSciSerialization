# ESM Format Package Analytics - Julia Integration
#
# Provides macros and functions for integrating performance monitoring
# and analytics into Julia ESM format packages.

module ESMAnalytics

using Dates
using JSON3
using SQLite
using UUIDs
import Base.Threads

export @track_performance, @record_event, initialize_analytics, submit_feedback,
       get_performance_summary, get_usage_summary, track_operation

# Global analytics state
mutable struct AnalyticsState
    enabled::Bool
    package_name::String
    version::String
    user_id::String
    session_id::String
    db_path::String
    platform_info::Dict{String, Any}
end

# Global instance
const ANALYTICS = Ref{Union{AnalyticsState, Nothing}}(nothing)

"""
    initialize_analytics(package_name::String, version::String; enabled=nothing, db_path=nothing)

Initialize analytics for a Julia package.
"""
function initialize_analytics(package_name::String, version::String;
                             enabled::Union{Bool, Nothing}=nothing,
                             db_path::Union{String, Nothing}=nothing)
    if enabled === nothing
        enabled = get(ENV, "ESM_ANALYTICS_ENABLED", "1") in ("1", "true", "yes")
    end

    if !enabled
        ANALYTICS[] = nothing
        return nothing
    end

    if db_path === nothing
        db_path = joinpath(homedir(), ".esm_analytics", "analytics.db")
    end

    # Ensure directory exists
    mkpath(dirname(db_path))

    # Generate or load user ID
    user_id = get_or_create_user_id()
    session_id = string(uuid4())

    # Collect platform info
    platform_info = Dict{String, Any}(
        "os" => string(Sys.KERNEL),
        "architecture" => string(Sys.MACHINE),
        "julia_version" => string(VERSION),
        "cpu_count" => string(Sys.CPU_THREADS),
        "memory_gb" => string(round(Sys.total_memory() / (1024^3), digits=1))
    )

    analytics = AnalyticsState(
        enabled, package_name, version, user_id, session_id,
        db_path, platform_info
    )

    ANALYTICS[] = analytics
    initialize_database(analytics)

    return analytics
end

"""
    get_or_create_user_id()

Get or create an anonymous user ID.
"""
function get_or_create_user_id()
    user_file = joinpath(homedir(), ".esm_analytics", ".user_id")

    if isfile(user_file)
        return strip(read(user_file, String))
    end

    # Create anonymous ID based on machine characteristics
    machine_id = gethostname() * string(Sys.MACHINE)
    using SHA
    user_id = bytes2hex(sha256(machine_id))[1:16]

    # Ensure directory exists
    mkpath(dirname(user_file))
    write(user_file, user_id)

    return user_id
end

"""
    initialize_database(analytics::AnalyticsState)

Initialize SQLite database for analytics storage.
"""
function initialize_database(analytics::AnalyticsState)
    db = SQLite.DB(analytics.db_path)

    # Create tables
    SQLite.execute(db, """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            duration_ms REAL NOT NULL,
            memory_mb REAL NOT NULL,
            timestamp TEXT NOT NULL,
            package TEXT NOT NULL,
            version TEXT NOT NULL,
            platform_info TEXT NOT NULL,
            file_size_bytes INTEGER,
            success BOOLEAN NOT NULL,
            error_message TEXT,
            metadata TEXT
        )
    """)

    SQLite.execute(db, """
        CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            package TEXT NOT NULL,
            version TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            file_type TEXT,
            file_size_category TEXT,
            success BOOLEAN NOT NULL,
            error_type TEXT,
            metadata TEXT
        )
    """)

    SQLite.execute(db, """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id TEXT UNIQUE NOT NULL,
            package TEXT NOT NULL,
            version TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            feedback_type TEXT NOT NULL,
            severity INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            platform_info TEXT NOT NULL,
            reproduction_steps TEXT,
            expected_behavior TEXT,
            actual_behavior TEXT,
            metadata TEXT
        )
    """)

    # Create indices
    SQLite.execute(db, "CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp)")
    SQLite.execute(db, "CREATE INDEX IF NOT EXISTS idx_performance_operation ON performance_metrics(operation)")
    SQLite.execute(db, "CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_events(timestamp)")
    SQLite.execute(db, "CREATE INDEX IF NOT EXISTS idx_usage_event_type ON usage_events(event_type)")
    SQLite.execute(db, "CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback(timestamp)")

    SQLite.close!(db)
end

"""
    @track_performance(operation_name, expr)

Macro to track performance of an expression.
"""
macro track_performance(operation_name, expr)
    quote
        local analytics = ANALYTICS[]
        if analytics === nothing || !analytics.enabled
            $(esc(expr))
        else
            local start_time = time()
            local start_memory = GC.gc()
            local memory_before = Base.gc_live_bytes()

            local result = nothing
            local success = true
            local error_message = nothing

            try
                result = $(esc(expr))
            catch e
                success = false
                error_message = string(e)
                rethrow(e)
            finally
                local end_time = time()
                GC.gc()
                local memory_after = Base.gc_live_bytes()

                local duration_ms = (end_time - start_time) * 1000
                local memory_mb = max(0, (memory_after - memory_before) / (1024^2))

                record_performance_metric(
                    analytics,
                    $(string(operation_name)),
                    duration_ms,
                    memory_mb,
                    success,
                    error_message
                )
            end

            result
        end
    end
end

"""
    @record_event(event_type, expr)

Macro to record usage events.
"""
macro record_event(event_type, expr)
    quote
        local analytics = ANALYTICS[]
        if analytics === nothing || !analytics.enabled
            $(esc(expr))
        else
            local result = nothing
            local success = true
            local error_type = nothing

            try
                result = $(esc(expr))
            catch e
                success = false
                error_type = string(typeof(e))
                rethrow(e)
            finally
                record_usage_event(
                    analytics,
                    $(string(event_type)),
                    success,
                    error_type
                )
            end

            result
        end
    end
end

"""
    record_performance_metric(analytics, operation, duration_ms, memory_mb, success, error_message)

Record a performance metric to the database.
"""
function record_performance_metric(analytics::AnalyticsState, operation::String,
                                 duration_ms::Real, memory_mb::Real,
                                 success::Bool, error_message::Union{String, Nothing})
    db = SQLite.DB(analytics.db_path)

    try
        SQLite.execute(db, """
            INSERT INTO performance_metrics
            (operation, duration_ms, memory_mb, timestamp, package, version,
             platform_info, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            operation,
            duration_ms,
            memory_mb,
            string(now(UTC)),
            analytics.package_name,
            analytics.version,
            JSON3.write(analytics.platform_info),
            success,
            error_message
        ])
    finally
        SQLite.close!(db)
    end
end

"""
    record_usage_event(analytics, event_type, success, error_type)

Record a usage event to the database.
"""
function record_usage_event(analytics::AnalyticsState, event_type::String,
                           success::Bool, error_type::Union{String, Nothing})
    db = SQLite.DB(analytics.db_path)

    try
        SQLite.execute(db, """
            INSERT INTO usage_events
            (event_type, package, version, timestamp, user_id, session_id, success, error_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            event_type,
            analytics.package_name,
            analytics.version,
            string(now(UTC)),
            analytics.user_id,
            analytics.session_id,
            success,
            error_type
        ])
    finally
        SQLite.close!(db)
    end
end

"""
    submit_feedback(feedback_type, severity, title, description; kwargs...)

Submit user feedback about the package.
"""
function submit_feedback(feedback_type::String, severity::Int, title::String,
                        description::String;
                        reproduction_steps::Union{String, Nothing}=nothing,
                        expected_behavior::Union{String, Nothing}=nothing,
                        actual_behavior::Union{String, Nothing}=nothing,
                        metadata::Union{Dict, Nothing}=nothing)

    analytics = ANALYTICS[]
    if analytics === nothing || !analytics.enabled
        return nothing
    end

    feedback_id = string(uuid4())

    db = SQLite.DB(analytics.db_path)

    try
        SQLite.execute(db, """
            INSERT INTO feedback
            (feedback_id, package, version, timestamp, user_id, feedback_type,
             severity, title, description, platform_info, reproduction_steps,
             expected_behavior, actual_behavior, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            feedback_id,
            analytics.package_name,
            analytics.version,
            string(now(UTC)),
            analytics.user_id,
            feedback_type,
            severity,
            title,
            description,
            JSON3.write(analytics.platform_info),
            reproduction_steps,
            expected_behavior,
            actual_behavior,
            metadata === nothing ? nothing : JSON3.write(metadata)
        ])
    finally
        SQLite.close!(db)
    end

    return feedback_id
end

"""
    get_performance_summary(days=30)

Get performance summary for the last N days.
"""
function get_performance_summary(days::Int=30)
    analytics = ANALYTICS[]
    if analytics === nothing || !analytics.enabled
        return nothing
    end

    cutoff_date = now(UTC) - Day(days)
    db = SQLite.DB(analytics.db_path)

    try
        # Get metrics by operation
        result = SQLite.execute(db, """
            SELECT operation,
                   COUNT(*) as count,
                   AVG(duration_ms) as avg_duration,
                   AVG(memory_mb) as avg_memory,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM performance_metrics
            WHERE timestamp > ? AND package = ?
            GROUP BY operation
        """, [string(cutoff_date), analytics.package_name])

        operations = Dict{String, Dict{String, Any}}()
        for row in result
            operations[row.operation] = Dict(
                "count" => row.count,
                "avg_duration_ms" => round(row.avg_duration, digits=2),
                "avg_memory_mb" => round(row.avg_memory, digits=2),
                "successful" => row.successful,
                "success_rate" => round((row.successful / row.count) * 100, digits=1)
            )
        end

        return Dict(
            "package" => analytics.package_name,
            "version" => analytics.version,
            "period_days" => days,
            "operations" => operations,
            "platform_info" => analytics.platform_info
        )
    finally
        SQLite.close!(db)
    end
end

"""
    get_usage_summary(days=30)

Get usage summary for the last N days.
"""
function get_usage_summary(days::Int=30)
    analytics = ANALYTICS[]
    if analytics === nothing || !analytics.enabled
        return nothing
    end

    cutoff_date = now(UTC) - Day(days)
    db = SQLite.DB(analytics.db_path)

    try
        result = SQLite.execute(db, """
            SELECT event_type,
                   COUNT(*) as count,
                   COUNT(DISTINCT user_id) as unique_users,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM usage_events
            WHERE timestamp > ? AND package = ?
            GROUP BY event_type
        """, [string(cutoff_date), analytics.package_name])

        events = Dict{String, Dict{String, Any}}()
        for row in result
            events[row.event_type] = Dict(
                "total_events" => row.count,
                "unique_users" => row.unique_users,
                "successful_events" => row.successful,
                "success_rate" => round((row.successful / row.count) * 100, digits=1)
            )
        end

        return Dict(
            "package" => analytics.package_name,
            "version" => analytics.version,
            "period_days" => days,
            "events" => events
        )
    finally
        SQLite.close!(db)
    end
end

"""
    track_operation(f, operation_name; file_size_bytes=nothing, metadata=nothing)

Function wrapper for tracking operations.
"""
function track_operation(f::Function, operation_name::String;
                        file_size_bytes::Union{Int, Nothing}=nothing,
                        metadata::Union{Dict, Nothing}=nothing)
    analytics = ANALYTICS[]
    if analytics === nothing || !analytics.enabled
        return f()
    end

    start_time = time()
    GC.gc()
    memory_before = Base.gc_live_bytes()

    result = nothing
    success = true
    error_message = nothing

    try
        result = f()
    catch e
        success = false
        error_message = string(e)
        rethrow(e)
    finally
        end_time = time()
        GC.gc()
        memory_after = Base.gc_live_bytes()

        duration_ms = (end_time - start_time) * 1000
        memory_mb = max(0, (memory_after - memory_before) / (1024^2))

        record_performance_metric(
            analytics,
            operation_name,
            duration_ms,
            memory_mb,
            success,
            error_message
        )

        # Also record usage event
        record_usage_event(
            analytics,
            operation_name,
            success,
            success ? nothing : string(typeof(error_message))
        )
    end

    return result
end

end # module ESMAnalytics