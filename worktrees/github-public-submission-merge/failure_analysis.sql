WITH failure_logs AS (
  SELECT
    terminal_command,
    success_metric,
    JSON_VALUE(vscode_state_delta, '$.edit.change.newText') AS code_snippet
  FROM
    `the-qube-5e031.firestore_export.emulator_training_sequences`
  WHERE success_metric < 0.5
  LIMIT 10
),
prompts_to_analyze AS (
  SELECT
    terminal_command,
    CONCAT(
      'Analyze failure: Command "', terminal_command,
      '" resulted in code "', IFNULL(code_snippet, 'none'),
      '" with a low success score of ', CAST(success_metric AS STRING),
      '. Explain the technical gap for the avatar training log.'
    ) AS prompt
  FROM failure_logs
)
SELECT
  t.terminal_command,
  t.ml_generate_text_result
FROM
  ML.GENERATE_TEXT(
    MODEL `the-qube-5e031.firestore_export.gemini_model`,
    TABLE prompts_to_analyze,
    STRUCT(
        0.2 AS temperature
    )
  ) AS t;
