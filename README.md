# Escola do Futuro — Sistema de Autenticação & Controle de Acesso (EE Antonio Reginato)

Aplicação educacional completa demonstrando **autenticação, geração de JWT e proteção de rotas** com backend FastAPI e páginas HTML integradas.

---

## 🚀 Como Executar

### 1. Instalar as Dependências

```bash
pip install -r requirements.txt
```

> **Compatibilidade:** Totalmente compatível com Python 3.10, 3.11, 3.12 e 3.13 (utiliza `bcrypt` diretamente e o manipulador de `lifespan` moderno do FastAPI).

---

### 2. Iniciar o Servidor FastAPI

```bash
python main.py
```
*(ou: `uvicorn main:app --reload --port 8000`)*

---

### 3. Acessos

- **Portal de Acesso / Login:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Área Restrita (Página Protegida):** [http://127.0.0.1:8000/painel](http://127.0.0.1:8000/painel)
- **Documentação Interativa Swagger:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🔑 Credenciais Padrão para Teste

Ao iniciar, o banco SQLite (`escola_auth.db`) é criado/atualizado automaticamente com os perfis pedagógicos padrão para teste (também é possível digitar apenas o usuário curto no campo de login, como `gestor`, `professor` ou `diretor`):

| Perfil | Usuário (Login Curto) | E-mail Institucional | Senha | Relatórios Liberados |
| :--- | :--- | :--- | :--- | :--- |
| **Gestor** (`gestor`) | `gestor` | `


` | `gestor123` | `#REL-01` (SARESP) e `#REL-02` (Diário de Classe) |
| **Professor** (`professor`) | `professor` | `professor@escola.sp.gov.br` | `professor123` | `#REL-02` (Diário de Classe) |
| **Diretor / Diretoria** (`diretor`) | `diretor` | `diretor@escola.sp.gov.br` | `diretor123` | `#REL-01`, `#REL-02` e `#REL-03` (Exclusivo Diretoria) |
| **Admin / Coordenação** (`gestor`) | `admin` | `admin@escola.sp.gov.br` | `admin123` | `#REL-01` (SARESP) e `#REL-02` (Diário de Classe) |

---

## 📡 Endpoints Implementados no FastAPI

| Método | Rota | Descrição | Segurança |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Serve a interface web de login `index.html` | Pública |
| `GET` | `/painel` | Serve a página de área restrita `painel.html` com menu por relatório | Pública (validação no client/API) |
| `GET` | `/painel-servidor` | Página restrita bloqueada diretamente pelo servidor | Requer `?token=...` |
| `GET` | `/api/dados-restritos` | Retorna dados confidenciais gerais e matriz de relatórios liberados para o perfil | `Bearer <JWT>` (401 se ausente) |
| `GET` | `/api/relatorios/saresp` | `#REL-01`: Desempenho SARESP e Avaliações Diagnósticas 2026 | `Bearer <JWT>` + Perfil `gestor` ou `diretor` (403 caso contrário) |
| `GET` | `/api/relatorios/diario-classe` | `#REL-02`: Diário de Classe & Lançamento de Médias Bimestrais | `Bearer <JWT>` + Perfil `professor`, `gestor` ou `diretor` (403 caso contrário) |
| `GET` | `/api/relatorios/auditoria-matriculas` | `#REL-03`: Auditoria de Matrículas e Frequência Escolar | `Bearer <JWT>` + Perfil `diretor` (403 caso contrário) |
| `GET` | `/auth/health` | Healthcheck de monitoramento do backend | Pública |
| `POST` | `/auth/register` | Criação de nova conta (Nome, Email, Perfil, Senha) | Pública |
| `POST` | `/auth/login` | Login via JSON retornando JWT Token e Perfil | Pública |
| `POST` | `/auth/token` | Login via OAuth2 Form (suporte ao Swagger UI) | Pública |
| `GET` | `/auth/me` | Retorna os dados do usuário autenticado | `Bearer <JWT>` |
| `POST` | `/auth/logout` | Encerra a sessão | `Bearer <JWT>` |

---

## 🎓 Demonstração Pedagógica: Autorizado vs. Acesso Negado

A aplicação foi desenhada especificamente para ilustrar os conceitos de segurança web (Autenticação `401` e Autorização RBAC `403`):

1. **Acesso Negado por Falta de Autenticação (HTTP 401 Unauthorized):**
   - Acesse diretamente no navegador: `http://127.0.0.1:8000/painel` sem estar logado.
   - A página detecta a ausência do token, aciona o backend e exibe a tela vermelha de **Acesso Negado**, explicando didaticamente por que a rota foi bloqueada e mostrando o JSON real retornado pelo FastAPI.

2. **Acesso Autorizado e Menu Específico por Perfil (HTTP 200 OK vs HTTP 403 Forbidden):**
   - Acesse `http://127.0.0.1:8000` e efetue login com `professor`, `gestor` ou `diretor`.
   - No painel (`/painel`), utilize o **Menu de Chamadas por Perfil** para consultar os relatórios `#REL-01` (`/api/relatorios/saresp`), `#REL-02` (`/api/relatorios/diario-classe`) e `#REL-03` (`/api/relatorios/auditoria-matriculas`).
   - Cada chamada envia o cabeçalho `Authorization: Bearer <token>`, o FastAPI executa `decode_access_token()` e valida o campo `role` do usuário:
     - **Professor** acessa `#REL-02` (HTTP 200) e recebe bloqueio **HTTP 403** em `#REL-01` e `#REL-03`.
     - **Gestor** acessa `#REL-01` e `#REL-02` (HTTP 200) e recebe bloqueio **HTTP 403** em `#REL-03` (Exclusivo Diretoria).
     - **Diretor** acessa todos os três relatórios (`#REL-01`, `#REL-02` e `#REL-03`) com **HTTP 200**.

3. **Simulação Interativa de Revogação de Token:**
   - Na página restrita autorizada, clique no botão **"Simular Negação (Apagar Token e Recarregar)"** para ver a mudança de estado em tempo real.

ESPECIFICAÇÃO ORIENTADORA Sistema de Registro e Acompanhamento de Ocorrências de Alunos
Documento de referência para agentes de IA e equipe de desenvolvimento
Base documental: formulário impresso "Relatório de Ocorrência" da E.E. Prof. Amilcare Mattei -- Ensino Médio Integral, apresentado como imagem pelo solicitante. O objetivo é orientar a evolução de uma aplicação já existente em FastAPI, que possui endpoints implementados.
1. Finalidade e diretrizes de implementação
Este documento não determina a reescrita da API. Ele orienta os agentes de IA a inspecionar o projeto FastAPI existente, compreender seus modelos, autenticação, convenções e endpoints e, somente então, propor alterações incrementais para persistir, consultar e acompanhar ocorrências.
Preservar os endpoints, contratos e regras de negócio já utilizados. Antes de criar rota ou tabela, verificar se já existe recurso equivalente.
Não duplicar cadastros de alunos, professores, escolas, turmas, séries, disciplinas ou usuários. Preferir relacionamentos com as entidades existentes.
Usar migrações versionadas (por exemplo, Alembic, caso já faça parte do projeto); não alterar o banco diretamente em produção.
Separar o registro factual da ocorrência, as classificações assinaladas, os encaminhamentos e as manifestações posteriores.
Não transformar o formulário em um sistema punitivo automático. O sistema registra fatos, providências e acompanhamento; decisões são humanas e devem respeitar as normas da rede.
Quando uma informação não existir no formulário ou no sistema atual, não inventar valores obrigatórios. Registrar como decisão pendente ou campo opcional.
2. Leitura funcional do formulário de referência
O formulário apresenta cabeçalho institucional e um registro de ocorrência com identificação do aluno, série, professor, disciplina, aula e data. Em seguida, há uma lista de situações comportamentais, um campo "Outro", o relato do professor, a assinatura do professor, a seleção de encaminhamento, espaço para registros/continuidade e, ao final, data, assinatura e ciência dos responsáveis.
| Área do formulário | Conteúdo identificado na imagem | Representação sugerida |
| --- | --- | --- |
| Identificação institucional | Governo do Estado de São Paulo; Secretaria de Estado da Educação; Unidade Regional de Ensino de Marília; E.E. "Prof. Amilcare Mattei" -- Ensino Médio Integral. | Vincular à escola já cadastrada; não replicar endereço e contatos em cada ocorrência. |
| Aluno e contexto | Nome do(a) aluno(a); Série; Nome do(a) Professor(a); Disciplina; Aula; Data. | Referências às entidades existentes e campos de contexto da ocorrência. |
| Classificações | Sete situações descritas e opção "Outro". | Catálogo de tipos de ocorrência + associação N:N com o registro. |
| Relato do professor | Campo textual livre. | Texto obrigatório ou opcional conforme decisão da escola; preservar o texto original. |
| Autoria | Assinatura do(a) professor(a). | Identidade autenticada do autor e registro de confirmação/assinatura, sem presumir assinatura digital certificada. |
| Encaminhamento | Diretor; Vice Diretor; PCG; PCA. | Um ou mais encaminhamentos, com responsável/função, data e situação. |
| Acompanhamento | Linhas livres após o encaminhamento. | Histórico de interações/andamentos, com autor e data. |
| Ciência dos responsáveis | Data; Assinatura; Ciência dos responsáveis. | Registro de comunicação e ciência, com meio, data e evidência quando disponível. |
3. Catálogo inicial de situações do formulário
Os textos abaixo devem ser cadastrados fielmente como opções selecionáveis. A aplicação pode permitir selecionar mais de uma opção para uma mesma ocorrência.
| Código sugerido | Descrição fiel / resumida |
| --- | --- |
| TIPO_01 -- Frequência e pontualidade | Não frequenta a escola regular e pontualmente (atrasos), não realizando os esforços necessários para progredir nas diversas áreas da educação. |
| TIPO_02 -- Preparação e materiais | Não está preparado para as aulas e não mantém adequadamente livros e demais materiais escolares de uso pessoal. |
| TIPO_03 -- Convivência e ambiente de aprendizagem | Não contribui para a criação e manutenção de um ambiente de aprendizagem colaborativo e seguro, que garanta o direito de todos os alunos de estudar e aprender. |
| TIPO_04 -- Ausência da aula | Ausenta-se das aulas, sem prévia justificativa ou autorização dos professores da escola. |
| TIPO_05 -- Uso de dispositivos | Utiliza, em salas de aula e demais locais de aprendizado escolar, equipamentos eletrônicos como celulares e outros dispositivos de comunicação e entretenimento que perturbem o ambiente escolar ou prejudiquem o aprendizado. |
| TIPO_06 -- Atividade alheia à aula | Ocupa-se durante a aula, de qualquer atividade que lhe seja alheia. |
| TIPO_07 -- Desrespeito ou agressão | Desrespeita professores, funcionários, colegas de sala ou utiliza-se de qualquer forma de agressão. |
| TIPO_08 -- Outro | Outro: descrição livre, a ser preenchida pelo autor. |
Observação: os códigos são identificadores técnicos sugeridos, não constam no formulário. O texto exibido ao usuário deve preservar a redação oficial aprovada pela escola.
4. Modelo de dados relacional proposto
O modelo abaixo é lógico. Os nomes físicos e os tipos devem ser adaptados ao padrão já adotado no repositório (SQLAlchemy, SQLModel ou outro). Antes de implementar, mapear as entidades existentes e reutilizá-las.
4.1 Tabela principal: ocorrencias
| Campo lógico | Tipo / regra sugerida | Finalidade |
| --- | --- | --- |
| id | UUID ou PK padrão do projeto | Identificador único. |
| escola_id | FK para escola/unidade existente | Escopo institucional do registro. |
| aluno_id | FK para aluno existente; obrigatório | Aluno relacionado. |
| turma_id | FK opcional para turma/matrícula existente | Contexto da turma no momento do fato. |
| serie_snapshot | Texto curto opcional | Série exibida no formulário; usar apenas se não houver vínculo histórico confiável. |
| professor_id | FK para usuário/servidor existente; obrigatório | Autor/professor responsável pelo registro. |
| disciplina_id | FK opcional para disciplina existente | Disciplina em que ocorreu. |
| aula_referencia | Texto curto ou número opcional | Aula/período informado no formulário; esclarecer formato com a escola. |
| data_ocorrencia | DATE ou DATETIME conforme regra definida | Data do fato, distinta da data de criação. |
| relato_professor | TEXT | Relato factual do professor. |
| outro_detalhe | TEXT nullable | Complemento quando a opção "Outro" for selecionada. |
| status | Enum/string controlada | Estado do fluxo; ver seção 6. |
| criado_em / atualizado_em | DATETIME com timezone, conforme padrão do projeto | Auditoria técnica. |
| criado_por / atualizado_por | FK para usuário, quando aplicável | Rastreabilidade. |
Não armazenar nome, RA, e-mail ou outros dados do aluno em duplicidade se a tabela de alunos já os mantém. Se houver necessidade de preservar a série/turma histórica, documentar a razão e adotar snapshot apenas para os campos necessários.
4.2 Catálogo e associação de tipos
| Tabela | Campos principais | Regras |
| --- | --- | --- |
| tipos_ocorrencia | id; codigo; descricao; ativo; ordem_exibicao; criado_em; atualizado_em | Cadastro controlado das opções do formulário. Não apagar tipos já utilizados; inativar. |
| ocorrencia_tipos | id; ocorrencia_id FK; tipo_ocorrencia_id FK; detalhe TEXT nullable | Tabela associativa para permitir várias classificações por ocorrência. Impor unicidade (ocorrencia_id, tipo_ocorrencia_id). |
A opção "Outro" pode ser um tipo do catálogo e exigir detalhe quando selecionada. Validar essa condição no serviço/API, não apenas na interface.
4.3 Encaminhamentos
| Tabela | Campos principais | Regras |
| --- | --- | --- |
| encaminhamentos | id; ocorrencia_id FK; destinatario_usuario_id FK nullable; funcao_destino; encaminhado_por FK; encaminhado_em; observacao; status; concluido_em nullable | Permite um ou mais encaminhamentos para Diretor, Vice Diretor, PCG ou PCA. Destinatário nominal pode ser associado quando conhecido. |
As funções Diretor, Vice Diretor, PCG e PCA devem ser valores controlados ou derivadas dos papéis já existentes no sistema. Não criar um cadastro paralelo de usuários. Se a aplicação permitir múltiplos destinatários, cada encaminhamento deve ser um registro independente.
4.4 Acompanhamento e ciência dos responsáveis
| Tabela | Campos principais | Regras |
| --- | --- | --- |
| andamentos_ocorrencia | id; ocorrencia_id FK; autor_id FK; tipo; descricao TEXT; registrado_em; anexo_id FK nullable | Cada anotação é um evento imutável no histórico. Evitar sobrescrever o relato inicial. |
| ciencias_responsaveis | id; ocorrencia_id FK; responsavel_nome nullable; tipo_vinculo nullable; meio_comunicacao; data_contato; data_ciencia nullable; status; observacao; comprovante_arquivo_id nullable; registrado_por FK | Registra tentativa/realização de contato e ciência. Não presumir que ciência equivale a concordância. |
A imagem mostra data, assinatura e ciência dos responsáveis, mas não define meios de comunicação, quantidade de responsáveis nem formato de evidência. Esses detalhes devem ser validados com a escola antes de torná-los obrigatórios. Não armazenar imagem de assinatura sem necessidade e sem política de acesso/retensão.
4.5 Anexos (opcional)
Se já existir módulo de arquivos, reutilizá-lo. Caso contrário, considerar uma tabela genérica de anexos com id, nome original, chave/localização de armazenamento, tipo MIME, tamanho, hash, enviado_por e enviado_em. Guardar o arquivo fora do banco e proteger o acesso por autorização. Não anexar documentos pessoais por padrão.
5. Relacionamentos e cardinalidades
Uma escola possui muitos registros de ocorrência; cada ocorrência pertence a uma escola.
Um aluno pode possuir muitas ocorrências; cada ocorrência referencia um aluno.
Um professor/usuário pode registrar muitas ocorrências; cada ocorrência possui um autor.
Uma ocorrência pode ter várias classificações e cada tipo pode aparecer em várias ocorrências (N:N).
Uma ocorrência pode ter vários encaminhamentos, andamentos e registros de ciência.
Disciplina, turma e matrícula devem apontar para os cadastros já existentes, respeitando o histórico escolar disponível.
6. Fluxo de trabalho sugerido
| Etapa | Ação | Estado possível |
| --- | --- | --- |
| 1. Registro | Professor seleciona aluno, contexto, data, tipos e descreve o fato. | RASCUNHO (se houver salvamento parcial) ou REGISTRADA. |
| 2. Encaminhamento | Professor encaminha para uma ou mais funções da equipe gestora/pedagógica. | ENCAMINHADA. |
| 3. Análise | Destinatário analisa e registra providências ou solicita complementação. | EM_ANALISE. |
| 4. Acompanhamento | Equipe registra contatos, reuniões, orientações e demais andamentos pertinentes. | EM_ACOMPANHAMENTO. |
| 5. Ciência | Secretaria/equipe registra comunicação e ciência dos responsáveis. | AGUARDANDO_CIENCIA ou CIENCIA_REGISTRADA. |
| 6. Encerramento | Responsável autorizado registra conclusão e justificativa/resumo. | ENCERRADA. |
Os estados são uma proposta de trabalho, não estão impressos no formulário. A escola deve aprovar o fluxo e as permissões antes da implementação. Permitir reabertura apenas a perfis autorizados e registrar o motivo.
7. Orientação para evolução da API FastAPI existente
Antes de escrever código, o agente de IA deve produzir um inventário do projeto:
Localizar estrutura de pastas, configuração, dependências e versão do Python/FastAPI.
Identificar ORM, Base/metadata, sessão/conexão, convenção de modelos, schemas Pydantic e camada de serviços/repositórios.
Listar endpoints existentes, métodos, payloads, respostas, dependências de autenticação e autorização.
Identificar entidades existentes de aluno, professor/usuário, escola, turma, disciplina, papéis e arquivos.
Verificar migrações, testes, tratamento de erros, paginação, filtros e padrão de nomenclatura.
Entregar uma proposta de impacto: o que será reutilizado, criado, alterado e o que não será tocado.
Somente após esse inventário, implementar de forma incremental. Não presumir nomes de módulos, tabelas, prefixos de rota ou bibliotecas.
7.1 Endpoints funcionais esperados (referência, não imposição)
| Operação | Endpoint ilustrativo | Observações |
| --- | --- | --- |
| Consultar catálogo | GET /tipos-ocorrencia | Retornar somente tipos ativos para novos registros; manter histórico de inativos. |
| Criar ocorrência | POST /ocorrencias | Validar aluno, escola, autor, tipos e permissões. |
| Listar ocorrências | GET /ocorrencias | Filtros por aluno, turma, período, status, autor e tipo; respeitar escopo de acesso. |
| Detalhar ocorrência | GET /ocorrencias/{id} | Retornar relato, classificações, encaminhamentos e histórico conforme permissão. |
| Atualizar registro | PATCH /ocorrencias/{id} | Restringir edição do relato após encaminhamento; preferir adendo auditável. |
| Encaminhar | POST /ocorrencias/{id}/encaminhamentos | Criar registros separados por destinatário/função. |
| Registrar andamento | POST /ocorrencias/{id}/andamentos | Adicionar evento ao histórico, sem apagar eventos anteriores. |
| Registrar ciência | POST /ocorrencias/{id}/ciencias | Registrar comunicação, data e evidência permitida. |
| Alterar status | PATCH /ocorrencias/{id}/status | Validar transições e autorização no backend. |
Os caminhos acima são exemplos. Se já houver endpoints equivalentes, preservar seus contratos e adaptar apenas o necessário.
8. Validações e integridade
Confirmar que o aluno pertence à escola/escopo do usuário e que a matrícula/turma é compatível com a data, quando esses dados existirem.
A data do fato não deve ser confundida com criado_em. Definir política para registros retroativos.
Exigir ao menos uma classificação, se essa for a regra aprovada; caso "Outro" seja escolhido, exigir descrição.
Validar que o autor tem permissão para registrar ocorrências na escola e, quando aplicável, na turma.
Impedir encaminhamento para função inexistente/inativa ou para usuário fora do escopo institucional.
Não permitir exclusão física de ocorrência encaminhada/consultada; preferir cancelamento/inativação justificada e auditada.
Usar transações para criação da ocorrência e suas classificações iniciais, evitando registros parciais.
Aplicar limites de tamanho aos campos textuais e validar anexos por tipo, tamanho e autorização.
9. Segurança, privacidade e proteção de dados
O sistema tratará dados pessoais de estudantes, possivelmente crianças e adolescentes, e relatos que podem conter informações delicadas. A implementação deve seguir as políticas da Secretaria/rede e a LGPD, com foco no melhor interesse do estudante.
Aplicar menor privilégio: professor acessa registros pertinentes ao seu contexto; equipe gestora acessa conforme atribuição; demais perfis não recebem acesso automático.
Verificar autorização em cada operação e em cada consulta por ID, evitando acesso indevido por troca de identificador.
Registrar trilha de auditoria para criação, alteração, encaminhamento, leitura sensível quando exigido, ciência, cancelamento e encerramento.
Evitar dados sensíveis desnecessários no relato. Orientar linguagem objetiva, factual, respeitosa e sem rótulos ou diagnósticos.
Proteger anexos e documentos; não expor URLs públicas permanentes.
Definir retenção, descarte, exportação e atendimento a solicitações conforme política institucional; não inventar prazo de retenção.
Não usar dados reais de alunos em ambientes de desenvolvimento, testes, prompts externos ou demonstrações. Preferir dados sintéticos.
Não enviar conteúdo de ocorrências para serviços externos de IA sem autorização institucional, base legal e controles específicos.
10. Auditoria e histórico
Além dos campos created_at/updated_at, manter histórico de eventos relevante. O relato original deve permanecer identificável mesmo quando houver complementação. Recomenda-se registrar: entidade afetada, id, ação, usuário, data/hora, valores alterados (com cuidado para não replicar desnecessariamente dados pessoais), justificativa e origem da operação. A trilha não deve ser editável por usuários comuns.
11. Consultas e relatórios
Consulta individual do histórico do aluno, limitada ao escopo autorizado.
Consulta por período, turma, série, tipo, status, professor e encaminhamento.
Pendências de análise, acompanhamento e ciência dos responsáveis.
Indicadores agregados por período/turma/tipo, evitando exposição nominal em painéis gerenciais quando não necessária.
Exportações devem respeitar as mesmas permissões da tela e registrar quem exportou, quando e quais filtros foram aplicados.
12. Estratégia de implementação em etapas
Etapa 0 -- Diagnóstico: mapear código, banco, endpoints e entidades existentes; apresentar relatório de compatibilidade.
Etapa 1 -- Persistência mínima: catálogo de tipos, tabela principal e tabela associativa; migração e testes.
Etapa 2 -- API: integrar schemas, serviços e endpoints existentes; autenticação, autorização e filtros.
Etapa 3 -- Encaminhamentos e histórico: implementar destinatários, andamentos e transições de status.
Etapa 4 -- Ciência e anexos: somente após definição institucional de meios, evidências e retenção.
Etapa 5 -- Interface e relatórios: reproduzir os campos do formulário, validar usabilidade e produzir consultas autorizadas.
13. Testes mínimos de aceite
Criar ocorrência com aluno, professor, data, disciplina/aula, relato e uma classificação.
Criar ocorrência com várias classificações sem duplicar a mesma classificação.
Selecionar "Outro" sem descrição deve falhar, caso a regra seja aprovada.
Usuário sem permissão não consegue consultar ocorrência de outra escola/turma.
Professor não consegue atribuir encaminhamento ou alterar status reservado à gestão.
Encaminhamento e andamento ficam registrados com autor e data/hora.
Registrar ciência não altera nem apaga o relato do professor.
Filtros por período, aluno, tipo e status retornam resultados consistentes e paginados.
Migração pode ser aplicada em banco vazio e em banco com dados existentes, sem perda.
Endpoints existentes continuam funcionando (testes de regressão).
14. Prompt-base para agentes de IA
Você está trabalhando em uma aplicação existente construída com FastAPI e que já possui endpoints. Implemente a funcionalidade de registro e acompanhamento de ocorrências de alunos seguindo esta especificação e o formulário de referência. Antes de alterar arquivos, inspecione o repositório, identifique ORM, banco, autenticação, entidades e endpoints existentes. Reutilize os cadastros de aluno, professor/usuário, escola, turma e disciplina; não crie duplicatas. Apresente primeiro um plano de alteração com arquivos, tabelas, relacionamentos, migrações e endpoints afetados. Implemente apenas após validar compatibilidade com o padrão atual. Preserve contratos existentes, use migrações versionadas, validação no backend, autorização por escola/perfil, auditoria e testes. Modele separadamente ocorrência, tipos selecionados, encaminhamentos, andamentos e ciência dos responsáveis. Não invente regras institucionais ausentes: sinalize decisões pendentes. Não use dados reais de estudantes em testes. Ao concluir, informe tabelas criadas/alteradas, endpoints reaproveitados/criados, migração, testes executados e decisões que dependem da escola.
15. Decisões que precisam ser confirmadas pela escola/equipe
Uma ocorrência pode ser registrada por mais de um professor ou sempre terá um único autor?
A turma/série deve refletir o vínculo do aluno na data do fato ou o cadastro atual?
O campo "Aula" representa número da aula, horário, componente curricular ou outro identificador?
Quais perfis podem visualizar, editar, encaminhar, cancelar e encerrar ocorrências?
Encaminhamento pode ser múltiplo? Diretor, Vice Diretor, PCG e PCA são destinos funcionais ou pessoas específicas?
Quais estados e transições serão adotados no fluxo real?
Como e por quais meios os responsáveis são comunicados? O que comprova ciência?
Assinatura será manuscrita digitalizada, confirmação autenticada no sistema ou apenas identificação do usuário?
Quais anexos são permitidos e qual política de guarda/retensão deve ser aplicada?
Quais relatórios e exportações são necessários e para quais perfis?
16. Limites da fonte e observações finais
A imagem permite identificar os campos e as sete situações listadas, mas não informa regras de negócio, permissões, estados do processo, política de retenção, formato de assinatura, estrutura atual do banco ou contratos dos endpoints FastAPI. Por isso, este documento separa o que está explícito no formulário das propostas técnicas. O agente de IA deve tratar as propostas como orientação inicial e confirmar decisões institucionais antes de torná-las obrigatórias.
Princípio central: evoluir a aplicação existente com o menor impacto possível, preservando a rastreabilidade do registro e garantindo acesso restrito e responsável às informações dos estudantes.
prompt

Turmas Ativas14 SalasEnsino Fundamental e Médio
Documentos Restritos Desbloqueados para este Perfil:
Código
Documento Sigiloso
Classificação
Status
#REL-01
Desempenho SARESP e Avaliações Diagnósticas 2026
Restrito à Gestão
Disponível
#REL-02
Diário de Classe & Lançamento de Médias Bimestrais
Professores / Gestão
Disponível
#REL-03
Auditoria de Matrículas e Frequência Escolar
Exclusivo Diretoria
Disponível
Como a Permissão Foi Validada Tecnologicamente?
O frontend enviou o cabeçalho HTTP:Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5c...m1fvknF4Zo
O FastAPI executou decode_access_token() conferindo a assinatura HMAC-SHA256 e o prazo de expiração.
Simular Negação (Apagar Token e Recarregar)[Voltar ao Portal Inicial](http://127.0.0.1:8000/)Encerrar Sessão

o texto acima se refere a um exemplo pedagógico para consulta de três tipos de usuarios: gestor, professor/gestor e diretoria. Implemente na aplicação esses três relatórios hipotéticos inclusive o menu expecífico para cada chamada. Crie os usuários: gestor, professor, diretor com suas respectivas senhas de acesso e informe os dados no redme.md
