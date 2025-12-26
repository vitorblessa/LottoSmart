# LottoSmart - Sistema de Apostas Inteligentes para Quina e Dupla Sena

## Problema Original
Criar uma aplicação de apostas inteligentes para Quina e Dupla Sena, com:
- Análise estatística (números quentes, frios, atrasados)
- Geração de apostas baseadas em critérios de combinação
- Histórico de jogos sem duplicatas
- Data do próximo sorteio e premiação
- Conferência automática de resultados

## Escolhas do Usuário
1. Integração com API da Caixa para dados históricos
2. Sem autenticação (uso local)
3. Histórico compartilhado
4. Conferência automática de resultados
5. Design: Dark Luxury Theme

## Tarefas Concluídas

### Backend
- [x] Integração com API Caixa (quina e dupla_sena)
- [x] Cálculo de estatísticas (hot/cold/delayed numbers)
- [x] Geração de apostas com 4 estratégias (hot, cold, balanced, coverage)
- [x] Salvamento de apostas no MongoDB (com prevenção de duplicatas via hash)
- [x] Conferência de apostas contra resultados
- [x] Cache de resultados no MongoDB

### Frontend
- [x] Dashboard com próximos sorteios e resultados
- [x] Página Quina com gerador de apostas
- [x] Página Dupla Sena com gerador de apostas
- [x] Página Histórico com listagem e conferência
- [x] Página Estatísticas com gráficos (Recharts)
- [x] Design Dark Luxury com glassmorphism
- [x] Componentes de bolas de loteria estilizados
- [x] Responsividade mobile

### Endpoints da API
- GET /api/lottery/{type}/latest - Último resultado
- GET /api/lottery/{type}/history - Histórico de resultados
- GET /api/lottery/{type}/statistics - Análise estatística
- GET /api/lottery/{type}/next-draw - Próximo sorteio
- POST /api/bets/generate - Gerar apostas
- POST /api/bets - Salvar aposta
- GET /api/bets - Listar apostas
- POST /api/bets/check/{id} - Conferir aposta
- DELETE /api/bets/{id} - Excluir aposta

## Próximas Tarefas Sugeridas

### Melhorias de Funcionalidade
1. Filtro por período nas estatísticas (últimos 30, 60, 90 dias)
2. Análise de sequências e padrões numéricos
3. Histórico de ganhos/perdas acumulados
4. Modo offline com dados em cache local

### Melhorias de UX
1. Exportar apostas para imagem/PDF compartilhável
2. Animações nas bolas sorteadas
3. Tooltips explicativos nos gráficos
4. Dark/Light mode toggle (opcional)

### Integrações Futuras
1. Notificações push de resultados (PWA)
2. Compartilhamento em redes sociais
3. Integração com calendário para lembrar sorteios

## Tecnologias Utilizadas
- Backend: FastAPI, Motor (async MongoDB), httpx, Pydantic
- Frontend: React 19, Tailwind CSS, Shadcn/UI, Recharts, Lucide Icons
- Database: MongoDB
- Fonts: Outfit, Manrope, JetBrains Mono
