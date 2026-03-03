# Platform Services

Deployed service versions, IPs, and URLs. Last updated: 2026-02-25, v0.160.0.

## GitOps & Platform Controllers

| Service | Version | Notes |
|---|---|---|
| FluxCD | v2.7.5 | `clusters/asgard/`, PAT `gh-homelab-fluxcd` |
| MetalLB | v0.15.3 | L2 mode, IPAddressPool 192.168.2.201-250 |
| ingress-nginx | v1.14.3 | LB 192.168.2.201, `allow-snippet-annotations=false` |
| cert-manager | v1.19.3 | Self-signed CA, clusterissuer `homelab-ca-issuer` |
| Tailscale operator | v1.94.2 | API server proxy, dual ingress on every app |
| ESO | v2.0.0 | ClusterSecretStore `onepassword-connect`, VIP 192.168.2.72 |
| NFS provisioner | v4.0.2 | StorageClass `nfs-kubernetes`, Retain policy |
| Longhorn | v1.11.0 | 2-replica, StorageClass `longhorn`, `defaultClass: false` |

## Monitoring Stack

| Service | Version | Notes |
|---|---|---|
| kube-prometheus-stack | chart 82.1.1 | Grafana 12.3.3, Prometheus v3.9.1, Alertmanager v0.31.1 |
| Grafana | 12.3.3 | Keycloak SSO, `grafana.oryx-tegu.ts.net` |
| Loki | 3.6.5 | chart 6.53.0 |
| Promtail | 3.5.1 | |
| pve-exporter | 3.8.1 | Proxmox node metrics |
| ServiceMonitor config | — | `serviceMonitorSelector: {}` + `NilUsesHelmValues: false` |

## Identity & Auth

| Service | Version | Notes |
|---|---|---|
| Keycloak | 26.5.3 | `homelab` realm, PostgreSQL VIP 192.168.2.44, `keycloak.oryx-tegu.ts.net` |
| OAuth2 Proxy | v7.14.2 | Protects 14/21 nginx ingresses |
| CoreDNS override | — | `keycloak.oryx-tegu.ts.net` → `keycloak.192.168.2.201.nip.io` |

## Backup

| Service | Version | Notes |
|---|---|---|
| Velero | v1.17.2 | CSI snapshots + Kopia, MinIO BSL |
| MinIO | chart 5.4.0 | 50Gi NFS, cluster-internal S3 |
| Snapshot Controller | v8.2.0 | VolumeSnapshotClass `longhorn-snapshot-vsc` |
| PostgreSQL backup | — | pg_dumpall CronJob → 192.168.2.161:/volume1/postgresql-backups |

## Applications

| App | Version | Namespace | URL |
|-----|---------|-----------|-----|
| Homepage | v1.10.1 | homepage | homepage.oryx-tegu.ts.net |
| Portainer CE | 2.33.7 | portainer | portainer.oryx-tegu.ts.net |
| Nexus | 3.89.1 | nexus | nexus.oryx-tegu.ts.net |
| Coder | v2.30.1 | coder | coder.oryx-tegu.ts.net |
| Windmill | 1.639.0 | windmill | windmill.oryx-tegu.ts.net |
| Linkwarden | v2.13.5 | linkwarden | linkwarden.oryx-tegu.ts.net |
| Keycloak | 26.5.3 | keycloak | keycloak.oryx-tegu.ts.net |
| Grafana | 12.3.3 | monitoring | grafana.oryx-tegu.ts.net |
| Loki | 3.6.5 | monitoring | — |
