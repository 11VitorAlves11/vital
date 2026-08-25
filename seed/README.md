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
  domínio sem sobreposições nem lacunas. `flag` ∈ `normal` | `warn` | `alert`.
- **`bands` a `null` = métrica trend-only**: registada e visualizada em tendência, sem
  flag. Só existe flag onde há standard clínico validado — aplicar "standards" inventados
  a estimativas de bioimpedância seria pseudo-precisão.
- **`source`** identifica a proveniência do standard (OMS, ACE/ACSM, IDF), para auditoria.

## Proveniência dos standards

| Standard | Aplicação |
|---|---|
| OMS | Classificação do IMC; perímetro abdominal (em conjunto com a IDF) |
| ACE/ACSM | Categorias de percentagem de gordura corporal, por sexo |
| IDF | Limiares de perímetro abdominal para risco cardiometabólico |

Os intervalos de referência dos biomarcadores seguem valores laboratoriais de adulto
correntes; variam entre laboratórios e métodos analíticos — daí serem apenas fallback.
