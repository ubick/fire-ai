"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Checkbox } from "@/components/ui/checkbox"
import { Upload, Eye, Loader2, CheckCircle2, AlertCircle } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// Generate months from Jan 2024 to current month
function generateMonthOptions() {
    const months = []
    const now = new Date()
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth() + 1

    for (let year = 2024; year <= currentYear; year++) {
        const endMonth = year === currentYear ? currentMonth : 12
        const startMonth = year === 2024 ? 1 : 1

        for (let month = startMonth; month <= endMonth; month++) {
            months.push({ year, month })
        }
    }

    return months.reverse() // Most recent first
}

interface ProcessResult {
    success: boolean
    message: string
    mode: string
    transactions_count?: number
    data: Array<Record<string, number | string>>
}

export default function ImportPage() {
    const [csvFiles, setCsvFiles] = useState<string[]>([])
    const [defaultCsv, setDefaultCsv] = useState<string>("")
    const [selectedCsv, setSelectedCsv] = useState<string>("")
    const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear())
    const [selectedMonth, setSelectedMonth] = useState<number>(-1) // -1 = Auto
    const [override, setOverride] = useState<boolean>(false)
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<ProcessResult | null>(null)
    const [error, setError] = useState<string | null>(null)

    const monthOptions = generateMonthOptions()

    useEffect(() => {
        async function fetchCsvFiles() {
            try {
                const res = await fetch(`${API_URL}/api/csv-files`)
                if (!res.ok) throw new Error("Failed to fetch CSV files")
                const data = await res.json()
                setCsvFiles(data.files || [])
                setDefaultCsv(data.default || "")
                setSelectedCsv(data.default || "")
            } catch (err) {
                console.error("Error fetching CSV files:", err)
            }
        }
        fetchCsvFiles()
    }, [])

    const handleProcess = async (mode: "shadow" | "live") => {
        setLoading(true)
        setError(null)
        setResult(null)

        try {
            const payload = {
                csv_file: selectedCsv,
                mode: mode,
                override: override,
                ...(selectedMonth === -1
                    ? { auto_date: true }
                    : { year: selectedYear, month: selectedMonth, auto_date: false }
                )
            }

            const res = await fetch(`${API_URL}/api/process`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            })

            const data = await res.json()

            if (!res.ok) {
                throw new Error(data.detail || "Processing failed")
            }

            setResult(data)
        } catch (err) {
            setError(err instanceof Error ? err.message : "An error occurred")
        } finally {
            setLoading(false)
        }
    }

    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    // Get all columns from result data for the table
    const tableColumns = result?.data?.[0]
        ? Object.keys(result.data[0]).filter(k => k !== "Month")
        : []

    // Priority columns for display
    const priorityColumns = ["Totals", "Necessary", "Discretionary", "Excess"]
    const categoryColumns = tableColumns.filter(c => !priorityColumns.includes(c))

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Import Transactions</h1>
                <p className="text-muted-foreground">
                    Process your transaction data and update Google Sheets
                </p>
            </div>

            {/* Controls Card */}
            <Card>
                <CardHeader>
                    <CardTitle>Import Settings</CardTitle>
                    <CardDescription>
                        Select your CSV file and target month, then choose to preview or import
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Form Layout: Stacked vertically with better spacing */}
                    <div className="flex flex-col gap-6 max-w-xl">
                        {/* CSV File Selector */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                <Upload className="h-4 w-4" /> CSV File
                            </label>
                            <Select value={selectedCsv} onValueChange={setSelectedCsv}>
                                <SelectTrigger className="w-full h-11">
                                    <SelectValue placeholder="Select CSV file" />
                                </SelectTrigger>
                                <SelectContent>
                                    {csvFiles.map((file) => (
                                        <SelectItem key={file} value={file}>
                                            <span className="truncate block max-w-[300px]" title={file}>
                                                {file} {file === defaultCsv && "(newest)"}
                                            </span>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Month Selector */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                <Loader2 className="h-4 w-4" /> Target Month
                            </label>
                            <Select
                                value={selectedMonth === -1 ? "auto" : `${selectedYear}-${selectedMonth}`}
                                onValueChange={(val) => {
                                    if (val === "auto") {
                                        setSelectedMonth(-1)
                                    } else {
                                        const [year, month] = val.split("-").map(Number)
                                        setSelectedYear(year)
                                        setSelectedMonth(month)
                                    }
                                }}
                            >
                                <SelectTrigger className="h-11">
                                    <SelectValue placeholder="Select month" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="auto">
                                        <span className="font-medium">Auto (Next Logical Month)</span>
                                    </SelectItem>
                                    {monthOptions.map(({ year, month }) => (
                                        <SelectItem key={`${year}-${month}`} value={`${year}-${month}`}>
                                            {monthNames[month - 1]} {year}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Override Checkbox */}
                        <div className="flex items-center space-x-3 p-4 rounded-lg bg-secondary/30 border border-border/50 transition-colors hover:bg-secondary/50">
                            <Checkbox
                                id="override"
                                checked={override}
                                onCheckedChange={(checked) => setOverride(checked as boolean)}
                                className="h-5 w-5"
                            />
                            <div className="grid gap-1 leading-none cursor-pointer select-none" onClick={() => setOverride(!override)}>
                                <label
                                    htmlFor="override"
                                    className="text-sm font-semibold leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                >
                                    Override existing data
                                </label>
                                <p className="text-xs text-muted-foreground">
                                    Check this to overwrite data for the selected month
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-col sm:flex-row gap-4 pt-4">
                        <Button
                            variant="outline"
                            size="lg"
                            onClick={() => handleProcess("shadow")}
                            disabled={loading || !selectedCsv}
                            className="flex-1 h-12 gap-2 text-base font-medium transition-all"
                        >
                            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Eye className="h-5 w-5" />}
                            Shadow Mode (Preview)
                        </Button>

                        <Button
                            size="lg"
                            onClick={() => handleProcess("live")}
                            disabled={loading || !selectedCsv}
                            className="flex-1 h-12 gap-2 text-base font-medium bg-orange-500/15 text-orange-500 border border-orange-500/20 hover:bg-orange-500/25 shadow-lg shadow-orange-500/5 transition-all"
                        >
                            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
                            Live Import
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Error Display */}
            {error && (
                <Card className="border-destructive">
                    <CardContent className="flex items-center gap-3 pt-6">
                        <AlertCircle className="h-5 w-5 text-destructive" />
                        <p className="text-destructive">{error}</p>
                    </CardContent>
                </Card>
            )}

            {/* Result Display */}
            {result && (
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <CheckCircle2 className={`h-5 w-5 ${result.mode === "live" ? "text-green-500" : "text-blue-500"}`} />
                            <div>
                                <CardTitle className="text-lg">{result.message}</CardTitle>
                                <CardDescription>
                                    {result.transactions_count} transactions processed in {result.mode} mode
                                </CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="rounded-md border overflow-x-auto">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="sticky left-0 bg-background">Month</TableHead>
                                        {priorityColumns.map((col) => (
                                            <TableHead key={col} className="text-right font-bold">{col}</TableHead>
                                        ))}
                                        {categoryColumns.map((col) => (
                                            <TableHead key={col} className="text-right">{col}</TableHead>
                                        ))}
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {result.data.map((row, idx) => (
                                        <TableRow key={idx}>
                                            <TableCell className="sticky left-0 bg-background font-medium">
                                                {row.Month}
                                            </TableCell>
                                            {priorityColumns.map((col) => (
                                                <TableCell key={col} className="text-right font-bold">
                                                    £{Number(row[col] || 0).toFixed(2)}
                                                </TableCell>
                                            ))}
                                            {categoryColumns.map((col) => (
                                                <TableCell key={col} className="text-right">
                                                    £{Number(row[col] || 0).toFixed(2)}
                                                </TableCell>
                                            ))}
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
