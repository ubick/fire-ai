"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PiggyBank, Save, RefreshCw, Database } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const BUDGET_CACHE_KEY = "fire_ai_budgets"
const CACHE_EXPIRY_DAYS = 7

interface CachedBudgets {
    budgets: Record<string, number>
    timestamp: number
}

// LocalStorage helpers
function getCachedBudgets(): Record<string, number> | null {
    if (typeof window === "undefined") return null
    try {
        const cached = localStorage.getItem(BUDGET_CACHE_KEY)
        if (!cached) return null
        const { budgets, timestamp }: CachedBudgets = JSON.parse(cached)
        return budgets
    } catch {
        return null
    }
}

function saveBudgetsToCache(budgets: Record<string, number>): void {
    if (typeof window === "undefined") return
    const cacheData: CachedBudgets = {
        budgets,
        timestamp: Date.now(),
    }
    localStorage.setItem(BUDGET_CACHE_KEY, JSON.stringify(cacheData))
}

function getCacheAge(): string | null {
    if (typeof window === "undefined") return null
    try {
        const cached = localStorage.getItem(BUDGET_CACHE_KEY)
        if (!cached) return null
        const { timestamp }: CachedBudgets = JSON.parse(cached)
        const ageMs = Date.now() - timestamp
        const ageHours = Math.floor(ageMs / (1000 * 60 * 60))
        const ageDays = Math.floor(ageHours / 24)
        if (ageDays > 0) return `${ageDays} day${ageDays > 1 ? "s" : ""} ago`
        if (ageHours > 0) return `${ageHours} hour${ageHours > 1 ? "s" : ""} ago`
        return "just now"
    } catch {
        return null
    }
}

export default function BudgetPage() {
    const [budgets, setBudgets] = useState<Record<string, number>>({})
    const [cacheAge, setCacheAge] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<string | null>(null)
    const [hasChanges, setHasChanges] = useState(false)

    // Load budgets from localStorage first, then fetch from API if needed
    const loadBudgets = () => {
        const cached = getCachedBudgets()
        if (cached) {
            setBudgets(cached)
            setCacheAge(getCacheAge())
        }
    }

    // Fetch budgets from Google Sheet via API
    const refreshFromSheet = async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`${API_URL}/api/budgets/refresh`, { method: "POST" })
            if (!res.ok) throw new Error(`Failed to refresh budgets: ${res.status}`)
            const data = await res.json()
            setBudgets(data.budgets)
            saveBudgetsToCache(data.budgets)
            setCacheAge("just now")
            setHasChanges(false)
            setSuccess("Budgets refreshed from Google Sheet")
            setTimeout(() => setSuccess(null), 3000)
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to refresh budgets")
        } finally {
            setLoading(false)
        }
    }

    // Save budgets to localStorage
    const saveBudgets = () => {
        setSaving(true)
        try {
            saveBudgetsToCache(budgets)
            setCacheAge("just now")
            setHasChanges(false)
            setSuccess("Budgets saved to local storage")
            setTimeout(() => setSuccess(null), 3000)
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to save budgets")
        } finally {
            setSaving(false)
        }
    }

    const handleBudgetChange = (category: string, value: string) => {
        const numValue = parseFloat(value) || 0
        setBudgets((prev) => ({ ...prev, [category]: numValue }))
        setHasChanges(true)
    }

    useEffect(() => {
        loadBudgets()
        // If no cached budgets, fetch from sheet
        const cached = getCachedBudgets()
        if (!cached) {
            refreshFromSheet()
        }
    }, [])

    // Categories to exclude from display (temporary sums and totals)
    const EXCLUDED_CATEGORIES = [
        "Excess Total",
        "Necessary Total",
        "Discret Total",
        "Totals",
        "Mortgage overpayment",
        "Mortgage Direct Debit",
        "Mortgage principal",
        "Mortgage interest",
    ]

    // Filter out excluded categories and zero budgets, then sort by value descending
    const categories = Object.entries(budgets)
        .filter(([category, value]) =>
            !EXCLUDED_CATEGORIES.includes(category) && value > 0
        )
        .sort((a, b) => b[1] - a[1])
        .map(([category]) => category)

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="space-y-2">
                <div className="flex items-center justify-between flex-wrap gap-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/25">
                            <PiggyBank className="h-7 w-7 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold tracking-tight">Budget Manager</h1>
                            <p className="text-muted-foreground">
                                Set monthly budgets for each category
                            </p>
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            onClick={refreshFromSheet}
                            disabled={loading}
                        >
                            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                            Refresh from Sheet
                        </Button>
                        <Button
                            onClick={saveBudgets}
                            disabled={saving || !hasChanges}
                        >
                            <Save className="h-4 w-4 mr-2" />
                            {saving ? "Saving..." : "Save Changes"}
                        </Button>
                    </div>
                </div>

                {/* Cache status */}
                {cacheAge && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Database className="h-4 w-4" />
                        <span>Local data from {cacheAge}</span>
                    </div>
                )}

                {/* Error/Success messages */}
                {error && (
                    <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-4 py-2 rounded-lg">
                        {error}
                    </div>
                )}
                {success && (
                    <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 px-4 py-2 rounded-lg">
                        {success}
                    </div>
                )}
            </div>

            {/* Budget Cards */}
            <Card>
                <CardHeader>
                    <CardTitle>Monthly Budgets</CardTitle>
                    <CardDescription>
                        Edit the budget amounts for each expense category. Changes are saved locally.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading && Object.keys(budgets).length === 0 ? (
                        <div className="flex items-center justify-center py-8">
                            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                    ) : categories.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                            No budgets found. Click &quot;Refresh from Sheet&quot; to load budgets.
                        </div>
                    ) : (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {categories.map((category) => (
                                <div
                                    key={category}
                                    className="flex items-center gap-3 p-3 rounded-lg border bg-card"
                                >
                                    <div className="flex-1 min-w-0">
                                        <label
                                            htmlFor={`budget-${category}`}
                                            className="text-sm font-medium truncate block"
                                            title={category}
                                        >
                                            {category}
                                        </label>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <span className="text-muted-foreground">£</span>
                                        <Input
                                            id={`budget-${category}`}
                                            type="number"
                                            min="0"
                                            step="10"
                                            value={budgets[category] || 0}
                                            onChange={(e) => handleBudgetChange(category, e.target.value)}
                                            className="w-24 text-right"
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
