# Scoring Method

## Embedding vector

Each tool row is transformed into a 3D vector:

- `agent_id_encoded`: stable SHA-256 based value in `[0,1]`
- `complexity_normalized`: parsed complexity in `[0,1]`
- `input_count_normalized`: `input_parameter_count / max_input_count`

## Target vector

Default target is:

- `(0.5, 0.5, 0.5)`

CLI flags override target dimensions:

- `--target-complexity`
- `--target-input-count`

## Similarity

Cosine similarity is used for alignment scoring:

- `similarity_before = cosine(source_vector, target_vector)`

## Complexity redistribution

The optimized score is:

- `optimized_score = 0.5 * complexity_normalized + 0.5 * similarity_before`

Then binned into labels:

- `[0.00, 0.35)` -> `simple`
- `[0.35, 0.70)` -> `moderate`
- `[0.70, 1.00]` -> `complex`

## Determinism

Deterministic behavior is guaranteed by:

- stable hash encoding for agents
- no random operations
- fixed threshold bins
- stable row processing order