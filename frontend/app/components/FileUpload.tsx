'use client'

import { useState } from 'react'

interface FileUploadProps {
  onUploadSuccess: (datasetId: string, filename: string, preview: any[]) => void
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleFile = async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setError('Only CSV files are allowed')
      return
    }

    setUploading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(errorData.detail || `Upload failed: ${res.status}`)
      }

      const data = await res.json()
      onUploadSuccess(data.dataset_id, data.filename, data.preview)
      setError(null)
    } catch (err: any) {
      console.error('Upload failed:', err)
      setError(err.message || 'Failed to upload file. Make sure the backend server is running.')
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)

    const file = e.dataTransfer.files[0]
    if (file) {
      handleFile(file)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFile(file)
    }
  }

  return (
    <div>
      <div
        className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".csv"
          onChange={handleChange}
          disabled={uploading}
          style={{ display: 'none' }}
          id="file-input"
        />
        <label htmlFor="file-input" style={{ cursor: 'pointer' }}>
          {uploading ? (
            <p>Uploading...</p>
          ) : (
            <>
              <p>📁 Drag & drop CSV file here</p>
              <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '0.5rem' }}>
                or click to browse
              </p>
            </>
          )}
        </label>
      </div>

      {error && (
        <div style={{ color: '#c00', marginTop: '0.5rem', fontSize: '0.9rem' }}>
          {error}
        </div>
      )}
    </div>
  )
}
