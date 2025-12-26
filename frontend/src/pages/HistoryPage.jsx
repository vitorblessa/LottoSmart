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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { 
  History, Sparkles, Cherry, Star, Clover, Trash2, RefreshCw, 
  CheckCircle2, XCircle, Search, Filter
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LOTTERY_CONFIG = {
  quina: { icon: Sparkles, color: "violet", label: "Quina" },
  dupla_sena: { icon: Cherry, color: "rose", label: "Dupla Sena" },
  megasena: { icon: Star, color: "green", label: "Mega-Sena" },
  lotofacil: { icon: Clover, color: "teal", label: "Lotofácil" }
};

const LotteryBall = ({ number, variant = "neutral", size = "md", matched = false }) => {
  const sizeClasses = {
    sm: "w-7 h-7 text-xs",
    md: "w-9 h-9 text-sm",
    lg: "w-11 h-11 text-base"
  };
  
  const matchClass = matched ? "ring-2 ring-emerald-400 ring-offset-1 ring-offset-zinc-950" : "";
  
  return (
    <div className={`lottery-ball lottery-ball-${variant} ${sizeClasses[size]} ${matchClass}`}>
      {String(number).padStart(2, "0")}
    </div>
  );
};

const BetCard = ({ bet, onCheck, onDelete, checking, deleting }) => {
  const strategyLabels = {
    hot: "Quentes",
    cold: "Frios",
    balanced: "Equilibrado",
    coverage: "Cobertura",
    manual: "Manual"
  };
  
  const config = LOTTERY_CONFIG[bet.lottery_type] || LOTTERY_CONFIG.quina;
  const Icon = config.icon;
  const cardClass = `bet-card-${bet.lottery_type === "dupla_sena" ? "dupla" : bet.lottery_type}`;
  const variant = bet.lottery_type === "dupla_sena" ? "dupla" : bet.lottery_type;
  
  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <Card className={`glass rounded-xl bet-card ${cardClass}`} data-testid={`bet-card-${bet.id}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Icon className={`w-4 h-4 text-${config.color}-400`} />
            <span className="font-medium text-white">
              {config.label}
            </span>
            <span className={`strategy-badge strategy-${bet.strategy}`}>
              {strategyLabels[bet.strategy]}
            </span>
          </div>
          <span className="text-xs text-slate-500">{formatDate(bet.created_at)}</span>
        </div>
        
        <div className="flex flex-wrap gap-2 mb-3">
          {bet.numbers.map((num) => {
            const isMatched = bet.result?.matches?.includes(num);
            return (
              <LotteryBall 
                key={num} 
                number={num} 
                variant={variant} 
                size="md" 
                matched={isMatched}
              />
            );
          })}
        </div>
        
        {/* Check Result */}
        {bet.checked && bet.result && (
          <div className={`p-3 rounded-lg mb-3 ${
            bet.result.is_winner 
              ? "bg-emerald-500/20 border border-emerald-500/30" 
              : "bg-zinc-800/50"
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {bet.result.is_winner ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-slate-500" />
                )}
                <span className={`text-sm font-medium ${
                  bet.result.is_winner ? "text-emerald-400" : "text-slate-400"
                }`}>
                  {bet.result.prize_tier || `${bet.result.match_count} acerto(s)`}
                </span>
              </div>
              <span className="text-xs text-slate-500">
                Concurso {bet.result.concurso}
              </span>
            </div>
            {bet.result.is_winner && (
              <p className="text-xs text-emerald-400/80 mt-1">
                Parabéns! Você acertou!
              </p>
            )}
          </div>
        )}
        
        <div className="flex gap-2">
          {!bet.checked && (
            <Button
              onClick={() => onCheck(bet.id)}
              disabled={checking}
              variant="outline"
              size="sm"
              className="flex-1 border-white/10 hover:bg-white/5"
              data-testid={`check-bet-${bet.id}`}
            >
              {checking ? (
                <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Search className="w-3 h-3 mr-1" />
              )}
              Conferir
            </Button>
          )}
          
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                data-testid={`delete-bet-${bet.id}`}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent className="bg-zinc-900 border-white/10">
              <AlertDialogHeader>
                <AlertDialogTitle>Remover aposta?</AlertDialogTitle>
                <AlertDialogDescription>
                  Esta ação não pode ser desfeita. A aposta será permanentemente removida do seu histórico.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="bg-zinc-800 border-white/10 hover:bg-zinc-700">
                  Cancelar
                </AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => onDelete(bet.id)}
                  className="bg-red-600 hover:bg-red-700"
                >
                  {deleting ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    "Remover"
                  )}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
};

const HistoryPage = () => {
  const [bets, setBets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [filter, setFilter] = useState("all");
  const [checkingAll, setCheckingAll] = useState(false);

  useEffect(() => {
    fetchBets();
  }, [filter]);

  const fetchBets = async () => {
    setLoading(true);
    try {
      const params = filter !== "all" ? `?lottery_type=${filter}` : "";
      const response = await axios.get(`${API}/bets${params}`);
      setBets(response.data.data);
    } catch (error) {
      console.error("Error fetching bets:", error);
      toast.error("Erro ao carregar histórico");
    } finally {
      setLoading(false);
    }
  };

  const checkBet = async (betId) => {
    setChecking(true);
    try {
      const response = await axios.post(`${API}/bets/check/${betId}`);
      const result = response.data.data;
      
      // Update local state
      setBets(prev => prev.map(b => 
        b.id === betId 
          ? { ...b, checked: true, result: result }
          : b
      ));
      
      if (result.is_winner) {
        toast.success(`Parabéns! ${result.prize_tier}!`);
      } else {
        toast.info(`${result.match_count} acerto(s) no concurso ${result.concurso}`);
      }
    } catch (error) {
      console.error("Error checking bet:", error);
      toast.error("Erro ao conferir aposta");
    } finally {
      setChecking(false);
    }
  };

  const deleteBet = async (betId) => {
    setDeleting(true);
    try {
      await axios.delete(`${API}/bets/${betId}`);
      setBets(prev => prev.filter(b => b.id !== betId));
      toast.success("Aposta removida");
    } catch (error) {
      console.error("Error deleting bet:", error);
      toast.error("Erro ao remover aposta");
    } finally {
      setDeleting(false);
    }
  };

  const checkAllBets = async () => {
    setCheckingAll(true);
    try {
      const response = await axios.post(`${API}/bets/check-all`);
      toast.success(`${response.data.checked_count} aposta(s) conferida(s)`);
      fetchBets();
    } catch (error) {
      console.error("Error checking all bets:", error);
      toast.error("Erro ao conferir apostas");
    } finally {
      setCheckingAll(false);
    }
  };

  const uncheckedCount = bets.filter(b => !b.checked).length;
  const winnerCount = bets.filter(b => b.result?.is_winner).length;

  return (
    <div className="space-y-8" data-testid="history-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="font-heading font-extrabold text-4xl text-white tracking-tight flex items-center gap-3">
            <History className="w-10 h-10 text-slate-400" />
            Histórico
          </h1>
          <p className="text-slate-400 mt-1">
            {bets.length} aposta(s) salva(s) • {uncheckedCount} não conferida(s) • {winnerCount} premiada(s)
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-40 bg-zinc-900 border-white/10" data-testid="filter-select">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Filtrar" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas</SelectItem>
              <SelectItem value="quina">Quina</SelectItem>
              <SelectItem value="dupla_sena">Dupla Sena</SelectItem>
            </SelectContent>
          </Select>
          
          {uncheckedCount > 0 && (
            <Button
              onClick={checkAllBets}
              disabled={checkingAll}
              className="bg-emerald-600 hover:bg-emerald-700"
              data-testid="check-all-btn"
            >
              {checkingAll ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4 mr-2" />
              )}
              Conferir Todas
            </Button>
          )}
        </div>
      </div>

      {/* Bets List */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      ) : bets.length === 0 ? (
        <Card className="glass rounded-xl">
          <CardContent className="p-12 text-center">
            <History className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="font-heading font-semibold text-xl text-white mb-2">
              Nenhuma aposta encontrada
            </h3>
            <p className="text-slate-400">
              {filter !== "all" 
                ? "Não há apostas com este filtro. Tente outro filtro."
                : "Comece gerando apostas na página da Quina ou Dupla Sena."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {bets.map((bet) => (
            <BetCard
              key={bet.id}
              bet={bet}
              onCheck={checkBet}
              onDelete={deleteBet}
              checking={checking}
              deleting={deleting}
            />
          ))}
        </div>
      )}

      {/* Stats Summary */}
      {bets.length > 0 && (
        <Card className="glass rounded-xl">
          <CardHeader>
            <CardTitle className="text-white font-heading">Resumo</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 rounded-lg bg-zinc-800/50">
                <p className="text-2xl font-mono font-bold text-white">{bets.length}</p>
                <p className="text-xs text-slate-500 uppercase">Total</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-violet-500/10">
                <p className="text-2xl font-mono font-bold text-violet-400">
                  {bets.filter(b => b.lottery_type === "quina").length}
                </p>
                <p className="text-xs text-slate-500 uppercase">Quina</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-rose-500/10">
                <p className="text-2xl font-mono font-bold text-rose-400">
                  {bets.filter(b => b.lottery_type === "dupla_sena").length}
                </p>
                <p className="text-xs text-slate-500 uppercase">Dupla Sena</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-emerald-500/10">
                <p className="text-2xl font-mono font-bold text-emerald-400">{winnerCount}</p>
                <p className="text-xs text-slate-500 uppercase">Premiadas</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default HistoryPage;
