interface DataTableProps {
  data: any[]
  columns: string[]
}

export default function DataTable({ data, columns }: DataTableProps) {
  if (!data || data.length === 0) {
    return <div>No data to display</div>
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx}>
              {columns.map((col) => (
                <td key={col}>
                  {typeof row[col] === 'number' 
                    ? row[col].toLocaleString() 
                    : String(row[col] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
