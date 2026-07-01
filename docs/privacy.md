# Privacidade e dados locais

O OrcFin foi projetado como aplicativo **local-first**: funções essenciais funcionam sem internet.

## O que fica no seu computador

| Dado | Local típico (Windows) |
|------|-------------------------|
| Banco SQLite | `C:\OrcFin\data\orcfin.db` |
| Preferências | `C:\OrcFin\config\settings.json` |
| Backups | `C:\OrcFin\backups\` (ou pasta configurada) |
| Chaves de API (IA) | Criptografadas no settings + keyring do sistema |

Você pode abrir a pasta de dados pelo assistente inicial ou em **Configurações → Privacidade e dados**.

## O que não sai do PC por padrão

- Linhas de extrato importados (CSV, OFX, PDF)
- Descrições e valores de lançamentos
- Dados de clientes e notas MEI
- Conteúdo de backups (arquivo criptografado local)

## Integração com IA (opcional)

Se você configurar um provedor de IA:

- Apenas **totais agregados** do período são enviados (receita, despesa, categorias em resumo).
- **Não** são enviadas descrições de transações, CPF, nomes de estabelecimentos nem linhas individuais.
- Antes de cada envio, o app exibe o **preview do payload** para você confirmar.
- O modo **Nunca usar internet** (offline estrito) bloqueia qualquer chamada externa.
- Eventos externos ficam registrados localmente em Configurações → Privacidade e dados.
- Sem chave configurada, o app usa análises locais e fallback offline.

## Exportação e portabilidade

- **CSV / JSON:** Configurações → exportação de lançamentos.
- **Backup `.orcfin.bak`:** cópia criptografada do banco; restauração guiada nas configurações.
- **Pacote contador MEI:** ZIP com PDF e CSVs gerados localmente.

## Apagar tudo

**Configurações → Zona de perigo → Instalação limpa** remove o banco e preferências da pasta de dados atual e reabre o assistente inicial. Feche o app antes de apagar manualmente a pasta `C:\OrcFin` no Explorer.

## Aviso

O OrcFin é ferramenta de organização financeira. Não substitui contador, advogado ou orientação fiscal oficial. Valide obrigações MEI e declarações com profissional habilitado.