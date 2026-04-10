import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { resolveSubsystemRefs, CircularReferenceError, RefLoadError } from './ref-loading.js'
import type { EsmFile } from './types.js'
import * as fs from 'node:fs/promises'
import * as os from 'node:os'
import * as path from 'node:path'

describe('resolveSubsystemRefs', () => {
  let tmpDir: string

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'esm-ref-test-'))
  })

  afterEach(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true })
  })

  it('does nothing for files with no refs', async () => {
    const file = {
      esm: '0.1.0',
      metadata: { name: 'test' },
      models: {
        Atm: { variables: {}, equations: [] },
      },
    } as unknown as EsmFile

    await resolveSubsystemRefs(file, tmpDir)
    expect(file.models!.Atm).toBeDefined()
  })

  it('resolves a local file ref into a subsystem', async () => {
    const refContent = JSON.stringify({
      esm: '0.1.0',
      metadata: { name: 'sub' },
      models: {
        Inner: {
          variables: { x: { type: 'state' } },
          equations: [],
        },
      },
    })
    await fs.writeFile(path.join(tmpDir, 'inner.esm.json'), refContent)

    const file = {
      esm: '0.1.0',
      metadata: { name: 'main' },
      models: {
        Outer: {
          variables: {},
          equations: [],
          subsystems: {
            Inner: { ref: './inner.esm.json' },
          },
        },
      },
    } as unknown as EsmFile

    await resolveSubsystemRefs(file, tmpDir)
    const inner = file.models!.Outer!.subsystems!.Inner as any
    expect(inner.ref).toBeUndefined()
    expect(inner.variables.x).toBeDefined()
  })

  it('throws RefLoadError when local file is missing', async () => {
    const file = {
      esm: '0.1.0',
      metadata: { name: 'main' },
      models: {
        Outer: {
          variables: {},
          equations: [],
          subsystems: {
            Missing: { ref: './does-not-exist.esm.json' },
          },
        },
      },
    } as unknown as EsmFile

    await expect(resolveSubsystemRefs(file, tmpDir)).rejects.toBeInstanceOf(RefLoadError)
  })

  it('detects circular references', async () => {
    const aContent = JSON.stringify({
      esm: '0.1.0',
      metadata: { name: 'a' },
      models: {
        A: {
          variables: {},
          equations: [],
          subsystems: { Cycle: { ref: './b.esm.json' } },
        },
      },
    })
    const bContent = JSON.stringify({
      esm: '0.1.0',
      metadata: { name: 'b' },
      models: {
        B: {
          variables: {},
          equations: [],
          subsystems: { Cycle: { ref: './a.esm.json' } },
        },
      },
    })
    await fs.writeFile(path.join(tmpDir, 'a.esm.json'), aContent)
    await fs.writeFile(path.join(tmpDir, 'b.esm.json'), bContent)

    const file = {
      esm: '0.1.0',
      metadata: { name: 'main' },
      models: {
        Root: {
          variables: {},
          equations: [],
          subsystems: { Start: { ref: './a.esm.json' } },
        },
      },
    } as unknown as EsmFile

    await expect(resolveSubsystemRefs(file, tmpDir)).rejects.toBeInstanceOf(CircularReferenceError)
  })

  it('resolves refs inside reaction systems', async () => {
    const refContent = JSON.stringify({
      esm: '0.1.0',
      metadata: { name: 'sub' },
      reaction_systems: {
        SubChem: {
          species: { O3: {} },
          parameters: {},
          reactions: [],
        },
      },
    })
    await fs.writeFile(path.join(tmpDir, 'subchem.esm.json'), refContent)

    const file = {
      esm: '0.1.0',
      metadata: { name: 'main' },
      reaction_systems: {
        Chem: {
          species: {},
          parameters: {},
          reactions: [],
          subsystems: {
            Sub: { ref: './subchem.esm.json' },
          },
        },
      },
    } as unknown as EsmFile

    await resolveSubsystemRefs(file, tmpDir)
    const sub = file.reaction_systems!.Chem!.subsystems!.Sub as any
    expect(sub.ref).toBeUndefined()
    expect(sub.species.O3).toBeDefined()
  })
})
