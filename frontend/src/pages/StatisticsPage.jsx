import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { 
  BarChart3, Sparkles, Cherry, Star, Clover, RefreshCw, Flame, 
  Snowflake, Target, TrendingUp, PieChart
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, PieChart as RechartsPie, Pie, Cell, Legend
} from "recharts";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LOTTERY_TABS = [
  { key: "megasena", label: "Mega-Sena", icon: Star, color: "#22c55e" },
  { key: "lotofacil", label: "Lotofácil", icon: Clover, color: "#14b8a6" },
  { key: "quina", label: "Quina", icon: Sparkles, color: "#8b5cf6" },
  { key: "dupla_sena", label: "Dupla Sena", icon: Cherry, color: "#f43f5e" }
];

const LotteryBall = ({ number, variant = "neutral", size = "md", frequency }) => {
  const sizeClasses = {
    sm: "w-8 h-8 text-sm",
    md: "w-10 h-10 text-base",
    lg: "w-12 h-12 text-lg"
  };
  
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`lottery-ball lottery-ball-${variant} ${sizeClasses[size]}`}>
        {String(number).padStart(2, "0")}
      </div>
      {frequency !== undefined && (
        <span className="text-xs text-slate-500">{frequency}x</span>
      )}
    </div>
  );
};

const FrequencyChart = ({ data, color }) => {
  const chartData = data.slice(0, 15).map(item => ({
    name: String(item.number).padStart(2, "0"),
    frequency: item.frequency,
    percentage: item.percentage
  }));

  if (!chartData || chartData.length === 0) {
    return <div className="h-64 flex items-center justify-center text-slate-500">Sem dados</div>;
  }

  return (
    <div className="h-64 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis 
            dataKey="name" 
            stroke="#71717a" 
            fontSize={10}
            tickLine={false}
          />
          <YAxis 
            stroke="#71717a" 
            fontSize={10}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip 
            contentStyle={{ 
              background: "#18181b", 
              border: "1px solid #27272a",
              borderRadius: "8px",
              fontSize: "12px"
            }}
            formatter={(value, name) => [value, name === "frequency" ? "Frequência" : "Porcentagem"]}
            labelFormatter={(label) => `Número ${label}`}
          />
          <Bar 
            dataKey="frequency" 
            fill={color}
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

const DistributionChart = ({ data, title }) => {
  const COLORS = ["#10b981", "#f59e0b", "#ef4444"];
  
  const chartData = [
    { name: "Baixa (1-26)", value: data.low || 0 },
    { name: "Média (27-53)", value: data.medium || 0 },
    { name: "Alta (54-80)", value: data.high || 0 }
  ];

  const hasData = chartData.some(d => d.value > 0);
  if (!hasData) {
    return <div className="h-64 flex items-center justify-center text-slate-500">Sem dados</div>;
  }

  return (
    <div className="h-64 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <RechartsPie>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={80}
            paddingAngle={5}
            dataKey="value"
            label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
            labelLine={false}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip 
            contentStyle={{ 
              background: "#18181b", 
              border: "1px solid #27272a",
              borderRadius: "8px",
              fontSize: "12px"
            }}
          />
          <Legend 
            wrapperStyle={{ fontSize: "12px" }}
            formatter={(value) => <span style={{ color: "#a1a1aa" }}>{value}</span>}
          />
        </RechartsPie>
      </ResponsiveContainer>
    </div>
  );
};

const EvenOddChart = ({ data }) => {
  const chartData = [
    { name: "Pares", value: data.even, color: "#3b82f6" },
    { name: "Ímpares", value: data.odd, color: "#f59e0b" }
  ];

  return (
    <div className="flex items-center justify-center gap-8">
      {chartData.map((item) => (
        <div key={item.name} className="text-center">
          <div 
            className="w-24 h-24 rounded-full flex items-center justify-center border-4"
            style={{ borderColor: item.color }}
          >
            <span className="font-mono font-bold text-2xl text-white">
              {item.value.toFixed(0)}%
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-2">{item.name}</p>
        </div>
      ))}
    </div>
  );
};

const StatisticsPage = () => {
  const [quinaStats, setQuinaStats] = useState(null);
  const [duplaStats, setDuplaStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("quina");

  useEffect(() => {
    fetchAllStats();
  }, []);

  const fetchAllStats = async () => {
    setLoading(true);
    try {
      const [quinaRes, duplaRes] = await Promise.all([
        axios.get(`${API}/lottery/quina/statistics`),
        axios.get(`${API}/lottery/dupla_sena/statistics`)
      ]);
      
      setQuinaStats(quinaRes.data.data);
      setDuplaStats(duplaRes.data.data);
    } catch (error) {
      console.error("Error fetching statistics:", error);
      toast.error("Erro ao carregar estatísticas");
    } finally {
      setLoading(false);
    }
  };

  const stats = activeTab === "quina" ? quinaStats : duplaStats;
  const primaryColor = activeTab === "quina" ? "#8b5cf6" : "#f43f5e";
  const Icon = activeTab === "quina" ? Sparkles : Cherry;

  if (loading) {
    return (
      <div className="space-y-6" data-testid="statistics-page-loading">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="statistics-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="font-heading font-extrabold text-4xl text-white tracking-tight flex items-center gap-3">
            <BarChart3 className="w-10 h-10 text-slate-400" />
            Estatísticas
          </h1>
          <p className="text-slate-400 mt-1">
            Análise detalhada dos resultados históricos
          </p>
        </div>
        
        <Button
          onClick={fetchAllStats}
          variant="outline"
          className="border-white/10 hover:bg-white/5"
          data-testid="refresh-stats-btn"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Atualizar
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="bg-zinc-900 border border-white/10 p-1">
          <TabsTrigger 
            value="quina" 
            className="data-[state=active]:bg-violet-600 data-[state=active]:text-white"
            data-testid="tab-quina"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Quina
          </TabsTrigger>
          <TabsTrigger 
            value="dupla_sena" 
            className="data-[state=active]:bg-rose-600 data-[state=active]:text-white"
            data-testid="tab-dupla"
          >
            <Cherry className="w-4 h-4 mr-2" />
            Dupla Sena
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6 space-y-6">
          {/* Summary */}
          <Card className="glass rounded-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white font-heading">
                <Icon className="w-5 h-5" style={{ color: primaryColor }} />
                Resumo Estatístico
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 rounded-lg bg-zinc-800/50">
                  <p className="text-3xl font-mono font-bold text-white">
                    {stats?.total_draws_analyzed || 0}
                  </p>
                  <p className="text-xs text-slate-500 uppercase mt-1">Concursos Analisados</p>
                </div>
                <div className="text-center p-4 rounded-lg bg-emerald-500/10">
                  <p className="text-3xl font-mono font-bold text-emerald-400">
                    {stats?.hot_numbers?.[0]?.number || "—"}
                  </p>
                  <p className="text-xs text-slate-500 uppercase mt-1">Mais Sorteado</p>
                </div>
                <div className="text-center p-4 rounded-lg bg-blue-500/10">
                  <p className="text-3xl font-mono font-bold text-blue-400">
                    {stats?.cold_numbers?.[0]?.number || "—"}
                  </p>
                  <p className="text-xs text-slate-500 uppercase mt-1">Menos Sorteado</p>
                </div>
                <div className="text-center p-4 rounded-lg bg-amber-500/10">
                  <p className="text-3xl font-mono font-bold text-amber-400">
                    {stats?.delayed_numbers?.[0]?.number || "—"}
                  </p>
                  <p className="text-xs text-slate-500 uppercase mt-1">Mais Atrasado</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Hot Numbers */}
          <Card className="glass rounded-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white font-heading">
                <Flame className="w-5 h-5 text-emerald-400" />
                Números Quentes (Mais Frequentes)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3 mb-6">
                {stats?.hot_numbers?.slice(0, 10).map((h) => (
                  <LotteryBall 
                    key={h.number} 
                    number={h.number} 
                    variant="hot" 
                    size="lg"
                    frequency={h.frequency}
                  />
                ))}
              </div>
              <FrequencyChart data={stats?.hot_numbers || []} color="#10b981" />
            </CardContent>
          </Card>

          {/* Cold Numbers */}
          <Card className="glass rounded-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white font-heading">
                <Snowflake className="w-5 h-5 text-blue-400" />
                Números Frios (Menos Frequentes)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3 mb-6">
                {stats?.cold_numbers?.slice(0, 10).map((c) => (
                  <LotteryBall 
                    key={c.number} 
                    number={c.number} 
                    variant="cold" 
                    size="lg"
                    frequency={c.frequency}
                  />
                ))}
              </div>
              <FrequencyChart data={stats?.cold_numbers || []} color="#3b82f6" />
            </CardContent>
          </Card>

          {/* Delayed Numbers */}
          <Card className="glass rounded-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white font-heading">
                <Target className="w-5 h-5 text-amber-400" />
                Números Atrasados
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                {stats?.delayed_numbers?.slice(0, 15).map((d) => (
                  <div key={d.number} className="flex flex-col items-center gap-1">
                    <LotteryBall number={d.number} variant="delayed" size="lg" />
                    <span className="text-xs text-slate-500">
                      {typeof d.draws_since === "number" 
                        ? `${d.draws_since} sorteios`
                        : "Nunca saiu"}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Distribution Charts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Range Distribution */}
            <Card className="glass rounded-xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white font-heading">
                  <PieChart className="w-5 h-5 text-slate-400" />
                  Distribuição por Faixa
                </CardTitle>
              </CardHeader>
              <CardContent>
                <DistributionChart data={stats?.range_distribution || { low: 0, medium: 0, high: 0 }} />
              </CardContent>
            </Card>

            {/* Even/Odd Ratio */}
            <Card className="glass rounded-xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white font-heading">
                  <TrendingUp className="w-5 h-5 text-slate-400" />
                  Proporção Par/Ímpar
                </CardTitle>
              </CardHeader>
              <CardContent>
                <EvenOddChart data={stats?.even_odd_ratio || { even: 50, odd: 50 }} />
              </CardContent>
            </Card>
          </div>

          {/* Strategy Tips */}
          <Card className="glass rounded-xl border-amber-500/20">
            <CardHeader>
              <CardTitle className="text-white font-heading">Dicas Estratégicas</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm text-slate-400 space-y-2">
                <li className="flex items-start gap-2">
                  <Flame className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <span>
                    <strong className="text-white">Números Quentes:</strong> Estatisticamente mais frequentes, 
                    mas lembre-se que cada sorteio é independente.
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <Snowflake className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                  <span>
                    <strong className="text-white">Números Frios:</strong> Menos sorteados historicamente, 
                    alguns jogadores acreditam que estão "prontos para sair".
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <Target className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                  <span>
                    <strong className="text-white">Números Atrasados:</strong> Há muito tempo sem aparecer, 
                    podem ser interessantes para diversificação.
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <TrendingUp className="w-4 h-4 text-violet-400 mt-0.5 flex-shrink-0" />
                  <span>
                    <strong className="text-white">Equilíbrio:</strong> Mantenha uma boa distribuição entre 
                    números baixos, médios e altos, assim como entre pares e ímpares.
                  </span>
                </li>
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default StatisticsPage;
