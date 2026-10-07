# Dicionário de Comunicação — CWS 500C

## 1. Objetivo

Arquivo de referência rápida para desenvolvimento e testes da comunicação entre o computador e o CWS 500C via RS-232.

> Os comandos e feedbacks devem ser classificados como **confirmados**, **em investigação** ou **não validados** até serem verificados no manual e no equipamento.

---

# 2. Comunicação Serial

| Parâmetro | Valor |
|---|---|
| Interface | RS-232 |
| Data bits | 8 bits |
| Baud rate | A confirmar |
| Paridade | A confirmar |
| Stop bits | A confirmar |
| Controle de fluxo | A confirmar |
| Terminador | LF `0x0A` — confirmar |
| Checksum | `100H - soma ASCII` — confirmar |

---

# 3. Pinagem

| Sinal | PC — DB25 | CWS 500C — DB9 |
|---|---:|---:|
| TXD | 2 | 3 — RXD |
| RXD | 3 | 2 — TXD |
| GND | 7 | 5 — GND |

A ligação TXD/RXD é cruzada.

---

# 4. Estrutura de comando

Fluxo esperado:

```text
Comando
   ↓
Calcular checksum
   ↓
Adicionar checksum
   ↓
Adicionar LF
   ↓
Enviar via RS-232
   ↓
Receber resposta
   ↓
Interpretar feedback
```

Formato ainda em validação:

```text
[COMANDO] + [CHECKSUM] + LF
```

---

# 5. Dicionário de Comandos

| Comando | Função | Enviado | Feedback esperado | Status |
|---|---|---|---|---|
| `PC;` | Identificação/comunicação | — | — | A validar |
| `CC;` | Identificação/comunicação CWS | — | — | A validar |
| `AR;` | Desconexão/retorno | — | — | A validar |
| `???` | — | — | — | Pendente |
| `???` | — | — | — | Pendente |

> Não preencher comandos desconhecidos por suposição. Adicionar somente após confirmação no manual ou teste controlado.

---

# 6. Dicionário de Feedback

| Feedback recebido | Significado | Ação do software | Status |
|---|---|---|---|
| `???` | Comunicação aceita | Continuar | A validar |
| `???` | Comando inválido | Registrar erro | A validar |
| `???` | Equipamento ocupado | Aguardar/tentar novamente | A validar |
| `???` | Erro de comunicação | Registrar erro | A validar |
| `???` | — | — | Pendente |

---

# 7. Tipos de Resultado

O software deverá futuramente diferenciar:

```text
SUCESSO
ERRO
TIMEOUT
COMANDO_INVALIDO
RESPOSTA_INVALIDA
SEM_RESPOSTA
PORTA_INDISPONIVEL
```

---

# 8. Registro dos testes

Cada teste deve registrar:

```text
Data:
Hora:
Porta:
Equipamento:
Configuração serial:

Comando enviado:
Bytes enviados:

Resposta recebida:
Bytes recebidos:

Checksum:
Resultado:
Observação:
```

Exemplo:

```text
Data: 06/10/2026
Hora: 10:30
Porta: COM5
Equipamento: CWS 500C

Comando enviado: PC;
Bytes enviados: ...

Resposta recebida: ...
Bytes recebidos: ...

Resultado: SUCESSO
Observação: Equipamento respondeu corretamente.
```

---

# 9. Status das informações

### Confirmado

Informações verificadas diretamente no manual ou em teste controlado.

### Em investigação

Informações encontradas nas anotações/documentação, mas ainda não confirmadas.

### Não validado

Informações baseadas somente em hipótese ou comportamento ainda não testado.

---

# 10. Primeiro teste

O primeiro teste deve ser realizado **sem acionar saída de RF**.

Objetivo:

```text
Python
  ↓
RS-232
  ↓
CWS 500C
  ↓
Resposta
  ↓
Python
```

Validar inicialmente:

- [ ] Porta COM correta
- [ ] Comunicação física
- [ ] Baud rate
- [ ] Paridade
- [ ] Stop bits
- [ ] Data bits
- [ ] Comando
- [ ] Checksum
- [ ] Terminador LF
- [ ] Resposta
- [ ] Timeout
- [ ] Tratamento de erro

---

# 11. Arquivos do projeto

```text
V-22 André/
│
├── conexao_ucws_500.py
├── teste_comunicacao.py
├── DICIONARIO_COMUNICACAO.md
├── protocolo_comunicacao.md
└── COMUNICACAO_CWS500C.md
```

### Responsabilidade

```text
conexao_ucws_500.py
→ comunicação com o equipamento

teste_comunicacao.py
→ testar a comunicação sem interface gráfica

DICIONARIO_COMUNICACAO.md
→ comandos e feedbacks

protocolo_comunicacao.md
→ detalhes técnicos do protocolo

COMUNICACAO_CWS500C.md
→ documentação geral da comunicação
```