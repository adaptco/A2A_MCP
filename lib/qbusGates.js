'use strict';

const { verifyBinding, manifestSignaturePayload, verifyDuoSig } = require('./bindings');

function resolveProvider(manifestsProvider) {
  if (typeof manifestsProvider === 'function') {
    return manifestsProvider;
  }
  if (manifestsProvider && typeof manifestsProvider.getAuthorityMap === 'function') {
    return () => manifestsProvider.getAuthorityMap();
  }
  throw new Error('manifestsProvider must be a function or expose getAuthorityMap()');
}

function logOnceFactory(logger) {
  const cache = new Set();
  return (message) => {
    if (cache.has(message)) {
      return;
    }
    cache.add(message);
    if (logger && typeof logger.warn === 'function') {
      logger.warn(message);
    } else if (logger && typeof logger.log === 'function') {
      logger.log(message);
    } else {
      console.warn(message);
    }
  };
}

function qbusGateGuard(manifestsProvider, ledgerClient, opts = {}) {
  const provider = resolveProvider(manifestsProvider);
  const logger = opts.logger || console;
  const logOnce = logOnceFactory(logger);
  const skewSeconds = Number.isFinite(opts.skew_seconds) ? opts.skew_seconds : 30;

  async function ensureManifest() {
    const info = await provider();
    if (!info || !info.manifest) {
      throw new Error('authority manifest unavailable');
    }
    return info;
  }

  function respond(res, status, errorCode, message, details) {
    res.status(status).json({
      error_code: errorCode,
      message,
      details: details || {}
    });
  }

  function getBindingTuple(req) {
    if (req && req.body && typeof req.body === 'object') {
      if (req.body.binding && typeof req.body.binding === 'object') {
        return req.body.binding;
      }
      return req.body;
    }
    if (req && req.query && typeof req.query === 'object') {
      return req.query;
    }
    return null;
  }

  return async function qbusGateMiddleware(req, res, next) {
    let manifestInfo;
    try {
      manifestInfo = await ensureManifest();
    } catch (err) {
      const message = 'Authority manifest unavailable';
      logOnce(message);
      respond(res, 503, 'MANIFEST_UNAVAILABLE', message, { reason: err.message });
      return;
    }

    const manifest = manifestInfo.manifest;

    if (!manifestInfo.hasHashFile || !manifestInfo.hashMatches || !manifestInfo.hasSignatureFile) {
      const message = 'Authority manifest has not been frozen or signed';
      logOnce(message);
      respond(res, 403, 'UNSIGNED_MANIFEST', message, {
        hashMatches: manifestInfo.hashMatches,
        hasHashFile: manifestInfo.hasHashFile,
        hasSignatureFile: manifestInfo.hasSignatureFile
      });
      return;
    }

    const duo = manifestInfo.duo || verifyDuoSig(
      manifestSignaturePayload(manifest),
      manifest && manifest.signatures && manifest.signatures.maker,
      manifest && manifest.signatures && manifest.signatures.checker,
      {
        maker: manifest && manifest.maker && manifest.maker.public_key,
        checker: manifest && manifest.checker && manifest.checker.public_key
      }
    );

    if (!duo.ok) {
      const message = 'Maker/checker signatures failed verification';
      logOnce(`${message}: ${duo.errors ? duo.errors.join('; ') : 'unknown reason'}`);
      respond(res, 403, 'G2_DUO_SIG_MISMATCH', message, {
        duo
      });
      return;
    }

    const effectiveAfter = manifest && manifest.effective_after;
    const effectiveDate = effectiveAfter ? new Date(effectiveAfter) : null;
    if (!effectiveDate || Number.isNaN(effectiveDate.getTime())) {
      const message = 'Authority manifest effective_after is invalid';
      logOnce(message);
      respond(res, 503, 'G3_AUTH_MAP_NOT_YET_EFFECTIVE', message, {
        effective_after: effectiveAfter
      });
      return;
    }
    const skewMs = Math.max(0, skewSeconds) * 1000;
    const now = Date.now();
    if (effectiveDate.getTime() - skewMs > now) {
      const message = 'Authority manifest not yet effective';
      logOnce(message);
      respond(res, 503, 'G3_AUTH_MAP_NOT_YET_EFFECTIVE', message, {
        effective_after: effectiveAfter,
        skew_seconds: skewSeconds
      });
      return;
    }

    const tuple = getBindingTuple(req);
    const verification = verifyBinding(manifest, tuple);
    if (!verification.ok) {
      const message = 'Requested binding tuple not authorized by manifest';
      logOnce(`${message}: ${JSON.stringify(verification.details || {})}`);
      respond(res, 403, 'G1_SCOPE_VIOLATION', message, verification.details || {});
      return;
    }

    if (ledgerClient && typeof ledgerClient.recordGateCheck === 'function') {
      try {
        await ledgerClient.recordGateCheck({
          tuple: verification.normalized,
          manifest_hash: manifestInfo.hash,
          at: new Date().toISOString()
        });
      } catch (err) {
        logOnce(`Ledger client recordGateCheck failed: ${err.message}`);
      }
    }

    req.qbus = {
      manifest: manifestInfo,
      binding: verification
    };
    next();
  };
}

module.exports = qbusGateGuard;
