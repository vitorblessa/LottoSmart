# LottoSmart - Sistema de Apostas Inteligentes para Quina e Dupla Sena

## Visão Geral
Aplicação web full-stack para geração de apostas inteligentes baseadas em análise estatística dos resultados históricos da Quina e Dupla Sena (loterias brasileiras da Caixa Econômica Federal).

## Arquitetura

### Backend (FastAPI + MongoDB)
- **server.py**: API REST com endpoints para:
  - Buscar resultados das loterias (API Caixa)
  - Calcular estatísticas (números quentes/frios/atrasados)
  - Gerar apostas inteligentes com estratégias
  - Gerenciar histórico de apostas (sem duplicatas)
  - Conferir apostas contra resultados

### Frontend (React + Tailwind + Shadcn/UI)
- **Dashboard**: Visão geral com próximos sorteios e resultados recentes
- **QuinaPage**: Geração de apostas para Quina
- **DuplaSenaPage**: Geração de apostas para Dupla Sena
- **HistoryPage**: Histórico de apostas salvas com conferência
- **StatisticsPage**: Análise estatística com gráficos

## Funcionalidades Implementadas

### ✅ Análise Estatística
- Números quentes (mais frequentes)
- Números frios (menos frequentes)
- Números atrasados (tempo sem sair)
- Distribuição par/ímpar
- Distribuição por faixas (baixa/média/alta)

### ✅ Geração de Apostas
- **Estratégia Hot**: Foco em números mais sorteados
- **Estratégia Cold**: Foco em números menos sorteados
- **Estratégia Balanced**: Mix equilibrado
- **Estratégia Coverage**: Cobertura máxima de faixas

### ✅ Gestão de Histórico
- Salvamento de apostas
- Prevenção de duplicatas (hash MD5)
- Conferência automática contra resultados
- Exclusão de apostas

### ✅ Integração com API Caixa
- Resultados em tempo real
- Informações do próximo sorteio
- Data e prêmio estimado

## Stack Tecnológica
- **Backend**: FastAPI, Motor (async MongoDB), httpx
- **Frontend**: React 19, Tailwind CSS, Shadcn/UI, Recharts
- **Database**: MongoDB
- **Design**: Dark Luxury Theme (Neon-Noir)

## Tarefas Concluídas
1. ✅ Integração com API da Caixa Econômica Federal
2. ✅ Sistema de análise estatística completo
3. ✅ Gerador de apostas com 4 estratégias
4. ✅ Histórico de apostas sem duplicatas
5. ✅ Conferência automática de resultados
6. ✅ Interface Dark Luxury com glassmorphism
7. ✅ Gráficos de frequência e distribuição
8. ✅ Responsividade mobile

## Próximas Tarefas Sugeridas
1. Adicionar filtro por período nas estatísticas
2. Exportar apostas para PDF/imagem
3. Notificações de sorteio (opcional)
4. Modo offline com dados em cache
5. Análise de padrões de sequências
