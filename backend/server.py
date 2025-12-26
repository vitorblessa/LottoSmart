from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import random
from collections import Counter
import hashlib

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="LottoSmart - Apostas Inteligentes")

# Lottery configurations
LOTTERY_CONFIG = {
    "quina": {"max_number": 80, "numbers_to_pick": 5, "api_name": "quina"},
    "dupla_sena": {"max_number": 50, "numbers_to_pick": 6, "api_name": "duplasena"},
    "lotofacil": {"max_number": 25, "numbers_to_pick": 15, "api_name": "lotofacil"},
    "megasena": {"max_number": 60, "numbers_to_pick": 6, "api_name": "megasena"}
}

VALID_LOTTERY_TYPES = list(LOTTERY_CONFIG.keys())

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===================== MODELS =====================

class LotteryResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    concurso: int
    data: str
    dezenas: List[str]
    dezenas_segundo_sorteio: Optional[List[str]] = None
    premio_principal: float = 0.0
    acumulado: bool = False
    valor_acumulado: float = 0.0
    proximo_concurso: Optional[int] = None
    data_proximo_concurso: Optional[str] = None
    valor_estimado_proximo: float = 0.0

class Statistics(BaseModel):
    hot_numbers: List[Dict[str, Any]]
    cold_numbers: List[Dict[str, Any]]
    delayed_numbers: List[Dict[str, Any]]
    even_odd_ratio: Dict[str, float]
    range_distribution: Dict[str, int]
    total_draws_analyzed: int

class GeneratedBet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lottery_type: str
    numbers: List[int]
    strategy: str
    explanation: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checked: bool = False
    result: Optional[Dict[str, Any]] = None

class BetCreate(BaseModel):
    lottery_type: str
    numbers: List[int]
    strategy: str = "manual"
    explanation: str = "Aposta manual"

class BetCheckResult(BaseModel):
    bet_id: str
    lottery_type: str
    numbers: List[int]
    concurso: int
    drawn_numbers: List[int]
    matches: List[int]
    match_count: int
    prize_tier: Optional[str] = None
    is_winner: bool

# ===================== LOTTERY API SERVICE =====================

async def fetch_lottery_data(lottery_type: str, concurso: Optional[int] = None) -> Optional[Dict]:
    """Fetch lottery data from Caixa API"""
    config = LOTTERY_CONFIG.get(lottery_type)
    if not config:
        return None
    
    api_name = config["api_name"]
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{api_name}"
    
    if concurso:
        url = f"{url}/{concurso}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Error fetching lottery data: {e}")
    
    return None

async def fetch_multiple_results(lottery_type: str, count: int = 100) -> List[Dict]:
    """Fetch multiple lottery results for statistics"""
    results = []
    
    # First get latest to know the current concurso
    latest = await fetch_lottery_data(lottery_type)
    if not latest:
        # Return cached data from DB
        cached = await db[f"{lottery_type}_results"].find({}, {"_id": 0}).sort("concurso", -1).limit(count).to_list(count)
        return cached
    
    current_concurso = latest.get("numero", latest.get("concurso", 0))
    
    # Store latest
    await store_result(lottery_type, latest)
    results.append(latest)
    
    # Fetch previous results
    for i in range(1, min(count, 50)):  # Limit API calls
        concurso_num = current_concurso - i
        if concurso_num <= 0:
            break
        
        # Check if we have it cached
        cached = await db[f"{lottery_type}_results"].find_one({"concurso": concurso_num}, {"_id": 0})
        if cached:
            results.append(cached)
        else:
            data = await fetch_lottery_data(lottery_type, concurso_num)
            if data:
                await store_result(lottery_type, data)
                results.append(data)
    
    return results

async def store_result(lottery_type: str, data: Dict):
    """Store lottery result in database"""
    concurso = data.get("numero", data.get("concurso"))
    if not concurso:
        return
    
    doc = {
        "concurso": concurso,
        "data": data.get("dataApuracao", data.get("data", "")),
        "dezenas": data.get("listaDezenas", data.get("dezenas", [])),
        "acumulado": data.get("acumulado", False),
        "valor_acumulado": data.get("valorAcumuladoProximoConcurso", 0),
        "proximo_concurso": data.get("numeroConcursoProximo"),
        "data_proximo_concurso": data.get("dataProximoConcurso"),
        "valor_estimado_proximo": data.get("valorEstimadoProximoConcurso", 0),
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Handle Dupla Sena second draw
    if lottery_type == "dupla_sena":
        dezenas_2 = data.get("listaDezenasSegundoSorteio", [])
        if dezenas_2:
            doc["dezenas_segundo_sorteio"] = dezenas_2
    
    await db[f"{lottery_type}_results"].update_one(
        {"concurso": concurso},
        {"$set": doc},
        upsert=True
    )

# ===================== STATISTICS SERVICE =====================

def calculate_statistics(results: List[Dict], lottery_type: str) -> Statistics:
    """Calculate statistical analysis of lottery numbers"""
    if not results:
        return Statistics(
            hot_numbers=[],
            cold_numbers=[],
            delayed_numbers=[],
            even_odd_ratio={"even": 0, "odd": 0},
            range_distribution={"low": 0, "medium": 0, "high": 0},
            total_draws_analyzed=0
        )
    
    config = LOTTERY_CONFIG.get(lottery_type, {"max_number": 60})
    max_number = config["max_number"]
    all_numbers = []
    last_seen = {i: -1 for i in range(1, max_number + 1)}
    
    for idx, result in enumerate(results):
        dezenas = result.get("dezenas", result.get("listaDezenas", []))
        for d in dezenas:
            num = int(d)
            all_numbers.append(num)
            if last_seen[num] == -1:
                last_seen[num] = idx
        
        # Include second draw for Dupla Sena
        if lottery_type == "dupla_sena":
            dezenas_2 = result.get("dezenas_segundo_sorteio", result.get("listaDezenasSegundoSorteio", []))
            for d in dezenas_2:
                num = int(d)
                all_numbers.append(num)
    
    # Frequency count
    frequency = Counter(all_numbers)
    total_draws = len(results)
    
    # Hot numbers (most frequent)
    hot = frequency.most_common(15)
    hot_numbers = [{"number": n, "frequency": f, "percentage": round(f / total_draws * 100, 1)} for n, f in hot]
    
    # Cold numbers (least frequent)
    all_freq = [(i, frequency.get(i, 0)) for i in range(1, max_number + 1)]
    cold = sorted(all_freq, key=lambda x: x[1])[:15]
    cold_numbers = [{"number": n, "frequency": f, "percentage": round(f / total_draws * 100, 1) if total_draws > 0 else 0} for n, f in cold]
    
    # Delayed numbers (longest since last appearance)
    delayed = sorted([(n, last_seen[n]) for n in range(1, max_number + 1) if last_seen[n] == -1 or last_seen[n] > 5], 
                     key=lambda x: x[1] if x[1] >= 0 else 999, reverse=True)[:15]
    delayed_numbers = [{"number": n, "draws_since": d if d >= 0 else "never"} for n, d in delayed]
    
    # Even/Odd ratio
    even_count = sum(1 for n in all_numbers if n % 2 == 0)
    odd_count = len(all_numbers) - even_count
    total = even_count + odd_count
    even_odd_ratio = {
        "even": round(even_count / total * 100, 1) if total > 0 else 0,
        "odd": round(odd_count / total * 100, 1) if total > 0 else 0
    }
    
    # Range distribution
    third = max_number // 3
    range_dist = {"low": 0, "medium": 0, "high": 0}
    for n in all_numbers:
        if n <= third:
            range_dist["low"] += 1
        elif n <= 2 * third:
            range_dist["medium"] += 1
        else:
            range_dist["high"] += 1
    
    return Statistics(
        hot_numbers=hot_numbers,
        cold_numbers=cold_numbers,
        delayed_numbers=delayed_numbers,
        even_odd_ratio=even_odd_ratio,
        range_distribution=range_dist,
        total_draws_analyzed=total_draws
    )

# ===================== BET GENERATION SERVICE =====================

def generate_smart_bet(statistics: Statistics, lottery_type: str, strategy: str = "balanced") -> GeneratedBet:
    """Generate intelligent bet based on statistics"""
    config = LOTTERY_CONFIG.get(lottery_type, {"max_number": 60, "numbers_to_pick": 6})
    max_number = config["max_number"]
    numbers_to_pick = config["numbers_to_pick"]
    
    hot_nums = [h["number"] for h in statistics.hot_numbers]
    cold_nums = [c["number"] for c in statistics.cold_numbers]
    delayed_nums = [d["number"] for d in statistics.delayed_numbers if isinstance(d["draws_since"], int)]
    
    selected = []
    explanation_parts = []
    
    if strategy == "hot":
        # Focus on hot numbers
        pool = hot_nums[:20] if len(hot_nums) >= 20 else hot_nums + list(range(1, max_number + 1))
        pool = list(set(pool))
        selected = random.sample(pool[:max(25, numbers_to_pick + 5)], min(numbers_to_pick, len(pool)))
        explanation_parts.append("Foco em números quentes (mais frequentes)")
        
    elif strategy == "cold":
        # Focus on cold/delayed numbers
        pool = cold_nums + delayed_nums
        pool = list(set(pool))
        if len(pool) < numbers_to_pick:
            pool = pool + [n for n in range(1, max_number + 1) if n not in pool]
        selected = random.sample(pool[:max(30, numbers_to_pick + 10)], min(numbers_to_pick, len(pool)))
        explanation_parts.append("Foco em números frios e atrasados (menos frequentes)")
        
    elif strategy == "balanced":
        # Mix of hot, cold, and delayed - proportional to numbers_to_pick
        hot_count = max(1, numbers_to_pick // 3)
        cold_count = max(1, numbers_to_pick // 4)
        delayed_count = max(1, numbers_to_pick // 5) if delayed_nums else 0
        
        hot_pick = random.sample(hot_nums[:15], min(hot_count, len(hot_nums))) if hot_nums else []
        cold_pick = random.sample(cold_nums[:15], min(cold_count, len(cold_nums))) if cold_nums else []
        delayed_pick = random.sample(delayed_nums[:10], min(delayed_count, len(delayed_nums))) if delayed_nums else []
        
        selected = list(set(hot_pick + cold_pick + delayed_pick))
        
        # Fill remaining with random balanced selection
        remaining = numbers_to_pick - len(selected)
        all_numbers = list(range(1, max_number + 1))
        available = [n for n in all_numbers if n not in selected]
        
        while remaining > 0 and available:
            n = random.choice(available)
            selected.append(n)
            available.remove(n)
            remaining -= 1
        
        explanation_parts.append("Combinação equilibrada de números quentes, frios e atrasados")
        
    elif strategy == "coverage":
        # Maximum coverage across ranges
        third = max_number // 3
        low = list(range(1, third + 1))
        medium = list(range(third + 1, 2 * third + 1))
        high = list(range(2 * third + 1, max_number + 1))
        
        picks_per_range = numbers_to_pick // 3
        extra = numbers_to_pick % 3
        
        low_picks = min(picks_per_range + (1 if extra > 0 else 0), len(low))
        medium_picks = min(picks_per_range + (1 if extra > 1 else 0), len(medium))
        high_picks = min(numbers_to_pick - low_picks - medium_picks, len(high))
        
        selected = random.sample(low, low_picks)
        selected += random.sample(medium, medium_picks)
        selected += random.sample(high, high_picks)
        
        explanation_parts.append("Máxima cobertura nas faixas baixa, média e alta")
    
    # Ensure we have exactly the right number of picks
    selected = sorted(list(set(selected)))[:numbers_to_pick]
    
    # Fill if we don't have enough
    while len(selected) < numbers_to_pick:
        available = [n for n in range(1, max_number + 1) if n not in selected]
        if available:
            selected.append(random.choice(available))
        else:
            break
    
    selected = sorted(selected)
    even_count = sum(1 for n in selected if n % 2 == 0)
    odd_count = numbers_to_pick - even_count
    
    explanation_parts.append(f"Pares: {even_count}, Ímpares: {odd_count}")
    
    # Check for sequential numbers and adjust if too many
    selected_sorted = sorted(selected)
    sequential_count = sum(1 for i in range(len(selected_sorted) - 1) if selected_sorted[i+1] - selected_sorted[i] == 1)
    
    if sequential_count > 2:
        explanation_parts.append("⚠️ Contém algumas sequências (pode ser ajustado)")
    
    return GeneratedBet(
        lottery_type=lottery_type,
        numbers=sorted(selected),
        strategy=strategy,
        explanation=" | ".join(explanation_parts)
    )

def get_bet_hash(lottery_type: str, numbers: List[int]) -> str:
    """Generate unique hash for a bet to prevent duplicates"""
    sorted_nums = sorted(numbers)
    key = f"{lottery_type}:{','.join(map(str, sorted_nums))}"
    return hashlib.md5(key.encode()).hexdigest()

# ===================== API ROUTES =====================

@api_router.get("/")
async def root():
    return {"message": "LottoSmart - API de Apostas Inteligentes"}

# Lottery Results
@api_router.get("/lottery/{lottery_type}/latest")
async def get_latest_result(lottery_type: str):
    """Get latest lottery result"""
    if lottery_type not in VALID_LOTTERY_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de loteria inválido. Use: {', '.join(VALID_LOTTERY_TYPES)}")
    
    data = await fetch_lottery_data(lottery_type)
    if data:
        await store_result(lottery_type, data)
        return {
            "success": True,
            "data": {
                "concurso": data.get("numero", data.get("concurso")),
                "data": data.get("dataApuracao", data.get("data")),
                "dezenas": data.get("listaDezenas", data.get("dezenas", [])),
                "dezenas_segundo_sorteio": data.get("listaDezenasSegundoSorteio", []) if lottery_type == "dupla_sena" else None,
                "acumulado": data.get("acumulado", False),
                "valor_acumulado": data.get("valorAcumuladoProximoConcurso", 0),
                "proximo_concurso": data.get("numeroConcursoProximo"),
                "data_proximo_concurso": data.get("dataProximoConcurso"),
                "valor_estimado_proximo": data.get("valorEstimadoProximoConcurso", 0)
            }
        }
    
    # Try to get from cache
    cached = await db[f"{lottery_type}_results"].find_one({}, {"_id": 0}, sort=[("concurso", -1)])
    if cached:
        return {"success": True, "data": cached, "cached": True}
    
    raise HTTPException(status_code=503, detail="Não foi possível obter os resultados")

@api_router.get("/lottery/{lottery_type}/history")
async def get_lottery_history(
    lottery_type: str,
    limit: int = Query(20, ge=1, le=100)
):
    """Get lottery result history"""
    if lottery_type not in VALID_LOTTERY_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de loteria inválido. Use: {', '.join(VALID_LOTTERY_TYPES)}")
    
    # First fetch latest to update cache
    await fetch_multiple_results(lottery_type, limit)
    
    results = await db[f"{lottery_type}_results"].find({}, {"_id": 0}).sort("concurso", -1).limit(limit).to_list(limit)
    
    return {"success": True, "data": results, "count": len(results)}

@api_router.get("/lottery/{lottery_type}/statistics")
async def get_lottery_statistics(lottery_type: str):
    """Get statistical analysis of lottery numbers"""
    if lottery_type not in VALID_LOTTERY_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de loteria inválido. Use: {', '.join(VALID_LOTTERY_TYPES)}")
    
    results = await fetch_multiple_results(lottery_type, 100)
    statistics = calculate_statistics(results, lottery_type)
    
    return {"success": True, "data": statistics.model_dump()}

@api_router.get("/lottery/{lottery_type}/next-draw")
async def get_next_draw(lottery_type: str):
    """Get information about next draw"""
    if lottery_type not in ["quina", "dupla_sena"]:
        raise HTTPException(status_code=400, detail="Tipo de loteria inválido")
    
    data = await fetch_lottery_data(lottery_type)
    if data:
        return {
            "success": True,
            "data": {
                "proximo_concurso": data.get("numeroConcursoProximo"),
                "data_proximo_concurso": data.get("dataProximoConcurso"),
                "valor_estimado": data.get("valorEstimadoProximoConcurso", 0),
                "acumulado": data.get("acumulado", False),
                "valor_acumulado": data.get("valorAcumuladoProximoConcurso", 0)
            }
        }
    
    raise HTTPException(status_code=503, detail="Não foi possível obter informações do próximo sorteio")

# Bet Generation
@api_router.post("/bets/generate")
async def generate_bets(
    lottery_type: str = Query(..., description="quina ou dupla_sena"),
    strategy: str = Query("balanced", description="hot, cold, balanced, coverage"),
    count: int = Query(1, ge=1, le=10)
):
    """Generate intelligent bets based on statistics"""
    if lottery_type not in ["quina", "dupla_sena"]:
        raise HTTPException(status_code=400, detail="Tipo de loteria inválido")
    
    if strategy not in ["hot", "cold", "balanced", "coverage"]:
        raise HTTPException(status_code=400, detail="Estratégia inválida")
    
    # Get statistics
    results = await fetch_multiple_results(lottery_type, 100)
    statistics = calculate_statistics(results, lottery_type)
    
    bets = []
    attempts = 0
    max_attempts = count * 3
    
    while len(bets) < count and attempts < max_attempts:
        bet = generate_smart_bet(statistics, lottery_type, strategy)
        bet_hash = get_bet_hash(lottery_type, bet.numbers)
        
        # Check if this exact bet already exists in generated bets
        is_duplicate = any(get_bet_hash(b.lottery_type, b.numbers) == bet_hash for b in bets)
        
        if not is_duplicate:
            bets.append(bet)
        
        attempts += 1
    
    return {
        "success": True,
        "data": [b.model_dump() for b in bets],
        "strategy_used": strategy,
        "statistics_summary": {
            "total_draws_analyzed": statistics.total_draws_analyzed,
            "top_hot_numbers": [h["number"] for h in statistics.hot_numbers[:5]],
            "top_cold_numbers": [c["number"] for c in statistics.cold_numbers[:5]]
        }
    }

# Bet Management
@api_router.post("/bets")
async def save_bet(bet: BetCreate):
    """Save a bet (prevent duplicates)"""
    if bet.lottery_type not in ["quina", "dupla_sena"]:
        raise HTTPException(status_code=400, detail="Tipo de loteria inválido")
    
    bet_hash = get_bet_hash(bet.lottery_type, bet.numbers)
    
    # Check for duplicate
    existing = await db.bets.find_one({"hash": bet_hash})
    if existing:
        raise HTTPException(status_code=409, detail="Esta aposta já existe no histórico")
    
    bet_doc = {
        "id": str(uuid.uuid4()),
        "lottery_type": bet.lottery_type,
        "numbers": sorted(bet.numbers),
        "strategy": bet.strategy,
        "explanation": bet.explanation,
        "hash": bet_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checked": False,
        "result": None
    }
    
    await db.bets.insert_one(bet_doc)
    
    # Return without _id
    if "_id" in bet_doc:
        del bet_doc["_id"]
    
    return {"success": True, "data": bet_doc}

@api_router.get("/bets")
async def get_bets(
    lottery_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """Get saved bets history"""
    query = {}
    if lottery_type:
        if lottery_type not in ["quina", "dupla_sena"]:
            raise HTTPException(status_code=400, detail="Tipo de loteria inválido")
        query["lottery_type"] = lottery_type
    
    bets = await db.bets.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"success": True, "data": bets, "count": len(bets)}

@api_router.delete("/bets/{bet_id}")
async def delete_bet(bet_id: str):
    """Delete a saved bet"""
    result = await db.bets.delete_one({"id": bet_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Aposta não encontrada")
    
    return {"success": True, "message": "Aposta removida com sucesso"}

# Bet Checking
@api_router.post("/bets/check/{bet_id}")
async def check_bet(bet_id: str, concurso: Optional[int] = None):
    """Check a bet against a specific draw result"""
    bet = await db.bets.find_one({"id": bet_id}, {"_id": 0})
    if not bet:
        raise HTTPException(status_code=404, detail="Aposta não encontrada")
    
    lottery_type = bet["lottery_type"]
    
    # Get result for the specified or latest concurso
    if concurso:
        data = await fetch_lottery_data(lottery_type, concurso)
    else:
        data = await fetch_lottery_data(lottery_type)
    
    if not data:
        raise HTTPException(status_code=503, detail="Não foi possível obter o resultado")
    
    drawn_numbers = [int(d) for d in data.get("listaDezenas", data.get("dezenas", []))]
    bet_numbers = bet["numbers"]
    
    matches = [n for n in bet_numbers if n in drawn_numbers]
    match_count = len(matches)
    
    # Determine prize tier
    prize_tier = None
    is_winner = False
    
    if lottery_type == "quina":
        if match_count == 5:
            prize_tier = "Quina (5 acertos)"
            is_winner = True
        elif match_count == 4:
            prize_tier = "Quadra (4 acertos)"
            is_winner = True
        elif match_count == 3:
            prize_tier = "Terno (3 acertos)"
            is_winner = True
        elif match_count == 2:
            prize_tier = "Duque (2 acertos)"
            is_winner = True
    else:  # dupla_sena
        if match_count == 6:
            prize_tier = "Sena (6 acertos)"
            is_winner = True
        elif match_count == 5:
            prize_tier = "Quina (5 acertos)"
            is_winner = True
        elif match_count == 4:
            prize_tier = "Quadra (4 acertos)"
            is_winner = True
        elif match_count == 3:
            prize_tier = "Terno (3 acertos)"
            is_winner = True
    
    result = {
        "concurso": data.get("numero", data.get("concurso")),
        "data": data.get("dataApuracao", data.get("data")),
        "drawn_numbers": drawn_numbers,
        "matches": matches,
        "match_count": match_count,
        "prize_tier": prize_tier,
        "is_winner": is_winner,
        "checked_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Update bet with result
    await db.bets.update_one(
        {"id": bet_id},
        {"$set": {"checked": True, "result": result}}
    )
    
    return {
        "success": True,
        "data": BetCheckResult(
            bet_id=bet_id,
            lottery_type=lottery_type,
            numbers=bet_numbers,
            concurso=result["concurso"],
            drawn_numbers=drawn_numbers,
            matches=matches,
            match_count=match_count,
            prize_tier=prize_tier,
            is_winner=is_winner
        ).model_dump()
    }

@api_router.post("/bets/check-all")
async def check_all_bets(lottery_type: Optional[str] = None):
    """Check all unchecked bets against latest results"""
    query = {"checked": False}
    if lottery_type:
        query["lottery_type"] = lottery_type
    
    unchecked_bets = await db.bets.find(query, {"_id": 0}).to_list(100)
    
    results = []
    for bet in unchecked_bets:
        try:
            # Get latest result for this lottery type
            data = await fetch_lottery_data(bet["lottery_type"])
            if data:
                drawn_numbers = [int(d) for d in data.get("listaDezenas", data.get("dezenas", []))]
                matches = [n for n in bet["numbers"] if n in drawn_numbers]
                
                result = {
                    "bet_id": bet["id"],
                    "concurso": data.get("numero", data.get("concurso")),
                    "matches": matches,
                    "match_count": len(matches)
                }
                results.append(result)
                
                # Update bet
                await db.bets.update_one(
                    {"id": bet["id"]},
                    {"$set": {"checked": True, "result": result}}
                )
        except Exception as e:
            logger.error(f"Error checking bet {bet['id']}: {e}")
    
    return {"success": True, "data": results, "checked_count": len(results)}

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
