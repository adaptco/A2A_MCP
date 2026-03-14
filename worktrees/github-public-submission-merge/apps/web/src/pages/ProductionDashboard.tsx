import React, { useState, useEffect, useCallback, useRef } from "react";
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
    LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceLine,
    Area, AreaChart
} from "recharts";
import "./ProductionDashboard.css";
import { ViolationActions } from "../components/ViolationActions";


// ── Design tokens (AxQxOS Governance Plane) ───────────────────────────────────
const T = {
    bg: "#040B14",
    panel: "#070F1C",
    panelHi: "#0C1828",
    border: "#18D8EF18",
    borderHi: "#18D8EF55",
    cyan: "#18D8EF",
    green: "#00C893",
    amber: "#FFB800",
    red: "#FF3D3D",
    purple: "#7C3AED",
    dim: "#2A4A5A",
    text: "#A0C8D8",
    textHi: "#E0F4FA",
    mono: "'Share Tech Mono', 'Courier New', monospace",
    display: "'Orbitron', 'Arial Black', sans-serif",
};

// ── Physical constants (mirrored from monotonicity_validator.py) ──────────────
const RULES = [
    { id: "C5_SYMMETRY_VIOLATION", label: "C5 SYMMETRY", threshold: 0.8, color: T.red },
    { id: "WHEEL_GEOMETRY_MISMATCH", label: "WHEEL GEOMETRY", threshold: 0.7, color: T.amber },
    { id: "PAINT_RSM_INVALID", label: "PAINT / RSM", threshold: 0.8, color: T.red },
    { id: "TOPOLOGY_SCHEMA_DRIFT", label: "TOPOLOGY SCHEMA", threshold: 0.6, color: T.cyan },
];

const SEED = "0x19840907";
const SCHEMA = "0x1984_Q9";
const BATCHES = Array.from( { length: 10 }, ( _, i ) => `B-${ 100 + i }` );

// ── Deterministic seed-based "live" simulation ────────────────────────────────
function seededRand ( seed: number, i: number ) {
    const x = Math.sin( seed + i ) * 10000;
    return x - Math.floor( x );
}

function buildHeatmapData ( tick: number ) {
    return RULES.map( ( rule, ri ) =>
        BATCHES.map( ( _, bi ) => {
            const base = [ 0.15, 0.55, 0.82, 0.28 ][ ri ];
            const drift = Math.sin( ( bi + tick * 0.05 ) * 0.7 + ri * 1.3 ) * 0.14;
            return Math.max( 0, Math.min( 1, base + drift ) );
        } )
    );
}

function buildDriftSeries ( tick: number ) {
    return BATCHES.map( ( b, i ) => ( {
        batch: b,
        C5: Math.max( 0, 0.15 + Math.sin( ( i + tick * 0.04 ) * 0.8 ) * 0.12 ),
        WHEEL: Math.max( 0, 0.55 + Math.sin( ( i + tick * 0.03 ) * 0.6 + 1 ) * 0.15 ),
        PAINT: Math.max( 0, 0.82 + Math.sin( ( i + tick * 0.02 ) * 0.9 + 2 ) * 0.1 ),
        TOPOLOGY: Math.max( 0, 0.28 + Math.sin( ( i + tick * 0.05 ) * 0.5 + 3 ) * 0.13 ),
    } ) );
}

function buildViolationPie ( data2d: number[][] ) {
    let stable = 0, fail = 0, qc = 0, pending = 0;
    data2d.forEach( ( row, ri ) => row.forEach( val => {
        const thresh = RULES[ ri ].threshold;
        if ( val < 0.15 ) stable++;
        else if ( val >= thresh ) fail++;
        else if ( val >= thresh * 0.7 ) qc++;
        else pending++;
    } ) );
    return [
        { name: "Stable", value: stable, color: T.green },
        { name: "Pending", value: pending, color: T.cyan },
        { name: "QC", value: qc, color: T.amber },
        { name: "Fail", value: fail, color: T.red },
    ];
}

// ── HITL queue seed data ──────────────────────────────────────────────────────
const INITIAL_QUEUE = [
    { id: "VIO-001", rule: "PAINT_RSM_INVALID", batch: "B-102", intensity: 0.87, status: "pending", ts: "14:22:01" },
    { id: "VIO-002", rule: "WHEEL_GEOMETRY_MISMATCH", batch: "B-104", intensity: 0.73, status: "pending", ts: "14:23:15" },
    { id: "VIO-003", rule: "C5_SYMMETRY_VIOLATION", batch: "B-106", intensity: 0.92, status: "pending", ts: "14:24:44" },
    { id: "VIO-004", rule: "PAINT_RSM_INVALID", batch: "B-107", intensity: 0.81, status: "pending", ts: "14:25:03" },
    { id: "VIO-005", rule: "TOPOLOGY_SCHEMA_DRIFT", batch: "B-108", intensity: 0.67, status: "pending", ts: "14:26:18" },
];

// ── Sub-components ────────────────────────────────────────────────────────────
const mono = T.mono;
const disp = T.display;

function Panel ( { title, accent = T.cyan, children, badge, pulse = false }: any ) {
    return (
        <div className="pd-panel" style={ {
            background: T.panel,
            border: `1px solid ${ accent }22`,
            borderTop: `2px solid ${ accent }`,
        } }>
            <div className="pd-panel-header" style={ {
                background: T.panelHi,
                borderBottom: `1px solid ${ accent }18`,
            } }>
                <span className="pd-panel-title" style={ {
                    color: accent,
                    textShadow: `0 0 8px ${ accent }66`
                } }>
                    { title }
                </span>
                <div style={ { display: "flex", gap: "6px", alignItems: "center" } }>
                    { pulse && <span style={ {
                        width: 7, height: 7, borderRadius: "50%", background: T.red,
                        boxShadow: `0 0 8px ${ T.red }`, animation: "pulse 1.2s infinite", display: "inline-block"
                    } } /> }
                    { badge && <span style={ {
                        fontFamily: mono, fontSize: "8px", color: accent,
                        background: `${ accent }14`, padding: "2px 8px", borderRadius: "10px",
                        border: `1px solid ${ accent }33`
                    } }>{ badge }</span> }
                </div>
            </div>
            <div style={ { flex: 1, overflow: "hidden" } }>
                { children }
            </div>
        </div>
    );
}

function StatPill ( { label, value, color = T.cyan, glow = false }: any ) {
    return (
        <div className="pd-stat-pill" style={ {
            background: T.panelHi,
            border: `1px solid ${ color }22`,
        } }>
            <span className="pd-stat-label">{ label }</span>
            <span className="pd-stat-value" style={ {
                color,
                textShadow: glow ? `0 0 16px ${ color }` : "none",
            } }>{ value }</span>
        </div>
    );
}

function IntensityCell ( { val, threshold, onClick }: any ) {
    const hitl = val >= threshold;
    const warn = val >= threshold * 0.7;
    const bg = val < 0.1
        ? `rgba(0,200,147,0.1)`
        : hitl ? `rgba(255,61,61,${ val * 0.85 })`
            : warn ? `rgba(255,184,0,${ val * 0.75 })`
                : `rgba(0,200,147,${ val * 0.5 })`;
    return (
        <div
            onClick={ onClick }
            className="pd-intensity-cell"
            style={ {
                background: bg,
                border: hitl ? `1px solid ${ T.red }66` : "1px solid transparent",
            } }
            title={ `${ ( val * 100 ).toFixed( 1 ) }%` }
        >
            { hitl && <span style={ { fontSize: "7px", color: T.red, fontFamily: mono } }>⚠</span> }
        </div>
    );
}

function DecisionRow ( { item, onDecide }: any ) {
    const rule = RULES.find( r => r.id === item.rule );
    const color = rule?.color ?? T.cyan;
    const decided = item.status !== "pending";
    return (
        <div className="pd-decision-row" style={ {
            opacity: decided ? 0.5 : 1,
            background: decided ? "transparent" : `${ color }06`,
        } }>
            <span style={ { fontFamily: mono, fontSize: "8px", color: T.dim } }>{ item.id }</span>
            <div>
                <div style={ { fontFamily: mono, fontSize: "9px", color } }>{ rule?.label ?? item.rule }</div>
                <div style={ { fontFamily: mono, fontSize: "7px", color: T.dim } }>
                    { item.batch } · { item.ts }
                </div>
            </div>
            <div style={ { display: "flex", alignItems: "center", gap: "4px" } }>
                <div style={ {
                    flex: 1, height: "4px", borderRadius: "2px",
                    background: `rgba(255,61,61,${ item.intensity * 0.9 })`,
                } } />
                <span style={ { fontFamily: mono, fontSize: "7px", color: T.red } }>
                    { ( item.intensity * 100 ).toFixed( 0 ) }%
                </span>
            </div>
            <span style={ {
                fontFamily: mono, fontSize: "7px", textAlign: "center",
                padding: "2px 6px", borderRadius: "2px",
                color: item.status === "approved" ? T.green : item.status === "rejected" ? T.red : T.amber,
                border: `1px solid ${ item.status === "approved" ? T.green : item.status === "rejected" ? T.red : T.amber }44`,
            } }>
                { item.status.toUpperCase() }
            </span>
            <ViolationActions
                item={ item }
                onDecide={ onDecide }
            />
        </div>
    );
}

// ── Custom chart tooltip ───────────────────────────────────────────────────────
function CustomDriftTooltip ( { active, payload, label }: any ) {
    if ( !active || !payload?.length ) return null;
    return (
        <div style={ {
            background: T.panelHi, border: `1px solid ${ T.borderHi }`,
            borderRadius: "4px", padding: "10px 14px", fontFamily: mono, fontSize: "8px",
        } }>
            <div style={ { color: T.cyan, marginBottom: "6px", letterSpacing: "2px" } }>{ label }</div>
            { payload.map( ( p: any ) => (
                <div key={ p.dataKey } style={ { color: p.color, display: "flex", justifyContent: "space-between", gap: "16px" } }>
                    <span>{ p.dataKey }</span>
                    <span style={ { fontFamily: disp, fontSize: "10px" } }>{ ( p.value * 100 ).toFixed( 1 ) }%</span>
                </div>
            ) ) }
        </div>
    );
}

function CustomPieTip ( { active, payload }: any ) {
    if ( !active || !payload?.length ) return null;
    const d = payload[ 0 ];
    return (
        <div style={ {
            background: T.panelHi, border: `1px solid ${ d.payload.color }44`,
            borderRadius: "4px", padding: "8px 12px", fontFamily: mono, fontSize: "9px",
        } }>
            <div style={ { color: d.payload.color } }>{ d.name }</div>
            <div style={ { color: T.textHi, fontFamily: disp, fontSize: "14px" } }>{ d.value }</div>
            <div style={ { color: T.dim } }>cells</div>
        </div>
    );
}

// ── Telemetry injector panel ───────────────────────────────────────────────────
function TelemetryInjector ( { onInject }: any ) {
    const [ vals, setVals ] = useState( { wheel_spokes: "5", wheel_finish: "RSM", fov: "60", body_color: "obsidian_black" } );
    const [ log, setLog ] = useState<any[]>( [] );

    const inject = () => {
        const pred = {
            wheel_spokes: parseInt( vals.wheel_spokes ),
            wheel_finish: vals.wheel_finish,
            fov_degrees: parseFloat( vals.fov ),
            body_color: vals.body_color,
            wheel_model: "advan_gt_beyond",
            stroke_color: "#18D8EF",
            render_width: 3840,
            render_height: 2160,
            camera_angle: "low_angle_3q",
            background_schema: "gemini_galaxy",
        };
        const violations = [];
        if ( pred.wheel_spokes !== 5 ) violations.push( `C5_SYMMETRY: ${ pred.wheel_spokes }-spoke ⚠` );
        if ( pred.wheel_finish !== "RSM" ) violations.push( `PAINT_RSM: ${ pred.wheel_finish } ⚠` );
        if ( Math.abs( pred.fov_degrees - 60 ) > 5 ) violations.push( `TOPOLOGY: FOV=${ pred.fov_degrees }° ⚠` );
        if ( pred.body_color !== "obsidian_black" ) violations.push( `PAINT: ${ pred.body_color } ⚠` );
        const entry = {
            ts: new Date().toLocaleTimeString(),
            status: violations.length === 0 ? "PASS" : "REJECT",
            violations,
        };
        setLog( l => [ entry, ...l ].slice( 0, 5 ) );
        onInject( pred, violations.length === 0 );
    };

    const field = ( label: string, key: keyof typeof vals, type = "text", opts?: string[] ) => (
        <div style={ { display: "flex", flexDirection: "column", gap: "3px" } }>
            <label style={ { fontFamily: mono, fontSize: "7px", color: T.dim, letterSpacing: "1px" } }>{ label }</label>
            { opts ? (
                <select
                    title={ label }
                    aria-label={ label }
                    value={ vals[ key ] }
                    onChange={ e => setVals( v => ( { ...v, [ key ]: e.target.value } ) ) }
                    style={ {
                        background: T.bg, border: `1px solid ${ T.border }`, color: T.text,
                        fontFamily: mono, fontSize: "9px", padding: "4px 6px", borderRadius: "2px"
                    } }>
                    { opts.map( o => <option key={ o }>{ o }</option> ) }
                </select>
            ) : (
                <input
                    title={ label }
                    aria-label={ label }
                    type={ type }
                    value={ vals[ key ] }
                    onChange={ e => setVals( v => ( { ...v, [ key ]: e.target.value } ) ) }
                    style={ {
                        background: T.bg, border: `1px solid ${ T.border }`, color: T.text,
                        fontFamily: mono, fontSize: "9px", padding: "4px 6px", borderRadius: "2px",
                        width: "100%"
                    } } />
            ) }
        </div>
    );

    return (
        <div className="pd-injector-form">
            <div style={ { fontFamily: mono, fontSize: "8px", color: T.dim } }>
                Inject prediction against physical constants — SEED { SEED }
            </div>
            <div style={ { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" } }>
                { field( "WHEEL SPOKES", "wheel_spokes", "number" ) }
                { field( "WHEEL FINISH", "wheel_finish", "text", [ "RSM", "matte_black", "gloss_white", "carbon" ] ) }
                { field( "FOV (degrees)", "fov", "number" ) }
                { field( "BODY COLOR", "body_color", "text", [ "obsidian_black", "racing_green", "white", "silver" ] ) }
            </div>
            <button type="button" onClick={ inject } style={ {
                background: "transparent", border: `1px solid ${ T.cyan }`,
                color: T.cyan, fontFamily: disp, fontSize: "8px", letterSpacing: "3px",
                padding: "7px", cursor: "pointer", borderRadius: "2px",
                transition: "all 0.2s",
            } }>⚡ INJECT PAYLOAD</button>
            <div style={ { flex: 1, overflow: "hidden" } }>
                { log.map( ( e, i ) => (
                    <div key={ i } style={ {
                        display: "flex", gap: "8px", padding: "3px 0",
                        borderBottom: `1px solid ${ T.border }`,
                        fontFamily: mono, fontSize: "7px",
                    } }>
                        <span style={ { color: T.dim, flexShrink: 0 } }>{ e.ts }</span>
                        <span style={ { color: e.status === "PASS" ? T.green : T.red, flexShrink: 0 } }>{ e.status }</span>
                        <span style={ { color: T.dim, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }>
                            { e.violations.length ? e.violations.join( " · " ) : "All constants nominal" }
                        </span>
                    </div>
                ) ) }
            </div>
        </div>
    );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function GovernanceDashboard () {
    const [ tick, setTick ] = useState( 0 );
    const [ live, setLive ] = useState( true );
    const [ queue, setQueue ] = useState( INITIAL_QUEUE );
    const [ totalBatches, setTotalBatches ] = useState( 10 );
    const [ totalViolations, setTotalViolations ] = useState( 47 );
    const [ injections, setInjections ] = useState( 0 );
    const [ governanceStatus, setGovernanceStatus ] = useState( "ESCALATED" );
    const [ selectedCell, setSelectedCell ] = useState<any>( null );

    const heatmap = buildHeatmapData( tick );
    const driftSeries = buildDriftSeries( tick );
    const pieData = buildViolationPie( heatmap );

    const pendingCount = queue.filter( q => q.status === "pending" ).length;
    const criticalCount = heatmap.flat().filter( ( v, i ) => {
        const ri = Math.floor( i / BATCHES.length );
        return v >= ( RULES[ ri ]?.threshold ?? 1 );
    } ).length;

    // Live tick
    useEffect( () => {
        if ( !live ) return;
        const iv = setInterval( () => setTick( t => t + 1 ), 2000 );
        return () => clearInterval( iv );
    }, [ live ] );

    // Auto-add violations to queue
    useEffect( () => {
        if ( tick > 0 && tick % 15 === 0 )
        {
            const ruleIdx = Math.floor( seededRand( tick, 1 ) * RULES.length );
            const batchIdx = Math.floor( seededRand( tick, 2 ) * BATCHES.length );
            const intensity = 0.75 + seededRand( tick, 3 ) * 0.2;
            const rule = RULES[ ruleIdx ];
            if ( intensity >= rule.threshold )
            {
                const newItem = {
                    id: `VIO-${ String( queue.length + 1 ).padStart( 3, "0" ) }`,
                    rule: rule.id,
                    batch: BATCHES[ batchIdx ],
                    intensity: parseFloat( intensity.toFixed( 3 ) ),
                    status: "pending",
                    ts: new Date().toLocaleTimeString(),
                };
                setQueue( q => [ newItem, ...q ].slice( 0, 12 ) );
                setTotalViolations( v => v + 1 );
                setTotalBatches( b => tick % 20 === 0 ? b + 1 : b );
            }
        }
    }, [ tick ] );

    const handleDecide = useCallback( ( id: string, decision: string ) => {
        setQueue( q => q.map( item =>
            item.id === id ? { ...item, status: decision } : item
        ) );
        const remaining = queue.filter( q => q.status === "pending" && q.id !== id ).length - 1;
        setGovernanceStatus( remaining <= 0 ? "NOMINAL" : "ESCALATED" );
    }, [ queue ] );

    const handleInject = ( pred: any, passed: boolean ) => {
        setInjections( i => i + 1 );
        if ( !passed )
        {
            setTotalViolations( v => v + 1 );
            const rule = RULES.find( r => r.id === "C5_SYMMETRY_VIOLATION" ) || RULES[ 0 ];
            const newItem = {
                id: `VIO-${ String( queue.length + 1 ).padStart( 3, "0" ) }`,
                rule: rule.id,
                batch: "INJECTED",
                intensity: 0.95, // High intensity for forced injection
                status: "pending",
                ts: new Date().toLocaleTimeString(),
            };
            setQueue( q => [ newItem, ...q ].slice( 0, 12 ) );
        }
    };

    // Threshold lines for drift chart
    const DRIFT_THRESHOLDS = [
        { y: 0.8, label: "C5/PAINT", color: T.red },
        { y: 0.7, label: "WHEEL", color: T.amber },
        { y: 0.6, label: "TOPOLOGY", color: T.cyan },
    ];

    return (
        <div className="production-dashboard">
            <style>{ `
        @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.85)} }
        @keyframes scanIn { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:translateY(0)} }
        @keyframes glow { 0%,100%{box-shadow:0 0 8px #18D8EF33} 50%{box-shadow:0 0 16px #18D8EF66} }
        button:hover { filter: brightness(1.2); }
        select:focus, input:focus { outline: 1px solid #18D8EF66; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-thumb { background: #18D8EF22; }
        * { box-sizing: border-box; }
      `}</style>

            {/* ── HEADER ── */ }
            <div className="pd-header">
                <div>
                    <div className="pd-header-title">
                        GOVERNANCE & HITL DASHBOARD
                    </div>
                    <div className="pd-header-subtitle">
                        WAREHOUSE PHYSICS PLANE · SCHEMA { SCHEMA } · SEED { SEED }
                    </div>
                </div>
                <div className="pd-kpi-container">
                    {/* KPI pills */ }
                    { [
                        { l: "BATCHES", v: totalBatches, c: T.cyan },
                        { l: "VIOLATIONS", v: totalViolations, c: T.red },
                        { l: "HITL QUEUE", v: pendingCount, c: pendingCount > 0 ? T.amber : T.green },
                        { l: "INJECTIONS", v: injections, c: T.purple },
                    ].map( ( { l, v, c } ) => (
                        <div key={ l } className="pd-kpi-pill" style={ {
                            background: `${ c }12`,
                            border: `1px solid ${ c }33`,
                        } }>
                            <div className="pd-kpi-label">{ l }</div>
                            <div className="pd-kpi-value" style={ { color: c } }>{ v }</div>
                        </div>
                    ) ) }
                    {/* Status */ }
                    <div className="pd-governance-status" style={ {
                        background: governanceStatus === "NOMINAL" ? `${ T.green }12` : `${ T.red }12`,
                        border: `1px solid ${ governanceStatus === "NOMINAL" ? T.green : T.red }44`,
                    } }>
                        <span className="pd-status-dot" style={ {
                            background: governanceStatus === "NOMINAL" ? T.green : T.red,
                            boxShadow: `0 0 8px ${ governanceStatus === "NOMINAL" ? T.green : T.red }`,
                            animation: governanceStatus !== "NOMINAL" ? "pulse 1.2s infinite" : "none",
                        } } />
                        <span className="pd-status-text" style={ {
                            color: governanceStatus === "NOMINAL" ? T.green : T.red,
                        } }>
                            { governanceStatus }
                        </span>
                    </div>
                    {/* Live toggle */ }
                    <button type="button" onClick={ () => setLive( l => !l ) } className="pd-live-toggle" style={ {
                        background: live ? `${ T.green }18` : "transparent",
                        border: `1px solid ${ live ? T.green : T.dim }`,
                        color: live ? T.green : T.dim,
                    } }>
                        { live ? "● LIVE" : "○ PAUSED" }
                    </button>
                </div>
            </div>

            {/* ── ROW 1: Stats + Pie + Drift ── */ }
            <div className="pd-main-grid">

                {/* KPI column */ }
                <div style={ { display: "flex", flexDirection: "column", gap: "8px" } }>
                    <StatPill label="CRITICAL CELLS" value={ criticalCount } color={ T.red } glow={ criticalCount > 5 } />
                    <StatPill label="AVG INTENSITY" value={ `${ ( heatmap.flat().reduce( ( a, v ) => a + v, 0 ) / heatmap.flat().length * 100 ).toFixed( 1 ) }%` } color={ T.amber } />
                    <StatPill label="PENDING HITL" value={ pendingCount } color={ pendingCount > 0 ? T.amber : T.green } />
                    <StatPill label="TICK / EPOCH" value={ tick } color={ T.cyan } glow />
                    <div style={ {
                        background: T.panelHi,
                        border: `1px solid ${ T.border }`,
                        borderRadius: "4px",
                        padding: "8px 12px",
                        fontSize: "8px",
                        lineHeight: "1.8",
                        color: T.dim,
                    } }>
                        <div style={ { color: T.cyan, letterSpacing: "2px", marginBottom: "4px" } }>INVARIANTS</div>
                        { [ [ "SPOKES", "5 (C5)" ], [ "FINISH", "RSM" ], [ "COLOR", "OBSIDIAN" ], [ "FOV", "60°" ], [ "RES", "3840×2160" ] ].map( ( [ k, v ] ) => (
                            <div key={ k } style={ { display: "flex", justifyContent: "space-between" } }>
                                <span>{ k }</span><span style={ { color: T.green } }>{ v }</span>
                            </div>
                        ) ) }
                    </div>
                </div>

                {/* Pie chart */ }
                <Panel title="/// VIOLATION DISTRIBUTION" accent={ T.cyan }
                    badge={ `${ pieData.find( p => p.name === "Fail" )?.value ?? 0 } FAIL` }
                    pulse={ criticalCount > 5 }>
                    <div style={ { height: "220px", padding: "8px" } }>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie data={ pieData } cx="50%" cy="50%" innerRadius={ 48 } outerRadius={ 78 }
                                    paddingAngle={ 3 } dataKey="value" strokeWidth={ 0 }>
                                    { pieData.map( ( d, i ) => (
                                        <Cell key={ i } fill={ d.color } opacity={ 0.85 } />
                                    ) ) }
                                </Pie>
                                <Tooltip content={ <CustomPieTip /> } />
                                <Legend
                                    formatter={ ( val, entry: any ) => (
                                        <span style={ { fontFamily: mono, fontSize: "8px", color: entry.color } }>
                                            { val }
                                        </span>
                                    ) }
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div style={ { padding: "0 14px 8px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" } }>
                        { pieData.map( d => (
                            <div key={ d.name } style={ { display: "flex", alignItems: "center", gap: "6px" } }>
                                <div style={ { width: 8, height: 8, borderRadius: "1px", background: d.color, flexShrink: 0 } } />
                                <span style={ { fontFamily: mono, fontSize: "8px", color: T.dim } }>{ d.name }</span>
                                <span style={ { fontFamily: disp, fontSize: "10px", color: d.color, marginLeft: "auto" } }>
                                    { d.value }
                                </span>
                            </div>
                        ) ) }
                    </div>
                </Panel>

                {/* Drift line chart */ }
                <Panel title="/// DRIFT MONOTONICITY — COMPLEXITY OVER BATCHES" accent={ T.amber }
                    badge="THRESHOLD ACTIVE">
                    <div style={ { height: "280px", padding: "8px 4px 0 0" } }>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={ driftSeries } margin={ { top: 8, right: 16, bottom: 8, left: -10 } }>
                                <CartesianGrid stroke={ T.border } strokeDasharray="3 3" />
                                <XAxis dataKey="batch" tick={ { fontFamily: mono, fontSize: 8, fill: T.dim } } tickLine={ false } />
                                <YAxis domain={ [ 0, 1.05 ] } tickFormatter={ v => `${ ( v * 100 ).toFixed( 0 ) }%` }
                                    tick={ { fontFamily: mono, fontSize: 7, fill: T.dim } } tickLine={ false } />
                                <Tooltip content={ <CustomDriftTooltip /> } />
                                { DRIFT_THRESHOLDS.map( t => (
                                    <ReferenceLine key={ t.y } y={ t.y } stroke={ t.color }
                                        strokeDasharray="5 3" strokeOpacity={ 0.6 }
                                        label={ {
                                            value: t.label, fontSize: 7, fill: t.color,
                                            fontFamily: mono, position: "insideTopRight"
                                        } } />
                                ) ) }
                                { [
                                    { key: "C5", color: T.red },
                                    { key: "WHEEL", color: T.amber },
                                    { key: "PAINT", color: "#FF6B6B" },
                                    { key: "TOPOLOGY", color: T.cyan },
                                ].map( ( { key, color } ) => (
                                    <Line key={ key } type="monotone" dataKey={ key } stroke={ color }
                                        strokeWidth={ 1.5 } dot={ false } isAnimationActive={ false }
                                        activeDot={ { r: 4, fill: color, strokeWidth: 0 } } />
                                ) ) }
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </Panel>
            </div>

            {/* ── ROW 2: Heatmap ── */ }
            <div style={ { padding: "0 8px 8px" } }>
                <Panel title="/// RULE-FAILURE HEATMAP — HARD REJECT VIOLATIONS · 10-BATCH WINDOW"
                    accent={ T.red } badge={ `${ criticalCount } CRITICAL` } pulse={ criticalCount > 0 }>
                    <div style={ { padding: "10px 14px" } }>
                        <div style={ { display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px" } }>
                            {/* Y labels */ }
                            <div style={ { display: "flex", flexDirection: "column", gap: "4px" } }>
                                { RULES.map( r => (
                                    <div key={ r.id } style={ {
                                        height: "28px", display: "flex", alignItems: "center",
                                        fontSize: "8px", color: T.dim, letterSpacing: "1px"
                                    } }>
                                        <span style={ {
                                            width: 6, height: 6, borderRadius: "50%", background: r.color,
                                            marginRight: 6, flexShrink: 0, boxShadow: `0 0 4px ${ r.color }`
                                        } } />
                                        { r.label }
                                    </div>
                                ) ) }
                            </div>
                            {/* Cells */ }
                            <div>
                                { RULES.map( ( rule, ri ) => (
                                    <div key={ rule.id } style={ {
                                        display: "grid",
                                        gridTemplateColumns: `repeat(${ BATCHES.length }, 1fr)`,
                                        gap: "3px", marginBottom: "4px"
                                    } }>
                                        { BATCHES.map( ( batch, bi ) => (
                                            <IntensityCell
                                                key={ bi }
                                                val={ heatmap[ ri ][ bi ] }
                                                threshold={ rule.threshold }
                                                onClick={ () => setSelectedCell(
                                                    selectedCell?.ri === ri && selectedCell?.bi === bi
                                                        ? null
                                                        : { ri, bi, rule, batch, val: heatmap[ ri ][ bi ] }
                                                ) }
                                            />
                                        ) ) }
                                    </div>
                                ) ) }
                                {/* X labels */ }
                                <div style={ { display: "grid", gridTemplateColumns: `repeat(${ BATCHES.length }, 1fr)`, gap: "3px", marginTop: "4px" } }>
                                    { BATCHES.map( b => (
                                        <div key={ b } style={ { fontSize: "7px", color: T.dim, textAlign: "center" } }>{ b }</div>
                                    ) ) }
                                </div>
                            </div>
                        </div>

                        {/* Selected cell detail */ }
                        { selectedCell && (
                            <div style={ {
                                marginTop: "10px",
                                background: `${ selectedCell.rule.color }12`,
                                border: `1px solid ${ selectedCell.rule.color }44`,
                                borderRadius: "3px",
                                padding: "8px 12px",
                                display: "flex",
                                gap: "24px",
                                alignItems: "center",
                                animation: "scanIn 0.2s ease",
                            } }>
                                <div>
                                    <div style={ { fontSize: "7px", color: T.dim } }>RULE</div>
                                    <div style={ { fontFamily: disp, fontSize: "10px", color: selectedCell.rule.color } }>
                                        { selectedCell.rule.label }
                                    </div>
                                </div>
                                <div>
                                    <div style={ { fontSize: "7px", color: T.dim } }>BATCH</div>
                                    <div style={ { fontFamily: mono, fontSize: "11px", color: T.textHi } }>{ selectedCell.batch }</div>
                                </div>
                                <div>
                                    <div style={ { fontSize: "7px", color: T.dim } }>INTENSITY</div>
                                    <div style={ { fontFamily: disp, fontSize: "14px", color: selectedCell.rule.color } }>
                                        { ( selectedCell.val * 100 ).toFixed( 1 ) }%
                                    </div>
                                </div>
                                <div>
                                    <div style={ { fontSize: "7px", color: T.dim } }>THRESHOLD</div>
                                    <div style={ { fontFamily: mono, fontSize: "11px", color: T.amber } }>
                                        { ( selectedCell.rule.threshold * 100 ).toFixed( 0 ) }%
                                    </div>
                                </div>
                                <div>
                                    <div style={ { fontSize: "7px", color: T.dim } }>STATUS</div>
                                    <div style={ {
                                        fontFamily: disp, fontSize: "10px",
                                        color: selectedCell.val >= selectedCell.rule.threshold ? T.red : T.amber
                                    } }>
                                        { selectedCell.val >= selectedCell.rule.threshold ? "⚠ HITL REQUIRED" : "WARN" }
                                    </div>
                                </div>
                                <button type="button" onClick={ () => setSelectedCell( null ) }
                                    style={ {
                                        marginLeft: "auto", background: "none", border: `1px solid ${ T.dim }`,
                                        color: T.dim, fontFamily: mono, fontSize: "8px", padding: "3px 8px",
                                        cursor: "pointer", borderRadius: "2px"
                                    } }>CLOSE</button>
                            </div>
                        ) }

                        {/* Legend */ }
                        <div style={ {
                            display: "flex", justifyContent: "space-between", marginTop: "8px",
                            fontSize: "7px", color: T.dim
                        } }>
                            <span>T-MINUS 10 BATCHES</span>
                            <div style={ { display: "flex", alignItems: "center", gap: "6px" } }>
                                <span style={ { color: T.green } }>Stable</span>
                                { [ 0.2, 0.4, 0.6, 0.8, 1.0 ].map( ( v, i ) => (
                                    <div key={ v } style={ {
                                        width: 12, height: 12, borderRadius: "2px",
                                        background: i < 2 ? `rgba(0,200,147,${ v * 0.8 })` : i < 4 ? `rgba(255,184,0,${ v * 0.7 })` : `rgba(255,61,61,0.9)`
                                    } } />
                                ) ) }
                                <span style={ { color: T.red } }>Critical Drift</span>
                            </div>
                            <span>LATEST RELEASE</span>
                        </div>
                    </div>
                </Panel>
            </div>

            {/* ── ROW 3: HITL Queue + Injector ── */ }
            <div style={ { display: "grid", gridTemplateColumns: "1fr 340px", gap: "8px", padding: "0 8px 8px", flex: 1, minHeight: 0 } }>

                {/* Decision table */ }
                <Panel title="/// HITL DECISION TABLE — INTERACTIVE OVERRIDES"
                    accent={ T.amber } badge={ `${ pendingCount } PENDING` } pulse={ pendingCount > 0 }>
                    <div style={ { overflow: "auto", height: "100%" } }>
                        {/* Header */ }
                        <div className="pd-decision-header">
                            <span>ID</span><span>RULE / BATCH</span>
                            <span>INTENSITY</span><span>STATUS</span><span>ACTION</span>
                        </div>
                        { queue.map( item => (
                            <DecisionRow key={ item.id } item={ item } onDecide={ handleDecide } />
                        ) ) }
                        { queue.length === 0 && (
                            <div style={ { padding: "24px", textAlign: "center", color: T.dim, fontSize: "9px" } }>
                                No violations in queue. Governance nominal.
                            </div>
                        ) }
                    </div>
                </Panel>

                {/* Telemetry injector */ }
                <Panel title="/// TELEMETRY INJECTOR — LIVE PAYLOAD TEST" accent={ T.purple }>
                    <TelemetryInjector onInject={ handleInject } />
                </Panel>
            </div>

            {/* ── FOOTER ── */ }
            <div className="pd-footer">
                <span>AxQxOS · Governance Plane · monotonicity_validator.py · Dwight Layer</span>
                <span>Schema { SCHEMA } · Seed { SEED } · Sol.F1 Bus · &quot;Canonical truth, attested and replayable.&quot;</span>
                <span>Luma Quality Gate · Ed25519 receipts · /receipts/ · Sovereignty Chain ACTIVE</span>
            </div>
        </div>
    );
}
