import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { 
  Cherry, Wand2, Save, RefreshCw, Flame, Snowflake, 
  Target, Zap, Calendar, Trophy, Brain
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LotteryBall = ({ number, variant = "neutral", size = "md" }) => {
  const sizeClasses = {
    sm: "w-8 h-8 text-sm",
    md: "w-10 h-10 text-base",
    lg: "w-12 h-12 text-lg",
    xl: "w-14 h-14 text-xl"
  };
  
  return (
    <div className={`lottery-ball lottery-ball-${variant} ${sizeClasses[size]}`}>
      {String(number).padStart(2, "0")}
    </div>
  );
};

const StrategyCard = ({ strategy, icon: Icon, title, description, selected, onSelect }) => {
  const strategyColors = {
    hot: "border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20",
    cold: "border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20",
    balanced: "border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20",
    coverage: "border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20"
  };
  
  const iconColors = {
    hot: "text-emerald-400",
    cold: "text-blue-400",
    balanced: "text-rose-400",
    coverage: "text-amber-400"
  };
  
  return (
    <button
      onClick={() => onSelect(strategy)}
      className={`p-4 rounded-xl border transition-all duration-300 text-left w-full ${strategyColors[strategy]} ${
        selected ? "ring-2 ring-white/30" : ""
      }`}
      data-testid={`strategy-${strategy}`}
    >
      <div className="flex items-center gap-3 mb-2">
        <Icon className={`w-5 h-5 ${iconColors[strategy]}`} />
        <span className="font-semibold text-white">{title}</span>
      </div>
      <p className="text-xs text-slate-400">{description}</p>
    </button>
  );
};

const GeneratedBetCard = ({ bet, onSave, saving }) => {
  const strategyLabels = {
    hot: "Números Quentes",
    cold: "Números Frios",
    balanced: "Equilibrado",
    coverage: "Cobertura Máxima"
  };
  
  return (
    <Card className="card-dupla rounded-xl" data-testid="generated-bet">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-4">
          <span className={`strategy-badge strategy-${bet.strategy}`}>
            {strategyLabels[bet.strategy]}
          </span>
        </div>
        
        <div className="flex flex-wrap gap-3 justify-center mb-4">
          {bet.numbers.map((num) => (
            <LotteryBall key={num} number={num} variant="dupla" size="lg" />
          ))}
        </div>
        
        <p className="text-xs text-slate-400 text-center mb-4">
          {bet.explanation}
        </p>
        
        <Button 
          onClick={() => onSave(bet)} 
          disabled={saving}
          className="btn-dupla w-full"
          data-testid="save-bet-btn"
        >
          {saving ? (
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Salvar Aposta
        </Button>
      </CardContent>
    </Card>
  );
};

const DuplaSenaPage = () => {
  const [nextDraw, setNextDraw] = useState(null);
  const [latestResult, setLatestResult] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [selectedStrategy, setSelectedStrategy] = useState("balanced");
  const [betCount, setBetCount] = useState("1");
  const [generatedBets, setGeneratedBets] = useState([]);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [nextRes, latestRes, statsRes] = await Promise.all([
        axios.get(`${API}/lottery/dupla_sena/next-draw`),
        axios.get(`${API}/lottery/dupla_sena/latest`),
        axios.get(`${API}/lottery/dupla_sena/statistics`)
      ]);
      
      setNextDraw(nextRes.data.data);
      setLatestResult(latestRes.data.data);
      setStatistics(statsRes.data.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Erro ao carregar dados da Dupla Sena");
    } finally {
      setLoading(false);
    }
  };

  const generateBets = async () => {
    setGenerating(true);
    try {
      const response = await axios.post(
        `${API}/bets/generate?lottery_type=dupla_sena&strategy=${selectedStrategy}&count=${betCount}`
      );
      setGeneratedBets(response.data.data);
      toast.success(`${response.data.data.length} aposta(s) gerada(s)!`);
    } catch (error) {
      console.error("Error generating bets:", error);
      toast.error("Erro ao gerar apostas");
    } finally {
      setGenerating(false);
    }
  };

  const saveBet = async (bet) => {
    setSaving(true);
    try {
      await axios.post(`${API}/bets`, {
        lottery_type: bet.lottery_type,
        numbers: bet.numbers,
        strategy: bet.strategy,
        explanation: bet.explanation
      });
      toast.success("Aposta salva com sucesso!");
      setGeneratedBets(prev => prev.filter(b => b.id !== bet.id));
    } catch (error) {
      if (error.response?.status === 409) {
        toast.error("Esta aposta já existe no histórico");
      } else {
        toast.error("Erro ao salvar aposta");
      }
    } finally {
      setSaving(false);
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
      minimumFractionDigits: 0
    }).format(num);
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="dupla-sena-page-loading">
        <Skeleton className="h-12 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-64 col-span-2" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="dupla-sena-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-rose-600 to-red-700 flex items-center justify-center glow-dupla">
          <Cherry className="w-8 h-8 text-white" />
        </div>
        <div>
          <h1 className="font-heading font-extrabold text-4xl text-white tracking-tight">
            Dupla Sena
          </h1>
          <p className="text-slate-400">Duas chances de ganhar em cada concurso</p>
        </div>
      </div>

      {/* Next Draw & Latest Result */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Next Draw */}
        <Card className="card-dupla rounded-xl" data-testid="dupla-next-draw">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white font-heading">
              <Trophy className="w-5 h-5 text-yellow-400" />
              Próximo Sorteio
              {nextDraw?.acumulado && (
                <span className="px-2 py-1 text-xs font-bold bg-yellow-500/20 text-yellow-400 rounded-full">
                  ACUMULADO
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center mb-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider">Prêmio Estimado</p>
              <p className="prize-value text-4xl">{formatCurrency(nextDraw?.valor_estimado)}</p>
            </div>
            <div className="flex justify-center gap-8">
              <div className="text-center">
                <p className="text-xs text-slate-500 uppercase">Concurso</p>
                <p className="font-mono font-bold text-xl text-white">{nextDraw?.proximo_concurso}</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-slate-500 uppercase">Data</p>
                <p className="font-medium text-slate-300 flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {nextDraw?.data_proximo_concurso || "A definir"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Latest Result */}
        <Card className="glass rounded-xl" data-testid="dupla-latest-result">
          <CardHeader>
            <CardTitle className="text-white font-heading">Último Resultado</CardTitle>
            <p className="text-sm text-slate-500">
              Concurso {latestResult?.concurso} • {latestResult?.data}
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs text-slate-500 mb-2">1º Sorteio</p>
              <div className="flex flex-wrap gap-2 justify-center">
                {latestResult?.dezenas?.map((num) => (
                  <LotteryBall key={`1-${num}`} number={num} variant="dupla" size="lg" />
                ))}
              </div>
            </div>
            {latestResult?.dezenas_segundo_sorteio?.length > 0 && (
              <div className="pt-3 border-t border-white/5">
                <p className="text-xs text-slate-500 mb-2">2º Sorteio</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {latestResult.dezenas_segundo_sorteio.map((num) => (
                    <LotteryBall key={`2-${num}`} number={num} variant="dupla" size="lg" />
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Statistics Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="glass rounded-xl">
          <CardContent className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                <Flame className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500 uppercase">Números Quentes</p>
                <p className="text-sm text-slate-400">Mais sorteados</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {statistics?.hot_numbers?.slice(0, 5).map((h) => (
                <LotteryBall key={h.number} number={h.number} variant="hot" size="sm" />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="glass rounded-xl">
          <CardContent className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Snowflake className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500 uppercase">Números Frios</p>
                <p className="text-sm text-slate-400">Menos sorteados</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {statistics?.cold_numbers?.slice(0, 5).map((c) => (
                <LotteryBall key={c.number} number={c.number} variant="cold" size="sm" />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="glass rounded-xl">
          <CardContent className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <Target className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500 uppercase">Atrasados</p>
                <p className="text-sm text-slate-400">Mais tempo sem sair</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {statistics?.delayed_numbers?.slice(0, 5).map((d) => (
                <LotteryBall key={d.number} number={d.number} variant="delayed" size="sm" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bet Generator */}
      <Card className="glass rounded-xl" data-testid="bet-generator">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white font-heading">
            <Wand2 className="w-5 h-5 text-rose-400" />
            Gerador de Apostas
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Strategy Selection */}
          <div>
            <p className="text-sm text-slate-400 mb-3">Escolha sua estratégia:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              <StrategyCard
                strategy="hot"
                icon={Flame}
                title="Números Quentes"
                description="Foco nos números mais sorteados"
                selected={selectedStrategy === "hot"}
                onSelect={setSelectedStrategy}
              />
              <StrategyCard
                strategy="cold"
                icon={Snowflake}
                title="Números Frios"
                description="Foco nos números menos sorteados"
                selected={selectedStrategy === "cold"}
                onSelect={setSelectedStrategy}
              />
              <StrategyCard
                strategy="balanced"
                icon={Zap}
                title="Equilibrado"
                description="Mix de quentes, frios e atrasados"
                selected={selectedStrategy === "balanced"}
                onSelect={setSelectedStrategy}
              />
              <StrategyCard
                strategy="coverage"
                icon={Target}
                title="Cobertura Máxima"
                description="Distribuição por faixas"
                selected={selectedStrategy === "coverage"}
                onSelect={setSelectedStrategy}
              />
            </div>
          </div>

          {/* Quantity Selection */}
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <p className="text-sm text-slate-400 mb-2">Quantidade de apostas:</p>
              <Select value={betCount} onValueChange={setBetCount}>
                <SelectTrigger className="w-full bg-zinc-900 border-white/10" data-testid="bet-count-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 5, 10].map((n) => (
                    <SelectItem key={n} value={String(n)}>{n} aposta{n > 1 ? "s" : ""}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex-1">
              <p className="text-sm text-slate-400 mb-2">&nbsp;</p>
              <Button 
                onClick={generateBets} 
                disabled={generating}
                className="btn-dupla w-full"
                data-testid="generate-bets-btn"
              >
                {generating ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Wand2 className="w-4 h-4 mr-2" />
                )}
                Gerar Apostas
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Generated Bets */}
      {generatedBets.length > 0 && (
        <div>
          <h2 className="font-heading font-bold text-xl text-white mb-4">
            Apostas Geradas
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {generatedBets.map((bet) => (
              <GeneratedBetCard 
                key={bet.id} 
                bet={bet} 
                onSave={saveBet}
                saving={saving}
              />
            ))}
          </div>
        </div>
      )}

      {/* Info */}
      <Card className="glass rounded-xl border-rose-500/20">
        <CardContent className="p-4">
          <h3 className="font-semibold text-white mb-2">Como funciona a Dupla Sena?</h3>
          <ul className="text-sm text-slate-400 space-y-1">
            <li>• Escolha 6 números de 01 a 50</li>
            <li>• <strong>Dois sorteios</strong> por concurso = mais chances!</li>
            <li>• Acerte 6 números = Sena (prêmio principal)</li>
            <li>• Acerte 5 números = Quina</li>
            <li>• Acerte 4 números = Quadra</li>
            <li>• Acerte 3 números = Terno</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};

export default DuplaSenaPage;
