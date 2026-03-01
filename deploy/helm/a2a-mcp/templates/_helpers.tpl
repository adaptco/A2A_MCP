{{- define "a2a-mcp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "a2a-mcp.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "a2a-mcp.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "a2a-mcp.labels" -}}
app.kubernetes.io/name: {{ include "a2a-mcp.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "a2a-mcp.mcpServiceName" -}}
{{- printf "%s-mcp" (include "a2a-mcp.fullname" .) -}}
{{- end -}}

{{- define "a2a-mcp.orchestratorServiceName" -}}
{{- printf "%s-orchestrator" (include "a2a-mcp.fullname" .) -}}
{{- end -}}

{{- define "a2a-mcp.postgresServiceName" -}}
{{- printf "%s-postgres" (include "a2a-mcp.fullname" .) -}}
{{- end -}}

{{- define "a2a-mcp.configName" -}}
{{- if .Values.config.nameOverride -}}
{{- .Values.config.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-config" (include "a2a-mcp.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "a2a-mcp.secretName" -}}
{{- if .Values.secrets.nameOverride -}}
{{- .Values.secrets.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-secret" (include "a2a-mcp.fullname" .) -}}
{{- end -}}
{{- end -}}
