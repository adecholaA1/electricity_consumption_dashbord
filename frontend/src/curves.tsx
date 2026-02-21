import * as React from "react"
// import { TrendingUp } from "lucide-react"
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"
import { ModeToggle } from "./components/ui/mode-toggle"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardFooter,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import axios from 'axios'
import type { AxiosResponse } from "axios"
import { useEffect } from "react"

const API_URL = "http://localhost:3001"

const chartConfig = {
  true_value: {
    label: "true value",
    color: "var(--chart-1)",
  },
  rte_forecast: {
    label: "rte forecast",
    color: "var(--chart-2)",
  },
  our_forecast: {
    label: "our forecast",
    color: "var(--chart-3)",
  },
} satisfies ChartConfig

interface ChartDataItems {
  date: string;
  "true value": number ;
  "rte forecast": number;
  "our forecast": number;
}

export function ChartAreaInteractive() {
  const [timeRange, setTimeRange] = React.useState("90d")
  const [filteredData, setFilteredData] = React.useState<ChartDataItems[]>([])
  const [allData, setAllData] = React.useState<ChartDataItems[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    if (allData.length === 0) return
    filterData(allData, timeRange)
  }, [timeRange, allData])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const response: AxiosResponse<ChartDataItems[]> = await axios.get(
        `${API_URL}/api/data?range=${timeRange}`
      )
      setAllData(response.data)
      filterData(response.data, timeRange)
    } catch (err) {
      console.error("Erreur fetch:", err)
      setError("Impossible de récupérer les données. Vérifiez que le backend est lancé.")
    } finally {
      setLoading(false)
    }
  }



  const filterData = (data: ChartDataItems[], range: string) => {
    let daysToSubtract = 90
    if (range === "30d") daysToSubtract = 30
    else if (range === "7d") daysToSubtract = 7
    const now = new Date()
    const startDate = new Date(now)
    startDate.setDate(startDate.getDate() - daysToSubtract)
    setFilteredData(data.filter(item => new Date(item.date) >= startDate))
  }

  /*const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString("fr-FR", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      timeZone: "Europe/Paris",  // Force le timezone
      timeZoneName: "short",
    })
  }*/

  

    const formatTooltipDate = (dateStr: string) => {
        const date = new Date(dateStr)
    
        const formatter = new Intl.DateTimeFormat('fr-FR', {
            timeZone: 'Europe/Paris',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short'
        })
    
    // Remplacer les / par des -
    return formatter.format(date).replace(/\//g, '-')
    }

//   <div style={{display:"flex", flexDirection:"column"}}></div>

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>

      {/* Toggle dark/light */}
      <div style={{ display: "flex", justifyContent: "end", marginBottom: "15px" }}>
        <ModeToggle />
      </div>
      {/* Graphique principal */}
      <Card>
        <CardHeader className="flex items-center gap-2 space-y-0 border-b py-5 sm:flex-col">
          <div className="grid flex-1 gap-1">
            <CardTitle className="text-center">Day-Ahead Load Forecast</CardTitle>
            <CardDescription className="text-center">
              France — Actual Consumption vs RTE Forecasts vs Our Forecasts
            </CardDescription>
          </div>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[160px] rounded-lg sm:ml-auto" aria-label="Select a value">
              <SelectValue placeholder="Last 3 months" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="90d" className="rounded-lg">Last 3 months</SelectItem>
              <SelectItem value="30d" className="rounded-lg">Last 30 days</SelectItem>
              <SelectItem value="7d" className="rounded-lg">Last 7 days</SelectItem>
            </SelectContent>
          </Select>
        </CardHeader>

        <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
          {loading ? (
            <div style={{ textAlign: "center", padding: "60px", color: "var(--muted-foreground)" }}>
              Chargement des données...
            </div>
          ) : error ? (
            <div style={{ textAlign: "center", padding: "60px", color: "red" }}>
              ⚠️ {error}
            </div>
          ) : filteredData.length === 0 ? (
            <div style={{ textAlign: "center", padding: "60px" }}>
              Aucune donnée disponible pour cette période
            </div>
          ) : (
            <ChartContainer config={chartConfig}>
              <LineChart data={filteredData} margin={{ left: 12, right: 12 }}>
                <CartesianGrid vertical={false} />
                <XAxis
                    dataKey="date"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    minTickGap={32}
                    tickFormatter={(value) => {
                        const date = new Date(value)
                        return date.toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        })
                    }}
                />
                <YAxis
                domain={[30000, 5000]}
                scale="linear"
                interval={0}
                label={{
                    value: 'Hourly electricity consumption (MW)',
                    angle: -90,
                    position: 'insideLeft',
                    style: { 
                        textAnchor: 'middle',
                        fontSize: 14,
                      }
                  }}
                
                />
                {/* <YAxis
                  domain={["auto", "auto"]}
                  tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                /> */}
                <ChartTooltip 
                    cursor={false} 
                    content={<ChartTooltipContent 
                        labelFormatter={(label) => formatTooltipDate(label as string)}
                    />} 
                    />
                <Line
                  dataKey="true value"
                  type="monotone"
                  stroke="var(--color-true_value)"
                  strokeWidth={4}
                  dot={false}
                  connectNulls={false}
                />
                <Line
                  dataKey="rte forecast"
                  type="monotone"
                  stroke="var(--color-rte_forecast)"
                  strokeWidth={2}
                //   strokeDasharray="3 3"
                  dot={false}
                  connectNulls={false}
                />
                <Line
                  dataKey="our forecast"
                  type="monotone"
                  stroke="var(--color-our_forecast)"
                  strokeWidth={2}
                //   strokeDasharray="5 5"
                  dot={false}
                  connectNulls={false}
                />
              </LineChart>
            </ChartContainer>
          )}
        </CardContent>

        <CardFooter>
          <div className="flex w-full items-start gap-2 text-sm">
            <div className="grid gap-2">
              <div className="flex flex-col items-start font-medium gap-1">
                <span>Actual consumption for day D is generated on D+1 at 2 a.m.</span>
                <span>RTE forecasts for D+1 are generated on D at 8 p.m.</span>
                <span>Our forecasts for D+1 are generated on D at 10 a.m.</span>{" "}
              </div>
              <div className="text-muted-foreground flex items-center gap-2 leading-none">
               © Actual consumption and RTE forecasts come from the RTE France consumption API.
              </div>
            </div>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}

export default ChartAreaInteractive