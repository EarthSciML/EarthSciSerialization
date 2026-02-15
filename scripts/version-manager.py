#!/usr/bin/env python3
"""
Version Manager for EarthSciSerialization cross-language libraries.

This script manages versioning and compatibility tracking across all language implementations.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class VersionManager:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.workspace_config = self._load_workspace_config()

    def _load_workspace_config(self) -> Dict:
        config_path = self.workspace_root / "workspace.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Workspace config not found: {config_path}")

        with open(config_path, 'r') as f:
            return json.load(f)

    def _save_workspace_config(self):
        config_path = self.workspace_root / "workspace.json"
        with open(config_path, 'w') as f:
            json.dump(self.workspace_config, f, indent=2, default=str)

    def get_current_version(self) -> str:
        return self.workspace_config["version"]

    def bump_version(self, bump_type: str = "patch") -> str:
        """Bump version following semantic versioning."""
        current = self.get_current_version()
        major, minor, patch = map(int, current.split('.'))

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")

        new_version = f"{major}.{minor}.{patch}"
        self.workspace_config["version"] = new_version
        self.workspace_config["updated"] = datetime.now().isoformat()

        return new_version

    def update_package_versions(self, new_version: str):
        """Update version in all package configuration files."""
        packages = self.workspace_config["dependencies"]

        for package_name, package_info in packages.items():
            package_path = Path(package_info["path"])
            package_type = package_info["type"]

            try:
                if package_type == "julia":
                    self._update_julia_version(package_path, new_version)
                elif package_type == "typescript":
                    self._update_typescript_version(package_path, new_version)
                elif package_type == "python":
                    self._update_python_version(package_path, new_version)
                elif package_type == "rust":
                    self._update_rust_version(package_path, new_version)
                elif package_type == "go":
                    self._update_go_version(package_path, new_version)

                # Update version in workspace config
                package_info["version"] = new_version

                print(f"✓ Updated {package_name} to v{new_version}")

            except Exception as e:
                print(f"✗ Failed to update {package_name}: {e}")

    def _update_julia_version(self, package_path: Path, version: str):
        project_toml = self.workspace_root / package_path / "Project.toml"
        if project_toml.exists():
            content = project_toml.read_text()
            updated = re.sub(r'version = "[^"]*"', f'version = "{version}"', content)
            project_toml.write_text(updated)

    def _update_typescript_version(self, package_path: Path, version: str):
        package_json = self.workspace_root / package_path / "package.json"
        if package_json.exists():
            with open(package_json, 'r') as f:
                data = json.load(f)
            data["version"] = version
            with open(package_json, 'w') as f:
                json.dump(data, f, indent=2)

    def _update_python_version(self, package_path: Path, version: str):
        pyproject_toml = self.workspace_root / package_path / "pyproject.toml"
        if pyproject_toml.exists():
            content = pyproject_toml.read_text()
            updated = re.sub(r'version = "[^"]*"', f'version = "{version}"', content)
            pyproject_toml.write_text(updated)

    def _update_rust_version(self, package_path: Path, version: str):
        cargo_toml = self.workspace_root / package_path / "Cargo.toml"
        if cargo_toml.exists():
            content = cargo_toml.read_text()
            updated = re.sub(r'version = "[^"]*"', f'version = "{version}"', content)
            cargo_toml.write_text(updated)

    def _update_go_version(self, package_path: Path, version: str):
        # Go modules don't have a version file, but we can update a version.go file if it exists
        version_go = self.workspace_root / package_path / "pkg/esm/version.go"
        if version_go.exists():
            content = version_go.read_text()
            updated = re.sub(r'Version = "[^"]*"', f'Version = "{version}"', content)
            version_go.write_text(updated)
        else:
            # Create version.go if it doesn't exist
            version_go.parent.mkdir(parents=True, exist_ok=True)
            version_go.write_text(f'''package esm

// Version of the ESM format library
const Version = "{version}"
''')

    def check_compatibility(self) -> Dict[str, bool]:
        """Check compatibility between all language implementations."""
        results = {}
        packages = self.workspace_config["dependencies"]

        for package_name, package_info in packages.items():
            package_path = self.workspace_root / Path(package_info["path"])
            package_type = package_info["type"]

            try:
                if package_type == "julia":
                    results[package_name] = self._test_julia_package(package_path)
                elif package_type == "typescript":
                    results[package_name] = self._test_typescript_package(package_path)
                elif package_type == "python":
                    results[package_name] = self._test_python_package(package_path)
                elif package_type == "rust":
                    results[package_name] = self._test_rust_package(package_path)
                elif package_type == "go":
                    results[package_name] = self._test_go_package(package_path)
                else:
                    results[package_name] = False
            except Exception as e:
                print(f"Error testing {package_name}: {e}")
                results[package_name] = False

        return results

    def _test_julia_package(self, package_path: Path) -> bool:
        try:
            cmd = ["julia", "--project=.", "-e", "using Pkg; Pkg.test()"]
            result = subprocess.run(cmd, cwd=package_path, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _test_typescript_package(self, package_path: Path) -> bool:
        try:
            # Check if package.json exists and has test script
            package_json = package_path / "package.json"
            if not package_json.exists():
                return False

            with open(package_json) as f:
                data = json.load(f)

            if "test:ci" in data.get("scripts", {}):
                cmd = ["npm", "run", "test:ci"]
            elif "test" in data.get("scripts", {}):
                cmd = ["npm", "test"]
            else:
                return False

            result = subprocess.run(cmd, cwd=package_path, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _test_python_package(self, package_path: Path) -> bool:
        try:
            cmd = ["python3", "-m", "pytest", "tests/", "-v"]
            result = subprocess.run(cmd, cwd=package_path, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _test_rust_package(self, package_path: Path) -> bool:
        try:
            cmd = ["cargo", "test"]
            result = subprocess.run(cmd, cwd=package_path, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _test_go_package(self, package_path: Path) -> bool:
        try:
            cmd = ["go", "test", "./..."]
            result = subprocess.run(cmd, cwd=package_path, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def update_compatibility_matrix(self, version: str, test_results: Dict[str, bool]):
        """Update the compatibility matrix with test results."""
        if "compatibility_matrix" not in self.workspace_config:
            self.workspace_config["compatibility_matrix"] = {}

        # Determine overall status
        all_passed = all(test_results.values())
        status = "compatible" if all_passed else "incompatible"

        # Create compatibility entry
        compatibility_entry = {
            "status": status,
            "tested": datetime.now().isoformat(),
        }

        # Add individual package versions
        for package_name, package_info in self.workspace_config["dependencies"].items():
            package_type = package_info["type"]
            compatibility_entry[package_type] = version

        self.workspace_config["compatibility_matrix"][version] = compatibility_entry

        print(f"Compatibility matrix updated for v{version}: {status}")

    def generate_release_notes(self, version: str, previous_version: Optional[str] = None) -> str:
        """Generate release notes for the new version."""
        notes = [f"# Release v{version}"]
        notes.append("")
        notes.append(f"Released: {datetime.now().strftime('%Y-%m-%d')}")
        notes.append("")

        if previous_version:
            notes.append(f"## Changes since v{previous_version}:")
            notes.append("")

            # Get git log between versions
            try:
                cmd = ["git", "log", f"v{previous_version}..HEAD", "--pretty=format:- %s (%h)"]
                result = subprocess.run(cmd, cwd=self.workspace_root, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    notes.append(result.stdout)
                    notes.append("")
            except subprocess.SubprocessError:
                notes.append("- Various improvements and bug fixes")
                notes.append("")

        notes.append("## Package Versions:")
        for package_name, package_info in self.workspace_config["dependencies"].items():
            package_type = package_info["type"].title()
            registry_info = ""

            if package_type == "Julia":
                registry_info = f" (Julia General Registry)"
            elif package_type == "Typescript":
                registry_info = f" (npm: {package_info.get('npm_name', 'esm-format')})"
            elif package_type == "Python":
                registry_info = f" (PyPI: {package_info.get('pypi_name', 'esm-format')})"
            elif package_type == "Rust":
                registry_info = f" (crates.io: {package_info.get('crate_name', 'esm-format')})"
            elif package_type == "Go":
                registry_info = f" (Go modules)"

            notes.append(f"- {package_type}: v{version}{registry_info}")

        notes.append("")
        notes.append("## Installation:")
        notes.append("```bash")
        notes.append("# Julia")
        notes.append("julia> ] add ESMFormat")
        notes.append("")
        notes.append("# TypeScript/JavaScript")
        notes.append("npm install esm-format")
        notes.append("")
        notes.append("# Python")
        notes.append("pip install esm-format")
        notes.append("")
        notes.append("# Rust")
        notes.append("cargo add esm-format")
        notes.append("")
        notes.append("# Go")
        notes.append("go get github.com/ctessum/EarthSciSerialization/packages/esm-format-go")
        notes.append("```")

        return "\\n".join(notes)


def main():
    if len(sys.argv) < 2:
        print("Usage: python version-manager.py <command> [args]")
        print("Commands:")
        print("  bump <major|minor|patch>  - Bump version and update all packages")
        print("  check                     - Check compatibility between packages")
        print("  release <version>         - Prepare release with given version")
        print("  notes <version> [prev]    - Generate release notes")
        sys.exit(1)

    manager = VersionManager()
    command = sys.argv[1]

    if command == "bump":
        bump_type = sys.argv[2] if len(sys.argv) > 2 else "patch"
        new_version = manager.bump_version(bump_type)
        manager.update_package_versions(new_version)
        manager._save_workspace_config()
        print(f"Bumped version to v{new_version}")

    elif command == "check":
        print("Checking package compatibility...")
        results = manager.check_compatibility()

        print("\\nCompatibility Results:")
        for package, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {package}: {status}")

        all_compatible = all(results.values())
        print(f"\\nOverall: {'✓ All packages compatible' if all_compatible else '✗ Some packages failed'}")

        if not all_compatible:
            sys.exit(1)

    elif command == "release":
        if len(sys.argv) < 3:
            print("Usage: python version-manager.py release <version>")
            sys.exit(1)

        version = sys.argv[2]
        print(f"Preparing release v{version}...")

        # Update versions
        manager.workspace_config["version"] = version
        manager.update_package_versions(version)

        # Check compatibility
        print("Running compatibility checks...")
        test_results = manager.check_compatibility()
        manager.update_compatibility_matrix(version, test_results)

        manager._save_workspace_config()
        print(f"Release v{version} prepared successfully!")

    elif command == "notes":
        if len(sys.argv) < 3:
            print("Usage: python version-manager.py notes <version> [previous_version]")
            sys.exit(1)

        version = sys.argv[2]
        prev_version = sys.argv[3] if len(sys.argv) > 3 else None

        notes = manager.generate_release_notes(version, prev_version)
        print(notes)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()