"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Bar, BarChart, Cell, XAxis, YAxis, ResponsiveContainer, ReferenceLine, LabelList } from "recharts"
import { Flame, TrendingDown, TrendingUp, Wallet, RefreshCw, Database } from "lucide-react"

interface AnalyticsData {
  months: string[]
  categories: string[]
  averages: Record<string, number>
  monthly_data: Array<Record<string, string | number>>
  totals_per_month: Array<{ month: string, total: number }>
  total_spend_12m: number | null
  total_spend_prev_12m: number | null
  yoy_difference: number | null
  yoy_percentage: number | null
  budgets: Record<string, number>
}

interface CachedData {
  data: AnalyticsData
  timestamp: number
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const CACHE_KEY = "fire_ai_analytics"
const BUDGET_CACHE_KEY = "fire_ai_budgets"
const CACHE_EXPIRY_DAYS = 7

// Get budgets from localStorage
function getCachedBudgets(): Record<string, number> | null {
  if (typeof window === "undefined") return null
  try {
    const cached = localStorage.getItem(BUDGET_CACHE_KEY)
    if (!cached) return null
    const { budgets } = JSON.parse(cached)
    return budgets
  } catch {
    return null
  }
}

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

  // Helper to determine budget status color
  const getBudgetColor = (amount: number, budget: number | undefined) => {
    if (!budget || budget === 0) return "url(#colorGradient)" // Default orange gradient
    const ratio = amount / budget
    if (ratio <= 1) return "url(#greenGradient)"      // Under budget - green
    if (ratio <= 1.2) return "url(#orangeGradient)"   // Up to 20% over - orange
    return "url(#redGradient)"                         // More than 20% over - red
  }

  // Get budgets: localStorage first, then API data fallback
  const budgets = getCachedBudgets() || data?.budgets || {}

  // Prepare chart data from averages with budget info - top 12 by spend
  const chartData = data?.averages
    ? Object.entries(data.averages)
      .map(([category, amount]) => {
        const budget = budgets[category] || 0
        const remaining = budget > 0 ? budget - Number(amount) : 0
        const overBudget = budget > 0 && Number(amount) > budget
        // Create label for budget delta
        let deltaLabel = ""
        if (budget > 0) {
          deltaLabel = overBudget
            ? `+£${Math.abs(remaining).toFixed(0)}`
            : `-£${remaining.toFixed(0)}`
        }
        return {
          category: category.length > 12 ? category.substring(0, 12) + "…" : category,
          fullCategory: category,
          amount: Number(amount),
          budget: budget,
          remaining: remaining,
          deltaLabel: deltaLabel,
          overBudget: overBudget,
          fill: getBudgetColor(Number(amount), budget),
        }
      })
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 12)
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
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* Total Spend Card */}
            <Card className="bg-gradient-to-br from-purple-500/10 to-violet-600/10 border-purple-500/20">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Total Spend (12m)</CardTitle>
                <Wallet className="h-4 w-4 text-purple-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  £{data.total_spend_12m?.toLocaleString() || "N/A"}
                </div>
                {data.yoy_difference != null && data.yoy_percentage != null ? (
                  <p className={`text-xs font-medium flex items-center gap-1 ${data.yoy_difference <= 0 ? "text-emerald-500" : "text-red-500"}`}>
                    {data.yoy_difference <= 0 ? (
                      <TrendingDown className="h-3 w-3" />
                    ) : (
                      <TrendingUp className="h-3 w-3" />
                    )}
                    YoY {data.yoy_difference >= 0 ? "+" : ""}£{Math.abs(data.yoy_difference).toLocaleString()} ({data.yoy_percentage >= 0 ? "+" : ""}{data.yoy_percentage}%)
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground">YoY: N/A (need 24m data)</p>
                )}
              </CardContent>
            </Card>

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
          </div>

          {/* Budget vs Spend Grid */}
          <Card>
            <CardHeader>
              <CardTitle>Budget vs Spend</CardTitle>
              <CardDescription>
                Monthly average over the last {monthsCount} months • Top 12 categories by spend
              </CardDescription>
            </CardHeader>
            <CardContent>
              {chartData.length === 0 ? (
                <div className="flex h-[200px] flex-col items-center justify-center gap-4">
                  <p className="text-muted-foreground">No category data available</p>
                </div>
              ) : (
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                  {chartData.map((item) => {
                    const percentage = item.budget > 0
                      ? (item.amount / item.budget) * 100
                      : 0
                    const isOverBudget = item.overBudget

                    // Thresholds: green <100%, peach 100-130%, pink >130%
                    // Pastel colors with dark text for contrast
                    const getBadgeStyle = () => {
                      if (item.budget === 0) return { bg: '#94a3b8', text: '#1e293b' } // slate
                      if (percentage > 130) return { bg: '#FFADAD', text: '#7f1d1d' } // pastel pink
                      if (percentage >= 100) return { bg: '#FFD6A5', text: '#78350f' } // pastel peach  
                      return { bg: '#CAFFBF', text: '#14532d' } // pastel green
                    }
                    const badgeStyle = getBadgeStyle()

                    // For split bar calculation
                    const greenWidth = isOverBudget
                      ? (item.budget / item.amount) * 100  // Budget portion when over
                      : percentage  // Normal percentage when under
                    const redWidth = isOverBudget
                      ? 100 - greenWidth  // Excess portion
                      : 0

                    return (
                      <div
                        key={item.fullCategory}
                        className="rounded-lg border bg-card p-4 space-y-3"
                      >
                        {/* Header: Category + Status */}
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-sm truncate" title={item.fullCategory}>
                            {item.fullCategory}
                          </span>
                          {item.budget > 0 && (
                            <span
                              className="text-xs font-semibold px-2 py-0.5 rounded-full"
                              style={{ backgroundColor: badgeStyle.bg, color: badgeStyle.text }}
                            >
                              {isOverBudget
                                ? `+£${Math.abs(item.remaining).toFixed(0)}`
                                : `£${item.remaining.toFixed(0)} left`}
                            </span>
                          )}
                        </div>

                        {/* Amounts */}
                        <div className="flex items-baseline justify-between text-sm">
                          <span className="text-2xl font-bold">£{item.amount.toFixed(0)}</span>
                          {item.budget > 0 && (
                            <span className="text-muted-foreground">
                              of £{item.budget.toFixed(0)}
                            </span>
                          )}
                        </div>

                        {/* Progress bar - split for over budget */}
                        {item.budget > 0 ? (
                          <div className="h-2 w-full rounded-full bg-muted overflow-hidden flex">
                            {isOverBudget ? (
                              <>
                                {/* Green portion = budget */}
                                <div
                                  className="h-full transition-all"
                                  style={{ width: `${greenWidth}%`, backgroundColor: '#CAFFBF' }}
                                />
                                {/* Pink portion = excess */}
                                <div
                                  className="h-full transition-all rounded-r-full"
                                  style={{ width: `${redWidth}%`, backgroundColor: '#FFADAD' }}
                                />
                              </>
                            ) : (
                              /* Under budget - single colored bar */
                              <div
                                className="h-full rounded-full transition-all"
                                style={{ width: `${Math.min(percentage, 100)}%`, backgroundColor: badgeStyle.bg }}
                              />
                            )}
                          </div>
                        ) : (
                          <div className="h-2 w-full rounded-full bg-muted">
                            <div className="h-full rounded-full bg-gray-400 w-0" />
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
