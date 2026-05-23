{{- define "enterprise-rag.name" -}}
enterprise-rag
{{- end -}}

{{- define "enterprise-rag.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "enterprise-rag.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "enterprise-rag.labels" -}}
app.kubernetes.io/name: {{ include "enterprise-rag.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "enterprise-rag.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "enterprise-rag.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* Shared env: ConfigMap (non-secret) + Secret (sensitive) */}}
{{- define "enterprise-rag.envFrom" -}}
- configMapRef:
    name: {{ include "enterprise-rag.fullname" . }}-config
- secretRef:
    name: {{ include "enterprise-rag.fullname" . }}-secrets
{{- end -}}
