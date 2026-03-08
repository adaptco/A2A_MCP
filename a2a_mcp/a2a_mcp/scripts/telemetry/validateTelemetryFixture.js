#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function resolveFixturePath() {
  const defaultCapsuleDir = process.env.TELEMETRY_CAPSULE_DIR || path.resolve(__dirname, '../../capsules/telemetry');
  const defaultEventSource = process.env.TELEMETRY_EVENT_SOURCE || 'capsule.telemetry.render.v1.events_examples';
  const defaultFile = process.env.TELEMETRY_EVENT_FILE || path.join(defaultCapsuleDir, `${defaultEventSource}.jsonl`);

  const [firstArg] = process.argv.slice(2);
  if (!firstArg) {
    return defaultFile;
  }

  if (path.isAbsolute(firstArg)) {
    return firstArg;
  }

  return path.resolve(process.cwd(), firstArg);
}

function readFixture(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return content
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  } catch (error) {
    throw new Error(`Unable to read fixture at ${filePath}: ${error.message}`);
  }
}

function parseEvents(lines) {
  const events = [];

  for (const [index, line] of lines.entries()) {
    try {
      const parsed = JSON.parse(line);
      events.push(parsed);
    } catch (error) {
      throw new Error(`Line ${index + 1} is not valid JSON: ${error.message}`);
    }
  }

  return events;
}

function validateEvents(events) {
  const errors = [];
  const warnings = [];
  const typeSet = new Set();

  let expectedSequence = null;
  let renderStats = createStatsCollector();
  let compositeStats = createStatsCollector();
  let ioStats = createStatsCollector();

  events.forEach((event, index) => {
    const location = `event ${index + 1}`;

    if (typeof event !== 'object' || event === null) {
      errors.push(`${location}: expected an object but received ${typeof event}`);
      return;
    }

    if (!Object.prototype.hasOwnProperty.call(event, 'type')) {
      errors.push(`${location}: missing required field \\"type\\"`);
    } else if (typeof event.type !== 'string' || !event.type.trim()) {
      errors.push(`${location}: field \\"type\\" must be a non-empty string`);
    } else {
      typeSet.add(event.type);
    }

    if (!Object.prototype.hasOwnProperty.call(event, 'sequence')) {
      errors.push(`${location}: missing required field \\"sequence\\"`);
    } else if (!Number.isInteger(event.sequence)) {
      errors.push(`${location}: field \\"sequence\\" must be an integer`);
    } else if (event.sequence < 0) {
      errors.push(`${location}: field \\"sequence\\" must be non-negative`);
    } else if (expectedSequence === null) {
      expectedSequence = event.sequence + 1;
    } else {
      if (event.sequence !== expectedSequence) {
        warnings.push(
          `${location}: expected sequence ${expectedSequence} but received ${event.sequence}`
        );
        expectedSequence = event.sequence + 1;
      } else {
        expectedSequence += 1;
      }
    }

    if (event.timings && typeof event.timings === 'object') {
      updateStats(renderStats, event.timings, 'render_ms', location, warnings);
      updateStats(compositeStats, event.timings, 'composite_ms', location, warnings);
      updateStats(ioStats, event.timings, 'io_ms', location, warnings);
    }
  });

  return {
    errors,
    warnings,
    stats: {
      eventCount: events.length,
      typeCount: typeSet.size,
      types: [...typeSet].sort(),
      timings: {
        render: finalizeStats(renderStats),
        composite: finalizeStats(compositeStats),
        io: finalizeStats(ioStats)
      }
    }
  };
}

function createStatsCollector() {
  return {
    count: 0,
    min: Infinity,
    max: -Infinity,
    sum: 0,
    values: []
  };
}

function updateStats(stats, timings, key, location, warnings) {
  if (!Object.prototype.hasOwnProperty.call(timings, key)) {
    warnings.push(`${location}: timings missing \\"${key}\\"`);
    return;
  }

  const value = timings[key];
  if (typeof value !== 'number' || Number.isNaN(value)) {
    warnings.push(`${location}: timings field \\"${key}\\" must be a number`);
    return;
  }

  if (value < 0) {
    warnings.push(`${location}: timings field \\"${key}\\" should be non-negative (received ${value})`);
  }

  stats.count += 1;
  stats.min = Math.min(stats.min, value);
  stats.max = Math.max(stats.max, value);
  stats.sum += value;
  stats.values.push(value);
}

function computePercentile(sortedValues, percentile) {
  if (!sortedValues.length) {
    return null;
  }

  const index = (percentile / 100) * (sortedValues.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;

  if (lower === upper) {
    return sortedValues[lower];
  }

  return sortedValues[lower] * (1 - weight) + sortedValues[upper] * weight;
}

function finalizeStats(stats) {
  if (!stats.count) {
    return { count: 0 };
  }

  const average = stats.sum / stats.count;
  const sorted = [...stats.values].sort((a, b) => a - b);
  return {
    count: stats.count,
    min: stats.min,
    max: stats.max,
    average,
    median: computePercentile(sorted, 50),
    p95: computePercentile(sorted, 95)
  };
}

function formatRange(stats, label) {
  if (!stats.count) {
    return `- ${label}: no samples`;
  }

  return (
    `- ${label}: min ${stats.min.toFixed(2)}ms, max ${stats.max.toFixed(2)}ms, ` +
    `avg ${stats.average.toFixed(2)}ms, median ${stats.median.toFixed(2)}ms, p95 ${stats.p95.toFixed(2)}ms ` +
    `(${stats.count} samples)`
  );
}

function main() {
  const filePath = resolveFixturePath();

  try {
    if (!fs.existsSync(filePath)) {
      throw new Error(`Fixture not found at ${filePath}`);
    }

    const lines = readFixture(filePath);
    if (!lines.length) {
      throw new Error(`Fixture at ${filePath} is empty`);
    }

    const events = parseEvents(lines);
    const { errors, warnings, stats } = validateEvents(events);

    warnings.forEach((warning) => {
      console.warn(`⚠️  ${warning}`);
    });

    if (errors.length) {
      errors.forEach((error) => {
        console.error(`❌ ${error}`);
      });
      console.error(`Telemetry fixture validation failed with ${errors.length} error(s).`);
      process.exit(1);
    }

    console.log(`✅ Validated ${stats.eventCount} telemetry event(s) across ${stats.typeCount} type(s).`);
    if (stats.types.length) {
      console.log(`- Event types: ${stats.types.join(', ')}`);
    }
    console.log(formatRange(stats.timings.render, 'render_ms'));
    console.log(formatRange(stats.timings.composite, 'composite_ms'));
    console.log(formatRange(stats.timings.io, 'io_ms'));
  } catch (error) {
    console.error(`❌ ${error.message}`);
    process.exit(1);
  }
}

main();
