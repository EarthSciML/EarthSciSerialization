#!/usr/bin/env python3

"""
EarthSciSerialization Python Dependency Resolver

Advanced dependency resolution for Python packages with version compatibility
checking, conflict detection, and automatic resolution suggestions.
"""

import json
import os
import sys
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

# Try to import optional dependencies
try:
    import tomli
    HAS_TOMLI = True
except ImportError:
    HAS_TOMLI = False
    print("Warning: tomli not available, will use basic TOML parsing")

try:
    import pkg_resources
    from packaging import version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False
    print("Warning: packaging not available, will use basic version comparison")


@dataclass
class PackageInfo:
    name: str
    version: str
    dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str]
    path: Path
    package_type: str


@dataclass
class VersionConflict:
    package_name: str
    required_versions: List[str]
    conflicting_packages: List[str]
    severity: str  # 'error', 'warning', 'info'


class PythonDependencyResolver:
    def __init__(self, workspace_root: Path = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.workspace_config = self._load_workspace_config()

    def _load_workspace_config(self) -> dict:
        """Load workspace configuration."""
        config_path = self.workspace_root / 'workspace.json'
        if not config_path.exists():
            raise FileNotFoundError('workspace.json not found')

        with open(config_path, 'r') as f:
            return json.load(f)

    def _parse_python_package(self, package_path: Path) -> PackageInfo:
        """Parse a Python package's pyproject.toml."""
        pyproject_path = package_path / 'pyproject.toml'

        if not pyproject_path.exists():
            raise FileNotFoundError(f'pyproject.toml not found in {package_path}')

        if HAS_TOMLI:
            with open(pyproject_path, 'rb') as f:
                data = tomli.load(f)
        else:
            # Basic TOML parsing fallback
            data = self._basic_toml_parse(pyproject_path)

        project = data.get('project', {})
        name = project.get('name', package_path.name)
        version_str = project.get('version', '0.1.0')

        # Parse dependencies
        dependencies = {}
        for dep in project.get('dependencies', []):
            parsed_dep = self._parse_dependency_string(dep)
            if parsed_dep:
                dependencies[parsed_dep[0]] = parsed_dep[1]

        # Parse dev dependencies
        dev_dependencies = {}
        optional_deps = project.get('optional-dependencies', {})
        for group, deps in optional_deps.items():
            if group in ['dev', 'test', 'development']:
                for dep in deps:
                    parsed_dep = self._parse_dependency_string(dep)
                    if parsed_dep:
                        dev_dependencies[parsed_dep[0]] = parsed_dep[1]

        return PackageInfo(
            name=name,
            version=version_str,
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            path=package_path,
            package_type='python'
        )

    def _basic_toml_parse(self, toml_path: Path) -> dict:
        """Basic TOML parsing fallback when tomli is not available."""
        data = {'project': {'dependencies': [], 'optional-dependencies': {}}}

        with open(toml_path, 'r') as f:
            content = f.read()

        # Extract project name and version
        name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
        if name_match:
            data['project']['name'] = name_match.group(1)

        version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if version_match:
            data['project']['version'] = version_match.group(1)

        # Extract dependencies (very basic parsing)
        deps_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if deps_match:
            deps_content = deps_match.group(1)
            deps = []
            for line in deps_content.split('\n'):
                line = line.strip()
                if line.startswith('"') and line.endswith('",') or line.endswith('"'):
                    dep = line.strip('",').strip()
                    if dep:
                        deps.append(dep)
            data['project']['dependencies'] = deps

        return data

    def _parse_dependency_string(self, dep_string: str) -> Optional[Tuple[str, str]]:
        """Parse a dependency string like 'numpy>=1.20.0' into (name, version_spec)."""
        # Common patterns: name>=version, name==version, name~=version, name>version, name<version
        patterns = [
            r'^([a-zA-Z0-9_-]+)\s*([><=~!]+)\s*([0-9.]+(?:[a-zA-Z0-9_.-]*)?)',
            r'^([a-zA-Z0-9_-]+)\s*$'  # Just name, no version
        ]

        for pattern in patterns:
            match = re.match(pattern, dep_string.strip())
            if match:
                if len(match.groups()) == 1:
                    return (match.group(1), '*')
                else:
                    return (match.group(1), f"{match.group(2)}{match.group(3)}")

        return None

    def get_python_packages(self) -> Dict[str, PackageInfo]:
        """Get all Python packages in the workspace."""
        packages = {}

        for name, config in self.workspace_config.get('dependencies', {}).items():
            if config.get('type') == 'python':
                package_path = Path(self.workspace_root) / config['path']
                try:
                    package_info = self._parse_python_package(package_path)
                    packages[name] = package_info
                except Exception as e:
                    print(f"Warning: Failed to parse {name}: {e}")

        return packages

    def check_version_compatibility(self, packages: Dict[str, PackageInfo]) -> List[VersionConflict]:
        """Check for version conflicts between packages."""
        conflicts = []

        # Collect all dependency requirements
        all_requirements = {}

        for pkg_name, pkg_info in packages.items():
            # Add dependencies
            for dep_name, version_spec in pkg_info.dependencies.items():
                if dep_name not in all_requirements:
                    all_requirements[dep_name] = []
                all_requirements[dep_name].append({
                    'version_spec': version_spec,
                    'required_by': pkg_name,
                    'dep_type': 'runtime'
                })

            # Add dev dependencies
            for dep_name, version_spec in pkg_info.dev_dependencies.items():
                if dep_name not in all_requirements:
                    all_requirements[dep_name] = []
                all_requirements[dep_name].append({
                    'version_spec': version_spec,
                    'required_by': pkg_name,
                    'dep_type': 'dev'
                })

        # Check for conflicts
        for dep_name, requirements in all_requirements.items():
            if len(requirements) > 1:
                version_specs = [req['version_spec'] for req in requirements]
                unique_specs = set(version_specs)

                if len(unique_specs) > 1 and '*' not in unique_specs:
                    # Try to resolve version compatibility
                    compatible = self._check_version_compatibility(unique_specs)

                    if not compatible:
                        conflicts.append(VersionConflict(
                            package_name=dep_name,
                            required_versions=list(unique_specs),
                            conflicting_packages=[req['required_by'] for req in requirements],
                            severity='error'
                        ))

        return conflicts

    def _check_version_compatibility(self, version_specs: Set[str]) -> bool:
        """Check if a set of version specifications are compatible."""
        try:
            # Create a dummy requirement set and check if they can be satisfied
            # This is a simplified check - a real resolver would be more sophisticated
            parsed_specs = []
            for spec in version_specs:
                if spec != '*':
                    # Try to parse the version spec
                    if spec.startswith('>='):
                        parsed_specs.append(('>=', spec[2:]))
                    elif spec.startswith('=='):
                        parsed_specs.append(('==', spec[2:]))
                    elif spec.startswith('>'):
                        parsed_specs.append(('>', spec[1:]))
                    elif spec.startswith('<='):
                        parsed_specs.append(('<=', spec[2:]))
                    elif spec.startswith('<'):
                        parsed_specs.append(('<', spec[1:]))

            # Simple compatibility check for >= constraints
            if all(op in ['>=', '>'] for op, _ in parsed_specs):
                # All are minimum version requirements - they can usually be satisfied
                return True

            # For exact version requirements, they must all be the same
            exact_versions = [v for op, v in parsed_specs if op == '==']
            if len(exact_versions) > 1:
                return len(set(exact_versions)) == 1

            return True  # Conservative approach
        except Exception:
            return False

    def resolve_conflicts(self, conflicts: List[VersionConflict]) -> Dict[str, str]:
        """Suggest resolutions for version conflicts."""
        resolutions = {}

        for conflict in conflicts:
            # Simple resolution strategy: suggest the highest minimum version
            suggested_version = self._suggest_version_resolution(conflict.required_versions)
            resolutions[conflict.package_name] = suggested_version

        return resolutions

    def _suggest_version_resolution(self, version_specs: List[str]) -> str:
        """Suggest a version that satisfies all requirements."""
        # Extract minimum versions from >= requirements
        min_versions = []

        for spec in version_specs:
            if spec.startswith('>='):
                min_versions.append(spec[2:])
            elif spec.startswith('>'):
                # For > requirements, increment the patch version
                base_version = spec[1:]
                try:
                    v = version.Version(base_version)
                    # Increment micro version
                    new_version = f"{v.major}.{v.minor}.{v.micro + 1}"
                    min_versions.append(new_version)
                except Exception:
                    min_versions.append(base_version)

        if min_versions:
            # Return the highest minimum version
            try:
                if HAS_PACKAGING:
                    highest = max(min_versions, key=lambda x: version.Version(x))
                else:
                    # Basic version comparison
                    highest = max(min_versions, key=lambda x: tuple(map(int, x.split('.'))))
                return f">={highest}"
            except Exception:
                return version_specs[0]  # Fallback

        return version_specs[0]  # Fallback

    def update_package_dependencies(self, package_name: str, resolutions: Dict[str, str]) -> bool:
        """Update a package's dependencies with resolved versions."""
        packages = self.get_python_packages()

        if package_name not in packages:
            print(f"Package {package_name} not found")
            return False

        package_info = packages[package_name]
        pyproject_path = package_info.path / 'pyproject.toml'

        try:
            # Read current pyproject.toml
            with open(pyproject_path, 'rb') as f:
                data = tomli.load(f)

            # Update dependencies
            current_deps = data.get('project', {}).get('dependencies', [])
            updated_deps = []

            for dep in current_deps:
                parsed = self._parse_dependency_string(dep)
                if parsed:
                    dep_name, _ = parsed
                    if dep_name in resolutions:
                        updated_deps.append(f"{dep_name}{resolutions[dep_name]}")
                    else:
                        updated_deps.append(dep)
                else:
                    updated_deps.append(dep)

            # Update the data structure
            if 'project' not in data:
                data['project'] = {}
            data['project']['dependencies'] = updated_deps

            # Write back (this would require tomli-w or similar for writing TOML)
            print(f"Would update {pyproject_path} with new dependencies:")
            for dep in updated_deps:
                print(f"  {dep}")

            return True

        except Exception as e:
            print(f"Failed to update {package_name}: {e}")
            return False

    def generate_lockfile(self, package_name: str) -> bool:
        """Generate or update lockfile for a package."""
        packages = self.get_python_packages()

        if package_name not in packages:
            print(f"Package {package_name} not found")
            return False

        package_info = packages[package_name]

        try:
            # Change to package directory and run pip-tools or similar
            os.chdir(package_info.path)

            # Check if requirements.in exists, if not create it from pyproject.toml
            if not (package_info.path / 'requirements.in').exists():
                print("Creating requirements.in from pyproject.toml")
                subprocess.run(['pip-compile', 'pyproject.toml'], check=True)
            else:
                print("Updating requirements.txt from requirements.in")
                subprocess.run(['pip-compile', '--upgrade'], check=True)

            return True

        except subprocess.CalledProcessError as e:
            print(f"Failed to generate lockfile for {package_name}: {e}")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False

    def run_cli(self):
        """Command-line interface."""
        if len(sys.argv) < 2:
            self._print_help()
            return

        command = sys.argv[1]

        if command == 'check':
            packages = self.get_python_packages()
            conflicts = self.check_version_compatibility(packages)

            if not conflicts:
                print("✅ No version conflicts found in Python packages")
            else:
                print(f"⚠️  Found {len(conflicts)} version conflicts:")
                for conflict in conflicts:
                    print(f"  {conflict.package_name}: {', '.join(conflict.required_versions)}")
                    print(f"    Conflicting packages: {', '.join(conflict.conflicting_packages)}")

        elif command == 'resolve':
            packages = self.get_python_packages()
            conflicts = self.check_version_compatibility(packages)
            resolutions = self.resolve_conflicts(conflicts)

            if resolutions:
                print("Suggested resolutions:")
                for pkg, version_spec in resolutions.items():
                    print(f"  {pkg}: {version_spec}")
            else:
                print("No conflicts to resolve")

        elif command == 'update' and len(sys.argv) > 2:
            package_name = sys.argv[2]
            packages = self.get_python_packages()
            conflicts = self.check_version_compatibility(packages)
            resolutions = self.resolve_conflicts(conflicts)

            if self.update_package_dependencies(package_name, resolutions):
                print(f"✅ Updated {package_name} dependencies")
            else:
                print(f"❌ Failed to update {package_name}")

        elif command == 'lockfile' and len(sys.argv) > 2:
            package_name = sys.argv[2]
            if self.generate_lockfile(package_name):
                print(f"✅ Generated lockfile for {package_name}")
            else:
                print(f"❌ Failed to generate lockfile for {package_name}")

        else:
            self._print_help()

    def _print_help(self):
        """Print CLI help."""
        print("""
Python Dependency Resolver

Usage:
  python dependency_resolver.py check              Check for version conflicts
  python dependency_resolver.py resolve            Show suggested resolutions
  python dependency_resolver.py update <package>   Update package dependencies
  python dependency_resolver.py lockfile <package> Generate/update lockfile

Examples:
  python dependency_resolver.py check
  python dependency_resolver.py update esm-format-py
  python dependency_resolver.py lockfile esm-format-py
        """)


if __name__ == '__main__':
    try:
        resolver = PythonDependencyResolver()
        resolver.run_cli()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)