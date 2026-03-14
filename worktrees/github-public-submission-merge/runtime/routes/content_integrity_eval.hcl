# content.integrity.eval.v1 sandbox orchestrator binding
#
# This binding keeps the route definition co-located with the manifest so
# the orchestrator can discover the harness and IO endpoints without having
# to ship ad-hoc overrides.

binding "content_integrity_eval" {
  cell        = "content-integrity-eval"
  manifest    = "manifests/content.integrity.eval.v1.yaml"
  harness     = "runtime/simulation/content_integrity_eval_harness.py"

  ingress  = ["scenario_bundle"]
  egress   = ["aggregate_metrics", "audit_ledger"]
}
