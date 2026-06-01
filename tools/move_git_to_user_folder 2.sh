#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="${1:-$(basename "$PROJECT_DIR")}"
BRANCH="${2:-}"
REMOTE_URL="${3:-https://github.com/jaimetur/${PROJECT_NAME}.git}"

LOCAL_GIT_BASE="$HOME/.local_git_repos"
LOCAL_GIT_DIR="$LOCAL_GIT_BASE/${PROJECT_NAME}.git"
TMP_GIT_DIR="$LOCAL_GIT_BASE/${PROJECT_NAME}.git.tmp.$$"

cd "$PROJECT_DIR"

fail() {
  echo "ERROR: $1"
  exit 1
}

safe_rm_rf() {
  local target="$1"

  [[ -n "$target" ]] || fail "ruta vacía para borrar"
  [[ "$target" != "/" ]] || fail "ruta peligrosa para borrar: /"

  case "$target" in
    "$PROJECT_DIR/.git"|"$LOCAL_GIT_BASE/$PROJECT_NAME.git.tmp."*|"$LOCAL_GIT_DIR")
      rm -rf "$target"
      ;;
    *)
      fail "borrado bloqueado por seguridad: $target"
      ;;
  esac
}

print_verification() {
  echo
  echo "============================================================"
  echo "Verificación final"
  echo "============================================================"
  git status
  echo
  git rev-parse --git-dir
  echo
  git branch -vv || true
  echo
  ls -ld .git
  file .git
  cat .git
  echo
  echo "Tamaño del gitdir externo:"
  du -sh "$LOCAL_GIT_DIR"
  echo
}

detect_branch() {
  [[ -n "$BRANCH" ]] && { echo "$BRANCH"; return; }

  local current_branch
  current_branch="$(git branch --show-current 2>/dev/null || true)"
  [[ -n "$current_branch" ]] && { echo "$current_branch"; return; }

  git show-ref --verify --quiet "refs/remotes/origin/4.0.0" && { echo "4.0.0"; return; }
  git show-ref --verify --quiet "refs/remotes/origin/main" && { echo "main"; return; }

  echo ""
}

rebuild_external_gitdir_from_origin() {
  echo "Reconstruyendo gitdir externo local desde origin..."

  [[ -e "$LOCAL_GIT_DIR" ]] && {
    echo "Eliminando gitdir externo incompleto:"
    echo "$LOCAL_GIT_DIR"
    safe_rm_rf "$LOCAL_GIT_DIR"
  }

  echo "Eliminando puntero .git inválido antes de reconstruir..."
  safe_rm_rf "$PROJECT_DIR/.git"

  git init --separate-git-dir="$LOCAL_GIT_DIR"
  git remote add origin "$REMOTE_URL"
  git fetch origin --prune --tags

  BRANCH="$(detect_branch)"
  [[ -n "$BRANCH" ]] || fail "no he podido detectar rama. Pásala como segundo argumento."

  git symbolic-ref HEAD "refs/heads/$BRANCH"
  git update-ref "refs/heads/$BRANCH" "origin/$BRANCH"
  git reset "origin/$BRANCH"
  git branch --set-upstream-to="origin/$BRANCH" "$BRANCH"

  print_verification
  echo "OK: metadata Git reconstruida correctamente en este Mac."
}

move_existing_gitdir_out_of_drive() {
  [[ -e "$LOCAL_GIT_DIR" ]] && fail "ya existe el git destino: $LOCAL_GIT_DIR"

  echo "Limpiando temporales antiguos seguros..."
  find "$LOCAL_GIT_BASE" -maxdepth 1 -name "${PROJECT_NAME}.git.tmp.*" -type d -exec rm -rf {} +

  echo "Eliminando locks obsoletos dentro de .git..."
  find .git -name "*.lock" -type f -print -delete || true

  echo "Quitando flags/atributos extendidos que puedan bloquear la copia..."
  chflags -R nouchg .git 2>/dev/null || true
  xattr -rc .git 2>/dev/null || true
  chmod -R u+rwX .git 2>/dev/null || true

  echo "Comprobando estado actual de Git..."
  git status
  echo

  echo "Copiando .git fuera de Google Drive..."
  mkdir -p "$TMP_GIT_DIR"
  rsync -a --progress --partial --inplace .git/ "$TMP_GIT_DIR/"

  echo
  echo "Verificando integridad del git copiado..."
  GIT_DIR="$TMP_GIT_DIR" GIT_WORK_TREE="$PROJECT_DIR" git fsck --full

  echo
  echo "Activando gitdir externo..."
  mv "$TMP_GIT_DIR" "$LOCAL_GIT_DIR"

  echo "Sustituyendo .git original por archivo puntero..."
  safe_rm_rf "$PROJECT_DIR/.git"
  printf 'gitdir: %s\n' "$LOCAL_GIT_DIR" > "$PROJECT_DIR/.git"

  print_verification
  echo "OK: metadata Git movida correctamente."
}

echo "============================================================"
echo "Moviendo metadata Git fuera de Google Drive"
echo "============================================================"
echo "Proyecto           : $PROJECT_NAME"
echo "Directorio proyecto: $PROJECT_DIR"
echo "Git destino        : $LOCAL_GIT_DIR"
echo "Git temporal       : $TMP_GIT_DIR"
echo "Remote por defecto : $REMOTE_URL"
echo

mkdir -p "$LOCAL_GIT_BASE"

if [[ -f ".git" ]]; then
  echo "Detectado .git como archivo puntero:"
  cat .git
  echo

  if git status >/dev/null 2>&1; then
    echo "OK: el gitdir externo ya existe y funciona."
    print_verification
    exit 0
  fi

  echo "El puntero .git existe, pero el gitdir externo no funciona en este Mac."
  rebuild_external_gitdir_from_origin
  exit 0
fi

if [[ -d ".git" ]]; then
  move_existing_gitdir_out_of_drive
  exit 0
fi

fail ".git no existe o no es válido"