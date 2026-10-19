# Trabalho Prático 1 — Indexação Geoespacial e Geometria Computacional Híbrida

Aplicação web local para simular entregadores em Belo Horizonte e localizar os
que estão dentro do raio de atendimento de um restaurante.

O projeto implementa manualmente a codificação Geohash Base32 e uma Radix Trie
compacta. Bibliotecas externas são usadas somente para transformação de
coordenadas, manipulação da malha viária e testes.

## Requisitos

- Python 3.11 ou superior;
- acesso à internet na primeira obtenção da malha viária do OpenStreetMap; e
- Windows, Linux ou macOS.

## Instalação

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No Linux ou macOS:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

O pacote é instalado em modo editável, portanto alterações em `src/tp1`
ficam disponíveis imediatamente para os scripts.

## Preparação dos restaurantes

A fonte utilizada é o conjunto [Atividade Econômica da Prefeitura de Belo
Horizonte](https://dados.pbh.gov.br/pt_BR/dataset/atividade-economica),
publicado sob licença Creative Commons Attribution. Baixe uma versão do CSV e
salve-a, por exemplo, como:

```text
data/raw/atividade_economica.csv
```

Depois execute:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_restaurants.py `
  data\raw\atividade_economica.csv `
  data\processed\restaurants.csv
```

O processamento é feito linha a linha. São mantidos estabelecimentos com CNAE
da classe `56112`, e a geometria é convertida de EPSG:31983 para EPSG:4326.

## Geração de entregadores

```powershell
.\.venv\Scripts\python.exe scripts\generate_couriers.py `
  data\processed\restaurants.csv `
  data\cache\bh_drive.graphml `
  100 `
  data\processed\couriers.csv `
  --seed 42
```

Na primeira execução, o OSMnx baixa a malha viária dirigível de Belo Horizonte
e a salva no caminho informado. As próximas execuções reutilizam o cache. As
posições são amostradas por uma distribuição normal ao redor dos restaurantes
e projetadas para a via mais próxima.

## Medição de consultas

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_queries.py `
  data\processed\restaurants.csv `
  data\cache\bh_drive.graphml `
  1000 `
  data\processed\benchmark.csv `
  --seed 42 `
  --radii 0.5 1 2 5
```

O CSV gerado contém semente, tamanho da frota, desvio da simulação,
restaurante, raio, precisão e quantidade de prefixos, candidatos recuperados
da Trie, entregadores filtrados e tempo da consulta em milissegundos.

## Dashboard

Depois de preparar `data/processed/restaurants.csv`, execute:

```powershell
.\.venv\Scripts\python.exe -m dashboard.app
```

No Linux ou macOS, use `./.venv/bin/python -m dashboard.app`. A página ficará
disponível em `http://127.0.0.1:8050`.

Ordem de uso:

1. informe a quantidade e, opcionalmente, altere a semente;
2. clique em **Gerar entregadores**;
3. pesquise e selecione um restaurante;
4. ajuste o raio; e
5. clique em **Buscar próximos**.

O restaurante aparece em azul-escuro, os entregadores encontrados em vermelho
e os demais em cinza. A tabela apresenta ID, distância e ETA; os cartões
mostram candidatos da Trie, encontrados, tamanho do prefixo e tempo da busca.

Na primeira geração, o OSMnx baixa a malha viária se o cache ainda não existir.
Isso pode levar alguns minutos. Se o CSV processado estiver ausente, o dashboard
abrirá com uma mensagem indicando que o script de preparação deve ser executado.

Os caminhos e o servidor podem ser alterados:

```powershell
.\.venv\Scripts\python.exe -m dashboard.app `
  --restaurants data\processed\restaurants.csv `
  --street-cache data\cache\bh_drive.graphml `
  --host 127.0.0.1 `
  --port 8050
```

Use `--debug` somente durante o desenvolvimento. O estado da frota fica na
memória do processo e é compartilhado entre todas as abas conectadas à mesma
execução; o dashboard foi projetado para uso local por uma pessoa.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Os testes não acessam a rede. A integração com a malha viária usa um grafo
sintético e a ingestão usa uma amostra pequena no diretório `tests/fixtures`.

## Organização

```text
src/tp1/
├── models.py       # modelos imutáveis
├── geohash.py      # Geohash, vizinhos e precisão por raio
├── trie.py         # Radix Trie compacta
├── geometry.py     # Haversine e ETA
├── restaurants.py  # preparação da PBH e repositório
├── simulation.py   # distribuição normal e ajuste às ruas
└── service.py      # fachada usada pela interface
dashboard/
├── app.py          # controlador, callbacks e comando de execução
├── components.py   # layout Dash e mapa Leaflet
├── presentation.py # conversão dos resultados para GeoJSON e tabela
└── assets/
    └── style.css   # estilo simples e responsivo
```

Arquivos brutos da PBH, ambiente virtual e cache do OpenStreetMap são
ignorados pelo Git. O relatório final será adicionado em uma etapa posterior.
