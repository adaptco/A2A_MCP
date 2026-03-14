'use strict'
/**
 * VH2 FRONTEND SOCKET — Static file server
 * Serves: vehicle simulation, unit tests, plugin JS, demo page
 */
const express  = require('express')
const path     = require('path')
const fs       = require('fs')

const app  = express()
const PORT = process.env.PORT || 3000
const HOST = process.env.HOST || '0.0.0.0'

// Mobile-first headers on all responses
app.use((_req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff')
  res.setHeader('Referrer-Policy', 'no-referrer')
  next()
})

// Serve all static files from /public
app.use(express.static(path.join(__dirname, 'public'), {
  maxAge: '1h',
  etag:   true,
}))

// Plugin JS (short-lived cache for updates)
app.get('/vh2-plugin.js', (_req, res) => {
  res.setHeader('Cache-Control', 'public, max-age=300')
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Content-Type', 'application/javascript')
  res.sendFile(path.join(__dirname, 'vh2-plugin.js'))
})

app.listen(PORT, HOST, () => {
  console.log(`VH2 Frontend Socket listening on ${HOST}:${PORT}`)
})
