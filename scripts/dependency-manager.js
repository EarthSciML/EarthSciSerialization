#!/usr/bin/env node

/**
 * EarthSciSerialization Package Dependency Manager
 *
 * Provides cross-language package dependency resolution, version compatibility
 * checking, dependency tree analysis, and automatic updates.
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawn } = require('child_process');

class DependencyManager {
  constructor() {
    this.workspaceRoot = path.resolve(__dirname, '..');
    this.workspaceConfig = this.loadWorkspaceConfig();
    this.packageManagers = {
      typescript: {
        configFile: 'package.json',
        lockFile: 'package-lock.json',
        installCommand: 'npm install',
        updateCommand: 'npm update',
        listCommand: 'npm list --json',
        parser: this.parseNpmPackage.bind(this)
      },
      python: {
        configFile: 'pyproject.toml',
        lockFile: 'poetry.lock',
        installCommand: 'pip install -e .',
        updateCommand: 'pip install --upgrade',
        listCommand: 'pip list --format=json',
        parser: this.parsePythonPackage.bind(this)
      },
      julia: {
        configFile: 'Project.toml',
        lockFile: 'Manifest.toml',
        installCommand: 'julia --project=. -e "using Pkg; Pkg.instantiate()"',
        updateCommand: 'julia --project=. -e "using Pkg; Pkg.update()"',
        listCommand: 'julia --project=. -e "using Pkg; println(Pkg.status())"',
        parser: this.parseJuliaPackage.bind(this)
      },
      rust: {
        configFile: 'Cargo.toml',
        lockFile: 'Cargo.lock',
        installCommand: 'cargo build',
        updateCommand: 'cargo update',
        listCommand: 'cargo tree --format "{p} {v}"',
        parser: this.parseRustPackage.bind(this)
      },
      go: {
        configFile: 'go.mod',
        lockFile: 'go.sum',
        installCommand: 'go mod download',
        updateCommand: 'go get -u ./...',
        listCommand: 'go list -m -u all',
        parser: this.parseGoPackage.bind(this)
      }
    };
  }

  loadWorkspaceConfig() {
    const configPath = path.join(this.workspaceRoot, 'workspace.json');
    if (!fs.existsSync(configPath)) {
      throw new Error('workspace.json not found. Run from the workspace root.');
    }
    return JSON.parse(fs.readFileSync(configPath, 'utf8'));
  }

  /**
   * Parse npm package.json and dependencies
   */
  parseNpmPackage(packagePath) {
    const pkgJsonPath = path.join(packagePath, 'package.json');
    if (!fs.existsSync(pkgJsonPath)) {
      throw new Error(`package.json not found in ${packagePath}`);
    }

    const pkg = JSON.parse(fs.readFileSync(pkgJsonPath, 'utf8'));
    return {
      name: pkg.name,
      version: pkg.version,
      dependencies: pkg.dependencies || {},
      devDependencies: pkg.devDependencies || {},
      peerDependencies: pkg.peerDependencies || {},
      engines: pkg.engines || {}
    };
  }

  /**
   * Parse Python pyproject.toml and dependencies
   */
  parsePythonPackage(packagePath) {
    const pyprojectPath = path.join(packagePath, 'pyproject.toml');
    if (!fs.existsSync(pyprojectPath)) {
      throw new Error(`pyproject.toml not found in ${packagePath}`);
    }

    // Simple TOML parsing for dependencies
    const content = fs.readFileSync(pyprojectPath, 'utf8');
    const lines = content.split('\n');

    let inDependencies = false;
    let inDevDependencies = false;
    const dependencies = {};
    const devDependencies = {};

    lines.forEach(line => {
      line = line.trim();
      if (line === 'dependencies = [') {
        inDependencies = true;
        inDevDependencies = false;
      } else if (line.includes('dev = [')) {
        inDependencies = false;
        inDevDependencies = true;
      } else if (line === ']' && (inDependencies || inDevDependencies)) {
        inDependencies = false;
        inDevDependencies = false;
      } else if (inDependencies && line.includes('"')) {
        const match = line.match(/"([^"]+)"/);
        if (match) {
          const depString = match[1];
          const [name, version] = depString.includes('>=')
            ? depString.split('>=')
            : [depString, '*'];
          dependencies[name] = version;
        }
      } else if (inDevDependencies && line.includes('"')) {
        const match = line.match(/"([^"]+)"/);
        if (match) {
          const depString = match[1];
          const [name, version] = depString.includes('>=')
            ? depString.split('>=')
            : [depString, '*'];
          devDependencies[name] = version;
        }
      }
    });

    // Extract version from project section
    const versionMatch = content.match(/version\s*=\s*"([^"]+)"/);
    const nameMatch = content.match(/name\s*=\s*"([^"]+)"/);

    return {
      name: nameMatch ? nameMatch[1] : path.basename(packagePath),
      version: versionMatch ? versionMatch[1] : '0.1.0',
      dependencies,
      devDependencies,
      engines: { python: '>=3.8' }
    };
  }

  /**
   * Parse Julia Project.toml and dependencies
   */
  parseJuliaPackage(packagePath) {
    const projectPath = path.join(packagePath, 'Project.toml');
    if (!fs.existsSync(projectPath)) {
      throw new Error(`Project.toml not found in ${packagePath}`);
    }

    const content = fs.readFileSync(projectPath, 'utf8');
    const lines = content.split('\n');

    let inDeps = false;
    let inCompat = false;
    const dependencies = {};
    const compatibility = {};

    lines.forEach(line => {
      line = line.trim();
      if (line === '[deps]') {
        inDeps = true;
        inCompat = false;
      } else if (line === '[compat]') {
        inDeps = false;
        inCompat = true;
      } else if (line.startsWith('[') && line !== '[deps]' && line !== '[compat]') {
        inDeps = false;
        inCompat = false;
      } else if (inDeps && line.includes('=')) {
        const [name, uuid] = line.split('=').map(s => s.trim().replace(/"/g, ''));
        dependencies[name] = uuid;
      } else if (inCompat && line.includes('=')) {
        const [name, version] = line.split('=').map(s => s.trim().replace(/"/g, ''));
        compatibility[name] = version;
      }
    });

    const versionMatch = content.match(/version\s*=\s*"([^"]+)"/);
    const nameMatch = content.match(/name\s*=\s*"([^"]+)"/);

    return {
      name: nameMatch ? nameMatch[1] : path.basename(packagePath),
      version: versionMatch ? versionMatch[1] : '0.1.0',
      dependencies,
      compatibility,
      engines: { julia: '1' }
    };
  }

  /**
   * Parse Rust Cargo.toml and dependencies
   */
  parseRustPackage(packagePath) {
    const cargoPath = path.join(packagePath, 'Cargo.toml');
    if (!fs.existsSync(cargoPath)) {
      throw new Error(`Cargo.toml not found in ${packagePath}`);
    }

    const content = fs.readFileSync(cargoPath, 'utf8');
    const lines = content.split('\n');

    let inDependencies = false;
    let inDevDependencies = false;
    let inBuildDependencies = false;
    const dependencies = {};
    const devDependencies = {};
    const buildDependencies = {};

    lines.forEach(line => {
      line = line.trim();
      if (line === '[dependencies]') {
        inDependencies = true;
        inDevDependencies = false;
        inBuildDependencies = false;
      } else if (line === '[dev-dependencies]') {
        inDependencies = false;
        inDevDependencies = true;
        inBuildDependencies = false;
      } else if (line === '[build-dependencies]') {
        inDependencies = false;
        inDevDependencies = false;
        inBuildDependencies = true;
      } else if (line.startsWith('[') && line !== '[dependencies]' && line !== '[dev-dependencies]' && line !== '[build-dependencies]') {
        inDependencies = false;
        inDevDependencies = false;
        inBuildDependencies = false;
      } else if ((inDependencies || inDevDependencies || inBuildDependencies) && line.includes('=')) {
        const [name, versionSpec] = line.split('=').map(s => s.trim());
        const version = versionSpec.replace(/["{},]/g, '').trim();

        if (inDependencies) {
          dependencies[name] = version;
        } else if (inDevDependencies) {
          devDependencies[name] = version;
        } else if (inBuildDependencies) {
          buildDependencies[name] = version;
        }
      }
    });

    // Extract package info from [package] section
    const versionMatch = content.match(/\[package\][\s\S]*?version\s*=\s*"([^"]+)"/);
    const nameMatch = content.match(/\[package\][\s\S]*?name\s*=\s*"([^"]+)"/);
    const editionMatch = content.match(/\[package\][\s\S]*?edition\s*=\s*"([^"]+)"/);

    return {
      name: nameMatch ? nameMatch[1] : path.basename(packagePath),
      version: versionMatch ? versionMatch[1] : '0.1.0',
      dependencies,
      devDependencies,
      buildDependencies,
      engines: { rust: editionMatch ? editionMatch[1] : '2021' }
    };
  }

  /**
   * Parse Go go.mod and dependencies
   */
  parseGoPackage(packagePath) {
    const goModPath = path.join(packagePath, 'go.mod');
    if (!fs.existsSync(goModPath)) {
      throw new Error(`go.mod not found in ${packagePath}`);
    }

    const content = fs.readFileSync(goModPath, 'utf8');
    const lines = content.split('\n');

    let inRequire = false;
    const dependencies = {};
    let moduleName = '';
    let goVersion = '';

    lines.forEach(line => {
      line = line.trim();
      if (line.startsWith('module ')) {
        moduleName = line.replace('module ', '').trim();
      } else if (line.startsWith('go ')) {
        goVersion = line.replace('go ', '').trim();
      } else if (line === 'require (' || line.startsWith('require (')) {
        inRequire = true;
      } else if (line === ')' && inRequire) {
        inRequire = false;
      } else if (inRequire && line.includes(' v')) {
        const parts = line.split(' ');
        const packageName = parts[0];
        const version = parts.find(p => p.startsWith('v'));
        if (packageName && version) {
          dependencies[packageName] = version;
        }
      } else if (line.startsWith('require ') && line.includes(' v') && !line.includes('(')) {
        // Single line require
        const requireLine = line.replace('require ', '').trim();
        const parts = requireLine.split(' ');
        const packageName = parts[0];
        const version = parts.find(p => p.startsWith('v'));
        if (packageName && version) {
          dependencies[packageName] = version;
        }
      }
    });

    return {
      name: moduleName || path.basename(packagePath),
      version: '0.1.0', // Go modules typically don't have a version in go.mod for the main module
      dependencies,
      engines: { go: goVersion || '1.19' }
    };
  }

  /**
   * Get all packages in the workspace
   */
  getAllPackages() {
    const packages = {};

    Object.entries(this.workspaceConfig.dependencies).forEach(([name, config]) => {
      const packagePath = path.resolve(this.workspaceRoot, config.path);
      const manager = this.packageManagers[config.type];

      if (!manager) {
        console.warn(`Unknown package type: ${config.type}`);
        return;
      }

      try {
        const packageInfo = manager.parser(packagePath);
        packages[name] = {
          ...packageInfo,
          path: packagePath,
          type: config.type,
          manager
        };
      } catch (error) {
        console.warn(`Failed to parse ${name}: ${error.message}`);
      }
    });

    return packages;
  }

  /**
   * Build dependency tree
   */
  buildDependencyTree() {
    const packages = this.getAllPackages();
    const tree = {};

    Object.entries(packages).forEach(([name, pkg]) => {
      tree[name] = {
        version: pkg.version,
        type: pkg.type,
        dependencies: pkg.dependencies,
        devDependencies: pkg.devDependencies || {},
        path: pkg.path
      };
    });

    return tree;
  }

  /**
   * Check for version conflicts
   */
  checkVersionConflicts() {
    const packages = this.getAllPackages();
    const conflicts = [];

    // Check for duplicate package names across different ecosystems
    const packagesByName = {};
    Object.entries(packages).forEach(([key, pkg]) => {
      const baseName = pkg.name.replace(/^esm-?format-?/i, '').toLowerCase();
      if (!packagesByName[baseName]) {
        packagesByName[baseName] = [];
      }
      packagesByName[baseName].push({ key, pkg });
    });

    // Check version consistency
    Object.entries(packagesByName).forEach(([baseName, pkgList]) => {
      if (pkgList.length > 1) {
        const versions = pkgList.map(({ pkg }) => pkg.version);
        const uniqueVersions = [...new Set(versions)];

        if (uniqueVersions.length > 1) {
          conflicts.push({
            type: 'version_mismatch',
            packages: pkgList.map(({ key, pkg }) => ({ name: key, version: pkg.version, type: pkg.type })),
            message: `Version mismatch for ${baseName}: ${uniqueVersions.join(', ')}`
          });
        }
      }
    });

    return conflicts;
  }

  /**
   * Update all package dependencies
   */
  async updateDependencies(packageName = null) {
    const packages = this.getAllPackages();
    const results = [];

    const packagesToUpdate = packageName
      ? { [packageName]: packages[packageName] }
      : packages;

    for (const [name, pkg] of Object.entries(packagesToUpdate)) {
      console.log(`Updating dependencies for ${name} (${pkg.type})...`);

      try {
        const cwd = pkg.path;
        let command = pkg.manager.updateCommand;

        // Special handling for Python with virtual environment
        if (pkg.type === 'python') {
          const venvPath = path.join(pkg.path, 'venv');
          if (fs.existsSync(venvPath)) {
            command = `source ${venvPath}/bin/activate && ${command}`;
          } else {
            command = `python3 -m venv venv && source venv/bin/activate && ${command}`;
          }
        }

        execSync(command, { cwd, stdio: 'inherit', shell: '/bin/bash' });
        results.push({ name, status: 'success' });
      } catch (error) {
        console.error(`Failed to update ${name}: ${error.message}`);
        results.push({ name, status: 'failed', error: error.message });
      }
    }

    return results;
  }

  /**
   * Install dependencies for a package
   */
  async installDependencies(packageName = null) {
    const packages = this.getAllPackages();
    const results = [];

    const packagesToInstall = packageName
      ? { [packageName]: packages[packageName] }
      : packages;

    for (const [name, pkg] of Object.entries(packagesToInstall)) {
      console.log(`Installing dependencies for ${name} (${pkg.type})...`);

      try {
        const cwd = pkg.path;
        let command = pkg.manager.installCommand;

        // Special handling for Python with virtual environment
        if (pkg.type === 'python') {
          const venvPath = path.join(pkg.path, 'venv');
          if (fs.existsSync(venvPath)) {
            command = `source ${venvPath}/bin/activate && ${command}`;
          } else {
            command = `python3 -m venv venv && source venv/bin/activate && ${command}`;
          }
        }

        execSync(command, { cwd, stdio: 'inherit', shell: '/bin/bash' });
        results.push({ name, status: 'success' });
      } catch (error) {
        console.error(`Failed to install dependencies for ${name}: ${error.message}`);
        results.push({ name, status: 'failed', error: error.message });
      }
    }

    return results;
  }

  /**
   * Generate compatibility report
   */
  generateCompatibilityReport() {
    const packages = this.getAllPackages();
    const tree = this.buildDependencyTree();
    const conflicts = this.checkVersionConflicts();

    const report = {
      timestamp: new Date().toISOString(),
      workspace: this.workspaceConfig.name,
      packages: Object.keys(packages).length,
      conflicts: conflicts.length,
      tree,
      conflicts,
      recommendations: []
    };

    // Add recommendations
    if (conflicts.length > 0) {
      report.recommendations.push(
        'Fix version conflicts by updating package versions to match'
      );
    }

    // Check for missing lock files
    Object.entries(packages).forEach(([name, pkg]) => {
      const lockFile = path.join(pkg.path, pkg.manager.lockFile);
      if (!fs.existsSync(lockFile)) {
        report.recommendations.push(
          `Generate lock file for ${name} by running install command`
        );
      }
    });

    return report;
  }

  /**
   * CLI interface
   */
  async run() {
    const [,, command, ...args] = process.argv;

    switch (command) {
      case 'list':
        const packages = this.getAllPackages();
        console.log('Workspace packages:');
        Object.entries(packages).forEach(([name, pkg]) => {
          console.log(`  ${name} (${pkg.type}): ${pkg.version}`);
        });
        break;

      case 'tree':
        const tree = this.buildDependencyTree();
        console.log('Dependency tree:');
        console.log(JSON.stringify(tree, null, 2));
        break;

      case 'conflicts':
        const conflicts = this.checkVersionConflicts();
        if (conflicts.length === 0) {
          console.log('No version conflicts found.');
        } else {
          console.log('Version conflicts:');
          conflicts.forEach(conflict => {
            console.log(`  ${conflict.message}`);
          });
        }
        break;

      case 'install':
        const packageName = args[0];
        await this.installDependencies(packageName);
        break;

      case 'update':
        const updatePackageName = args[0];
        await this.updateDependencies(updatePackageName);
        break;

      case 'report':
        const report = this.generateCompatibilityReport();
        console.log(JSON.stringify(report, null, 2));
        break;

      default:
        console.log(`
Usage: node dependency-manager.js <command> [options]

Commands:
  list                    List all packages in workspace
  tree                    Show dependency tree
  conflicts               Check for version conflicts
  install [package]       Install dependencies (all or specific package)
  update [package]        Update dependencies (all or specific package)
  report                  Generate compatibility report

Examples:
  node dependency-manager.js list
  node dependency-manager.js install esm-format-js
  node dependency-manager.js update
  node dependency-manager.js report
        `);
    }
  }
}

// Run if called directly
if (require.main === module) {
  const manager = new DependencyManager();
  manager.run().catch(console.error);
}

module.exports = DependencyManager;