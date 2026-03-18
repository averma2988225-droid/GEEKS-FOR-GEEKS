# QueryViz Frontend

Next.js 14 frontend for QueryViz - Natural Language to SQL visualization platform.

## Tech Stack

- **Next.js 14** (App Router)
- **React 19**
- **TypeScript**
- **Recharts** (for data visualization)

## Folder Structure

```
frontend/
├── app/
│   ├── components/
│   │   ├── Chart.tsx          # Chart rendering (bar, line, pie, kpi)
│   │   └── DataTable.tsx      # Data table display
│   ├── layout.tsx             # Root layout
│   ├── page.tsx               # Main page (query form + results)
│   └── globals.css            # Global styles
├── package.json
├── tsconfig.json
├── next.config.js
└── README.md
```

## Setup

1. Install dependencies:
```bash
npm install
```

## Run Development Server

```bash
npm run dev
```

Frontend will run on: **http://localhost:3000**

## Backend Connection

The frontend connects to the backend API at:
```
http://localhost:8000/api/query
```

Make sure the backend is running before using the frontend.

## Features

- Natural language query input
- Real-time SQL generation
- Multiple chart types:
  - Bar chart
  - Line chart
  - Pie chart
  - KPI (single value display)
- Data table view
- Error handling with column suggestions
- Execution time tracking

## Usage

1. Start the backend server (port 8000)
2. Start the frontend: `npm run dev`
3. Open http://localhost:3000
4. Enter a natural language query (e.g., "What is the average age by gender?")
5. View the generated SQL, chart, and data table

## Build for Production

```bash
npm run build
npm start
```
