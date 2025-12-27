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

# Lottery configurations with prize tiers
LOTTERY_CONFIG = {
    "quina": {
        "max_number": 80, 
        "numbers_to_pick": 5, 
        "api_name": "quina",
        "prize_tiers": {5: "Quina", 4: "Quadra", 3: "Terno", 2: "Duque"},
        "min_prize": 2
    },
    "dupla_sena": {
        "max_number": 50, 
        "numbers_to_pick": 6, 
        "api_name": "duplasena",
        "prize_tiers": {6: "Sena", 5: "Quina", 4: "Quadra", 3: "Terno"},
        "min_prize": 3
    },
    "lotofacil": {
        "max_number": 25, 
        "numbers_to_pick": 15, 
        "api_name": "lotofacil",
        "prize_tiers": {15: "15 acertos", 14: "14 acertos", 13: "13 acertos", 12: "12 acertos", 11: "11 acertos"},
        "min_prize": 11
    },
    "megasena": {
        "max_number": 60, 
        "numbers_to_pick": 6, 
        "api_name": "megasena",
        "prize_tiers": {6: "Sena", 5: "Quina", 4: "Quadra"},
        "min_prize": 4
    }
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

def analyze_winning_patterns(results: List[Dict], lottery_type: str) -> Dict:
    """Analyze patterns from winning combinations"""
    config = LOTTERY_CONFIG.get(lottery_type, {})
    max_number = config.get("max_number", 60)
    numbers_to_pick = config.get("numbers_to_pick", 6)
    
    patterns = {
        "even_odd_patterns": [],  # Distribution of even/odd in winning combos
        "range_patterns": [],      # Distribution across ranges
        "sum_patterns": [],        # Sum of winning numbers
        "consecutive_patterns": [], # Number of consecutive pairs
        "decade_patterns": [],     # Distribution by decade
        "repeat_from_last": [],    # Numbers that repeat from previous draw
    }
    
    prev_dezenas = None
    for result in results[:50]:  # Analyze last 50 draws
        dezenas = result.get("dezenas", result.get("listaDezenas", []))
        nums = sorted([int(d) for d in dezenas])
        
        if len(nums) != numbers_to_pick:
            continue
        
        # Even/Odd pattern
        even = sum(1 for n in nums if n % 2 == 0)
        patterns["even_odd_patterns"].append(even)
        
        # Range pattern (low/medium/high)
        third = max_number // 3
        low = sum(1 for n in nums if n <= third)
        med = sum(1 for n in nums if third < n <= 2 * third)
        high = sum(1 for n in nums if n > 2 * third)
        patterns["range_patterns"].append((low, med, high))
        
        # Sum pattern
        patterns["sum_patterns"].append(sum(nums))
        
        # Consecutive pattern
        consecutive = sum(1 for i in range(len(nums) - 1) if nums[i+1] - nums[i] == 1)
        patterns["consecutive_patterns"].append(consecutive)
        
        # Decade pattern
        decades = {}
        for n in nums:
            decade = (n - 1) // 10
            decades[decade] = decades.get(decade, 0) + 1
        patterns["decade_patterns"].append(decades)
        
        # Repeat from last
        if prev_dezenas:
            prev_nums = set(int(d) for d in prev_dezenas)
            repeats = sum(1 for n in nums if n in prev_nums)
            patterns["repeat_from_last"].append(repeats)
        
        prev_dezenas = dezenas
    
    # Calculate optimal ranges
    analysis = {}
    
    if patterns["even_odd_patterns"]:
        avg_even = sum(patterns["even_odd_patterns"]) / len(patterns["even_odd_patterns"])
        analysis["optimal_even"] = round(avg_even)
        analysis["optimal_odd"] = numbers_to_pick - round(avg_even)
    
    if patterns["sum_patterns"]:
        sums = patterns["sum_patterns"]
        analysis["optimal_sum_min"] = int(sum(sums) / len(sums) * 0.85)
        analysis["optimal_sum_max"] = int(sum(sums) / len(sums) * 1.15)
    
    if patterns["consecutive_patterns"]:
        analysis["avg_consecutive"] = sum(patterns["consecutive_patterns"]) / len(patterns["consecutive_patterns"])
    
    if patterns["range_patterns"]:
        avg_low = sum(p[0] for p in patterns["range_patterns"]) / len(patterns["range_patterns"])
        avg_med = sum(p[1] for p in patterns["range_patterns"]) / len(patterns["range_patterns"])
        avg_high = sum(p[2] for p in patterns["range_patterns"]) / len(patterns["range_patterns"])
        analysis["optimal_range"] = (round(avg_low), round(avg_med), round(avg_high))
    
    if patterns["repeat_from_last"]:
        analysis["avg_repeats"] = sum(patterns["repeat_from_last"]) / len(patterns["repeat_from_last"])
    
    return analysis

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

def generate_smart_bet(statistics: Statistics, lottery_type: str, strategy: str = "balanced", pattern_analysis: Dict = None) -> GeneratedBet:
    """Generate intelligent bet based on statistics and pattern analysis"""
    config = LOTTERY_CONFIG.get(lottery_type, {"max_number": 60, "numbers_to_pick": 6})
    max_number = config["max_number"]
    numbers_to_pick = config["numbers_to_pick"]
    
    hot_nums = [h["number"] for h in statistics.hot_numbers]
    cold_nums = [c["number"] for c in statistics.cold_numbers]
    delayed_nums = [d["number"] for d in statistics.delayed_numbers if isinstance(d["draws_since"], int)]
    
    # Get pattern-based optimal values
    optimal_even = pattern_analysis.get("optimal_even", numbers_to_pick // 2) if pattern_analysis else numbers_to_pick // 2
    optimal_odd = numbers_to_pick - optimal_even
    optimal_range = pattern_analysis.get("optimal_range", (numbers_to_pick // 3, numbers_to_pick // 3, numbers_to_pick // 3)) if pattern_analysis else None
    sum_min = pattern_analysis.get("optimal_sum_min", 0) if pattern_analysis else 0
    sum_max = pattern_analysis.get("optimal_sum_max", max_number * numbers_to_pick) if pattern_analysis else max_number * numbers_to_pick
    
    selected = []
    explanation_parts = []
    
    # Calculate ranges
    third = max_number // 3
    low_range = list(range(1, third + 1))
    mid_range = list(range(third + 1, 2 * third + 1))
    high_range = list(range(2 * third + 1, max_number + 1))
    
    def validate_bet(nums):
        """Validate bet against optimal patterns"""
        if len(nums) != numbers_to_pick:
            return False
        nums = sorted(nums)
        
        # Check sum range (with tolerance)
        total = sum(nums)
        if sum_min > 0 and sum_max > 0:
            if total < sum_min * 0.8 or total > sum_max * 1.2:
                return False
        
        # Check even/odd balance (with tolerance of 1)
        even = sum(1 for n in nums if n % 2 == 0)
        if abs(even - optimal_even) > 2:
            return False
        
        return True
    
    def generate_with_patterns():
        """Generate numbers following winning patterns"""
        result = []
        
        # Start with weighted selection from hot numbers (they appear more often)
        hot_weight = hot_nums[:10] if hot_nums else []
        
        # Distribute across ranges based on optimal_range
        if optimal_range:
            target_low, target_mid, target_high = optimal_range
        else:
            target_low = target_mid = target_high = numbers_to_pick // 3
        
        # Adjust for rounding
        remainder = numbers_to_pick - target_low - target_mid - target_high
        if remainder > 0:
            target_mid += remainder
        
        # Select from low range, preferring hot numbers
        low_hot = [n for n in hot_weight if n in low_range]
        low_other = [n for n in low_range if n not in low_hot]
        low_pool = low_hot + low_other
        if low_pool and target_low > 0:
            result.extend(random.sample(low_pool, min(target_low, len(low_pool))))
        
        # Select from mid range
        mid_hot = [n for n in hot_weight if n in mid_range]
        mid_other = [n for n in mid_range if n not in mid_hot]
        mid_pool = mid_hot + mid_other
        if mid_pool and target_mid > 0:
            available = [n for n in mid_pool if n not in result]
            result.extend(random.sample(available, min(target_mid, len(available))))
        
        # Select from high range
        high_hot = [n for n in hot_weight if n in high_range]
        high_other = [n for n in high_range if n not in high_hot]
        high_pool = high_hot + high_other
        if high_pool and target_high > 0:
            available = [n for n in high_pool if n not in result]
            result.extend(random.sample(available, min(target_high, len(available))))
        
        # Fill remaining if needed
        while len(result) < numbers_to_pick:
            available = [n for n in range(1, max_number + 1) if n not in result]
            if not available:
                break
            # Prefer hot numbers for filling
            hot_available = [n for n in hot_weight if n in available]
            if hot_available:
                result.append(random.choice(hot_available))
            else:
                result.append(random.choice(available))
        
        # Balance even/odd
        result = sorted(result)[:numbers_to_pick]
        even_count = sum(1 for n in result if n % 2 == 0)
        
        # Try to adjust even/odd balance
        attempts = 0
        while abs(even_count - optimal_even) > 1 and attempts < 10:
            if even_count > optimal_even:
                # Replace an even with an odd
                evens = [n for n in result if n % 2 == 0]
                odds_available = [n for n in range(1, max_number + 1) if n % 2 == 1 and n not in result]
                if evens and odds_available:
                    result.remove(random.choice(evens))
                    # Prefer hot odd numbers
                    hot_odds = [n for n in odds_available if n in hot_weight]
                    result.append(random.choice(hot_odds) if hot_odds else random.choice(odds_available))
            else:
                # Replace an odd with an even
                odds = [n for n in result if n % 2 == 1]
                evens_available = [n for n in range(1, max_number + 1) if n % 2 == 0 and n not in result]
                if odds and evens_available:
                    result.remove(random.choice(odds))
                    hot_evens = [n for n in evens_available if n in hot_weight]
                    result.append(random.choice(hot_evens) if hot_evens else random.choice(evens_available))
            
            even_count = sum(1 for n in result if n % 2 == 0)
            attempts += 1
        
        return sorted(result)[:numbers_to_pick]
    
    if strategy == "smart":
        # New: Pattern-based intelligent generation
        best_bet = None
        best_score = -1
        
        for _ in range(50):  # Try multiple times to find best bet
            candidate = generate_with_patterns()
            if validate_bet(candidate):
                # Score based on hot number presence
                score = sum(1 for n in candidate if n in hot_nums[:10])
                if score > best_score:
                    best_score = score
                    best_bet = candidate
        
        selected = best_bet if best_bet else generate_with_patterns()
        explanation_parts.append(f"Análise de padrões vencedores | {sum(1 for n in selected if n in hot_nums[:10])} números quentes")
        
    elif strategy == "hot":
        # Focus on hot numbers with pattern validation
        for _ in range(20):
            pool = hot_nums[:15] + random.sample(range(1, max_number + 1), max_number // 4)
            pool = list(set(pool))
            candidate = random.sample(pool, min(numbers_to_pick, len(pool)))
            if validate_bet(candidate):
                selected = candidate
                break
        if not selected:
            selected = random.sample(hot_nums[:20] if len(hot_nums) >= 20 else list(range(1, max_number + 1)), numbers_to_pick)
        explanation_parts.append(f"Foco em números quentes | {sum(1 for n in selected if n in hot_nums[:10])} top 10")
        
    elif strategy == "cold":
        # Focus on cold/delayed numbers (these may be "due")
        pool = cold_nums + delayed_nums
        pool = list(set(pool))
        if len(pool) < numbers_to_pick:
            pool = pool + [n for n in range(1, max_number + 1) if n not in pool]
        
        for _ in range(20):
            candidate = random.sample(pool[:max(30, numbers_to_pick + 10)], min(numbers_to_pick, len(pool)))
            if validate_bet(candidate):
                selected = candidate
                break
        if not selected:
            selected = random.sample(pool, min(numbers_to_pick, len(pool)))
        explanation_parts.append(f"Números frios/atrasados | Soma: {sum(selected)}")
        
    elif strategy == "balanced":
        # Mix with pattern optimization
        for _ in range(30):
            candidate = generate_with_patterns()
            if validate_bet(candidate):
                selected = candidate
                break
        if not selected:
            selected = generate_with_patterns()
        
        hot_count = sum(1 for n in selected if n in hot_nums[:10])
        cold_count = sum(1 for n in selected if n in cold_nums[:10])
        explanation_parts.append(f"Equilibrado | {hot_count} quentes, {cold_count} frios")
        
    elif strategy == "coverage":
        # Maximum coverage with pattern validation
        for _ in range(20):
            low_picks = min(optimal_range[0] if optimal_range else numbers_to_pick // 3, len(low_range))
            mid_picks = min(optimal_range[1] if optimal_range else numbers_to_pick // 3, len(mid_range))
            high_picks = numbers_to_pick - low_picks - mid_picks
            
            candidate = []
            if low_picks > 0:
                candidate.extend(random.sample(low_range, low_picks))
            if mid_picks > 0:
                candidate.extend(random.sample(mid_range, mid_picks))
            if high_picks > 0 and len(high_range) >= high_picks:
                candidate.extend(random.sample(high_range, high_picks))
            
            # Fill if needed
            while len(candidate) < numbers_to_pick:
                available = [n for n in range(1, max_number + 1) if n not in candidate]
                candidate.append(random.choice(available))
            
            if validate_bet(candidate):
                selected = candidate
                break
        
        if not selected:
            selected = generate_with_patterns()
        
        low_c = sum(1 for n in selected if n <= third)
        mid_c = sum(1 for n in selected if third < n <= 2 * third)
        high_c = sum(1 for n in selected if n > 2 * third)
        explanation_parts.append(f"Cobertura: {low_c} baixos, {mid_c} médios, {high_c} altos")
    
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
    
    explanation_parts.append(f"Pares: {even_count}, Ímpares: {odd_count} | Soma: {sum(selected)}")
    
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
    if lottery_type not in VALID_LOTTERY_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de loteria inválido. Use: {', '.join(VALID_LOTTERY_TYPES)}")
    
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
    lottery_type: str = Query(..., description="quina, dupla_sena, lotofacil, megasena"),
    strategy: str = Query("smart", description="smart, hot, cold, balanced, coverage"),
    count: int = Query(1, ge=1, le=10)
):
    """Generate intelligent bets based on statistics and pattern analysis"""
    if lottery_type not in VALID_LOTTERY_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de loteria inválido. Use: {', '.join(VALID_LOTTERY_TYPES)}")
    
    if strategy not in ["smart", "hot", "cold", "balanced", "coverage"]:
        raise HTTPException(status_code=400, detail="Estratégia inválida. Use: smart, hot, cold, balanced, coverage")
    
    # Get statistics and pattern analysis
    results = await fetch_multiple_results(lottery_type, 100)
    statistics = calculate_statistics(results, lottery_type)
    pattern_analysis = analyze_winning_patterns(results, lottery_type)
    
    bets = []
    attempts = 0
    max_attempts = count * 5
    
    while len(bets) < count and attempts < max_attempts:
        bet = generate_smart_bet(statistics, lottery_type, strategy, pattern_analysis)
        bet_hash = get_bet_hash(lottery_type, bet.numbers)
        
        # Check if this exact bet already exists in generated bets
        is_duplicate = any(get_bet_hash(b.lottery_type, b.numbers) == bet_hash for b in bets)
        
        if not is_duplicate:
            bets.append(bet)
        
        attempts += 1
    
    config = LOTTERY_CONFIG.get(lottery_type, {})
    
    return {
        "success": True,
        "data": [b.model_dump() for b in bets],
        "strategy_used": strategy,
        "statistics_summary": {
            "total_draws_analyzed": statistics.total_draws_analyzed,
            "top_hot_numbers": [h["number"] for h in statistics.hot_numbers[:5]],
            "top_cold_numbers": [c["number"] for c in statistics.cold_numbers[:5]]
        },
        "pattern_analysis": {
            "optimal_even_odd": f"{pattern_analysis.get('optimal_even', '?')}/{pattern_analysis.get('optimal_odd', '?')}",
            "optimal_sum_range": f"{pattern_analysis.get('optimal_sum_min', 0)} - {pattern_analysis.get('optimal_sum_max', 0)}",
            "optimal_range_distribution": pattern_analysis.get('optimal_range', None)
        },
        "prize_info": {
            "min_matches_to_win": config.get("min_prize", 0),
            "prize_tiers": config.get("prize_tiers", {})
        }
    }

# Bet Management
@api_router.post("/bets")
async def save_bet(bet: BetCreate):
    """Save a bet (prevent duplicates)"""
    if bet.lottery_type not in VALID_LOTTERY_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de loteria inválido. Use: {', '.join(VALID_LOTTERY_TYPES)}")
    
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
        if lottery_type not in VALID_LOTTERY_TYPES:
            raise HTTPException(status_code=400, detail=f"Tipo de loteria inválido. Use: {', '.join(VALID_LOTTERY_TYPES)}")
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

@api_router.delete("/bets")
async def delete_all_bets(lottery_type: Optional[str] = None):
    """Delete all bets (optionally filtered by lottery type)"""
    query = {}
    if lottery_type:
        if lottery_type not in VALID_LOTTERY_TYPES:
            raise HTTPException(status_code=400, detail=f"Tipo de loteria inválido. Use: {', '.join(VALID_LOTTERY_TYPES)}")
        query["lottery_type"] = lottery_type
    
    result = await db.bets.delete_many(query)
    
    return {
        "success": True, 
        "message": f"{result.deleted_count} aposta(s) removida(s) com sucesso",
        "deleted_count": result.deleted_count
    }

# Bet Checking
def get_prize_value_from_result(data: Dict, lottery_type: str, match_count: int) -> Optional[float]:
    """Extract prize value from API result based on match count"""
    try:
        # Different lotteries have different prize structures in the API
        premiacoes = data.get("listaRateioPremio", [])
        
        if lottery_type == "megasena":
            tier_map = {6: 0, 5: 1, 4: 2}  # Index in premiacoes list
        elif lottery_type == "lotofacil":
            tier_map = {15: 0, 14: 1, 13: 2, 12: 3, 11: 4}
        elif lottery_type == "quina":
            tier_map = {5: 0, 4: 1, 3: 2, 2: 3}
        elif lottery_type == "dupla_sena":
            tier_map = {6: 0, 5: 1, 4: 2, 3: 3}
        else:
            return None
        
        if match_count in tier_map:
            idx = tier_map[match_count]
            if idx < len(premiacoes):
                return premiacoes[idx].get("valorPremio", 0)
    except Exception:
        pass
    return None

@api_router.post("/bets/check/{bet_id}")
async def check_bet(bet_id: str, concurso: Optional[int] = None):
    """Check a bet against a specific draw result"""
    bet = await db.bets.find_one({"id": bet_id}, {"_id": 0})
    if not bet:
        raise HTTPException(status_code=404, detail="Aposta não encontrada")
    
    lottery_type = bet["lottery_type"]
    config = LOTTERY_CONFIG.get(lottery_type, {})
    min_prize = config.get("min_prize", 0)
    prize_tiers = config.get("prize_tiers", {})
    
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
    
    # Check second draw for Dupla Sena
    matches_second = []
    if lottery_type == "dupla_sena":
        drawn_second = [int(d) for d in data.get("listaDezenasSegundoSorteio", [])]
        matches_second = [n for n in bet_numbers if n in drawn_second]
    
    # Determine prize tier and value
    prize_tier = None
    prize_value = None
    is_winner = False
    
    if match_count >= min_prize:
        is_winner = True
        prize_tier = prize_tiers.get(match_count, f"{match_count} acertos")
        prize_value = get_prize_value_from_result(data, lottery_type, match_count)
    
    # For Dupla Sena, check if second draw is better
    if lottery_type == "dupla_sena" and len(matches_second) >= min_prize:
        if len(matches_second) > match_count:
            matches = matches_second
            match_count = len(matches_second)
            is_winner = True
            prize_tier = prize_tiers.get(match_count, f"{match_count} acertos") + " (2º sorteio)"
    
    result = {
        "concurso": data.get("numero", data.get("concurso")),
        "data": data.get("dataApuracao", data.get("data")),
        "drawn_numbers": drawn_numbers,
        "drawn_numbers_second": [int(d) for d in data.get("listaDezenasSegundoSorteio", [])] if lottery_type == "dupla_sena" else None,
        "matches": matches,
        "match_count": match_count,
        "prize_tier": prize_tier,
        "prize_value": prize_value,
        "is_winner": is_winner,
        "min_to_win": min_prize,
        "checked_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Update bet with result
    await db.bets.update_one(
        {"id": bet_id},
        {"$set": {"checked": True, "result": result}}
    )
    
    return {
        "success": True,
        "data": {
            "bet_id": bet_id,
            "lottery_type": lottery_type,
            "numbers": bet_numbers,
            "concurso": result["concurso"],
            "drawn_numbers": drawn_numbers,
            "matches": matches,
            "match_count": match_count,
            "prize_tier": prize_tier,
            "prize_value": prize_value,
            "is_winner": is_winner,
            "min_to_win": min_prize
        }
    }

@api_router.post("/bets/check-all")
async def check_all_bets(lottery_type: Optional[str] = None):
    """Check all unchecked bets against latest results"""
    query = {"checked": False}
    if lottery_type:
        query["lottery_type"] = lottery_type
    
    unchecked_bets = await db.bets.find(query, {"_id": 0}).to_list(100)
    
    results = []
    winners = 0
    total_prize = 0
    
    for bet in unchecked_bets:
        try:
            lt = bet["lottery_type"]
            config = LOTTERY_CONFIG.get(lt, {})
            min_prize = config.get("min_prize", 0)
            prize_tiers = config.get("prize_tiers", {})
            
            # Get latest result for this lottery type
            data = await fetch_lottery_data(lt)
            if data:
                drawn_numbers = [int(d) for d in data.get("listaDezenas", data.get("dezenas", []))]
                matches = [n for n in bet["numbers"] if n in drawn_numbers]
                match_count = len(matches)
                
                is_winner = match_count >= min_prize
                prize_tier = prize_tiers.get(match_count, f"{match_count} acertos") if is_winner else None
                prize_value = get_prize_value_from_result(data, lt, match_count) if is_winner else None
                
                result = {
                    "bet_id": bet["id"],
                    "lottery_type": lt,
                    "concurso": data.get("numero", data.get("concurso")),
                    "matches": matches,
                    "match_count": match_count,
                    "is_winner": is_winner,
                    "prize_tier": prize_tier,
                    "prize_value": prize_value,
                    "min_to_win": min_prize
                }
                results.append(result)
                
                if is_winner:
                    winners += 1
                    if prize_value:
                        total_prize += prize_value
                
                # Update bet
                await db.bets.update_one(
                    {"id": bet["id"]},
                    {"$set": {"checked": True, "result": result}}
                )
        except Exception as e:
            logger.error(f"Error checking bet {bet['id']}: {e}")
    
    return {
        "success": True, 
        "data": results, 
        "checked_count": len(results),
        "winners_count": winners,
        "total_prize_value": total_prize
    }

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
