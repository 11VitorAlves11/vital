# seed/ — catálogos clínicos

Catálogos partilhados entre utilizadores, carregados na base de dados no arranque
(`biomarkers` e `body_metrics`). Editar aqui, nunca directamente na BD.

## Ficheiros

| Ficheiro | Tabela | Conteúdo |
|---|---|---|
| `biomarkers.json` | `biomarkers` | Catálogo de biomarcadores + intervalos canónicos por sexo + aliases PT-PT |
| `body_metrics.json` | `body_metrics` | Métricas de composição corporal + bandas clínicas (ou trend-only) |

## Convenções

- **`slug`** é a chave estável (`UNIQUE`); `name` e `aliases` são texto apresentável
  e podem mudar sem migração de dados.
- **`aliases`** lista as designações usadas pelos laboratórios portugueses para o mesmo
  biomarcador. Alimenta o matching da extração LLM (case-insensitive, sem acentos).
  Todo o português é **PT-PT**.
- **Intervalos canónicos** (`ref_min_*` / `ref_max_*`) são apenas *fallback*: a fonte
  primária é o intervalo que o próprio laboratório reporta em `results.ref_min/ref_max`,
  porque varia entre laboratórios. `null` = limite não aplicável.
- **Bandas** (`bands_m` / `bands_f`) são intervalos **`[min, max)`** — `min` inclusivo,
  `max` exclusivo, `null` = sem limite desse lado. As bandas de cada sexo cobrem todo o
  domínio sem sobreposições nem lacunas. `flag` ∈ `normal` | `warn` | `alert`, ou `null`.
- **`flag` a `null` = a escala nomeia sem classificar.** Dá nome ao valor («Atleta»,
  «Aceitável») e não emite veredicto — é o caso das categorias do ACE/ACSM, que são de
  aptidão física e não clínicas. Dentro de uma métrica, as bandas ou classificam todas
  ou nenhuma: meio a meio deixaria o leitor sem saber distinguir uma coisa da outra.
- **`bands` a `null` = métrica trend-only**: registada e visualizada em tendência, sem
  flag. Só existe flag onde há standard clínico validado — aplicar "standards" inventados
  a estimativas de bioimpedância seria pseudo-precisão.
- **`source`** identifica a proveniência do standard (OMS, ACE/ACSM, IDF), para auditoria.
- **`trend_reason`** é a razão, numa linha, de a métrica não emitir veredicto — obrigatória
  em todas as que não classificam (sem bandas, ou com bandas que só nomeiam) e proibida nas
  que classificam, que declaram `source`. É o que o cartão mostra onde uma métrica
  classificada mostra o standard, em vez de repetir «Sem referência clínica» em toda a
  página. O texto longo continua em `notes`, que a página de detalhe mostra por inteiro.

## Proveniência dos standards

| Standard | Aplicação |
|---|---|
| OMS | Classificação do IMC; perímetro abdominal (em conjunto com a IDF) |
| ACE/ACSM | Categorias de percentagem de gordura corporal, por sexo — **nomeiam sem classificar** (aptidão física, não clínica) |
| GLIM/ESPEN | Limiares de IMLG para massa magra reduzida |
| IDF | Limiares de perímetro abdominal para risco cardiometabólico |

Os intervalos de referência dos biomarcadores seguem valores laboratoriais de adulto
correntes; variam entre laboratórios e métodos analíticos — daí serem apenas fallback.
