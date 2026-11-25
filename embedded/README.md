# embedded/

Esta pasta não contém firmware. Por decisão do professor orientador (25/11/2026), o projeto não usa ESP32 nem hardware.

A aquisição é uma estação simulada alimentada por dados da API Open-Meteo, publicados via MQTT:

- publicador: `src/api_publisher.py` e `scripts/sim_publisher.py` (`--source api`, padrão; `--source synthetic` é só fallback offline);
- contrato do payload e tópico `antecedengue/estacoes/<station_id>/leituras` inalterados (ver CLAUDE.md);
- estações e coordenadas em `config/stations_bairros.json`.

Sensores reais ficam como trabalho futuro.

Weather data by [Open-Meteo.com](https://open-meteo.com). A precipitação é de modelo/reanálise; a API gratuita é só para uso não comercial.
