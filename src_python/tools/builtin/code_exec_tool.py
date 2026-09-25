# Security Notice: Code Execution Tool REMOVED
# This tool was removed due to critical security vulnerability (RCE).
# No sandbox, no isolation, arbitrary code execution as full user.
# 
# If you need code execution capability, implement proper sandboxing:
# - Container-based (Docker, gVisor, Firecracker)
# - WASM runtime (wasmtime, wasmer)
# - Seccomp-bpf + namespaces + cgroups
# - Dedicated microservice with strict resource limits
#
# DO NOT RE-ENABLE without comprehensive security review.