# LottoSmart - Sistema de Apostas Inteligentes para Loterias Brasileiras

## Problema Original
Criar uma aplicação de apostas inteligentes para loterias brasileiras, com:
- Análise estatística (números quentes, frios, atrasados)
- Geração de apostas baseadas em critérios de combinação
- Histórico de jogos sem duplicatas
- Data do próximo sorteio e premiação
- Conferência automática de resultados

## Loterias Suportadas
1. **Mega-Sena** - 6 números de 01 a 60
2. **Lotofácil** - 15 números de 01 a 25
3. **Quina** - 5 números de 01 a 80
4. **Dupla Sena** - 6 números de 01 a 50 (2 sorteios)

## Escolhas do Usuário
1. Integração com API da Caixa para dados históricos
2. Sem autenticação (uso local)
3. Histórico compartilhado
4. Conferência automática de resultados
5. Design: Dark Luxury Theme

## Tarefas Concluídas

### Backend
- [x] Integração com API Caixa (4 loterias)
- [x] Configuração dinâmica por loteria (LOTTERY_CONFIG)
- [x] Cálculo de estatísticas (hot/cold/delayed numbers)
- [x] Geração de apostas com 4 estratégias
- [x] Salvamento de apostas no MongoDB (sem duplicatas)
- [x] Conferência de apostas contra resultados
- [x] Cache de resultados no MongoDB

### Frontend
- [x] Dashboard com 4 loterias
- [x] Página Mega-Sena
- [x] Página Lotofácil
- [x] Página Quina
- [x] Página Dupla Sena
- [x] Página Histórico (filtro por loteria)
- [x] Página Estatísticas (tabs para todas)
- [x] Design Dark Luxury com glassmorphism
- [x] Responsividade mobile

### Endpoints da API
- GET /api/lottery/{type}/latest
- GET /api/lottery/{type}/history
- GET /api/lottery/{type}/statistics
- GET /api/lottery/{type}/next-draw
- POST /api/bets/generate
- POST /api/bets
- GET /api/bets
- POST /api/bets/check/{id}
- DELETE /api/bets/{id}

## Próximas Tarefas Sugeridas
1. Filtro por período nas estatísticas
2. Análise de sequências e padrões numéricos
3. Histórico de ganhos/perdas acumulados
4. Exportar apostas para imagem/PDF

## Tecnologias
- Backend: FastAPI, Motor, httpx, Pydantic
- Frontend: React 19, Tailwind CSS, Shadcn/UI, Recharts
- Database: MongoDB
