#!/usr/bin/env node

import express from 'express';

const app = express();
app.use(express.json());

const PORT = 8080;

// Tool Logic
const renderVehicle = (args) => {
  console.log(`[MCP] Rendering vehicle: ${args.vehicle_model} | Symmetry: ${args.symmetry_mode}`);
  return {
    status: "success",
    message: "Vehicle rendered successfully",
    specs: args,
    render_path: `/output/${args.vehicle_model.replace(/\s+/g, "_")}.png`
  };
};

// HTTP Handler for MCP Adapter
app.post('/execute', (req, res) => {
  const { tool_name, arguments: args, trace_id } = req.body;

  console.log(`[HTTP] Execute ${tool_name} [Trace: ${trace_id}]`);

  if (tool_name === "render_vehicle_asset") {
    try {
      const result = renderVehicle(args);
      return res.json(result);
    } catch (error) {
      console.error(error);
      return res.status(500).json({ error: error.message });
    }
  }

  res.status(404).json({ error: `Unknown tool: ${tool_name}` });
});

app.listen(PORT, () => {
  console.log(`MCP Server listening on port ${PORT}`);
});