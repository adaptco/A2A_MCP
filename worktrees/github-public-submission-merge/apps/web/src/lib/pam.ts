import * as crypto from 'crypto';

/**
 * PAM (Project Automation & Merkle) Logic
 * Integrated into WorldOS Governance Plane (AxQxOS)
 */

export interface StyleToken {
    path: string;
    value: any;
    weight: number;
}

export interface Correction {
    path: string;
    value: any;
}

/**
 * Calculates the weighted drift score for a set of visual/logic tokens.
 * A score toward 1.0 indicates high divergence.
 */
export function calculateDriftScore ( tokens: StyleToken[] ): number {
    let totalWeight = 0;
    let weightedSum = 0;

    tokens.forEach( token => {
        totalWeight += token.weight;
        // Simplified: weighted by presence of data vs baseline
        weightedSum += token.weight * ( token.value ? 1 : 0 );
    } );

    if ( totalWeight === 0 ) return 0;
    return weightedSum / totalWeight;
}

/**
 * Verifies if a correction is within acceptable drift thresholds.
 */
export function verifyCorrection ( correction: Correction ): boolean {
    const driftScore = calculateDriftScore( [
        { path: correction.path, value: correction.value, weight: 1 }
    ] );

    // Threshold defined in pam_orchestrator.json is 0.5
    return driftScore < 0.5;
}

/**
 * Creates a deterministic SHA-256 hash of a correction for ledger sealing.
 */
export function sealCorrection ( correction: Correction ): string {
    const hash = crypto.createHash( 'sha256' );
    hash.update( JSON.stringify( correction ) );
    return hash.digest( 'hex' );
}

/**
 * Enforces guardrails against forbidden mutations.
 */
export function enforceGuardrails ( path: string ): boolean {
    const forbiddenPaths = [
        '/geometry/topology',
        '/identity/*'
    ];

    return !forbiddenPaths.some( forbiddenPath => {
        const escapedPattern = forbiddenPath
            .replace( /[.*+?^${}()|[\]\\]/g, '\\$&' )
            .replace( /\\\*/g, '.*' );
        const regex = new RegExp( `^${ escapedPattern }$` );
        return regex.test( path );
    } );
}

/**
 * Reverts a state change if verification fails.
 */
export function rollbackState ( path: string, previousValue: any ): void {
    console.warn( `[PAM] Guardrail violation or verification failure at ${ path }. Rolling back.` );
    // In a real environment, this would hook into the state manager dispatch
    console.log( `Rolling back ${ path } to previous value ${ JSON.stringify( previousValue ) }` );
}
