'use client'

import { useState } from 'react'
import Chart from './components/Chart'
import DataTable from './components/DataTable'
import FileUpload from './components/FileUpload'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_URL = `${API_BASE}/api/query`

interface QueryResponse {
  sql: string | null
  data: any[]
  columns: string[]
  chart_type: string
  error: string | null
  execution_time: number
  suggested_columns?: string[]
  needs_clarification?: boolean
  clarification?: string
  conversation_id: string
  context_used?: boolean
  insight?: string
}

interface ChatMessage {
  query: string
  response: QueryResponse
  timestamp: number
}

export default function Home() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<QueryResponse | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
  
  // CSV upload state
  const [datasetId, setDatasetId] = useState<string | null>(null)
  const [datasetFilename, setDatasetFilename] = useState<string | null>(null)
  const [datasetPreview, setDatasetPreview] = useState<any[] | null>(null)

  const handleUploadSuccess = (id: string, filename: string, preview: any[]) => {
    setDatasetId(id)
    setDatasetFilename(filename)
    setDatasetPreview(preview)
    setResponse(null) // Clear previous results
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!query.trim()) return

    setLoading(true)
    const currentQuery = query
    setQuery('') // Clear input immediately

    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query: currentQuery,
          dataset_id: datasetId || null,
          conversation_id: conversationId || null
        }),
      })

      if (!res.ok) {
        throw new Error(`Backend error: ${res.status} ${res.statusText}`)
      }

      const data = await res.json()
      setResponse(data)
      setConversationId(data.conversation_id)
      
      // Add to chat history
      setChatHistory(prev => [...prev, {
        query: currentQuery,
        response: data,
        timestamp: Date.now()
      }])
    } catch (error: any) {
      console.error('Query failed:', error)
      const errorResponse = {
        sql: null,
        data: [],
        columns: [],
        chart_type: 'kpi',
        error: error.message || 'Failed to connect to backend. Make sure the backend server is running on http://localhost:8000',
        execution_time: 0,
        conversation_id: conversationId || '',
      }
      setResponse(errorResponse)
      setChatHistory(prev => [...prev, {
        query: currentQuery,
        response: errorResponse,
        timestamp: Date.now()
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="header">
        <h1>QueryViz</h1>
        <p>Ask questions in natural language, get SQL and visualizations</p>
      </div>

      {/* CSV Upload Section */}
      {!datasetId ? (
        <div className="query-form">
          <h3 style={{ marginBottom: '1rem' }}>Upload Your Data (Optional)</h3>
          <FileUpload onUploadSuccess={handleUploadSuccess} />
          <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
            Or use the default consumer dataset below
          </p>
        </div>
      ) : (
        <div className="dataset-info">
          <strong>📊 Active Dataset:</strong> {datasetFilename}
          <button 
            className="switch-dataset" 
            onClick={() => {
              setDatasetId(null)
              setDatasetFilename(null)
              setDatasetPreview(null)
              setResponse(null)
            }}
          >
            Switch to default dataset
          </button>
          
          {datasetPreview && datasetPreview.length > 0 && (
            <div className="preview-table">
              <p style={{ marginTop: '0.5rem', marginBottom: '0.5rem' }}>
                <strong>Preview (first 5 rows):</strong>
              </p>
              <DataTable 
                data={datasetPreview} 
                columns={Object.keys(datasetPreview[0])} 
              />
            </div>
          )}
        </div>
      )}

      {/* Query Form */}
      <form onSubmit={handleSubmit} className="query-form">
        <div className="input-group">
          <input
            type="text"
            className="query-input"
            placeholder={conversationId ? "e.g., now only for females" : "e.g., What is the average age by gender?"}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? 'Processing...' : 'Submit'}
          </button>
        </div>
        {conversationId && (
          <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
            💬 Conversation active - You can refine your previous query
            <button
              type="button"
              onClick={() => {
                setConversationId(null)
                setChatHistory([])
                setResponse(null)
              }}
              style={{ marginLeft: '1rem', color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
            >
              Start new conversation
            </button>
          </div>
        )}
      </form>

      {loading && (
        <div className="loading">
          <p>Generating SQL and fetching results...</p>
        </div>
      )}

      {/* Chat History */}
      {chatHistory.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>Conversation History</h3>
          {chatHistory.map((msg, idx) => (
            <div key={idx} style={{ 
              background: 'white', 
              padding: '1rem', 
              borderRadius: '8px', 
              marginBottom: '1rem',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}>
              <div style={{ fontWeight: 'bold', color: '#2563eb', marginBottom: '0.5rem' }}>
                Q{idx + 1}: {msg.query}
              </div>
              {msg.response.context_used && (
                <div style={{ fontSize: '0.8rem', color: '#10b981', marginBottom: '0.5rem' }}>
                  ✓ Used previous context
                </div>
              )}
              {msg.response.sql && (
                <div style={{ fontSize: '0.85rem', color: '#666', fontFamily: 'monospace' }}>
                  {msg.response.sql}
                </div>
              )}
              {msg.response.error && (
                <div style={{ fontSize: '0.85rem', color: '#c00' }}>
                  Error: {msg.response.error}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {response && (
        <div className="results">
          {/* Clarification needed */}
          {response.needs_clarification && response.clarification && (
            <div style={{ background: '#fff3cd', padding: '1rem', borderRadius: '4px', marginBottom: '1rem' }}>
              <strong>⚠️ Clarification Needed:</strong>
              <p style={{ marginTop: '0.5rem' }}>{response.clarification}</p>
            </div>
          )}

          {/* Error display */}
          {response.error && (
            <div className="error">
              <strong>Error:</strong> {response.error}
              {response.suggested_columns && response.suggested_columns.length > 0 && (
                <div style={{ marginTop: '0.5rem' }}>
                  <strong>Suggested columns:</strong> {response.suggested_columns.join(', ')}
                </div>
              )}
            </div>
          )}

          {/* Success display */}
          {response.sql && (
            <>
              <div className="sql-display">
                <strong>Generated SQL:</strong>
                <pre style={{ marginTop: '0.5rem' }}>{response.sql}</pre>
              </div>

              {response.data.length > 0 && (
                <>
                  <div className="chart-container">
                    <h3 style={{ marginBottom: '1rem' }}>Visualization</h3>
                    <Chart 
                      data={response.data} 
                      columns={response.columns} 
                      chartType={response.chart_type} 
                    />
                    {response.insight && (
                      <div style={{ 
                        marginTop: '1rem', 
                        padding: '0.75rem', 
                        background: '#f0f9ff', 
                        borderLeft: '3px solid #2563eb',
                        fontSize: '0.9rem',
                        color: '#1e40af'
                      }}>
                        💡 {response.insight}
                      </div>
                    )}
                  </div>

                  <div>
                    <h3 style={{ marginBottom: '1rem' }}>Data Table</h3>
                    <DataTable data={response.data} columns={response.columns} />
                  </div>

                  <div className="meta">
                    <span>Chart Type: <strong>{response.chart_type}</strong></span>
                    {' • '}
                    <span>Rows: <strong>{response.data.length}</strong></span>
                    {' • '}
                    <span>Execution Time: <strong>{response.execution_time}ms</strong></span>
                    {response.context_used && (
                      <>
                        {' • '}
                        <span style={{ color: '#10b981' }}>✓ Context Used</span>
                      </>
                    )}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
