# homelab-iac

Proxmox homelab managed via Terraform + Ansible, K3s cluster with Flux GitOps.
Read this room for infrastructure topology, 1Password setup, and session state.
For gotchas and service inventory, see the specialty files below.

## Overview

- Proxmox: 5 nodes, bpg/proxmox provider v0.95.0, PVE 9.1.5
- K3s: v1.32.12+k3s1, 3 servers + 5 agents + 1 PostgreSQL VM
- Secrets: 1Password Connect mode (NOT service account)
- GitOps: Flux v2.7.5, entry point `clusters/asgard/`
- State: 20 apps deployed, v0.184.0 tagged

## Proxmox Topology

- pve-hx77g-1: 16cpu/32GB, LAN 192.168.2.13
- pve-um560-xt-1: 12cpu/31GB, LAN 192.168.2.10 — API endpoint, VM template host
- pve-um773-lite-1: 16cpu/31GB, LAN 192.168.2.11
- pve-um773-lite-2: 16cpu/31GB, LAN 192.168.2.12
- pve-originpc: 12cpu/67GB, LAN 192.168.2.14
- Server nodes (control plane): pve-um560-xt-1, pve-um773-lite-1, pve-um773-lite-2
- PostgreSQL VM: pve-hx77g-1 (2cpu/4GB, 40GB OS + 100GB data)
- NFS: `Proxmox_NAS` at 192.168.2.161:/volume1/proxmox

## 1Password

- Connect server: HA LXC (CT200 on pve-hx77g-1, CT201 on pve-originpc)
- VIP: `http://192.168.2.72:8080` (keepalived)
- SSH agent: `~/.1password/agent.sock` — use `--forks=1` with Ansible
- SSH key for K3s VMs: `homelab-k3s-cluster`, username `k3sadmin`

## Flux GitOps

- Entry point: `clusters/asgard/`
- Dependency chain: platform-controllers → platform-configs → apps
- GitHub PAT: 1Password item `gh-homelab-fluxcd`
- Bootstrap secret NOT auto-synced — rotate manually via kubectl patch

## Key Files

| Description | Path |
|---|---|
| Root module | `infrastructure/main.tf` |
| State backend | `infrastructure/backend.tf` (pg at 192.168.2.45) |
| K3s cluster | `infrastructure/modules/k3s/k3s-cluster.tf` |
| K3s inventory | `ansible/inventory/k3s.yml` |
| Flux entry | `clusters/asgard/` |
| ESO store | `kubernetes/platform/configs/cluster-secret-store.yaml` |
| Session state | `.claude/session-notes.md` |

## References

- [`technical-gotchas.md`](./technical-gotchas.md) — Terraform, K3s, Flux, 1Password, PostgreSQL, Ansible gotchas (all confirmed in production)
- [`platform-services.md`](./platform-services.md) — deployed service versions, IPs, and URLs
