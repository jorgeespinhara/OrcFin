# Privacidade e dados locais

O OrcFin foi projetado como aplicativo **local-first**: todas as funções essenciais operam sem internet e sem telemetria.

## O que fica no seu computador

| Dado | Local típico (Windows) |
|---|---|
| Banco SQLite (WAL) | `C:\OrcFin\data\orcfin.db` |
| Preferências | `C:\OrcFin\config\settings.json` |
| Backups criptografados | `C:\OrcFin\backups\` (`.orcfin.bak`) |
| Chaves de API (IA) | Criptografadas com AES-GCM + keyring do sistema (ou salt por instalação em `config/kdf_salt.bin`) |

## O que nunca sai do PC por padrão

- Linhas de extratos importados (`CSV`, `OFX`, `PDF`)
- Descrições e valores individuais de lançamentos
- Dados de clientes, notas fiscais e XML NF-e do MEI
- Conteúdo de backups (criptografados localmente)
- Telemetria ou métricas de uso (o app **não** envia telemetria)

## Integração com IA (opcional)

Se você configurar um provedor de IA (DeepSeek, Grok, Gemini, OpenAI ou Claude):

- Apenas **totais agregados** do período são enviados (receita, despesa e resumo por categoria).
- **Não** são enviadas descrições individuais, CPFs, CNPJs nem nomes de estabelecimentos.
- O modo **Offline Estrito** bloqueia qualquer chamada externa (IA, cotações e verificação de atualizações).
- Eventos externos ficam registrados localmente em `audit_events`.

## Suporte sem telemetria (Diagnóstico sanitizado)

Em **Configurações → Dados, Privacidade & IA → Exportar diagnóstico sanitizado**, o OrcFin gera um arquivo `.txt` contendo apenas versão do app, ambiente (OS/Python/SQLite) e últimos erros técnicos — removendo automaticamente e-mails, CPF/CNPJ, tokens, valores monetários e nomes de usuário do caminho do sistema.

## Verificação manual de atualizações

O botão **Verificar atualizações** consulta a API pública de releases do GitHub apenas quando clicado manualmente e é bloqueado automaticamente quando o **Modo Offline Estrito** está ativo.

## Aviso

O OrcFin é uma ferramenta local de organização financeira. Não substitui contador, advogado ou orientação fiscal oficial.
