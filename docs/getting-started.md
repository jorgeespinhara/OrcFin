# Primeiros passos

## Assistente de primeira execução

Na primeira abertura (ou após **Instalação limpa** em Configurações), o OrcFin exibe um assistente em cinco passos:

| Passo | Conteúdo |
|-------|----------|
| 1. Boas-vindas | Versão do app e princípio local-first |
| 2. Modo de uso | Finanças pessoais, MEI, ambos ou casal / múltiplos perfis |
| 3. Pasta dos dados | Padrão `C:\OrcFin` no Windows; opção de escolher outro local |
| 4. Backup | Ativar backup ao fechar o app |
| 5. Primeiro passo | Importar extrato, explorar com dados fictícios ou pular |

O assistente só aparece quando o banco está vazio e o onboarding ainda não foi concluído. Dados migrados de instalações antigas marcam o onboarding como concluído automaticamente.

## Depois do assistente

- **Pessoal:** dashboard com KPIs, lançamentos, importação e relatórios.
- **MEI:** configure o perfil MEI em Configurações ou pelo fluxo MEI; use obrigações, notas e pacote para contador.
- **Casal / múltiplos perfis:** perfis padrão *Usuário 1* e *Usuário 2*; alterne no seletor do topo ou use visão consolidada.

## Importar o primeiro extrato

1. Menu **Lançamentos** → **Importar**, ou **Cartões** → importar fatura.
2. Escolha CSV, OFX, QFX ou PDF (Nubank, Inter, C6, Bradesco, Itaú e outros).
3. Revise o preview, confirme categorias e salve.

O processamento é local; o conteúdo do arquivo não é enviado à internet.

## Backup

- **Configurações → Backup:** criar backup manual, restaurar, definir pasta e retenção.
- Com **Backup ao fechar** ativo, um arquivo `.orcfin.bak` é gerado ao sair do app.

Recomenda-se manter backups em disco externo ou nuvem pessoal, não apenas na mesma pasta do banco.

## Dados fictícios

No último passo do assistente, **Explorar com dados fictícios** insere lançamentos de exemplo para conhecer dashboards e relatórios sem expor dados reais. Você pode apagá-los depois em Lançamentos ou usar **Instalação limpa** em Configurações.

## Ajuda rápida

| Problema | O que fazer |
|----------|-------------|
| App não abre após mover a pasta | Execute sempre `OrcFin.exe` da pasta extraída; dados continuam em `C:\OrcFin` |
| Quero recomeçar do zero | Configurações → Zona de perigo → Instalação limpa |
| Quero mudar a pasta dos dados | Só no assistente inicial hoje; na versão portátil, edite com cuidado `data_root.txt` ou reinstale limpo |

Mais detalhes: [Instalação no Windows](install-windows.md).