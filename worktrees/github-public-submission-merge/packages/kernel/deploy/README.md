# Kernel deployment package

Build and package the kernel for deployment:

```bash
npm --prefix packages/kernel run package:deploy
```

Generated artifacts:

- `world-os-kernel-<version>.tgz` – npm deployment package
- `manifest.json` – artifact metadata (hash, size, package version)
- `SHA256SUMS.txt` – checksum file for integrity verification
