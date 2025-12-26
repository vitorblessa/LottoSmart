import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { 
  Sparkles, Cherry, Star, Clover, Trophy, Calendar, TrendingUp, 
  ArrowRight, RefreshCw, Flame, Snowflake, Clock
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LotteryBall = ({ number, variant = "neutral", size = "md" }) => {
  const sizeClasses = {
    sm: "w-8 h-8 text-sm",
    md: "w-10 h-10 text-base",
    lg: "w-12 h-12 text-lg"
  };
  
  return (
    <div className={`lottery-ball lottery-ball-${variant} ${sizeClasses[size]}`}>
      {String(number).padStart(2, "0")}
    </div>
  );
};

const NextDrawCard = ({ lotteryType, title, icon: Icon, variant }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNextDraw();
  }, [lotteryType]);

  const fetchNextDraw = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/lottery/${lotteryType}/next-draw`);
      setData(response.data.data);
    } catch (error) {
      console.error(`Error fetching ${lotteryType} next draw:`, error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    const num = value || 0;
    
    if (num >= 1000000000) {
      const billions = num / 1000000000;
      const formatted = billions % 1 === 0 ? billions.toFixed(0) : billions.toFixed(1).replace('.', ',');
      return `R$ ${formatted} ${billions >= 2 ? 'Bilhões' : 'Bilhão'}`;
    }
    if (num >= 1000000) {
      const millions = num / 1000000;
      const formatted = millions % 1 === 0 ? millions.toFixed(0) : millions.toFixed(1).replace('.', ',');
      return `R$ ${formatted} ${millions >= 2 ? 'Milhões' : 'Milhão'}`;
    }
    if (num >= 1000) {
      const thousands = num / 1000;
      const formatted = thousands % 1 === 0 ? thousands.toFixed(0) : thousands.toFixed(1).replace('.', ',');
      return `R$ ${formatted} Mil`;
    }
    
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(num);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "A definir";
    try {
      const [day, month, year] = dateStr.split("/");
      const date = new Date(year, month - 1, day);
      return date.toLocaleDateString("pt-BR", { 
        weekday: "short", 
        day: "2-digit", 
        month: "short" 
      });
    } catch {
      return dateStr;
    }
  };

  const cardClassMap = {
    quina: "card-quina",
    dupla: "card-dupla",
    megasena: "card-megasena",
    lotofacil: "card-lotofacil"
  };
  const btnClassMap = {
    quina: "btn-quina",
    dupla: "btn-dupla",
    megasena: "btn-megasena",
    lotofacil: "btn-lotofacil"
  };
  const routeMap = {
    quina: "/quina",
    dupla: "/dupla-sena",
    megasena: "/megasena",
    lotofacil: "/lotofacil"
  };
  
  const cardClass = cardClassMap[variant] || "card-quina";
  const btnClass = btnClassMap[variant] || "btn-quina";
  const route = routeMap[variant] || "/";

  if (loading) {
    return (
      <Card className={`${cardClass} rounded-xl`}>
        <CardHeader className="pb-2">
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-6 w-24" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`${cardClass} rounded-xl overflow-hidden`} data-testid={`next-draw-${lotteryType}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-white font-heading">
            <Icon className="w-5 h-5" />
            {title}
          </CardTitle>
          {data?.acumulado && (
            <span className="px-2 py-1 text-xs font-bold bg-yellow-500/20 text-yellow-400 rounded-full border border-yellow-500/30">
              ACUMULADO
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Prêmio Estimado</p>
          <p className="prize-value text-2xl md:text-3xl">{formatCurrency(data?.valor_estimado || data?.valor_acumulado)}</p>
        </div>
        
        <div className="flex items-center gap-4">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider">Concurso</p>
            <p className="font-mono font-bold text-white">{data?.proximo_concurso || "—"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider">Data</p>
            <p className="font-medium text-slate-300 flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {formatDate(data?.data_proximo_concurso)}
            </p>
          </div>
        </div>
        
        <Link to={route}>
          <Button className={`${btnClass} w-full mt-2`} data-testid={`goto-${lotteryType}-btn`}>
            Gerar Apostas <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
};

const LatestResultCard = ({ lotteryType, title, variant }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLatest();
  }, [lotteryType]);

  const fetchLatest = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/lottery/${lotteryType}/latest`);
      setData(response.data.data);
    } catch (error) {
      console.error(`Error fetching ${lotteryType} latest:`, error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card className="glass rounded-xl">
        <CardContent className="p-4">
          <Skeleton className="h-6 w-32 mb-4" />
          <div className="flex gap-2">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="w-10 h-10 rounded-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass rounded-xl" data-testid={`latest-result-${lotteryType}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-heading font-semibold text-white">{title}</h3>
            <p className="text-xs text-slate-500">Concurso {data?.concurso} • {data?.data}</p>
          </div>
        </div>
        
        <div className="flex flex-wrap gap-2 mb-2">
          {data?.dezenas?.map((num) => (
            <LotteryBall key={num} number={num} variant={variant} size="md" />
          ))}
        </div>
        
        {lotteryType === "dupla_sena" && data?.dezenas_segundo_sorteio?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-white/5">
            <p className="text-xs text-slate-500 mb-2">2º Sorteio</p>
            <div className="flex flex-wrap gap-2">
              {data.dezenas_segundo_sorteio.map((num) => (
                <LotteryBall key={num} number={num} variant={variant} size="sm" />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const QuickStats = ({ lotteryType }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, [lotteryType]);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/lottery/${lotteryType}/statistics`);
      setStats(response.data.data);
    } catch (error) {
      console.error("Error fetching stats:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !stats) {
    return (
      <div className="grid grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card className="glass rounded-xl stat-card">
        <CardContent className="p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
            <Flame className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase">Mais Quentes</p>
            <div className="flex gap-1 mt-1">
              {stats.hot_numbers?.slice(0, 3).map((h) => (
                <span key={h.number} className="font-mono font-bold text-emerald-400">
                  {String(h.number).padStart(2, "0")}
                </span>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card className="glass rounded-xl stat-card">
        <CardContent className="p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
            <Snowflake className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase">Mais Frios</p>
            <div className="flex gap-1 mt-1">
              {stats.cold_numbers?.slice(0, 3).map((c) => (
                <span key={c.number} className="font-mono font-bold text-blue-400">
                  {String(c.number).padStart(2, "0")}
                </span>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card className="glass rounded-xl stat-card">
        <CardContent className="p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
            <Clock className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase">Atrasados</p>
            <div className="flex gap-1 mt-1">
              {stats.delayed_numbers?.slice(0, 3).map((d) => (
                <span key={d.number} className="font-mono font-bold text-amber-400">
                  {String(d.number).padStart(2, "0")}
                </span>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const Dashboard = () => {
  const [recentBets, setRecentBets] = useState([]);
  const [loadingBets, setLoadingBets] = useState(true);

  useEffect(() => {
    fetchRecentBets();
  }, []);

  const fetchRecentBets = async () => {
    try {
      const response = await axios.get(`${API}/bets?limit=5`);
      setRecentBets(response.data.data);
    } catch (error) {
      console.error("Error fetching bets:", error);
    } finally {
      setLoadingBets(false);
    }
  };

  return (
    <div className="space-y-8" data-testid="dashboard">
      {/* Header */}
      <div>
        <h1 className="font-heading font-extrabold text-4xl md:text-5xl text-white tracking-tight">
          Dashboard
        </h1>
        <p className="text-slate-400 mt-2">
          Apostas inteligentes baseadas em análise estatística
        </p>
      </div>

      {/* Next Draws */}
      <section>
        <h2 className="font-heading font-bold text-xl text-white/90 mb-4 flex items-center gap-2">
          <Trophy className="w-5 h-5 text-yellow-400" />
          Próximos Sorteios
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <NextDrawCard 
            lotteryType="megasena" 
            title="Mega-Sena" 
            icon={Star} 
            variant="megasena" 
          />
          <NextDrawCard 
            lotteryType="lotofacil" 
            title="Lotofácil" 
            icon={Clover} 
            variant="lotofacil" 
          />
          <NextDrawCard 
            lotteryType="quina" 
            title="Quina" 
            icon={Sparkles} 
            variant="quina" 
          />
          <NextDrawCard 
            lotteryType="dupla_sena" 
            title="Dupla Sena" 
            icon={Cherry} 
            variant="dupla" 
          />
        </div>
      </section>

      {/* Latest Results */}
      <section>
        <h2 className="font-heading font-bold text-xl text-white/90 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-emerald-400" />
          Últimos Resultados
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <LatestResultCard lotteryType="megasena" title="Mega-Sena" variant="megasena" />
          <LatestResultCard lotteryType="lotofacil" title="Lotofácil" variant="lotofacil" />
          <LatestResultCard lotteryType="quina" title="Quina" variant="quina" />
          <LatestResultCard lotteryType="dupla_sena" title="Dupla Sena" variant="dupla" />
        </div>
      </section>

      {/* Quick Stats */}
      <section>
        <h2 className="font-heading font-bold text-xl text-white/90 mb-4">
          Estatísticas Rápidas - Mega-Sena
        </h2>
        <QuickStats lotteryType="megasena" />
      </section>

      {/* Recent Bets */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading font-bold text-xl text-white/90">
            Apostas Recentes
          </h2>
          <Link to="/historico">
            <Button variant="ghost" className="text-slate-400 hover:text-white">
              Ver todas <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </Link>
        </div>
        
        {loadingBets ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))}
          </div>
        ) : recentBets.length === 0 ? (
          <Card className="glass rounded-xl">
            <CardContent className="p-8 text-center">
              <p className="text-slate-500">Nenhuma aposta salva ainda</p>
              <p className="text-sm text-slate-600 mt-1">
                Gere apostas inteligentes na página da Quina ou Dupla Sena
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {recentBets.map((bet) => (
              <Card 
                key={bet.id} 
                className={`glass rounded-xl bet-card ${bet.lottery_type === "quina" ? "bet-card-quina" : "bet-card-dupla"}`}
              >
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      bet.lottery_type === "quina" 
                        ? "bg-violet-600/20" 
                        : "bg-rose-600/20"
                    }`}>
                      {bet.lottery_type === "quina" 
                        ? <Sparkles className="w-5 h-5 text-violet-400" />
                        : <Cherry className="w-5 h-5 text-rose-400" />
                      }
                    </div>
                    <div>
                      <p className="font-medium text-white">
                        {bet.lottery_type === "quina" ? "Quina" : "Dupla Sena"}
                      </p>
                      <div className="flex gap-2 mt-1">
                        {bet.numbers.map((n) => (
                          <span key={n} className="font-mono text-sm text-slate-400">
                            {String(n).padStart(2, "0")}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <span className={`strategy-badge strategy-${bet.strategy}`}>
                    {bet.strategy}
                  </span>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Disclaimer */}
      <Card className="glass rounded-xl border-amber-500/20">
        <CardContent className="p-4">
          <p className="text-xs text-amber-400/80 text-center">
            ⚠️ <strong>Aviso:</strong> Apesar do refinamento técnico e estatístico, jogos de loteria 
            são eventos aleatórios e não há garantia de premiação. Jogue com responsabilidade.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
