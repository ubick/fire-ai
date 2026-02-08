"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Bar, BarChart, XAxis, YAxis, ResponsiveContainer } from "recharts"
import { Flame, TrendingDown, TrendingUp, Wallet, RefreshCw, Database } from "lucide-react"

interface AnalyticsData {
  months: string[]
  categories: string[]
  averages: Record<string, number>
  monthly_data: Array<Record<string, string | number>>
}

interface CachedData {
  data: AnalyticsData
  timestamp: number
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const CACHE_KEY = "fire_ai_analytics"
const CACHE_EXPIRY_DAYS = 7

function getCachedData(): AnalyticsData | null {
  if (typeof window === "undefined") return null

  try {
    const cached = localStorage.getItem(CACHE_KEY)
    if (!cached) return null

    const { data, timestamp }: CachedData = JSON.parse(cached)
    const now = Date.now()
    const expiryMs = CACHE_EXPIRY_DAYS * 24 * 60 * 60 * 1000

    if (now - timestamp > expiryMs) {
      localStorage.removeItem(CACHE_KEY)
      return null
    }

    return data
  } catch {
    return null
  }
}

function setCachedData(data: AnalyticsData): void {
  if (typeof window === "undefined") return

  const cached: CachedData = {
    data,
    timestamp: Date.now()
  }
  localStorage.setItem(CACHE_KEY, JSON.stringify(cached))
}

function getCacheAge(): string | null {
  if (typeof window === "undefined") return null

  try {
    const cached = localStorage.getItem(CACHE_KEY)
    if (!cached) return null

    const { timestamp }: CachedData = JSON.parse(cached)
    const ageMs = Date.now() - timestamp
    const ageHours = Math.floor(ageMs / (1000 * 60 * 60))
    const ageDays = Math.floor(ageHours / 24)

    if (ageDays > 0) return `${ageDays}d ago`
    if (ageHours > 0) return `${ageHours}h ago`
    return "just now"
  } catch {
    return null
  }
}

export default function Dashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cacheAge, setCacheAge] = useState<string | null>(null)
  const [initialized, setInitialized] = useState(false)

  // Load from cache on mount
  useEffect(() => {
    const cached = getCachedData()
    if (cached) {
      setData(cached)
      setCacheAge(getCacheAge())
    }
    setInitialized(true)
  }, [])

  const fetchFromSheets = async () => {
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_URL}/api/analytics`)
      if (!res.ok) {
        throw new Error(`Failed to fetch analytics: ${res.status}`)
      }
      const json = await res.json()
      setData(json)
      setCachedData(json)
      setCacheAge("just now")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics")
    } finally {
      setLoading(false)
    }
  }

  // Prepare chart data from averages
  const chartData = data?.averages
    ? Object.entries(data.averages)
      .map(([category, amount]) => ({
        category: category.length > 12 ? category.substring(0, 12) + "…" : category,
        fullCategory: category,
        amount: Number(amount),
      }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 10)
    : []

  const chartConfig: ChartConfig = {
    amount: {
      label: "Average Spend",
      color: "hsl(var(--chart-1))",
    },
  }

  const totalMonthlyAvg = data?.averages
    ? Object.values(data.averages).reduce((sum, val) => sum + Number(val), 0)
    : 0

  const monthsCount = data?.months?.length || 0

  // Show loading state only before initialization
  if (!initialized) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-red-600 shadow-lg shadow-orange-500/25">
              <Flame className="h-7 w-7 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Welcome to FIRE AI</h1>
              <p className="text-muted-foreground">
                Your financial independence journey starts here
              </p>
            </div>
          </div>

          {/* Refresh Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={fetchFromSheets}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Fetching..." : "Refresh from Sheets"}
          </Button>
        </div>

        {/* Cache status */}
        {cacheAge && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Database className="h-3 w-3" />
            <span>Using cached data from {cacheAge} (expires in 7 days)</span>
          </div>
        )}
      </div>

      {/* No Data State - Prompt to fetch */}
      {!data && !loading && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <Database className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold">No cached data available</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Would you like to fetch your financial data from Google Sheets?
              </p>
            </div>
            <Button
              onClick={fetchFromSheets}
              className="gap-2 bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700"
            >
              <RefreshCw className="h-4 w-4" />
              Fetch from Google Sheets
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex flex-col items-center justify-center py-8 gap-4">
            <p className="text-destructive">{error}</p>
            <p className="text-sm text-muted-foreground">
              Make sure the API server is running at {API_URL}
            </p>
            <Button variant="outline" onClick={fetchFromSheets} disabled={loading}>
              Try Again
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Stats Cards - Only show when we have data */}
      {data && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="bg-gradient-to-br from-orange-500/10 to-red-600/10 border-orange-500/20">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Avg Monthly Spend</CardTitle>
                <Wallet className="h-4 w-4 text-orange-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">£{totalMonthlyAvg.toFixed(0)}</div>
                <p className="text-xs text-muted-foreground">
                  Based on {monthsCount} months of data
                </p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-green-500/10 to-emerald-600/10 border-green-500/20">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Data Period</CardTitle>
                <TrendingUp className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{monthsCount} months</div>
                <p className="text-xs text-muted-foreground">
                  {data?.months?.[0]} - {data?.months?.[data.months.length - 1]}
                </p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-blue-500/10 to-indigo-600/10 border-blue-500/20">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Categories Tracked</CardTitle>
                <TrendingDown className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data?.categories?.length || 0}</div>
                <p className="text-xs text-muted-foreground">Expense categories</p>
              </CardContent>
            </Card>
          </div>

          {/* Main Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Average Spend by Category</CardTitle>
              <CardDescription>
                Monthly average over the last {monthsCount} months
              </CardDescription>
            </CardHeader>
            <CardContent>
              {chartData.length === 0 ? (
                <div className="flex h-[400px] flex-col items-center justify-center gap-4">
                  <p className="text-muted-foreground">No category data available</p>
                </div>
              ) : (
                <ChartContainer config={chartConfig} className="h-[400px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
                      <XAxis type="number" tickFormatter={(value) => `£${value}`} />
                      <YAxis
                        dataKey="category"
                        type="category"
                        width={100}
                        tick={{ fontSize: 12 }}
                      />
                      <ChartTooltip
                        content={
                          <ChartTooltipContent
                            formatter={(value, name, props) => [
                              `£${Number(value).toFixed(2)}`,
                              props.payload.fullCategory
                            ]}
                          />
                        }
                      />
                      <Bar
                        dataKey="amount"
                        fill="url(#colorGradient)"
                        radius={[0, 4, 4, 0]}
                      />
                      <defs>
                        <linearGradient id="colorGradient" x1="0" y1="0" x2="1" y2="0">
                          <stop offset="0%" stopColor="hsl(25, 95%, 53%)" />
                          <stop offset="100%" stopColor="hsl(0, 84%, 60%)" />
                        </linearGradient>
                      </defs>
                    </BarChart>
                  </ResponsiveContainer>
                </ChartContainer>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
