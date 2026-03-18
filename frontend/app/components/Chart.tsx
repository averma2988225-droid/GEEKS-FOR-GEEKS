'use client'

import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface ChartProps {
  data: any[]
  columns: string[]
  chartType: string
}

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

export default function Chart({ data, columns, chartType }: ChartProps) {
  if (!data || data.length === 0) {
    return <div>No data to display</div>
  }

  // For KPI - show the metric value (last column)
  if (chartType === 'kpi') {
    const metricCol = columns.length > 1 ? columns[columns.length - 1] : columns[0]
    const labelCol = columns.length > 1 ? columns[0] : null
    const value = data[0][metricCol]
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <div style={{ fontSize: '3rem', fontWeight: 'bold', color: '#2563eb' }}>
          {typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value}
        </div>
        <div style={{ fontSize: '1rem', color: '#666', marginTop: '0.5rem' }}>
          {labelCol && data[0][labelCol] ? `${data[0][labelCol]} — ` : ''}{metricCol}
        </div>
      </div>
    )
  }

  // Determine x and y axes
  const xKey = columns[0]
  const yKey = columns[1] || columns[0]

  // Bar Chart
  if (chartType === 'bar') {
    return (
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey={yKey} fill="#2563eb" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  // Line Chart
  if (chartType === 'line') {
    return (
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey={yKey} stroke="#2563eb" strokeWidth={2} dot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  // Pie Chart
  if (chartType === 'pie') {
    return (
      <ResponsiveContainer width="100%" height={400}>
        <PieChart>
          <Pie
            data={data}
            dataKey={yKey}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            outerRadius={120}
            label
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  // Scatter Chart
  if (chartType === 'scatter') {
    return (
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} name={xKey} type="number" />
          <YAxis dataKey={yKey} name={yKey} type="number" />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} />
          <Legend />
          <Scatter name={`${xKey} vs ${yKey}`} data={data} fill="#2563eb" />
        </ScatterChart>
      </ResponsiveContainer>
    )
  }

  // Histogram (rendered as bar chart with no gaps)
  if (chartType === 'histogram') {
    return (
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={data} barCategoryGap={0} barGap={0}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey={yKey} fill="#8b5cf6" />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  // Fallback — render as bar chart
  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={xKey} />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey={yKey} fill="#2563eb" />
      </BarChart>
    </ResponsiveContainer>
  )
}
