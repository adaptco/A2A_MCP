# Grounding Exercise

This document describes how to use the Stripe CLI to "Ground" the Ghost Void runtime.

## Concept

In this simulation, the "Agency" of the character is initially floating in a void. To give it a platform to stand on, we must "Ground" it with Value.

We use a **Stripe Payment Intent** as the proxy for this Value. When a payment succeeds, the energy from that transaction crystallizes into a solid plane within the simulation.

## Prerequisites

- [Stripe CLI](https://docs.stripe.com/stripe-cli/install) installed and logged in (`stripe login`).
- The Ghost Void server running (`npm run start` in `server/`).
- The React Client open (`http://localhost:8080`).

## How to Ground the Runtime

1. **Start the Simulation**: Ensure the game is running. You will see the agent falling into the void or standing on the initial scaffolding.

2. **Forward Webhooks**:
    In a new terminal window, tell Stripe to forward events to our Grounding Receptor.

    ```bash
    stripe listen --forward-to localhost:8080/webhook
    ```

    *Note: Keep this window open.*

3. **Trigger the Genesis Event**:
    In another terminal, manually trigger a successful payment event.

    ```bash
    stripe trigger payment_intent.succeeded
    ```

4. **Observe**:
    - The Server log will show: `>> INITIATING GENESIS PLANE <<`
    - The Engine stdout will show: `>> GENESIS EVENT: Spawning Plane...`
    - **In the Game**: A new white platform will instantly appear at `(0, 500)`, effectively catching the falling agent or extending the world.

## Troubleshooting

- **No Plane Appears?**
  - Check the `stripe listen` output to ensure the webhook was sent (200 OK).
  - Check the Server console for the "GENESIS PLANE" log.
  - Ensure the C++ Engine was compiled and is running (check Server logs for "Engine process exited" errors).
