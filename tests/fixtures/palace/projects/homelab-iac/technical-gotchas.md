# Technical Gotchas

All confirmed in production. Critical subset duplicated in homelab-iac.md Overview.

## Terraform / Proxmox

- `user_account` and `user_data_file_id` MUTUALLY EXCLUSIVE in bpg/proxmox v0.95.0
- SSH username in provider must be OS user (`root`), not PVE API user
- `PROXMOX_VE_*` env vars silently override `provider "proxmox" {}` block — NEVER set them
- `download_file` needs `import` content type — only `Proxmox_NAS` has it, not `local-lvm`
- `agent { enabled = true }` makes TF wait for qemu-guest-agent — MUST include in cloud-config packages AND start in runcmd
- bpg/proxmox: changing `user_data_file_id` forces VM replacement — use `lifecycle { ignore_changes = [initialization] }`
- Terraform state lock stuck: use `terraform force-unlock -force <lock-id>`
- `terraform destroy -refresh=false` destroys ALL state — use `-target=module.k3s` to spare template
- Proxmox API tokens start with ZERO permissions — need explicit ACL at `/`
- `proxmox_virtual_environment_container` uses `start_on_boot` (NOT `on_boot` like VMs)
- Destroy+create same container ID races — PVE returns "VM N already exists". Fix: second targeted apply
- Privileged LXC feature flags require `root@pam` — API tokens fail

## K3s

- `--cluster-init` is for embedded etcd ONLY — do NOT use with external PostgreSQL
- With external PostgreSQL: all K3s servers use same `--datastore-endpoint` + `--token`
- Agent nodes need `--server` flag to join (servers discover each other via PostgreSQL)
- Bootstrap token must be simple string (NOT `K10...` format)
- `/readyz` endpoint requires auth — returns 401. Health checks must accept 200/401/403
- Registry mirrors: `override_path = true` strips `/v2/` prefix — append `/v2` to endpoint URL
- GHCR image tags: release names use `v0.x.y` but GHCR Docker tags do NOT — use `0.x.y`
- K8s pods can't resolve Tailscale MagicDNS (`.ts.net`) — use LAN IPs for in-cluster access
- VLAN double-tagging: if PVE hosts on VLAN 2 untagged via vmbr0, do NOT set `vlan_id = 2` on VMs
- QEMU guest agent not running = terraform plan hangs for minutes

## Kubernetes / Flux

- nginx `configuration-snippet` blocked by admission webhook — use `proxy-set-headers` + ConfigMap
- Flux Kustomization is ATOMIC — one failing resource blocks ALL resources in that Kustomization
- Dynamically provisioned PVCs: once bound, K8s adds `volumeName` (immutable) — include in manifests
- PV NFS `path` is immutable — delete PV+PVC and let Flux recreate
- Flux `spec.upgrade.force: true` handles StatefulSet immutable field changes
- Helm StatefulSet `volumeClaimTemplates` are immutable — delete Helm release secrets for fresh install
- ESO chart ships CRDs via Helm TEMPLATES — use `install.crds: Skip` in Flux HelmRelease
- All platform HelmReleases have `install.remediation.retries: 3`

## 1Password / ESO

- Connect vs Service Account modes are MUTUALLY EXCLUSIVE — unset `OP_SERVICE_ACCOUNT_TOKEN`
- Connect: default Login fields NOT addressable by `property` — use custom text fields only
- `op item create --category login` needs explicit `username=<value>`
- ExternalSecret API: use `external-secrets.io/v1` (NOT `v1beta1` — removed in ESO v2)
- ESO force-sync: annotate ExternalSecret with `force-sync=$(date +%s)`
- `op item get --field` returns placeholder for concealed fields — add `--reveal`

## PostgreSQL HA

- pg_hba.conf NOT replicated by streaming replication — add entries on BOTH primary and standby
- Pod traffic routes via node IP (192.168.2.x) — pg_hba needs `192.168.2.0/24`
- Keepalived health check: only check `pg_isready`, NOT `pg_is_in_recovery()` — causes deadlock
- Install keepalived on MASTER first, then BACKUP
- `pg_basebackup` waits for checkpoint — use `--checkpoint=fast` to avoid 5-minute wait

## Ansible

- Always use `uv run ansible-playbook` (bare `ansible-playbook` not in PATH)
- `group_vars/` must be adjacent to inventory file (`inventory/group_vars/`)
- Jinja2 + Bash: `${#array[@]}` breaks in templates — wrap in `{% raw %}...{% endraw %}`
- `((var++))` when var=0 returns exit code 1 — kills scripts with `set -euo pipefail`
- ansible-lint `partial-become`: `become_user` at task level requires `become: true` at same level
