<!-- adaptco-previz/README.md -->
# Adaptco Previz CLI

Adaptco Previz is a Node.js 20 command-line tool that validates asset descriptors and generates deterministic preview image stubs for pipeline testing.

## Features

- Validates asset descriptors with JSON Schema using Ajv.
- Generates preview artifacts with predictable filenames.
- Provides helpful CLI output suitable for automation.

## Prerequisites

- Node.js >= 20
- npm >= 9

## Installation

```bash
npm install
```

## Usage

Render a preview from a descriptor:

```bash
npm start -- render examples/descriptor.sample.json --out previews
```

The CLI prints the output path, and a `.png` stub will be created in the target directory.

Show help:

```bash
npm start -- --help
```

## Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Runs the CLI in watch mode (nodemon). |
| `npm run start` | Invokes the CLI. |
| `npm run build` | Placeholder build step. |
| `npm run test` | Executes Jest unit tests. |
| `npm run lint` | Lints the project with ESLint. |
| `npm run format` | Formats source files via Prettier. |

## Descriptor Schema

Descriptors must conform to [`schemas/asset-descriptor.schema.json`](schemas/asset-descriptor.schema.json). Example descriptor:

```json
{
  "id": "asset-42",
  "name": "Explainer Animation",
  "type": "video",
  "sourcePath": "assets/explainer/source.blend",
  "params": {
    "camera": "cam1",
    "duration": 120
  }
}
```

## Testing

```bash
npm test
```

## Docker

```bash
docker build -t adaptco-previz .
docker run --rm adaptco-previz --help
```

The container image defaults to running the CLI with the `--help` flag.

## Project Structure

```
src/
  cli.js
  render.js
  validator.js
schemas/
  asset-descriptor.schema.json
examples/
  descriptor.sample.json
previews/
  (generated previews)
```

## License

MIT
