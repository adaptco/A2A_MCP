# Virtual Display Driver Installation Workflow

Follow these steps to deploy the Virtual Display Driver on Windows based on the Installation Workflow guidance from the project documentation.

## 1. Download and Extract
- Retrieve the **Virtual Driver Control** application from the official project releases page.
- Extract the downloaded archive to a convenient location on your machine.

## 2. Launch and Install
- Run the Virtual Driver Control application.
- Choose **Install** to deploy the Virtual Display Driver package onto the system.

## 3. Validate Deployment
- Confirm the driver is active via **Device Manager** or the **Windows Display Settings** panel.
- Ensure the driver appears without error indicators before proceeding with additional configuration.

## Prerequisites
- Install the **Microsoft Visual C++ Redistributable** so that the required `vcruntime140.dll` dependency is available. Without this package the control application will fail to launch.

These steps prepare the virtual display stack for further configuration, testing, or integration with the scrollstream rehearsal tooling.
