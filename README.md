# Computador Ofertas Bot

Bot automatizado que busca ofertas de hardware de computador em múltiplas plataformas e envia via Telegram e WhatsApp.

## Plataformas Suportadas

| Ativo por padrão | Plataforma | Tipo |
|---|---|---|
| Sim | Mercado Livre | Marketplace |
| Sim | Shopee | Marketplace (API Afiliados) |
| Sim | Kabum | Loja especializada |
| Sim | Pichau | Loja especializada |
| Sim | Terabyte | Loja especializada |
| Sim | Amazon BR | Marketplace |
| Sim | Magazine Luiza | Marketplace |
| Sim | Zoom | Comparador de preços |
| Sim | Buscapé | Comparador de preços |
| Não | Amazon US | Internacional |
| Não | AliExpress | Internacional |
| Não | Newegg | Internacional |

## Score Inteligente

Cada oferta é avaliada por um sistema de 3 pilares:

1. **Histórico (40%)** - compara o preço atual com o histórico do produto
2. **Contexto (30%)** - desconto declarado, frete, parcelamento, cupom
3. **Qualidade (30%)** - regras anti-fake discount, confiabilidade da plataforma

Classificação: ⭐ Excelente (≥80) → 👍 Boa (60-79) → ➖ Média (40-59) → 👎 Fraca (<40)

## Configuração

1. Copie `.env.example` para `.env` e preencha as credenciais
2. Ajuste `config/platforms.toml` para ligar/desligar plataformas
3. Execute: `python src/main.py`

## GitHub Actions

O bot roda automaticamente a cada 3 horas via GitHub Actions.
Logs completos são salvos como artifact para debug.

## Estrutura de Logs

Cada execução gera em `logs/run_<id>/`:
- `bot.json` - log completo estruturado (JSON)
- `errors.json` - apenas WARNING+ (debug rápido)
- `summary.json` - resumo executivo da execução
