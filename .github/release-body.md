## OrcFin v0.2.12

Orçamento financeiro local para **pessoal**, **casal** e **MEI** — dados no seu computador, sem nuvem para cadastro ou relatórios.

### Destaques

- **Segurança:** no fallback sem keyring do SO, o salt PBKDF2 deixa de ser uma constante pública no código. Cada instalação gera 16 bytes aleatórios em `config/kdf_salt.bin` (permissões restritas), alinhado a NIST SP 800-132.
- Chaves de API já salvas com o salt antigo ainda abrem e são re-criptografadas automaticamente na próxima carga das configurações.

### Instalação (Windows)

1. Baixe `OrcFin-portable.zip` abaixo.
2. Extraia a pasta em qualquer local.
3. Execute `OrcFin.exe`.
4. Confira na barra de título: **OrcFin v0.2.12**.
5. No primeiro uso, escolha **Começar com dados fictícios** para ver o app populado.

> Executáveis sem assinatura digital podem ser sinalizados pelo SmartScreen. Use “Mais informações” → “Executar mesmo assim” se confiar na origem (release oficial deste repositório).

**Changelog completo:** https://github.com/jorgeespinhara/OrcFin/blob/main/CHANGELOG.md
