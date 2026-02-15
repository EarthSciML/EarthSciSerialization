# Installation & Setup

Get the ESM format libraries installed and running on your system. Choose the language(s) that best fit your workflow.

## Quick Install

### Julia
```bash
julia -e 'using Pkg; Pkg.add(url="https://github.com/EarthSciML/EarthSciSerialization", subdir="packages/ESMFormat.jl")'
```

### TypeScript/JavaScript
```bash
npm install esm-format
```

### Python
```bash
pip install esm-format  # When available on PyPI
# Or install from source:
git clone https://github.com/EarthSciML/EarthSciSerialization.git
cd EarthSciSerialization/packages/esm_format
pip install -e .
```

### Rust
```bash
cargo install esm-format --features cli
# Or add to Cargo.toml:
# [dependencies]
# esm-format = "0.1.0"
```

## Detailed Installation

### System Requirements

**Minimum Requirements:**
- **Julia**: Version 1.8 or later
- **Node.js**: Version 16 or later (for TypeScript/JavaScript)
- **Python**: Version 3.8 or later
- **Rust**: Version 1.65 or later

**Recommended:**
- **Julia**: Version 1.9+ for best ModelingToolkit integration
- **Node.js**: Version 18+ for ESM support
- **Python**: Version 3.10+ for latest features
- **Rust**: Version 1.70+ for latest optimization features

### Julia Installation

#### From GitHub (Recommended)
```julia
using Pkg
Pkg.add(url="https://github.com/EarthSciML/EarthSciSerialization", subdir="packages/ESMFormat.jl")
```

#### Development Setup
```julia
using Pkg
Pkg.develop(url="https://github.com/EarthSciML/EarthSciSerialization", subdir="packages/ESMFormat.jl")
```

#### Verify Installation
```julia
using ESMFormat
println("ESMFormat.jl installed successfully!")

# Test basic functionality
esm_data = """{"esm": "0.1.0", "metadata": {"name": "Test"}}"""
esm_file = parse_esm(esm_data)
println("Loaded test model: ", esm_file.metadata.name)
```

### TypeScript/JavaScript Installation

#### NPM
```bash
npm install esm-format
```

#### Yarn
```bash
yarn add esm-format
```

#### Pnpm
```bash
pnpm add esm-format
```

#### CDN (Browser)
```html
<!-- ES Modules -->
<script type="module">
  import { load, validate } from 'https://unpkg.com/esm-format/dist/esm/index.js';
</script>

<!-- UMD (older browsers) -->
<script src="https://unpkg.com/esm-format/dist/umd/index.js"></script>
```

#### Verify Installation
```javascript
// Node.js/CommonJS
const { load, validate } = require('esm-format');

// ES Modules
import { load, validate } from 'esm-format';

// Test functionality
const esmData = '{"esm": "0.1.0", "metadata": {"name": "Test"}}';
const esmFile = load(esmData);
console.log('Loaded test model:', esmFile.metadata.name);
```

### Python Installation

#### From PyPI (when available)
```bash
pip install esm-format
```

#### From Source
```bash
git clone https://github.com/EarthSciML/EarthSciSerialization.git
cd EarthSciSerialization/packages/esm_format
pip install -e .
```

#### With Optional Dependencies
```bash
# For visualization support
pip install esm-format[viz]

# For symbolic computation
pip install esm-format[symbolic]

# All optional features
pip install esm-format[all]
```

#### Virtual Environment Setup
```bash
# Create virtual environment
python -m venv esm_env
source esm_env/bin/activate  # Linux/macOS
# esm_env\Scripts\activate   # Windows

# Install package
pip install esm-format
```

#### Conda Environment
```bash
# Create conda environment
conda create -n esm_env python=3.10
conda activate esm_env

# Install dependencies
conda install numpy scipy matplotlib sympy

# Install ESM format
pip install esm-format
```

#### Verify Installation
```python
import esm_format
print("esm-format installed successfully!")

# Test basic functionality
esm_data = '{"esm": "0.1.0", "metadata": {"name": "Test"}}'
esm_file = esm_format.load_esm(esm_data)
print(f"Loaded test model: {esm_file.metadata.name}")
```

### Rust Installation

#### CLI Tool
```bash
# Install from GitHub
cargo install --git https://github.com/EarthSciML/EarthSciSerialization \
  --root . esm-format --features cli

# Or clone and install locally
git clone https://github.com/EarthSciML/EarthSciSerialization.git
cd EarthSciSerialization/packages/esm-format-rust
cargo install --path . --features cli
```

#### Library Dependency
Add to your `Cargo.toml`:
```toml
[dependencies]
esm-format = { git = "https://github.com/EarthSciML/EarthSciSerialization", package = "esm-format" }

# Or with specific features
esm-format = { git = "https://github.com/EarthSciML/EarthSciSerialization", package = "esm-format", features = ["wasm"] }
```

#### WebAssembly
```bash
# Install wasm-pack
cargo install wasm-pack

# Clone repository
git clone https://github.com/EarthSciML/EarthSciSerialization.git
cd EarthSciSerialization/packages/esm-format-rust

# Build for web
wasm-pack build --target web --features wasm
```

#### Verify Installation
```bash
# CLI tool
esm --version
esm validate --help

# Test functionality
echo '{"esm": "0.1.0", "metadata": {"name": "Test"}}' > test.esm
esm validate test.esm
```

```rust
// Library usage
use esm_format::{load, validate};

fn main() {
    let esm_data = r#"{"esm": "0.1.0", "metadata": {"name": "Test"}}"#;
    let esm_file = load(esm_data).unwrap();
    println!("Loaded test model: {}", esm_file.metadata.name);
}
```

## Multi-Language Setup

For comprehensive ESM format development, you may want multiple languages:

### Complete Development Environment
```bash
# 1. Install Julia
curl -fsSL https://install.julialang.org | sh
julia -e 'using Pkg; Pkg.add(url="https://github.com/EarthSciML/EarthSciSerialization", subdir="packages/ESMFormat.jl")'

# 2. Install Node.js and package
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
npm install -g esm-format

# 3. Install Python and package
sudo apt-get install python3 python3-pip
pip install esm-format

# 4. Install Rust and CLI
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cargo install esm-format --features cli
```

### Docker Environment
```dockerfile
FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl git build-essential \
    python3 python3-pip \
    nodejs npm

# Install Julia
RUN curl -fsSL https://install.julialang.org | sh

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install ESM packages
RUN pip install esm-format
RUN npm install -g esm-format
RUN cargo install esm-format --features cli
RUN julia -e 'using Pkg; Pkg.add(url="https://github.com/EarthSciML/EarthSciSerialization", subdir="packages/ESMFormat.jl")'

WORKDIR /workspace
```

## Troubleshooting

### Common Issues

#### Julia Package Installation
```julia
# If you get package conflicts
using Pkg
Pkg.resolve()

# If you need to update dependencies
Pkg.update()

# Clear package cache if needed
Pkg.gc()
```

#### Node.js Module Resolution
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Python Installation Issues
```bash
# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Install with verbose output for debugging
pip install -v esm-format

# Use --user if permissions issues
pip install --user esm-format
```

#### Rust Compilation Errors
```bash
# Update Rust toolchain
rustup update

# Clear cargo cache
cargo clean

# Install with verbose output
cargo install --verbose esm-format --features cli
```

### Platform-Specific Notes

#### Windows
- Use PowerShell or Command Prompt with Administrator privileges
- Install Visual Studio Build Tools for Rust compilation
- Use Python from Microsoft Store or python.org installer

#### macOS
- Install Xcode Command Line Tools: `xcode-select --install`
- Consider using Homebrew for Node.js and Python
- M1/M2 Macs: Ensure native ARM64 builds when possible

#### Linux
- Install build essentials: `sudo apt-get install build-essential`
- For Ubuntu/Debian, use apt for system packages
- For CentOS/RHEL, use yum/dnf for system packages

### Version Compatibility

| ESM Format | Julia Package | TypeScript | Python | Rust CLI |
|------------|--------------|------------|---------|----------|
| 0.1.0      | 0.1.0        | 0.1.0     | 0.1.0   | 0.1.0    |

All packages are designed to be compatible with ESM Format version 0.1.0. Cross-language compatibility is maintained through the shared JSON schema.

## Next Steps

After installation:
1. **Try the Quick Start** — [Quick Start Guide](quick-start.md)
2. **Choose Your Language** — Jump to your language-specific guide:
   - [Julia](julia.md) — For simulation and scientific computing
   - [TypeScript](typescript.md) — For web applications
   - [Python](python.md) — For data analysis and visualization
   - [Rust](rust.md) — For performance-critical applications
3. **Explore Examples** — Check out [Real-World Examples](../examples/)

## Getting Help

- **Installation Issues** — Check the [Troubleshooting Guide](../troubleshooting/)
- **Language-Specific Problems** — See individual language guides
- **Bug Reports** — File issues in the [GitHub repository](https://github.com/EarthSciML/EarthSciSerialization)

Ready to get started? Head to the [Quick Start Guide](quick-start.md)!