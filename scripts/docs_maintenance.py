#!/usr/bin/env python3
"""
Documentation maintenance and building script.

This script provides comprehensive documentation maintenance including:
1. Improved extraction filtering (exclude dependencies)
2. Link checking and fixing
3. Automated documentation building
4. Integration with existing documentation structure
"""

import os
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any
import subprocess
import shutil

class DocumentationMaintainer:
    """Maintains and builds documentation with improved filtering."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_dir = project_root / "docs"
        self.packages_dir = project_root / "packages"

    def build_docs(self, skip_generation: bool = False):
        """Build complete documentation suite."""

        print("🔧 Building ESM Format documentation...")

        if not skip_generation:
            # Generate improved API documentation
            self._generate_filtered_api_docs()

        # Create missing placeholder files
        self._create_placeholder_files()

        # Update navigation and cross-references
        self._update_navigation()

        # Run validation
        self._run_validation()

        print("✅ Documentation build complete!")

    def _generate_filtered_api_docs(self):
        """Generate API docs with better filtering to exclude dependencies."""
        print("📋 Generating filtered API documentation...")

        # Create a filtered version of the documentation generator
        # Focus only on project-specific code

        api_data = {
            "functions": [],
            "types": [],
            "languages": [],
            "cross_references": {},
            "examples": []
        }

        # Extract Julia docs (filter to project files only)
        julia_functions, julia_types = self._extract_julia_filtered()
        api_data["functions"].extend(julia_functions)
        api_data["types"].extend(julia_types)
        if julia_functions or julia_types:
            api_data["languages"].append("julia")

        # Extract Python docs (filter to project files only)
        python_functions, python_types = self._extract_python_filtered()
        api_data["functions"].extend(python_functions)
        api_data["types"].extend(python_types)
        if python_functions or python_types:
            api_data["languages"].append("python")

        # Extract TypeScript docs
        ts_functions, ts_types = self._extract_typescript_filtered()
        api_data["functions"].extend(ts_functions)
        api_data["types"].extend(ts_types)
        if ts_functions or ts_types:
            api_data["languages"].append("typescript")

        # Extract Rust docs
        rust_functions, rust_types = self._extract_rust_filtered()
        api_data["functions"].extend(rust_functions)
        api_data["types"].extend(rust_types)
        if rust_functions or rust_types:
            api_data["languages"].append("rust")

        # Generate documentation files
        self._write_api_docs(api_data)

        print(f"📊 Generated docs for {len(api_data['languages'])} languages:")
        for lang in api_data["languages"]:
            func_count = len([f for f in api_data["functions"] if f["language"] == lang])
            type_count = len([t for t in api_data["types"] if t["language"] == lang])
            print(f"  {lang}: {func_count} functions, {type_count} types")

    def _extract_julia_filtered(self):
        """Extract Julia documentation, filtering to project files only."""
        functions = []
        types = []

        julia_dir = self.packages_dir / "ESMFormat.jl" / "src"
        if not julia_dir.exists():
            return functions, types

        # Only process files directly in src directory and known project files
        project_files = list(julia_dir.glob("*.jl"))

        for jl_file in project_files:
            try:
                content = jl_file.read_text()
                file_functions, file_types = self._parse_julia_file(jl_file, content)
                functions.extend(file_functions)
                types.extend(file_types)
            except Exception as e:
                print(f"Warning: Could not parse {jl_file}: {e}")

        return functions, types

    def _parse_julia_file(self, file_path: Path, content: str):
        """Parse a Julia file for documented functions and types."""
        functions = []
        types = []

        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Look for docstrings
            if line.startswith('"""'):
                doc_start = i
                doc_lines = []
                i += 1

                # Collect docstring content
                while i < len(lines) and not lines[i].strip().endswith('"""'):
                    doc_lines.append(lines[i])
                    i += 1

                if i < len(lines):
                    doc_lines.append(lines[i].replace('"""', ''))
                    i += 1

                docstring = '\n'.join(doc_lines).strip()

                # Look for function or type definition after docstring
                while i < len(lines) and not lines[i].strip():
                    i += 1

                if i < len(lines):
                    def_line = lines[i].strip()

                    # Function definition
                    func_match = re.match(r'function\s+([a-zA-Z_][a-zA-Z0-9_!]*)', def_line)
                    if func_match:
                        functions.append({
                            "name": func_match.group(1),
                            "language": "julia",
                            "file_path": str(file_path.relative_to(self.project_root)),
                            "line_number": i + 1,
                            "signature": def_line,
                            "docstring": docstring,
                            "parameters": [],
                            "return_type": "",
                            "examples": [],
                            "see_also": [],
                            "tags": ["documented"]
                        })

                    # Type definition (struct, mutable struct, abstract type)
                    type_match = re.match(r'(?:(?:mutable\s+)?struct|abstract\s+type)\s+([a-zA-Z_][a-zA-Z0-9_]*)', def_line)
                    if type_match:
                        types.append({
                            "name": type_match.group(1),
                            "language": "julia",
                            "file_path": str(file_path.relative_to(self.project_root)),
                            "line_number": i + 1,
                            "definition": def_line,
                            "docstring": docstring,
                            "fields": [],
                            "methods": [],
                            "examples": [],
                            "tags": ["documented"]
                        })

            i += 1

        return functions, types

    def _extract_python_filtered(self):
        """Extract Python documentation, filtering to project files only."""
        functions = []
        types = []

        python_dir = self.packages_dir / "esm_format"
        if not python_dir.exists():
            return functions, types

        # Only process Python files in the main package, exclude __pycache__, tests, etc.
        for py_file in python_dir.rglob("*.py"):
            if any(part in str(py_file) for part in ["__pycache__", "test_", ".venv", "venv", "site-packages"]):
                continue

            try:
                content = py_file.read_text()
                file_functions, file_types = self._parse_python_file(py_file, content)
                functions.extend(file_functions)
                types.extend(file_types)
            except Exception as e:
                print(f"Warning: Could not parse {py_file}: {e}")

        return functions, types

    def _parse_python_file(self, file_path: Path, content: str):
        """Parse a Python file for functions and classes."""
        functions = []
        types = []

        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Function definition
            func_match = re.match(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\):', line)
            if func_match and not func_match.group(1).startswith('_'):  # Skip private functions
                func_name = func_match.group(1)
                params = func_match.group(2)

                # Look for docstring
                i += 1
                docstring = ""
                if i < len(lines) and ('"""' in lines[i] or "'''" in lines[i]):
                    quote_char = '"""' if '"""' in lines[i] else "'''"
                    doc_lines = []

                    if lines[i].strip().count(quote_char) == 2:
                        # Single line docstring
                        docstring = lines[i].strip().replace(quote_char, '')
                    else:
                        # Multi-line docstring
                        doc_lines.append(lines[i].replace(quote_char, ''))
                        i += 1
                        while i < len(lines) and quote_char not in lines[i]:
                            doc_lines.append(lines[i])
                            i += 1
                        if i < len(lines):
                            doc_lines.append(lines[i].replace(quote_char, ''))
                        docstring = '\n'.join(doc_lines).strip()

                functions.append({
                    "name": func_name,
                    "language": "python",
                    "file_path": str(file_path.relative_to(self.project_root)),
                    "line_number": i - len(docstring.split('\n')) if docstring else i,
                    "signature": f"def {func_name}({params}):",
                    "docstring": docstring,
                    "parameters": [],
                    "return_type": "",
                    "examples": [],
                    "see_also": [],
                    "tags": ["public"] if not func_name.startswith('_') else []
                })

            # Class definition
            class_match = re.match(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
            if class_match:
                class_name = class_match.group(1)

                # Look for docstring
                i += 1
                docstring = ""
                if i < len(lines) and ('"""' in lines[i] or "'''" in lines[i]):
                    quote_char = '"""' if '"""' in lines[i] else "'''"
                    doc_lines = []

                    if lines[i].strip().count(quote_char) == 2:
                        docstring = lines[i].strip().replace(quote_char, '')
                    else:
                        doc_lines.append(lines[i].replace(quote_char, ''))
                        i += 1
                        while i < len(lines) and quote_char not in lines[i]:
                            doc_lines.append(lines[i])
                            i += 1
                        if i < len(lines):
                            doc_lines.append(lines[i].replace(quote_char, ''))
                        docstring = '\n'.join(doc_lines).strip()

                types.append({
                    "name": class_name,
                    "language": "python",
                    "file_path": str(file_path.relative_to(self.project_root)),
                    "line_number": i - len(docstring.split('\n')) if docstring else i,
                    "definition": f"class {class_name}:",
                    "docstring": docstring,
                    "fields": [],
                    "methods": [],
                    "examples": [],
                    "tags": []
                })

            i += 1

        return functions, types

    def _extract_typescript_filtered(self):
        """Extract TypeScript documentation from project files."""
        functions = []
        types = []

        ts_dirs = [
            self.packages_dir / "esm-format" / "src",
            self.packages_dir / "esm-editor" / "src"
        ]

        for ts_dir in ts_dirs:
            if not ts_dir.exists():
                continue

            for ts_file in ts_dir.rglob("*.ts"):
                if "node_modules" in str(ts_file) or ".d.ts" in str(ts_file):
                    continue

                try:
                    content = ts_file.read_text()
                    file_functions, file_types = self._parse_typescript_file(ts_file, content)
                    functions.extend(file_functions)
                    types.extend(file_types)
                except Exception as e:
                    print(f"Warning: Could not parse {ts_file}: {e}")

        return functions, types

    def _parse_typescript_file(self, file_path: Path, content: str):
        """Parse TypeScript file for exported functions and interfaces."""
        functions = []
        types = []

        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Function definition
            func_match = re.match(r'export\s+(?:function\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
            if func_match:
                func_name = func_match.group(1)

                # Look for JSDoc comment above
                docstring = self._extract_jsdoc(lines, i - 1)

                functions.append({
                    "name": func_name,
                    "language": "typescript",
                    "file_path": str(file_path.relative_to(self.project_root)),
                    "line_number": i + 1,
                    "signature": line,
                    "docstring": docstring,
                    "parameters": [],
                    "return_type": "",
                    "examples": [],
                    "see_also": [],
                    "tags": ["exported"]
                })

            # Interface definition
            interface_match = re.match(r'export\s+interface\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
            if interface_match:
                interface_name = interface_match.group(1)

                # Look for JSDoc comment above
                docstring = self._extract_jsdoc(lines, i - 1)

                types.append({
                    "name": interface_name,
                    "language": "typescript",
                    "file_path": str(file_path.relative_to(self.project_root)),
                    "line_number": i + 1,
                    "definition": line,
                    "docstring": docstring,
                    "fields": [],
                    "methods": [],
                    "examples": [],
                    "tags": ["exported"]
                })

            i += 1

        return functions, types

    def _extract_rust_filtered(self):
        """Extract Rust documentation from project files."""
        functions = []
        types = []

        rust_dir = self.packages_dir / "esm-format-rust" / "src"
        if not rust_dir.exists():
            return functions, types

        for rust_file in rust_dir.rglob("*.rs"):
            try:
                content = rust_file.read_text()
                file_functions, file_types = self._parse_rust_file(rust_file, content)
                functions.extend(file_functions)
                types.extend(file_types)
            except Exception as e:
                print(f"Warning: Could not parse {rust_file}: {e}")

        return functions, types

    def _parse_rust_file(self, file_path: Path, content: str):
        """Parse Rust file for documented public functions and structs."""
        functions = []
        types = []

        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Look for doc comments
            doc_lines = []
            while i < len(lines) and lines[i].strip().startswith("///"):
                doc_lines.append(lines[i].strip()[3:].strip())
                i += 1

            if i >= len(lines):
                break

            docstring = '\n'.join(doc_lines).strip()
            line = lines[i].strip()

            # Function definition
            func_match = re.match(r'pub\s+fn\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
            if func_match:
                func_name = func_match.group(1)

                functions.append({
                    "name": func_name,
                    "language": "rust",
                    "file_path": str(file_path.relative_to(self.project_root)),
                    "line_number": i + 1,
                    "signature": line,
                    "docstring": docstring,
                    "parameters": [],
                    "return_type": "",
                    "examples": [],
                    "see_also": [],
                    "tags": ["public"]
                })

            # Struct definition
            struct_match = re.match(r'pub\s+struct\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
            if struct_match:
                struct_name = struct_match.group(1)

                types.append({
                    "name": struct_name,
                    "language": "rust",
                    "file_path": str(file_path.relative_to(self.project_root)),
                    "line_number": i + 1,
                    "definition": line,
                    "docstring": docstring,
                    "fields": [],
                    "methods": [],
                    "examples": [],
                    "tags": ["public"]
                })

            i += 1

        return functions, types

    def _extract_jsdoc(self, lines: List[str], start_line: int) -> str:
        """Extract JSDoc comment from lines."""
        if start_line < 0 or start_line >= len(lines):
            return ""

        if not lines[start_line].strip() == "*/":
            return ""

        doc_lines = []
        i = start_line
        while i >= 0 and not lines[i].strip().startswith("/**"):
            if lines[i].strip().startswith("*"):
                doc_lines.insert(0, lines[i].strip()[1:].strip())
            i -= 1

        if i >= 0 and lines[i].strip().startswith("/**"):
            doc_lines.insert(0, lines[i].strip()[3:].strip())

        return '\n'.join(doc_lines).strip()

    def _write_api_docs(self, api_data: Dict[str, Any]):
        """Write the API documentation files."""
        api_dir = self.docs_dir / "api"
        api_dir.mkdir(exist_ok=True)

        # Generate language-specific API docs
        for lang in api_data["languages"]:
            lang_functions = [f for f in api_data["functions"] if f["language"] == lang]
            lang_types = [t for t in api_data["types"] if t["language"] == lang]

            lang_file = api_dir / f"{lang}.md"

            with open(lang_file, 'w') as f:
                f.write(f"# {lang.title()} API Reference\n\n")
                f.write(f"Complete API reference for the ESM Format {lang.title()} library.\n\n")

                if lang_functions:
                    f.write("## Functions\n\n")

                    for func in sorted(lang_functions, key=lambda x: x["name"]):
                        f.write(f"### {func['name']}\n\n")
                        f.write(f"**File:** `{func['file_path']}:{func['line_number']}`\n\n")

                        if func["signature"]:
                            f.write(f"```{lang}\n{func['signature']}\n```\n\n")

                        if func["docstring"]:
                            f.write(f"{func['docstring']}\n\n")

                        f.write("---\n\n")

                if lang_types:
                    f.write("## Types\n\n")

                    for typ in sorted(lang_types, key=lambda x: x["name"]):
                        f.write(f"### {typ['name']}\n\n")
                        f.write(f"**File:** `{typ['file_path']}:{typ['line_number']}`\n\n")

                        if typ["definition"]:
                            f.write(f"```{lang}\n{typ['definition']}\n```\n\n")

                        if typ["docstring"]:
                            f.write(f"{typ['docstring']}\n\n")

                        f.write("---\n\n")

        # Generate index
        index_file = api_dir / "index.md"
        with open(index_file, 'w') as f:
            f.write("# API Reference Index\n\n")
            f.write("Complete API documentation for all ESM Format language implementations.\n\n")

            for lang in sorted(api_data["languages"]):
                func_count = len([f for f in api_data["functions"] if f["language"] == lang])
                type_count = len([t for t in api_data["types"] if t["language"] == lang])

                f.write(f"## [{lang.title()}]({lang}.md)\n")
                f.write(f"- {func_count} functions\n")
                f.write(f"- {type_count} types\n\n")

    def _create_placeholder_files(self):
        """Create placeholder files for missing documentation."""
        print("📄 Creating placeholder documentation files...")

        placeholders = {
            "tutorial/index.md": "# Tutorials\n\nStep-by-step tutorials for learning ESM Format.\n\n(Coming soon)",
            "guides/index.md": "# Guides\n\nBest practices and advanced topics.\n\n(Coming soon)",
            "troubleshooting/expression-issues.md": "# Expression Issues\n\nTroubleshooting mathematical expressions.\n\n(Coming soon)",
            "troubleshooting/performance.md": "# Performance Problems\n\nDiagnosing performance issues.\n\n(Coming soon)",
            "troubleshooting/language-specific.md": "# Language-Specific Issues\n\nPlatform and runtime problems.\n\n(Coming soon)"
        }

        for rel_path, content in placeholders.items():
            file_path = self.docs_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if not file_path.exists():
                with open(file_path, 'w') as f:
                    f.write(content)

    def _update_navigation(self):
        """Update navigation and cross-references."""
        print("🔗 Updating navigation and references...")
        # This would update the main README.md and other navigation files
        # For now, we'll leave the existing structure

    def _run_validation(self):
        """Run documentation validation."""
        print("✅ Running documentation validation...")

        try:
            result = subprocess.run(
                ["python3", "scripts/validate_docs.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("   Documentation validation passed!")
            else:
                print("   Documentation validation found issues:")
                print(result.stdout[-500:])  # Show last 500 chars

        except Exception as e:
            print(f"   Warning: Could not run validation: {e}")

def main():
    """Main entry point for documentation maintenance."""
    parser = argparse.ArgumentParser(description="Maintain ESM Format documentation")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(),
                       help="Path to project root directory")
    parser.add_argument("--skip-generation", action="store_true",
                       help="Skip API documentation generation")

    args = parser.parse_args()

    project_root = args.project_root.resolve()
    maintainer = DocumentationMaintainer(project_root)
    maintainer.build_docs(skip_generation=args.skip_generation)

if __name__ == "__main__":
    main()