const express = require('express');
const router = express.Router();

/**
 * GROUNDING RECEPTOR
 * 
 * Listens for "Value Events" (Stripe Webhooks) and translates them into 
 * "Ontological Definitions" (Game Objects) for the Engine.
 */
module.exports = (engine) => {
    // We need the engine process reference to communicate

    // Webhook Endpoint
    router.post('/', express.raw({ type: 'application/json' }), (req, res) => {
        const sig = req.headers['stripe-signature'];
        // In a real app, verify signature with Stripe SDK
        // const event = stripe.webhooks.constructEvent(req.body, sig, endpointSecret);

        // For Scaffolding/Grounding Exercise, we trust the "Trigger"
        let event;
        try {
            event = JSON.parse(req.body);
        } catch (err) {
            console.log('Webhook Error', err.message);
            return res.status(400).send(`Webhook Error: ${err.message}`);
        }

        console.log(`Grounding Receptor received: ${event.type}`);

        if (event.type === 'payment_intent.succeeded') {
            console.log(">> INITIATING GENESIS PLANE <<");

            // Construct the Genesis Command
            const genesisCommand = JSON.stringify({
                type: 'genesis_plane',
                origin: { x: 0, y: 500 }, // Ground level
                dimensions: { w: 1000, h: 50 },
                material: 'solid_value'
            });

            // Transmit to Engine via Intradimensional Pipe (Stdin)
            if (engine && engine.stdin) {
                engine.stdin.write(genesisCommand + '\n');
            }
        }

        res.json({ received: true });
    });

    return router;
};
