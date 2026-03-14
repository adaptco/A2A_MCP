# Hagen–Poiseuille Numeric Example

This note captures the fully worked laminar flow example requested in the latest control loop audit. It assumes water at 20 °C flowing through a smooth circular pipe and tabulates the velocity profile so it can be imported into other tooling or checked against solver outputs.

## Given Parameters

- Fluid density: $\rho = 998\,\text{kg·m}^{-3}$.
- Dynamic viscosity: $\mu = 1.002\times 10^{-3}\,\text{Pa·s}$.
- Pipe radius: $R = 0.01\,\text{m}$ (diameter $D = 0.02\,\text{m}$).
- Volumetric flow rate: $Q = 1.0\times 10^{-5}\,\text{m}^{3}\text{·s}^{-1}$.

## Derived Quantities

| Quantity | Expression | Value |
| --- | --- | --- |
| Cross-sectional area | $A = \pi R^2$ | $3.1416\times 10^{-4}\,\text{m}^2$ |
| Mean velocity | $\bar{u} = Q/A$ | $3.183\times 10^{-2}\,\text{m·s}^{-1}$ |
| Centerline velocity | $u_\max = 2\bar{u}$ | $6.366\times 10^{-2}\,\text{m·s}^{-1}$ |
| Axial pressure gradient | $\frac{\mathrm{d}p}{\mathrm{d}z} = -\frac{8\mu Q}{\pi R^4}$ | $-2.553\,\text{Pa·m}^{-1}$ |
| Wall shear stress | $\tau_w = -\frac{R}{2}\frac{\mathrm{d}p}{\mathrm{d}z}$ | $1.277\times 10^{-2}\,\text{Pa}$ |
| Reynolds number | $\mathrm{Re} = \frac{\rho \bar{u} D}{\mu}$ | $6.34\times 10^{2}$ |

All results are rounded to three significant figures.

## Velocity Profile

The axial velocity distribution obeys the standard parabolic form for laminar flow,

$$
 u_z(r) = -\frac{1}{4 \mu} \frac{\mathrm{d}p}{\mathrm{d}z} \left(R^2 - r^2\right) = u_\max \left(1 - \frac{r^2}{R^2}\right).
$$

The table below lists the velocity magnitude at eleven evenly spaced radial positions between the pipe centerline ($r = 0$) and the wall ($r = R$). Values are reported in metres per second.

| $r$ (m) | $u_z(r)$ (m·s⁻¹) |
| --- | --- |
| 0.00000 | 0.063660 |
| 0.00100 | 0.063023 |
| 0.00200 | 0.061114 |
| 0.00300 | 0.057931 |
| 0.00400 | 0.053474 |
| 0.00500 | 0.047745 |
| 0.00600 | 0.040742 |
| 0.00700 | 0.032467 |
| 0.00800 | 0.022918 |
| 0.00900 | 0.012095 |
| 0.01000 | 0.000000 |

## Validation Notes

- The Reynolds number ($\mathrm{Re} \approx 634$) confirms laminar conditions (well below the conventional transition threshold of $\mathrm{Re} \approx 2300$).
- The listed pressure gradient corresponds to a pressure drop of approximately $2.55\,\text{Pa}$ per metre of pipe length.
- Wall shear stress is obtained either from the analytic derivative of the parabolic profile or directly from the pressure gradient.

These figures can be pasted directly into spreadsheet or plotting software to compare against experimental or computational data sets.
