# WSL session recovery observed on Windows

This is an operator repair record for the Windows/Ubuntu WSL machine used on 18 October 2026. The application launchers do not make these global changes. Ordinary onboarding still needs only the working backend described in [developer onboarding](developer-onboarding.md).

## Diagnosis

WSL 2.7.10 with kernel 6.18.33.2 was capped at 2 GB and two processors. Existing containers kept responding, while new sessions intermittently failed with `Wsl/Service/0x8007274c`. The kernel reported `page allocation failure: order:7` in `vmbus_alloc_ring`, followed by relay `UtilAcceptVsock` waits. These observations match the allocation/fragmentation failure described in [Microsoft WSL issue 40795](https://github.com/microsoft/WSL/issues/40795).

## Applied host configuration

The existing Windows user `.wslconfig` was backed up before the authorized repair. On this 16 GB host, the final configuration is:

```ini
[wsl2]
memory=4GB
processors=4
swap=4GB
kernelCommandLine=sysctl.vm.compaction_proactiveness=80 sysctl.vm.min_free_kbytes=131072
```

WSL was restarted to apply it, and the effective memory, CPU count, swap and sysctl values were read back. The memory settings provide more room for simultaneous builds and containers. Proactive compaction and the free-memory reserve target availability of contiguous allocations. Compaction can trade CPU time and latency for reduced fragmentation; these are machine-specific settings, not application prerequisites. See [Microsoft's WSL configuration reference](https://learn.microsoft.com/en-us/windows/wsl/wsl-config) and [the kernel VM documentation](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html).

An upstream small-socket-buffer workaround was evaluated and reverted: booting this Docker installation with `net.core.rmem_default`/`wmem_default` set to 28672 prevented its bridge-address discovery. Both values remain at the normal observed value 212992. No network-buffer reduction is part of the final repair.

## Preserve services during recovery

Record running container names and preserve all named volumes and private files before restarting WSL. Stop Docker cleanly when possible. Start the same services afterward and verify application/database health and saved record fingerprints. Do not delete database or runtime volumes.

During this repair Docker retained a stale, empty `fincathon_default` network definition after its failed initialization. That project network was removed only after confirming it had zero endpoints, then recreated through the existing Compose configuration with the same persistent volumes. The original app and unrelated PostgreSQL service were restored. No Docker-wide prune, data reset or credential replacement was used.

The operational evidence, executed tests and host configuration backup are retained with the local repair report. This repair mitigates the observed host resource/fragmentation condition; it does not claim that an upstream kernel defect has been patched.
