import { spawn } from 'node:child_process'
import { readdir } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { r2ObjectKey } from '../src/media/r2-key-aliases.js'

const MIME_TYPES = {
  '.gif': 'image/gif',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.mov': 'video/quicktime',
  '.mp4': 'video/mp4',
  '.pdf': 'application/pdf',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
}

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(scriptDirectory, '..')
const wranglerBin = path.join(frontendRoot, 'node_modules', 'wrangler', 'bin', 'wrangler.js')

const options = Object.fromEntries(
  process.argv.slice(2).reduce((entries, value, index, values) => {
    if (value.startsWith('--') && values[index + 1] && !values[index + 1].startsWith('--')) {
      entries.push([value.slice(2), values[index + 1]])
    }
    return entries
  }, []),
)

const bucket = options.bucket
const sourceRoot = path.resolve(frontendRoot, options.source || '../backend/data/media')
const concurrency = Math.max(1, Number.parseInt(options.concurrency || '4', 10))

if (!bucket) {
  console.error('Usage: node scripts/upload-r2-media.mjs --bucket <name> [--source <directory>] [--concurrency 4]')
  process.exit(2)
}

async function listFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const nested = await Promise.all(
    entries.map((entry) => {
      const fullPath = path.join(directory, entry.name)
      return entry.isDirectory() ? listFiles(fullPath) : [fullPath]
    }),
  )
  return nested.flat()
}

function runWrangler(arguments_) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [wranglerBin, ...arguments_], {
      cwd: frontendRoot,
      env: process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })
    let output = ''
    child.stdout.on('data', (chunk) => { output += chunk })
    child.stderr.on('data', (chunk) => { output += chunk })
    child.on('error', reject)
    child.on('close', (code) => {
      if (code === 0) resolve()
      else reject(new Error(output.trim() || `Wrangler exited with code ${code}`))
    })
  })
}

async function upload(filePath) {
  const sourceKey = path.relative(sourceRoot, filePath).split(path.sep).join('/')
  const key = r2ObjectKey(sourceKey)
  const contentType = MIME_TYPES[path.extname(filePath).toLowerCase()] || 'application/octet-stream'
  const arguments_ = [
    'r2', 'object', 'put', `${bucket}/${key}`,
    '--file', filePath,
    '--remote',
    '--content-type', contentType,
    '--cache-control', 'public, max-age=3600',
    '--force',
  ]

  let lastError
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      await runWrangler(arguments_)
      return sourceKey === key ? key : `${sourceKey} -> ${key}`
    } catch (error) {
      lastError = error
      if (attempt < 3) await new Promise((resolve) => setTimeout(resolve, attempt * 1000))
    }
  }
  throw new Error(`Failed to upload ${key}: ${lastError.message}`)
}

const files = (await listFiles(sourceRoot)).sort()
let nextIndex = 0
let completed = 0

console.log(`[r2] Uploading ${files.length} files from ${sourceRoot} to ${bucket}`)

async function worker() {
  while (nextIndex < files.length) {
    const index = nextIndex
    nextIndex += 1
    const key = await upload(files[index])
    completed += 1
    console.log(`[r2] ${completed}/${files.length} ${key}`)
  }
}

await Promise.all(Array.from({ length: Math.min(concurrency, files.length) }, () => worker()))
console.log(`[r2] Finished uploading ${completed} files.`)
