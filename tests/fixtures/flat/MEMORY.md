# Homelab IAC Memory (Flat — Benchmark Baseline)

Everything in one file. This represents the naive approach: load the full
memory dump into context regardless of query specificity.

---

## Project Overview

- Proxmox homelab with 5 nodes managed via Terraform (bpg/proxmox provider v0.95.0)
- K3s cluster: 3 servers + 5 agents + 1 PostgreSQL VM, Ansible for k3s provisioning
- 1Password Connect for secrets management (Connect mode, NOT service account)
- Cluster name: "asgard-k3s-cluster", all nodes PVE 9.1.5
- K3s version: v1.32.12+k3s1 (upgraded from v1.28.3+k3s1 via 4 sequential hops)
- 20 apps deployed, v0.184.0 tagged

## Proxmox Cluster & K3s Topology

- 5 nodes: pve-hx77g-1 (16cpu/32GB), pve-um560-xt-1 (12cpu/31GB), pve-um773-lite-1 (16cpu/31GB), pve-um773-lite-2 (16cpu/31GB), pve-originpc (12cpu/67GB)
- Server nodes (control plane): pve-um560-xt-1, pve-um773-lite-1, pve-um773-lite-2
- PostgreSQL VM on pve-hx77g-1 (2cpu/4GB, 40GB OS + 100GB data)
- VM template: VM 9000 on pve-um560-xt-1 (Ubuntu 24.04 cloud image)
- API endpoint: https://pve-um560-xt-1.oryx-tegu.ts.net:8006
- NFS storage: `Proxmox_NAS` (192.168.2.161:/volume1/proxmox)
- PVE host LAN IPs: pve-um560-xt-1=192.168.2.10, pve-um773-lite-1=.11, pve-um773-lite-2=.12, pve-hx77g-1=.13, pve-originpc=.14

## 1Password Setup

- Connect server: HA on 2 LXC containers (CT200 on pve-hx77g-1, CT201 on pve-originpc)
- VIP: `http://192.168.2.72:8080` (keepalived), nodes: 192.168.2.70 + 192.168.2.71
- 2 vaults: Homelab (`e2xu6xow3lm3xssqph2jftrny4`), Dev (`qxhlzrgegpplamzkgg7kuxnhmm`)
- TF provider: Connect mode; 1Password TF provider v3.2.1
- SSH agent socket: `~/.1password/agent.sock`; `SSH_AUTH_SOCK` in `.env.d/base.env`
- SSH key for K3s VMs: `homelab-k3s-cluster`, username `k3sadmin`
- Ansible: use `--forks=1` with 1Password agent (parallel overwhelms approval dialog)

## Key Files

- `infrastructure/main.tf` — root module with providers, 1Password data sources
- `infrastructure/backend.tf` — pg backend (state at 192.168.2.45)
- `infrastructure/modules/k3s/k3s-cluster.tf` — k3s cluster definition
- `ansible/inventory/k3s.yml` — K3s cluster inventory
- `clusters/asgard/` — Flux GitOps entry point
- `kubernetes/platform/configs/cluster-secret-store.yaml` — ESO ClusterSecretStore
- `.claude/session-notes.md` — session resume state

## Flux GitOps Structure

- Entry point: `clusters/asgard/` (community standard pattern)
- Dependency chain: platform-controllers → platform-configs → apps
- FluxCD v2.7.5
- GitHub PAT for Flux: 1Password item `gh-homelab-fluxcd`
- Bootstrap secret is NOT auto-synced — rotate manually via kubectl patch

## Critical Gotchas

- `user_account` and `user_data_file_id` MUTUALLY EXCLUSIVE in bpg/proxmox v0.95.0
- `PROXMOX_VE_*` env vars silently override provider block — NEVER set them
- `--cluster-init` is for embedded etcd ONLY, not external PostgreSQL datastores
- 1Password auth modes (Connect vs Service Account) MUTUALLY EXCLUSIVE
- 1Password Connect: default Login fields NOT addressable by `property` — use custom text fields
- ExternalSecret API: use `external-secrets.io/v1` (NOT `v1beta1` — removed in ESO v2)
- K8s pods can't resolve Tailscale MagicDNS — use LAN IPs for in-cluster access
- pg_hba.conf NOT replicated by streaming replication — add entries on BOTH nodes
- Pod → same-LAN PostgreSQL routes via node IP — pg_hba needs `192.168.2.0/24`
- K3s registry mirrors: `override_path=true` strips `/v2/` — endpoint URL must include `/v2`

---

## Technical Gotchas (Full Reference)

### Terraform / Proxmox

- `user_account` and `user_data_file_id` are MUTUALLY EXCLUSIVE in bpg/proxmox v0.95.0
- SSH username in provider must be OS user (`root`), not PVE API user
- `PROXMOX_VE_*` env vars silently override provider block — NEVER set them
- `download_file` needs `import` content type — only `Proxmox_NAS` has it, not `local-lvm`
- `agent { enabled = true }` makes TF wait for qemu-guest-agent — MUST include in cloud-config AND start in runcmd
- bpg/proxmox: changing `user_data_file_id` forces VM replacement — use `lifecycle { ignore_changes = [initialization] }`
- Terraform state lock stuck: use `terraform force-unlock -force <lock-id>`
- `terraform destroy -refresh=false` destroys ALL state — use `-target=module.k3s` to spare template
- Proxmox API tokens start with ZERO permissions — need explicit ACL at `/`
- `proxmox_virtual_environment_container` uses `start_on_boot` (NOT `on_boot` like VMs)
- Destroy+create same container ID races: PVE returns "VM N already exists". Fix: second targeted apply
- Privileged LXC feature flags require `root@pam` — API tokens fail

### K3s

- `--cluster-init` is for embedded etcd ONLY, not external PostgreSQL
- With external PostgreSQL, all K3s servers use same `--datastore-endpoint` + `--token`
- Agent nodes need `--server` flag to join
- K3s bootstrap token must be simple string (NOT `K10...` format)
- K3s `/readyz` endpoint requires auth — returns 401. Health checks must accept 200/401/403
- K3s registry mirrors: `override_path = true` strips `/v2/` prefix — append `/v2` to endpoint
- GHCR image tags: GitHub release names use `v0.x.y` but GHCR tags do NOT — use `0.x.y`
- K8s pods can't resolve Tailscale MagicDNS — use LAN IPs for in-cluster access
- VLAN double-tagging: if PVE hosts are on VLAN 2 untagged via vmbr0, do NOT set `vlan_id = 2` on VMs
- QEMU guest agent not running = terraform plan hangs

### Kubernetes / Flux

- nginx ingress `configuration-snippet` blocked by admission webhook — use `proxy-set-headers` + ConfigMap
- Flux Kustomization is ATOMIC — one failing resource blocks ALL resources in that Kustomization
- Dynamically provisioned PVCs: once bound, K8s adds `volumeName` to spec (immutable)
- PV NFS `path` is immutable — delete PV+PVC and let Flux recreate
- Flux `spec.upgrade.force: true` handles StatefulSet immutable field changes
- Helm StatefulSet `volumeClaimTemplates` are immutable — delete Helm release secrets to force fresh install
- ESO chart ships CRDs via Helm TEMPLATES — use `install.crds: Skip` in Flux HelmRelease
- All platform HelmReleases have `install.remediation.retries: 3`

### 1Password / ESO

- 1Password auth modes (Connect vs Service Account) MUTUALLY EXCLUSIVE
- Connect: default Login fields NOT addressable by `property` — use custom text fields only
- `op item create --category login` needs explicit `username=<value>`
- ExternalSecret API: use `external-secrets.io/v1` (NOT `v1beta1`)
- ESO force-sync: annotate with `force-sync=$(date +%s)`
- `op item get --field` returns placeholder for concealed fields — add `--reveal`

### PostgreSQL HA

- pg_hba.conf NOT replicated — add entries on BOTH primary and standby
- Pod traffic routes via node IP (192.168.2.x) — pg_hba needs `192.168.2.0/24`
- Keepalived health check: only check `pg_isready`, NOT `pg_is_in_recovery()`
- Install keepalived on MASTER node FIRST, then BACKUP
- `pg_basebackup` waits for checkpoint — use `--checkpoint=fast`

### Ansible

- Always use `uv run ansible-playbook` (bare `ansible-playbook` not in PATH)
- `group_vars/` must be adjacent to inventory file
- Jinja2 + Bash collision: `${#array[@]}` breaks in templates — wrap in `{% raw %}...{% endraw %}`
- `((var++))` when var=0 returns exit code 1 — kills scripts with `set -euo pipefail`

---

## Platform Services

### GitOps & Platform Controllers

- **FluxCD** v2.7.5 — `clusters/asgard/`, GitHub PAT `gh-homelab-fluxcd`
- **MetalLB** v0.15.3 — L2 mode, IPAddressPool 192.168.2.201-250
- **ingress-nginx** v1.14.3 — LoadBalancer 192.168.2.201
- **cert-manager** v1.19.3 — self-signed CA chain, clusterissuer `homelab-ca-issuer`
- **Tailscale operator** v1.94.2 — API server proxy active, dual ingress pattern
- **ESO** v2.0.0 — ClusterSecretStore `onepassword-connect`, VIP 192.168.2.72
- **NFS provisioner** v4.0.2 — StorageClass `nfs-kubernetes`, Retain policy
- **Longhorn** v1.11.0 — 2-replica, StorageClass `longhorn`, `defaultClass: false`

### Monitoring Stack

- **kube-prometheus-stack** chart 82.1.1 — Grafana 12.3.3, Prometheus v3.9.1
- **Grafana** — Keycloak SSO via `auth.generic_oauth`, `grafana.oryx-tegu.ts.net`
- **Loki** 3.6.5 + **Promtail** 3.5.1
- **pve-exporter** 3.8.1
- ServiceMonitor discovery: `serviceMonitorSelector: {}` + `NilUsesHelmValues: false`

### Identity & Auth

- **Keycloak** 26.5.3 — `homelab` realm, PostgreSQL backend (VIP 192.168.2.44)
  - OIDC issuer: `https://keycloak.oryx-tegu.ts.net/auth/realms/homelab`
  - `KC_PROXY_HEADERS=xforwarded` (NOT KC_PROXY=edge — deprecated in 26.x)
- **OAuth2 Proxy** v7.14.2 — protects 14/21 nginx ingresses
- **CoreDNS override** — rewrites `keycloak.oryx-tegu.ts.net → keycloak.192.168.2.201.nip.io`

### Backup

- **Velero** v1.17.2 — CSI snapshots + Kopia, MinIO BSL
- **MinIO** — standalone, 50Gi NFS, cluster-internal S3
- **PostgreSQL backup** — pg_dumpall CronJob → NAS at 192.168.2.161:/volume1/postgresql-backups

### Applications

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
