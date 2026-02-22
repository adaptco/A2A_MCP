# Virtual Display Driver Integration Guide

The [Virtual Display Driver](https://github.com/VirtualDrivers/Virtual-Display-Driver) project provides a Windows indirect display driver (IDD) for creating fully virtual monitors. This guide captures the core operational notes needed when integrating the driver into orchestration pipelines or automated capsule deployments.

## Capabilities Overview
- **Virtual monitor creation** that mirrors the behaviour of physical displays, enabling headless rendering, remote desktops, and capture workflows.
- **Customisable timing** with user-defined resolutions, refresh rates (including fractional values), and HDR bit depths (10- and 12-bit).
- **EDID emulation** to overcome hardware EDID limitations and present bespoke capabilities to the operating system.
- **Platform coverage** including x64 and ARM64 Windows installations (ARM64 requires test-signing mode).

## Installation Workflow
1. Download the "Virtual Driver Control" application from the project releases page and extract the archive.
2. Launch the control application and select **Install** to deploy the driver package.
3. Validate the deployment via Device Manager or the Windows Display Settings panel.

> ℹ️ The Microsoft Visual C++ Redistributable must be present. If the `vcruntime140.dll` dependency is missing, install the latest Redistributable package from Microsoft.

### Understanding Driver Downloads

Driver downloads supply the operating system with the exact instructions required to communicate with hardware—or, in this case, a virtual device. Each driver acts as a translation layer that converts generic operating system requests into the device-specific language a component (physical or virtual) understands. Vendors release updated drivers to correct bugs, enhance performance, broaden feature support, and patch security issues. Always source the Virtual Display Driver package directly from the upstream project to ensure integrity and compatibility.

## Configuration
- Runtime settings are stored in `C:\\VirtualDisplayDriver\\vdd_settings.xml`. Modify this file to register or adjust virtual outputs, resolutions, and refresh cadence.
- Community-supplied PowerShell automations are available in the upstream repository for scripted provisioning.

## Pipeline Alignment: Photo → Prompt → Print → P3L

The sandbox manufacturing pipeline can rely on virtual displays to stage design reviews, capture artifacts, and validate telemetry without requiring physical monitors. The driver slots into each phase as follows:

### 1. Photo → Prompt
- Host the reference imagery, CAD snapshots, or concept art on a virtual display so remote reviewers can annotate assets without local peripherals.
- Use capture tooling (OBS, Teams, etc.) pointed at the virtual output to record the object descriptors—e.g.
  ```json
  { "subject": "GT3 race car", "scale": "1:7", "materials": ["PLA", "resin"], "style": "studio model" }
  ```
- Archive the captured prompt JSON alongside the photo hash to begin the proof chain.

### 2. Prompt → Print
- Leverage the virtual monitor as a headless workstation for procedural CAD (OpenSCAD, Fusion 360) or slicing UIs when running inside a build pipeline or remote VM.
- Stream the print preview and watertightness checks over the virtual display so stakeholders can sign off on STL exports prior to slicing (0.15 mm layer height, 0.4 mm nozzle parameters, tolerance test modules, etc.).

### 3. Print → P3L
- Use the virtual display as the visualization surface for logging dashboards that track the Proof → Flow → Execution records.
- Surface the JSON ledger output, sensor telemetry, and photographic validation frames on the virtual output for automated capture by orchestration agents before anchoring into the SSOT ledger.

When requesting a starter sandbox template, specify whether the target subject is a car, mecha, or environment so that the prompt scaffolding and CAD presets generated in stage 1 match the intended build.

## Operational Notes
- Virtual displays can be leveraged by streaming/recording agents, VR previews, or any workflow requiring deterministic off-screen rendering targets.
- HDR pipelines should confirm consumer application support for 10/12-bit surfaces when enabling high dynamic range output.
- When integrating into orchestration flows, ensure the driver service is started prior to binding capture agents to the virtual outputs.

For advanced feature toggles or troubleshooting, consult the upstream documentation and issue tracker.
