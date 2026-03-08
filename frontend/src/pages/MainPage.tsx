import { FormEvent, useEffect, useState } from 'react'
import {
  MusicVideoPlanRequest,
  MusicVideoPlanResponse,
  MusicVideoSourcesResponse,
  createMusicVideoPlan,
  getMusicVideoSources,
} from '../services/api'

const initialForm: MusicVideoPlanRequest = {
  title: 'Worldline Anthem',
  concept:
    'A synthetic avatar performer crosses a shifting lattice city while every section escalates from intimate telemetry fragments into wide geometric stage reveals.',
  lyrics_excerpt:
    'Signal in the dark, hold the line, break the orbit, come back brighter',
  protagonist: 'an original synthetic avatar performer in graphite tailoring',
  vibe: 'futurist, cinematic, precise, emotionally restrained',
  visual_motif: 'worldline lattice, capsule telemetry, geodesic motion',
  aspect_ratio: 'landscape',
  duration_seconds: 48,
  preferred_clip_seconds: 8,
  model: 'sora-2',
  top_k: 3,
}

function downloadText(filename: string, contents: string) {
  const blob = new Blob([contents], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

async function copyText(contents: string) {
  await navigator.clipboard.writeText(contents)
}

export default function MainPage() {
  const [form, setForm] = useState<MusicVideoPlanRequest>(initialForm)
  const [sources, setSources] = useState<MusicVideoSourcesResponse | null>(null)
  const [plan, setPlan] = useState<MusicVideoPlanResponse | null>(null)
  const [loadingSources, setLoadingSources] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedLabel, setCopiedLabel] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    getMusicVideoSources()
      .then((data) => {
        if (!active) return
        setSources(data)
      })
      .catch((sourceError) => {
        if (!active) return
        setError(sourceError instanceof Error ? sourceError.message : 'Failed to load sources.')
      })
      .finally(() => {
        if (active) setLoadingSources(false)
      })

    return () => {
      active = false
    }
  }, [])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      const response = await createMusicVideoPlan(form)
      setPlan(response)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Planning request failed.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCopy = async (label: string, contents: string) => {
    try {
      await copyText(contents)
      setCopiedLabel(label)
      window.setTimeout(() => setCopiedLabel((current) => (current === label ? null : current)), 1800)
    } catch {
      setError(`Clipboard write failed for ${label}.`)
    }
  }

  return (
    <main className="shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">A2A x Sora Long-Form Planner</p>
          <h1>Music video generation with RAG-grounded continuity.</h1>
          <p className="hero-text">
            This planner reads the ARIA kernel, the external agent registry, the orchestration
            skill spec, and the local avatar core to turn a brief into stitch-safe Sora clips.
          </p>
        </div>
        <div className="hero-metrics">
          <div className="metric-card">
            <span className="metric-value">
              {loadingSources ? '...' : sources?.source_catalog.filter((item) => item.exists).length ?? 0}
            </span>
            <span className="metric-label">Context sources</span>
          </div>
          <div className="metric-card">
            <span className="metric-value">{sources?.avatar_cast.length ?? 0}</span>
            <span className="metric-label">Avatar roles</span>
          </div>
          <div className="metric-card">
            <span className="metric-value">
              {sources?.openai_api_key_present ? 'Ready' : 'Dry'}
            </span>
            <span className="metric-label">Sora mode</span>
          </div>
        </div>
      </section>

      {error ? <div className="status-banner error">{error}</div> : null}

      <section className="workspace-grid">
        <form className="panel form-panel" onSubmit={handleSubmit}>
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Brief</p>
              <h2>Build a stitched shot plan</h2>
            </div>
            <button className="primary-button" type="submit" disabled={submitting}>
              {submitting ? 'Planning...' : 'Generate plan'}
            </button>
          </div>

          <label className="field">
            <span>Title</span>
            <input
              value={form.title}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
            />
          </label>

          <label className="field">
            <span>Concept</span>
            <textarea
              rows={5}
              value={form.concept}
              onChange={(event) => setForm((current) => ({ ...current, concept: event.target.value }))}
            />
          </label>

          <label className="field">
            <span>Lyrics or beat cues</span>
            <textarea
              rows={3}
              value={form.lyrics_excerpt ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, lyrics_excerpt: event.target.value }))
              }
            />
          </label>

          <div className="field-grid">
            <label className="field">
              <span>Protagonist</span>
              <input
                value={form.protagonist}
                onChange={(event) =>
                  setForm((current) => ({ ...current, protagonist: event.target.value }))
                }
              />
            </label>

            <label className="field">
              <span>Visual motif</span>
              <input
                value={form.visual_motif}
                onChange={(event) =>
                  setForm((current) => ({ ...current, visual_motif: event.target.value }))
                }
              />
            </label>
          </div>

          <div className="field-grid">
            <label className="field">
              <span>Vibe</span>
              <input
                value={form.vibe}
                onChange={(event) => setForm((current) => ({ ...current, vibe: event.target.value }))}
              />
            </label>

            <label className="field">
              <span>Duration (seconds)</span>
              <input
                min={4}
                max={240}
                type="number"
                value={form.duration_seconds}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    duration_seconds: Number(event.target.value),
                  }))
                }
              />
            </label>
          </div>

          <div className="field-grid three-up">
            <label className="field">
              <span>Preferred clip</span>
              <select
                value={form.preferred_clip_seconds ?? 8}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    preferred_clip_seconds: Number(event.target.value),
                  }))
                }
              >
                <option value={4}>4 seconds</option>
                <option value={8}>8 seconds</option>
                <option value={12}>12 seconds</option>
              </select>
            </label>

            <label className="field">
              <span>Aspect</span>
              <select
                value={form.aspect_ratio}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    aspect_ratio: event.target.value as 'landscape' | 'portrait',
                  }))
                }
              >
                <option value="landscape">Landscape</option>
                <option value="portrait">Portrait</option>
              </select>
            </label>

            <label className="field">
              <span>Model</span>
              <select
                value={form.model}
                onChange={(event) => setForm((current) => ({ ...current, model: event.target.value }))}
              >
                <option value="sora-2">sora-2</option>
                <option value="sora-2-pro">sora-2-pro</option>
              </select>
            </label>
          </div>

          <label className="field">
            <span>Top-k retrieval hits per shot</span>
            <input
              min={1}
              max={6}
              type="number"
              value={form.top_k}
              onChange={(event) =>
                setForm((current) => ({ ...current, top_k: Number(event.target.value) }))
              }
            />
          </label>

          <div className="source-strip">
            <div className="source-strip-header">
              <h3>Source availability</h3>
              <span>
                {sources?.sora_script_exists ? 'Sora CLI detected' : 'Sora CLI missing'}
              </span>
            </div>
            <div className="source-list">
              {sources?.source_catalog.map((source) => (
                <div className={`source-chip ${source.exists ? 'ok' : 'missing'}`} key={source.key}>
                  <strong>{source.label}</strong>
                  <span>{source.exists ? 'loaded' : 'missing'}</span>
                </div>
              ))}
            </div>
          </div>
        </form>

        <section className="panel results-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Plan output</p>
              <h2>Continuity, prompts, and render artifacts</h2>
            </div>
            {plan ? (
              <div className="panel-actions">
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => downloadText(`${plan.title}.jobs.jsonl`, plan.sora_batch.jsonl)}
                >
                  Download JSONL
                </button>
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() =>
                    downloadText(`${plan.title}.concat.txt`, plan.sora_batch.stitch_command)
                  }
                >
                  Save stitch command
                </button>
              </div>
            ) : null}
          </div>

          {!plan ? (
            <div className="empty-state">
              <p>
                Generate a plan to see the continuity bible, shot prompts, Sora batch JSONL,
                and the adapter dataset for LoRA-style prompt expansion.
              </p>
            </div>
          ) : (
            <>
              <div className="summary-grid">
                <article className="summary-card">
                  <span className="summary-value">{plan.shot_plan.length}</span>
                  <span className="summary-label">Shots</span>
                </article>
                <article className="summary-card">
                  <span className="summary-value">{plan.planned_duration_seconds}s</span>
                  <span className="summary-label">Planned runtime</span>
                </article>
                <article className="summary-card">
                  <span className="summary-value">
                    {plan.sora_batch.openai_api_key_present ? 'Live' : 'Dry-run'}
                  </span>
                  <span className="summary-label">Execution mode</span>
                </article>
              </div>

              <p className="plan-summary">{plan.summary}</p>

              {plan.notes.length > 0 ? (
                <div className="notes-block">
                  {plan.notes.map((note) => (
                    <p key={note}>{note}</p>
                  ))}
                </div>
              ) : null}

              <section className="section-block">
                <div className="section-header">
                  <h3>Continuity bible</h3>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() =>
                      handleCopy(
                        'continuity',
                        JSON.stringify(plan.continuity_bible, null, 2),
                      )
                    }
                  >
                    {copiedLabel === 'continuity' ? 'Copied' : 'Copy JSON'}
                  </button>
                </div>
                <div className="continuity-grid">
                  <div>
                    <p className="mini-label">Palette</p>
                    <div className="token-list">
                      {plan.continuity_bible.palette.map((tone) => (
                        <span className="token" key={tone}>
                          {tone}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mini-label">Narrative arc</p>
                    <div className="token-list">
                      {plan.continuity_bible.narrative_arc.map((beat) => (
                        <span className="token muted" key={beat}>
                          {beat}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mini-label">Rules</p>
                    {plan.continuity_bible.continuity_rules.map((rule) => (
                      <p className="rule-line" key={rule}>
                        {rule}
                      </p>
                    ))}
                  </div>
                </div>
              </section>

              <section className="section-block">
                <div className="section-header">
                  <h3>Avatar cast</h3>
                </div>
                <div className="avatar-grid">
                  {plan.avatar_cast.map((avatar) => (
                    <article className="avatar-card" key={avatar.avatar_id}>
                      <p className="avatar-style">{avatar.style}</p>
                      <h4>{avatar.avatar_name || avatar.agent_name}</h4>
                      <p>{avatar.description}</p>
                    </article>
                  ))}
                </div>
              </section>

              <section className="section-block">
                <div className="section-header">
                  <h3>Sora artifacts</h3>
                  <div className="panel-actions">
                    <button
                      className="ghost-button"
                      type="button"
                      onClick={() => handleCopy('jsonl', plan.sora_batch.jsonl)}
                    >
                      {copiedLabel === 'jsonl' ? 'Copied' : 'Copy JSONL'}
                    </button>
                    <button
                      className="ghost-button"
                      type="button"
                      onClick={() =>
                        handleCopy('dry-run', plan.sora_batch.dry_run_command)
                      }
                    >
                      {copiedLabel === 'dry-run' ? 'Copied' : 'Copy dry-run'}
                    </button>
                  </div>
                </div>
                <div className="artifact-grid">
                  <article className="artifact-card">
                    <p className="mini-label">Dry-run command</p>
                    <pre>{plan.sora_batch.dry_run_command}</pre>
                  </article>
                  <article className="artifact-card">
                    <p className="mini-label">Live command</p>
                    <pre>{plan.sora_batch.live_command}</pre>
                  </article>
                  <article className="artifact-card">
                    <p className="mini-label">Stitch command</p>
                    <pre>{plan.sora_batch.stitch_command}</pre>
                  </article>
                </div>
              </section>

              <section className="section-block">
                <div className="section-header">
                  <h3>Shot timeline</h3>
                </div>
                <div className="shot-list">
                  {plan.shot_plan.map((shot) => (
                    <article className="shot-card" key={shot.shot_id}>
                      <div className="shot-meta">
                        <span>{shot.shot_id}</span>
                        <span>{shot.start_second}s</span>
                        <span>{shot.duration_seconds}s</span>
                      </div>
                      <h4>{shot.section}</h4>
                      <p className="shot-focus">{shot.focus}</p>
                      {shot.lyric_cue ? <p className="cue-line">Cue: {shot.lyric_cue}</p> : null}
                      <div className="token-list">
                        {shot.source_hits.map((hit) => (
                          <span className="token muted" key={hit.chunk_id}>
                            {hit.source_label}
                          </span>
                        ))}
                      </div>
                      <pre>{shot.prompt}</pre>
                    </article>
                  ))}
                </div>
              </section>

              <section className="section-block">
                <div className="section-header">
                  <h3>Adapter dataset</h3>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() => handleCopy('adapter', plan.adapter_dataset_jsonl)}
                  >
                    {copiedLabel === 'adapter' ? 'Copied' : 'Copy JSONL'}
                  </button>
                </div>
                <div className="artifact-grid">
                  <article className="artifact-card">
                    <p className="mini-label">LoRA attention map</p>
                    <pre>{JSON.stringify(plan.lora_attention_map, null, 2)}</pre>
                  </article>
                  <article className="artifact-card">
                    <p className="mini-label">Sample adapter example</p>
                    <pre>
                      {JSON.stringify(plan.adapter_examples[0] ?? {}, null, 2)}
                    </pre>
                  </article>
                </div>
              </section>
            </>
          )}
        </section>
      </section>
    </main>
  )
}
