const API_BASE =
  import.meta.env.VITE_RUNTIME_API_BASE_URL ??
  import.meta.env.VITE_API_BASE_URL ??
  'http://localhost:8010'

export interface RegisterClientResponse {
  tenant_id: string
  client_key: string
}

export interface ScenarioEnvelope {
  tenant_id: string
  execution_id: string
  embedding_dim: number
  hash_current: string
  runtime_state: Record<string, unknown>
  scenario_trace: Array<Record<string, unknown>>
}

export interface RagContextEnvelope {
  retrieval_context: {
    chunks: Array<Record<string, unknown>>
  }
}

export interface LoraDatasetResponse {
  execution_id: string
  tenant_id: string
  dataset_commit: string
  drift: {
    passed: boolean
    reason: string
    pvalue: number
  }
  lora_dataset: Array<Record<string, unknown>>
}

export interface VerificationResponse {
  valid: boolean
  execution_id: string
  tenant_id: string
  event_count: number
  hash_head: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Runtime request failed with ${response.status}`)
  }

  return response.json() as Promise<T>
}

export async function registerRuntimeClient(
  apiKey = 'simulator-route',
): Promise<RegisterClientResponse> {
  const query = new URLSearchParams({
    api_key: apiKey,
    quota: '1000000',
  })

  return request<RegisterClientResponse>(`/mcp/register?${query.toString()}`, {
    method: 'POST',
  })
}

export async function setRuntimeBaseline(
  clientKey: string,
  tokens: number[],
): Promise<{ status: string; client_id: string }> {
  return request<{ status: string; client_id: string }>(`/mcp/${clientKey}/baseline`, {
    method: 'POST',
    body: JSON.stringify({ tokens }),
  })
}

export async function createRuntimeScenario(
  clientKey: string,
  payload: {
    tokens: number[]
    runtime_hints: Record<string, unknown>
  },
): Promise<ScenarioEnvelope> {
  return request<ScenarioEnvelope>(`/a2a/runtime/${clientKey}/scenario`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function createRuntimeRagContext(
  executionId: string,
  topK = 3,
): Promise<RagContextEnvelope> {
  return request<RagContextEnvelope>(`/a2a/scenario/${executionId}/rag-context`, {
    method: 'POST',
    body: JSON.stringify({ top_k: topK }),
  })
}

export async function createRuntimeLoraDataset(
  executionId: string,
  tokens: number[],
): Promise<LoraDatasetResponse> {
  return request<LoraDatasetResponse>(`/a2a/scenario/${executionId}/lora-dataset`, {
    method: 'POST',
    body: JSON.stringify({
      pvalue_threshold: 0.1,
      candidate_tokens: tokens,
    }),
  })
}

export async function verifyRuntimeExecution(
  executionId: string,
): Promise<VerificationResponse> {
  return request<VerificationResponse>(`/a2a/executions/${executionId}/verify`)
}
