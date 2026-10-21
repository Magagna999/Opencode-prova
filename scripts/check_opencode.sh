#!/bin/bash
# Esegue il controllo solo nelle sessioni cloud
if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
  exit 0
fi
if ! command -v opencode >/dev/null 2>&1; then
  npm install -g opencode-ai >/dev/null 2>&1 || echo "ATTENZIONE: opencode non è installato"
fi
echo "opencode versione: $(opencode --version 2>/dev/null)"
echo "Modelli gratuiti disponibili:"
opencode models opencode 2>/dev/null | grep -i free
exit 0
