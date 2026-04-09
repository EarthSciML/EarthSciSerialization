"""
Migration functionality for ESM format version compatibility.

Implements Section 8.3 of the ESM Libraries Specification:
migrate(file: EsmFile, target_version: String) -> EsmFile
"""

import copy
from typing import List, Tuple


class MigrationError(Exception):
    """Error raised when migration fails."""

    def __init__(self, message: str, from_version: str = "", to_version: str = ""):
        self.from_version = from_version
        self.to_version = to_version
        super().__init__(
            f"Migration error: {message} ({from_version} -> {to_version})"
            if from_version
            else f"Migration error: {message}"
        )


def _parse_version(version: str) -> Tuple[int, int, int]:
    """Parse a semantic version string into (major, minor, patch)."""
    parts = version.split(".")
    if len(parts) != 3:
        raise MigrationError(f"Invalid version format: {version}", version, "")
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        raise MigrationError(f"Invalid version format: {version}", version, "")


def _compare_versions(a: str, b: str) -> int:
    """Compare two semantic versions. Returns <0 if a<b, 0 if equal, >0 if a>b."""
    va = _parse_version(a)
    vb = _parse_version(b)
    if va < vb:
        return -1
    elif va > vb:
        return 1
    return 0


def _get_version(esm_file) -> str:
    """Get the version string from an ESM file object (supports .esm or .version)."""
    if hasattr(esm_file, "esm"):
        return esm_file.esm
    if hasattr(esm_file, "version"):
        return esm_file.version
    raise MigrationError("File has no version attribute")


def _set_version(esm_file, version: str):
    """Set the version string on an ESM file object."""
    if hasattr(esm_file, "esm"):
        esm_file.esm = version
    elif hasattr(esm_file, "version"):
        esm_file.version = version


def _migrate_species_units(esm_file, from_version: str, to_version: str):
    """Migrate species units from older format (e.g., ppbv) to newer format (mol/mol)."""
    from_ver = _parse_version(from_version)
    to_ver = _parse_version(to_version)

    # Migration from 0.0.x to 0.1.0+: convert ppbv/ppmv to mol/mol
    if from_ver[0] == 0 and from_ver[1] == 0 and to_ver[0] == 0 and to_ver[1] >= 1:
        reaction_systems = getattr(esm_file, "reaction_systems", None)
        if reaction_systems is None:
            return

        # Handle both dict-of-systems and list-of-systems
        systems = (
            reaction_systems.values()
            if isinstance(reaction_systems, dict)
            else reaction_systems
        )

        for system in systems:
            species_coll = getattr(system, "species", None)
            if species_coll is None:
                continue

            # Handle both dict-of-species and list-of-species
            species_iter = (
                species_coll.values()
                if isinstance(species_coll, dict)
                else species_coll
            )

            for species in species_iter:
                units = getattr(species, "units", None)
                default = getattr(species, "default", None)
                if units == "ppbv" and default is not None:
                    species.units = "mol/mol"
                    species.default = default / 1e9
                elif units == "ppmv" and default is not None:
                    species.units = "mol/mol"
                    species.default = default / 1e6


def _add_migration_notes(esm_file, from_version: str, to_version: str):
    """Add migration notes to the file metadata."""
    metadata = getattr(esm_file, "metadata", None)
    if metadata is None:
        return

    migration_note = f"Migrated from version {from_version} to version {to_version}"

    # Try to set migration_notes attribute if metadata supports it
    desc = getattr(metadata, "description", None)
    if desc:
        metadata.description = f"{desc}\nMigration notes: {migration_note}"
    else:
        metadata.description = f"Migration notes: {migration_note}"


def migrate(esm_file, target_version: str):
    """Migrate an ESM file to a target version.

    Args:
        esm_file: An ESM file object (EsmFile or compatible duck-typed object).
        target_version: The target version string (e.g., "0.1.0").

    Returns:
        A new ESM file object migrated to the target version.

    Raises:
        MigrationError: If migration is not possible.
    """
    current_version = _get_version(esm_file)

    _parse_version(current_version)
    current_ver = _parse_version(current_version)
    target_ver = _parse_version(target_version)

    # No migration needed
    if current_version == target_version:
        return copy.deepcopy(esm_file)

    # Cannot migrate across major versions
    if current_ver[0] != target_ver[0]:
        raise MigrationError(
            f"Cannot migrate across major versions: {current_version} to {target_version}",
            current_version,
            target_version,
        )

    # Only support forward migration
    if _compare_versions(current_version, target_version) > 0:
        raise MigrationError(
            f"Backward migration not supported: {current_version} to {target_version}",
            current_version,
            target_version,
        )

    migrated = copy.deepcopy(esm_file)

    # Update version
    _set_version(migrated, target_version)

    # Apply version-specific migrations
    _migrate_species_units(migrated, current_version, target_version)

    # Add migration notes
    _add_migration_notes(migrated, current_version, target_version)

    return migrated


def can_migrate(from_version: str, to_version: str) -> bool:
    """Check if migration is supported between two versions.

    Args:
        from_version: Source version string.
        to_version: Target version string.

    Returns:
        True if migration is supported.
    """
    try:
        from_ver = _parse_version(from_version)
        to_ver = _parse_version(to_version)
    except MigrationError:
        return False

    # Only support migration within same major version
    if from_ver[0] != to_ver[0]:
        return False

    # Only support forward migration (or same version)
    return _compare_versions(from_version, to_version) <= 0


def get_supported_migration_targets(from_version: str) -> List[str]:
    """Get supported migration target versions from a given version.

    Args:
        from_version: Source version string.

    Returns:
        List of supported target version strings.
    """
    try:
        from_ver = _parse_version(from_version)
    except MigrationError:
        return []

    targets = []

    if from_ver[0] == 0:
        if from_ver[1] == 0:
            targets.append("0.1.0")
        if from_ver[1] <= 1:
            targets.extend(["0.1.0", "0.1.1", "0.2.0"])

    # Filter to only versions later than from_version, deduplicate
    seen = set()
    result = []
    for target in targets:
        if target not in seen and _compare_versions(from_version, target) < 0:
            seen.add(target)
            result.append(target)

    return result
