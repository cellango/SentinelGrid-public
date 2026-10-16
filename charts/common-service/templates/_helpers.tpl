{{- define "common-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "common-service.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "common-service.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "common-service.networkPolicyPorts" -}}
{{- $ports := .ports | default (list) -}}
{{- range $port := $ports }}
- port: {{ if kindIs "map" $port }}{{ get $port "port" }}{{ else }}{{ $port }}{{ end }}
  protocol: {{ if and (kindIs "map" $port) (hasKey $port "protocol") }}{{ get $port "protocol" }}{{ else }}TCP{{ end }}
{{- end }}
{{- end -}}
