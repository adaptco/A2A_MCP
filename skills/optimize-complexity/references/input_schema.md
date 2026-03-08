# Input Schema

## Required columns

- `agent` (string)
- `tool_name` (string)
- `crud_category` (string)
- `complexity` (string or number)
- `input_parameter_count` (integer >= 0)

## Complexity values

Accepted forms:

- categorical: `simple`, `moderate`, `complex`
- numeric normalized: `0.0` to `1.0`
- numeric percent: `0` to `100` (auto-normalized with warning)

## Example row

```csv
agent,tool_name,crud_category,complexity,input_parameter_count
CoderAgent,repo.patch,update,complex,4
```

## Failure behavior

The script exits with code `2` on contract errors, such as:

- missing required columns
- invalid complexity token
- invalid or negative `input_parameter_count`
- empty CSV data rows